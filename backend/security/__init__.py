"""
SOAC Security Package
=====================

Secure Model Upload & Validation Unit for the Self-Optimizing AI Compiler.

This package provides defense-in-depth security for all user model uploads.
NO MODEL can enter the SOAC compiler without passing through this validation.

PUBLIC API:
    - secure_save_and_validate(upload_file, job_id) -> ValidationMetadata
      THE ONLY function external code should call.

EXCEPTION HIERARCHY:
    - SecurityValidationError (base)
        - InvalidFileExtensionError
        - BlockedFileExtensionError  
        - InvalidMimeTypeError
        - InvalidMagicBytesError
        - FileTooLargeError
        - PathTraversalError
        - OnnxValidationError
        - H5ValidationError
        - UnsupportedModelFormatError

USAGE:
    from backend.security import secure_save_and_validate, SecurityValidationError
    
    try:
        metadata = await secure_save_and_validate(upload_file, job_id)
        print(f"Validated: {metadata.file_hash}")
    except SecurityValidationError as e:
        print(f"Security check failed: {e}")

For more details, see: backend/security/README.md
"""

# Public API - THE ONLY ENTRY POINT
from .upload_validator import (
    secure_save_and_validate,
    secure_save_and_validate_sync,
    ValidationMetadata,
    create_job_directory,
    cleanup_job_directory,
)

# Exceptions - for structured error handling
from .exceptions import (
    SecurityValidationError,
    InvalidFileExtensionError,
    BlockedFileExtensionError,
    InvalidMimeTypeError,
    InvalidMagicBytesError,
    FileTooLargeError,
    PathTraversalError,
    OnnxValidationError,
    H5ValidationError,
    UnsupportedModelFormatError,
    CleanupError,
)

# Configuration - for inspection/testing only
from .config import (
    MAX_FILE_SIZE_BYTES,
    MAX_FILE_SIZE_MB,
    ALLOWED_EXTENSIONS,
    BLOCKED_EXTENSIONS,
)

# Version
__version__ = "1.0.0"

# Explicit public API
__all__ = [
    # Main function
    "secure_save_and_validate",
    "secure_save_and_validate_sync",
    "ValidationMetadata",
    
    # Directory management
    "create_job_directory",
    "cleanup_job_directory",
    
    # Base exception
    "SecurityValidationError",
    
    # Specific exceptions
    "InvalidFileExtensionError",
    "BlockedFileExtensionError",
    "InvalidMimeTypeError",
    "InvalidMagicBytesError",
    "FileTooLargeError",
    "PathTraversalError",
    "OnnxValidationError",
    "H5ValidationError",
    "UnsupportedModelFormatError",
    "CleanupError",
    
    # Configuration (read-only)
    "MAX_FILE_SIZE_BYTES",
    "MAX_FILE_SIZE_MB",
    "ALLOWED_EXTENSIONS",
    "BLOCKED_EXTENSIONS",
]
