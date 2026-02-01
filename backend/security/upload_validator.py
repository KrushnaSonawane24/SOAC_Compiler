"""
SOAC Upload Validator - Main Orchestrator
==========================================

THE SINGLE ENTRY POINT for all user model uploads.

This module orchestrates all security checks in a defense-in-depth pipeline.
No model can enter the SOAC compiler without passing through this validator.

VALIDATION PIPELINE (executed in order):
    1. Filename sanitization & path traversal detection
    2. Extension whitelist/blocklist check
    3. File size limit enforcement (before saving)
    4. Save to isolated per-job directory
    5. Magic byte validation (detect disguised executables)
    6. MIME type detection (content-based)
    7. Format-specific validation (ONNX checker, HDF5 structure)
    8. SHA-256 hash computation
    9. Return metadata or propagate exception

DESIGN PRINCIPLES:
    - FAIL FAST: Cheap checks first, expensive checks last
    - FAIL LOUD: All failures raise explicit exceptions
    - ALWAYS CLEANUP: Temp directories are cleaned on success AND failure
    - SINGLE ENTRY: secure_save_and_validate() is the ONLY public function
"""

import os
import re
import shutil
import tempfile
import logging
import atexit
import zipfile
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import BinaryIO, Optional, Protocol, runtime_checkable
from contextlib import ExitStack

from .config import (
    MAX_FILE_SIZE_BYTES,
    ALLOWED_EXTENSIONS,
    BLOCKED_EXTENSIONS,
    TEMP_DIR_PREFIX,
    TEMP_DIR_BASE,
    PATH_TRAVERSAL_PATTERNS,
    DANGEROUS_FILENAME_CHARS,
    HASH_CHUNK_SIZE,
)
from .exceptions import (
    SecurityValidationError,
    InvalidFileExtensionError,
    BlockedFileExtensionError,
    FileTooLargeError,
    PathTraversalError,
    InvalidMagicBytesError,
    InvalidMimeTypeError,
    OnnxValidationError,
    H5ValidationError,
    CleanupError,
)
from .hashing import compute_file_hash
from .magic_bytes import (
    validate_magic_bytes,
    is_potentially_executable,
    is_archive,
)
from .mime import validate_mime_type, detect_mime_type

# Conditional import of ONNX validator
try:
    from .onnx_validator import validate_onnx_model, get_onnx_model_info
    ONNX_VALIDATOR_AVAILABLE = True
except ImportError:
    ONNX_VALIDATOR_AVAILABLE = False
    validate_onnx_model = None  # type: ignore
    get_onnx_model_info = None  # type: ignore

# Conditional import of h5py for HDF5 validation
try:
    import h5py
    H5PY_AVAILABLE = True
except ImportError:
    H5PY_AVAILABLE = False
    h5py = None  # type: ignore


# Logger for upload validation events
logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass(frozen=True)
class ValidationMetadata:
    """
    Metadata returned after successful validation.
    
    This dataclass is IMMUTABLE (frozen=True) to prevent accidental modification.
    All fields are guaranteed to be set after successful validation.
    
    Attributes:
        file_path: Absolute path to the validated file in the job directory.
        file_hash: SHA-256 hash of the file (lowercase hex, 64 chars).
        file_size: File size in bytes.
        model_format: Detected format ("onnx", "h5", "keras", "savedmodel").
        original_filename: Original uploaded filename (sanitized).
        mime_type: Detected MIME type.
        validation_timestamp: ISO 8601 timestamp of validation completion.
        job_id: Unique job identifier for this upload.
        model_info: Optional format-specific metadata (e.g., ONNX graph info).
    """
    file_path: Path
    file_hash: str
    file_size: int
    model_format: str
    original_filename: str
    mime_type: str
    validation_timestamp: str
    job_id: str
    model_info: dict = field(default_factory=dict)


@runtime_checkable
class UploadFile(Protocol):
    """
    Protocol for FastAPI UploadFile or similar upload objects.
    
    This allows the validator to work with FastAPI's UploadFile or any
    object that provides a filename and a file-like read interface.
    """
    filename: str
    file: BinaryIO
    
    async def read(self, size: int = -1) -> bytes: ...
    async def seek(self, offset: int) -> None: ...


# =============================================================================
# JOB DIRECTORY MANAGEMENT
# =============================================================================

# Global registry of temp directories for cleanup
_temp_dir_registry: set[Path] = set()


def _register_temp_dir(path: Path) -> None:
    """Register a temp directory for cleanup tracking."""
    _temp_dir_registry.add(path)


def _unregister_temp_dir(path: Path) -> None:
    """Unregister a temp directory from cleanup tracking."""
    _temp_dir_registry.discard(path)


def _cleanup_all_temp_dirs() -> None:
    """Cleanup all registered temp directories on process exit."""
    for path in list(_temp_dir_registry):
        try:
            if path.exists():
                shutil.rmtree(path)
        except Exception as e:
            # Log but don't raise - we're in atexit
            logger.warning(f"Failed to cleanup temp dir {path}: {e}")
        finally:
            _temp_dir_registry.discard(path)


# Register cleanup on process exit
atexit.register(_cleanup_all_temp_dirs)


def create_job_directory(job_id: str) -> Path:
    """
    Create an isolated temporary directory for a specific job.
    
    Each upload gets its own directory to prevent cross-contamination
    between concurrent uploads and ensure clean cleanup.
    
    Args:
        job_id: Unique identifier for the job. Must be alphanumeric.
    
    Returns:
        Path to the created job directory.
    
    Raises:
        ValueError: If job_id contains invalid characters.
    """
    # Sanitize job_id to prevent path injection
    if not re.match(r'^[a-zA-Z0-9_-]+$', job_id):
        raise ValueError(f"Invalid job_id format: {job_id}")
    
    # Create temp directory with job_id suffix
    dir_name = f"{TEMP_DIR_PREFIX}{job_id}"
    
    if TEMP_DIR_BASE is not None:
        job_dir = Path(tempfile.mkdtemp(prefix=dir_name, dir=str(TEMP_DIR_BASE)))
    else:
        job_dir = Path(tempfile.mkdtemp(prefix=dir_name))
    
    _register_temp_dir(job_dir)
    logger.debug(f"Created job directory: {job_dir}")
    
    return job_dir


def cleanup_job_directory(job_dir: Path) -> None:
    """
    Clean up a job directory and all its contents.
    
    This function is safe to call multiple times and handles errors gracefully.
    
    Args:
        job_dir: Path to the job directory to clean up.
    """
    try:
        if job_dir.exists():
            shutil.rmtree(job_dir)
            logger.debug(f"Cleaned up job directory: {job_dir}")
    except Exception as e:
        logger.warning(f"Failed to cleanup job directory {job_dir}: {e}")
        raise CleanupError(str(job_dir), str(e))
    finally:
        _unregister_temp_dir(job_dir)


# =============================================================================
# FILENAME VALIDATION
# =============================================================================

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and injection attacks.
    
    This function:
        1. Removes any directory components (keeps only basename)
        2. Removes dangerous characters
        3. Normalizes whitespace
        4. Limits length
    
    Args:
        filename: The original filename from the upload.
    
    Returns:
        Sanitized filename safe for filesystem use.
    
    Raises:
        PathTraversalError: If path traversal is detected.
    """
    # Check for path traversal patterns BEFORE any processing
    check_path_traversal(filename)
    
    # Extract just the filename (remove any directory components)
    # Use both os.path.basename and pathlib for cross-platform safety
    filename = os.path.basename(filename)
    filename = Path(filename).name
    
    # Remove dangerous characters
    sanitized = ""
    for char in filename:
        if char not in DANGEROUS_FILENAME_CHARS:
            sanitized += char
    
    # Normalize whitespace
    sanitized = re.sub(r'\s+', '_', sanitized)
    
    # Limit length (255 is typical filesystem limit)
    max_length = 200
    if len(sanitized) > max_length:
        # Preserve extension when truncating
        ext = Path(sanitized).suffix
        name = Path(sanitized).stem[:max_length - len(ext)]
        sanitized = name + ext
    
    # Ensure we have a valid filename
    if not sanitized or sanitized.startswith('.'):
        sanitized = f"upload_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    return sanitized


def check_path_traversal(filename: str) -> None:
    """
    Check for path traversal attempts in a filename.
    
    This function MUST be called before any file operations to prevent
    directory escape attacks.
    
    Args:
        filename: The filename to check.
    
    Raises:
        PathTraversalError: If path traversal patterns are detected.
    
    Patterns Detected:
        - ".." (parent directory)
        - Absolute paths (/root, C:\\, etc.)
        - URL-encoded traversal (%2e%2e, etc.)
        - Null bytes (truncation attacks)
    """
    # Convert to lowercase for pattern matching
    filename_lower = filename.lower()
    
    # Check for traversal patterns
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if pattern.lower() in filename_lower:
            raise PathTraversalError(filename, f"Contains forbidden pattern: {pattern!r}")
    
    # Check for absolute paths (Unix)
    if filename.startswith('/'):
        raise PathTraversalError(filename, "Absolute Unix path detected")
    
    # Check for absolute paths (Windows)
    if len(filename) >= 2 and filename[1] == ':':
        raise PathTraversalError(filename, "Absolute Windows path detected")
    
    # Check for UNC paths (Windows network)
    if filename.startswith('\\\\'):
        raise PathTraversalError(filename, "UNC path detected")


# =============================================================================
# EXTENSION VALIDATION
# =============================================================================

def validate_extension(filename: str) -> str:
    """
    Validate that a file's extension is in the allowed whitelist.
    
    This is the FIRST validation step because it's fast and catches
    obvious attack attempts immediately.
    
    Args:
        filename: The filename to validate.
    
    Returns:
        The lowercase extension (e.g., ".onnx").
    
    Raises:
        BlockedFileExtensionError: If extension is explicitly blocked.
        InvalidFileExtensionError: If extension is not in whitelist.
    """
    ext = Path(filename).suffix.lower()
    
    # Check blocklist first (higher severity)
    if ext in BLOCKED_EXTENSIONS:
        raise BlockedFileExtensionError(filename, ext)
    
    # Check whitelist
    if ext not in ALLOWED_EXTENSIONS:
        raise InvalidFileExtensionError(filename, ext)
    
    return ext


# =============================================================================
# SIZE VALIDATION
# =============================================================================

def validate_file_size(size: int, filename: str) -> None:
    """
    Validate that a file does not exceed the maximum allowed size.
    
    This check should be performed BEFORE saving the file to disk
    to prevent disk exhaustion DoS attacks.
    
    Args:
        size: File size in bytes.
        filename: Filename for error reporting.
    
    Raises:
        FileTooLargeError: If size exceeds MAX_FILE_SIZE_BYTES.
    """
    if size > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError(
            filename=filename,
            file_size=size,
            max_size=MAX_FILE_SIZE_BYTES
        )


# =============================================================================
# FORMAT-SPECIFIC VALIDATION
# =============================================================================

def validate_h5_model(file_path: Path) -> dict:
    """
    Validate an HDF5/Keras model file.
    
    Args:
        file_path: Path to the .h5 file.
    
    Returns:
        Dictionary with model metadata.
    
    Raises:
        H5ValidationError: If file is not a valid HDF5 file.
    """
    if not H5PY_AVAILABLE:
        logger.warning("h5py not available, skipping HDF5 structure validation")
        return {"warning": "h5py not installed, deep validation skipped"}
    
    try:
        with h5py.File(str(file_path), 'r') as f:
            # Extract basic structure info
            info = {
                "keys": list(f.keys()),
                "attrs": dict(f.attrs.items()) if f.attrs else {},
            }
            
            # Check for Keras model structure
            if 'model_weights' in f or 'model_config' in f.attrs:
                info["is_keras_model"] = True
            else:
                info["is_keras_model"] = False
                
            return info
            
    except Exception as e:
        raise H5ValidationError(
            filename=file_path.name,
            reason="Failed to parse HDF5 structure",
            original_exception=e
        )


def validate_model_format(file_path: Path, extension: str) -> dict:
    """
    Perform format-specific validation based on file extension.
    
    Args:
        file_path: Path to the saved file.
        extension: Lowercase file extension (e.g., ".onnx").
    
    Returns:
        Dictionary with format-specific metadata.
    
    Raises:
        OnnxValidationError: For invalid ONNX files.
        H5ValidationError: For invalid HDF5 files.
    """
    if extension == ".onnx":
        if ONNX_VALIDATOR_AVAILABLE and validate_onnx_model is not None:
            model = validate_onnx_model(file_path)
            if get_onnx_model_info is not None:
                return get_onnx_model_info(model)
        else:
            logger.warning("ONNX validator not available, skipping graph validation")
            return {"warning": "onnx library not installed, deep validation skipped"}
    
    elif extension in (".h5", ".hdf5"):
        return validate_h5_model(file_path)
    
    elif extension == ".keras":
        # Keras native format is actually a ZIP file
        # We don't extract it, just verify it's a valid archive
        return {"format": "keras_native"}
    
    elif extension == ".tflite":
        return {"format": "tflite"}
    
    return {}


# =============================================================================
# MAIN VALIDATION FUNCTION
# =============================================================================

def secure_save_and_validate_sync(
    file_content: bytes,
    filename: str,
    job_id: str,
) -> ValidationMetadata:
    """
    Synchronous version of the main validation function.
    
    This function:
        1. Sanitizes the filename
        2. Validates extension
        3. Checks file size
        4. Creates isolated job directory
        5. Saves file to disk
        6. Validates magic bytes
        7. Validates MIME type
        8. Performs format-specific validation
        9. Computes SHA-256 hash
        10. Returns metadata
    
    Args:
        file_content: Raw file bytes.
        filename: Original filename from upload.
        job_id: Unique job identifier (alphanumeric).
    
    Returns:
        ValidationMetadata with all file information.
    
    Raises:
        SecurityValidationError: On any validation failure.
    """
    job_dir: Optional[Path] = None
    
    # Use ExitStack to ensure cleanup on ANY exit path
    with ExitStack() as stack:
        try:
            # Step 1: Sanitize filename and check for traversal
            logger.info(f"Starting validation for upload: {filename} (job: {job_id})")
            safe_filename = sanitize_filename(filename)
            
            # Step 2: Validate extension (fast check first)
            extension = validate_extension(safe_filename)
            logger.debug(f"Extension validated: {extension}")
            
            # Step 3: Check file size BEFORE saving
            file_size = len(file_content)
            validate_file_size(file_size, safe_filename)
            logger.debug(f"File size validated: {file_size} bytes")
            
            # Step 4: Create isolated job directory
            job_dir = create_job_directory(job_id)
            # Register cleanup even if we fail later
            stack.callback(lambda: cleanup_job_directory(job_dir) if job_dir else None)
            
            # Step 5: Save file to disk
            file_path = job_dir / safe_filename
            with open(file_path, 'wb') as f:
                f.write(file_content)
            logger.debug(f"File saved to: {file_path}")
            saved_file_path = file_path
            model_path = file_path
            detected_format = extension.lstrip(".")
            
            # Step 6: Validate magic bytes (catches disguised executables)
            if is_potentially_executable(saved_file_path):
                raise InvalidMagicBytesError(
                    filename=safe_filename,
                    expected_format=extension.lstrip('.'),
                    actual_bytes=file_content[:16]
                )
            
            if is_archive(saved_file_path) and extension not in (".keras", ".zip"):
                raise InvalidMagicBytesError(
                    filename=safe_filename,
                    expected_format=extension.lstrip('.'),
                    actual_bytes=file_content[:16]
                )
            
            # For HDF5 files, validate magic bytes explicitly
            if extension in (".h5", ".hdf5"):
                validate_magic_bytes(saved_file_path, "hdf5")
            
            logger.debug("Magic bytes validated")
            
            # Step 7: Validate MIME type
            mime_type = validate_mime_type(saved_file_path, extension)
            logger.debug(f"MIME type validated: {mime_type}")

            if extension == ".zip":
                extract_root = job_dir / "saved_model"
                extract_root.mkdir(exist_ok=True)

                max_members = 5000
                max_total_uncompressed = 250 * 1024 * 1024
                total_uncompressed = 0

                with zipfile.ZipFile(saved_file_path, "r") as zf:
                    infos = zf.infolist()
                    if len(infos) > max_members:
                        raise SecurityValidationError("ZIP contains too many files")

                    for info in infos:
                        name = info.filename
                        if not name:
                            continue
                        if name.startswith(("/", "\\")) or ":" in name:
                            raise SecurityValidationError("ZIP contains invalid paths")
                        parts = Path(name).parts
                        if any(p == ".." for p in parts):
                            raise SecurityValidationError("ZIP contains path traversal")
                        total_uncompressed += int(info.file_size or 0)
                        if total_uncompressed > max_total_uncompressed:
                            raise SecurityValidationError("ZIP expands beyond allowed size")

                    zf.extractall(extract_root)

                candidates = [extract_root] + [p for p in extract_root.iterdir() if p.is_dir()]
                savedmodel_dir = next((p for p in candidates if (p / "saved_model.pb").exists()), None)
                if savedmodel_dir is None:
                    raise SecurityValidationError("ZIP is not a TensorFlow SavedModel (missing saved_model.pb)")

                model_path = savedmodel_dir
                detected_format = "savedmodel"
            
            # Step 8: Format-specific validation
            if detected_format == "savedmodel":
                model_info = {"format": "savedmodel"}
            else:
                model_info = validate_model_format(model_path, extension)
            logger.debug(f"Format-specific validation complete")
            
            # Step 9: Compute SHA-256 hash
            file_hash = compute_file_hash(saved_file_path)
            logger.debug(f"File hash computed: {file_hash[:16]}...")
            
            # Step 10: Build metadata
            timestamp = datetime.now(timezone.utc).isoformat()
            
            metadata = ValidationMetadata(
                file_path=model_path,
                file_hash=file_hash,
                file_size=file_size,
                model_format=detected_format,
                original_filename=safe_filename,
                mime_type=mime_type,
                validation_timestamp=timestamp,
                job_id=job_id,
                model_info=model_info,
            )
            
            logger.info(
                f"Validation successful: {safe_filename} | "
                f"{file_size} bytes | hash: {file_hash[:16]}..."
            )
            
            # Unregister cleanup since we want to keep the directory
            _unregister_temp_dir(job_dir)
            stack.pop_all()  # Cancel the cleanup callback
            
            return metadata
            
        except SecurityValidationError:
            # Re-raise security exceptions as-is
            raise
        except Exception as e:
            # Wrap unexpected exceptions
            logger.error(f"Unexpected error during validation: {e}", exc_info=True)
            raise SecurityValidationError(
                f"Unexpected validation error: {e}",
                context={"filename": filename, "job_id": job_id}
            )


async def secure_save_and_validate(
    upload_file: UploadFile,
    job_id: str,
) -> ValidationMetadata:
    """
    THE SINGLE ENTRY POINT for user model uploads.
    
    This is the ONLY function that should be called from FastAPI routes.
    All other functions in this module are internal implementation details.
    
    Args:
        upload_file: FastAPI UploadFile object from the request.
        job_id: Unique job identifier (alphanumeric, e.g., UUID).
    
    Returns:
        ValidationMetadata containing:
            - file_path: Path to validated file in job directory
            - file_hash: SHA-256 hash (lowercase hex)
            - file_size: Size in bytes
            - model_format: Detected format (onnx/h5/savedmodel)
            - validation_timestamp: ISO 8601 timestamp
    
    Raises:
        SecurityValidationError (or subclass) on ANY validation failure.
    
    Usage:
        @app.post("/upload")
        async def upload_model(file: UploadFile, job_id: str):
            try:
                metadata = await secure_save_and_validate(file, job_id)
                return {"hash": metadata.file_hash, "path": str(metadata.file_path)}
            except SecurityValidationError as e:
                raise HTTPException(400, str(e))
    
    SECURITY GUARANTEES:
        - Path traversal attacks are blocked
        - Executables disguised as models are rejected
        - Archive bombs are rejected
        - Malformed ONNX graphs are rejected
        - Oversized files are rejected before full upload
        - All failures are explicit and logged
    """
    # Read file content (FastAPI UploadFile is async)
    content = await upload_file.read()
    filename = upload_file.filename or "unknown"
    
    # Delegate to sync implementation
    return secure_save_and_validate_sync(content, filename, job_id)
