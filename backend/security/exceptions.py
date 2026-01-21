"""
SOAC Security Exceptions
========================

Custom exception hierarchy for explicit, trackable security failures.

WHY CUSTOM EXCEPTIONS?
    - Generic exceptions like ValueError or IOError can be caught and silently 
      ignored by upstream code. Custom exceptions FORCE explicit handling.
    - Each exception type maps to a specific attack vector, enabling precise 
      security logging and incident response.
    - All exceptions inherit from SecurityValidationError, allowing catch-all 
      handling while preserving granularity.

DESIGN PRINCIPLE:
    Every exception includes a human-readable message AND the original 
    offending value (filename, size, etc.) for forensic logging.
"""

from typing import Optional, Any


class SecurityValidationError(Exception):
    """
    Base exception for ALL security validation failures.
    
    This is the ONLY exception type that should escape the security package.
    Downstream code should catch this to halt the compiler pipeline.
    
    Attributes:
        message: Human-readable error description
        context: Optional dict with forensic details (filename, size, etc.)
    """
    
    def __init__(self, message: str, context: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}
    
    def __str__(self) -> str:
        if self.context:
            context_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"{self.message} [{context_str}]"
        return self.message


class InvalidFileExtensionError(SecurityValidationError):
    """
    Raised when file extension is not in the allowed whitelist.
    
    THREAT MITIGATED:
        Attackers uploading executables (.exe, .dll), scripts (.py, .js, .sh),
        or archives (.zip, .rar) disguised with trusted extensions.
    
    NOTE:
        This is the FIRST check in the validation pipeline. Failing fast on
        extension prevents wasting resources on obviously malicious files.
    """
    
    def __init__(self, filename: str, extension: str):
        super().__init__(
            f"File extension '{extension}' is not allowed",
            context={"filename": filename, "extension": extension}
        )
        self.filename = filename
        self.extension = extension


class BlockedFileExtensionError(SecurityValidationError):
    """
    Raised when file extension is in the EXPLICIT blocklist.
    
    THREAT MITIGATED:
        Direct upload attempts of known dangerous extensions.
        More severe than InvalidFileExtensionError - this indicates
        likely malicious intent rather than user error.
    """
    
    def __init__(self, filename: str, extension: str):
        super().__init__(
            f"File extension '{extension}' is explicitly blocked",
            context={"filename": filename, "extension": extension, "severity": "high"}
        )
        self.filename = filename
        self.extension = extension


class InvalidMimeTypeError(SecurityValidationError):
    """
    Raised when MIME type detection reveals unexpected content.
    
    THREAT MITIGATED:
        Files with spoofed extensions (e.g., EXE renamed to .onnx).
        MIME detection uses libmagic to inspect actual file content,
        not the extension or HTTP Content-Type header.
    
    WHY THIS MATTERS:
        A file named "model.onnx" could actually be an executable.
        MIME detection catches this by reading the file's magic bytes.
    """
    
    def __init__(self, filename: str, detected_mime: str, expected_mimes: list[str]):
        super().__init__(
            f"MIME type '{detected_mime}' does not match expected types",
            context={
                "filename": filename,
                "detected_mime": detected_mime,
                "expected_mimes": expected_mimes
            }
        )
        self.filename = filename
        self.detected_mime = detected_mime
        self.expected_mimes = expected_mimes


class InvalidMagicBytesError(SecurityValidationError):
    """
    Raised when file's magic bytes don't match expected format signature.
    
    THREAT MITIGATED:
        Binary content spoofing. Even if MIME detection passes, we verify
        the exact byte sequence at the file's start matches known formats.
    
    EXAMPLE:
        HDF5 files MUST start with: 0x89 0x48 0x44 0x46 0x0d 0x0a 0x1a 0x0a
        If a file claims to be .h5 but has different magic bytes, it's rejected.
    """
    
    def __init__(self, filename: str, expected_format: str, actual_bytes: bytes):
        # Truncate bytes for logging safety (don't log entire malicious payloads)
        safe_bytes = actual_bytes[:16].hex() if actual_bytes else "empty"
        super().__init__(
            f"Magic bytes do not match expected format '{expected_format}'",
            context={
                "filename": filename,
                "expected_format": expected_format,
                "actual_bytes_hex": safe_bytes
            }
        )
        self.filename = filename
        self.expected_format = expected_format
        self.actual_bytes = actual_bytes


class FileTooLargeError(SecurityValidationError):
    """
    Raised when file exceeds maximum allowed size.
    
    THREAT MITIGATED:
        Denial of Service (DoS) via disk exhaustion. Attackers could upload
        massive files to fill disk space, crash the server, or cause OOM errors.
    
    IMPLEMENTATION NOTE:
        Size is checked BEFORE the full file is written to disk. We read
        the Content-Length header first, then stream with size limits.
    """
    
    def __init__(self, filename: str, file_size: int, max_size: int):
        super().__init__(
            f"File size {file_size:,} bytes exceeds maximum {max_size:,} bytes",
            context={
                "filename": filename,
                "file_size": file_size,
                "max_size": max_size,
                "excess_bytes": file_size - max_size
            }
        )
        self.filename = filename
        self.file_size = file_size
        self.max_size = max_size


class PathTraversalError(SecurityValidationError):
    """
    Raised when filename contains path traversal sequences.
    
    THREAT MITIGATED:
        Directory traversal attacks. Filenames like "../../../etc/passwd" or
        "..\\windows\\system32\\config" could escape the sandbox and overwrite
        system files.
    
    PATTERNS DETECTED:
        - ".." anywhere in the path
        - Absolute paths (/root, C:\\, etc.)
        - Null bytes (truncation attacks)
        - Special characters that could be interpreted by shells
    """
    
    def __init__(self, filename: str, reason: str):
        super().__init__(
            f"Path traversal attempt detected: {reason}",
            context={"filename": filename, "reason": reason, "severity": "critical"}
        )
        self.filename = filename
        self.reason = reason


class OnnxValidationError(SecurityValidationError):
    """
    Raised when ONNX model fails graph integrity validation.
    
    THREAT MITIGATED:
        - Malformed ONNX files that could crash the parser
        - Carefully crafted invalid graphs that exploit parser bugs
        - Files that pass magic byte checks but contain garbage data
    
    VALIDATION PERFORMED:
        - onnx.load() successfully parses the protobuf
        - onnx.checker.check_model() validates graph structure
        - IR version compatibility is verified
    """
    
    def __init__(self, filename: str, reason: str, original_exception: Optional[Exception] = None):
        super().__init__(
            f"ONNX validation failed: {reason}",
            context={
                "filename": filename,
                "reason": reason,
                "original_error": str(original_exception) if original_exception else None
            }
        )
        self.filename = filename
        self.reason = reason
        self.original_exception = original_exception


class H5ValidationError(SecurityValidationError):
    """
    Raised when HDF5/Keras model fails validation.
    
    THREAT MITIGATED:
        - Malformed HDF5 files that could crash the parser
        - Files with valid HDF5 structure but invalid Keras model data
    """
    
    def __init__(self, filename: str, reason: str, original_exception: Optional[Exception] = None):
        super().__init__(
            f"HDF5 validation failed: {reason}",
            context={
                "filename": filename,
                "reason": reason,
                "original_error": str(original_exception) if original_exception else None
            }
        )
        self.filename = filename
        self.reason = reason
        self.original_exception = original_exception


class UnsupportedModelFormatError(SecurityValidationError):
    """
    Raised when model format cannot be determined or is not supported.
    
    ALLOWED FORMATS:
        - .onnx (ONNX Runtime models)
        - .h5 (Keras/TensorFlow models)
        - SavedModel directory (TensorFlow)
    
    NOTE:
        This is a fallback exception. In most cases, either
        InvalidFileExtensionError or InvalidMagicBytesError will be raised first.
    """
    
    def __init__(self, filename: str, detected_type: Optional[str] = None):
        super().__init__(
            f"Unsupported model format",
            context={"filename": filename, "detected_type": detected_type}
        )
        self.filename = filename
        self.detected_type = detected_type


class CleanupError(SecurityValidationError):
    """
    Raised when temporary file/directory cleanup fails.
    
    SEVERITY: Warning (non-fatal)
    
    This exception is logged but typically not propagated, as the main
    validation has already completed. However, repeated cleanup failures
    indicate a resource leak that should be investigated.
    """
    
    def __init__(self, path: str, reason: str):
        super().__init__(
            f"Cleanup failed for path: {reason}",
            context={"path": path, "reason": reason}
        )
        self.path = path
        self.reason = reason
