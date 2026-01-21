"""
SOAC MIME Type Detection Module
===============================

Content-based MIME type detection using libmagic.

WHY NOT TRUST HTTP CONTENT-TYPE HEADERS?
    - HTTP headers are set by the CLIENT and can be trivially spoofed
    - An attacker can upload an EXE with Content-Type: application/octet-stream
    - We MUST inspect the actual file content to determine true type

WHY LIBMAGIC?
    - Industry standard for file type detection (used by the `file` command)
    - Inspects actual file content, not just extension
    - Comprehensive database of file signatures
    - Battle-tested and widely deployed

SECURITY CONSIDERATIONS:
    - Never trust the filename extension alone
    - Never trust HTTP Content-Type header
    - Always verify content matches expected MIME type for the claimed format
"""

from pathlib import Path
from typing import Optional

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None  # type: ignore

from .config import ALLOWED_MIME_TYPES, BLOCKED_MIME_TYPES
from .exceptions import InvalidMimeTypeError


def detect_mime_type(file_path: Path) -> str:
    """
    Detect MIME type of a file using libmagic (content-based detection).
    
    This function inspects the actual file content to determine its type,
    completely ignoring the file extension and any HTTP headers.
    
    Args:
        file_path: Path to the file to analyze. Must exist and be readable.
    
    Returns:
        MIME type string (e.g., "application/octet-stream", "application/x-hdf5").
    
    Raises:
        RuntimeError: If python-magic is not installed.
        FileNotFoundError: If file does not exist.
        PermissionError: If file is not readable.
    
    Example:
        >>> mime = detect_mime_type(Path("/path/to/model.onnx"))
        >>> print(mime)
        'application/octet-stream'
    
    Security Notes:
        - This function NEVER looks at the file extension
        - This function NEVER trusts HTTP headers
        - The returned MIME type is based solely on file content
    """
    if not MAGIC_AVAILABLE:
        raise RuntimeError(
            "python-magic is required for MIME detection. "
            "Install with: pip install python-magic-bin (Windows) or "
            "pip install python-magic (Linux/macOS)"
        )
    
    # Use magic.from_file with mime=True to get MIME type
    # This inspects the file content, not the extension
    mime_type = magic.from_file(str(file_path), mime=True)
    
    return mime_type


def validate_mime_type(file_path: Path, expected_extension: str) -> str:
    """
    Validate that a file's MIME type matches what's expected for its extension.
    
    This function:
        1. Detects the actual MIME type via libmagic
        2. Checks if the MIME type is in the BLOCKED list (always rejected)
        3. Checks if the MIME type matches expected types for the extension
    
    Args:
        file_path: Path to the file to validate.
        expected_extension: The file extension (e.g., ".onnx", ".h5").
    
    Returns:
        The detected MIME type if validation passes.
    
    Raises:
        InvalidMimeTypeError: If MIME type doesn't match expected types.
    
    Example:
        >>> mime = validate_mime_type(Path("/path/to/model.onnx"), ".onnx")
        >>> print(mime)
        'application/octet-stream'
    """
    detected_mime = detect_mime_type(file_path)
    
    # Check blocklist first (these are NEVER allowed)
    if detected_mime in BLOCKED_MIME_TYPES:
        raise InvalidMimeTypeError(
            filename=file_path.name,
            detected_mime=detected_mime,
            expected_mimes=list(ALLOWED_MIME_TYPES.get(expected_extension, set()))
        )
    
    # Get allowed MIME types for this extension
    allowed_mimes = ALLOWED_MIME_TYPES.get(expected_extension.lower())
    
    if allowed_mimes is None:
        # Extension not in our allowed list - this shouldn't happen
        # if extension validation ran first, but handle it gracefully
        raise InvalidMimeTypeError(
            filename=file_path.name,
            detected_mime=detected_mime,
            expected_mimes=[]
        )
    
    # Check if detected MIME is in allowed set
    if detected_mime not in allowed_mimes:
        raise InvalidMimeTypeError(
            filename=file_path.name,
            detected_mime=detected_mime,
            expected_mimes=list(allowed_mimes)
        )
    
    return detected_mime


def is_mime_blocked(mime_type: str) -> bool:
    """
    Check if a MIME type is in the blocklist.
    
    Args:
        mime_type: MIME type string to check.
    
    Returns:
        True if the MIME type is blocked, False otherwise.
    """
    return mime_type in BLOCKED_MIME_TYPES


def get_mime_description(file_path: Path) -> str:
    """
    Get a human-readable description of a file's type.
    
    Unlike detect_mime_type which returns a MIME string, this returns
    a descriptive string like "JPEG image data" or "ELF 64-bit executable".
    
    Useful for logging and error messages.
    
    Args:
        file_path: Path to the file to describe.
    
    Returns:
        Human-readable description of the file type.
    """
    if not MAGIC_AVAILABLE:
        raise RuntimeError("python-magic is required for MIME detection.")
    
    # Without mime=True, magic returns a description
    return magic.from_file(str(file_path), mime=False)
