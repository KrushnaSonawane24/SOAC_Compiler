"""
SOAC Magic Bytes Validation Module
==================================

Binary signature validation for file format verification.

WHAT ARE MAGIC BYTES?
    Magic bytes (or file signatures) are specific byte sequences at the
    start of files that identify their format. For example:
        - PDF files start with "%PDF"
        - ZIP files start with "PK"
        - EXE files start with "MZ"
        - HDF5 files start with \x89HDF\r\n\x1a\n

WHY VALIDATE MAGIC BYTES?
    - Extension can be changed (model.exe -> model.onnx)
    - MIME detection can be fooled in rare cases
    - Magic bytes are the GROUND TRUTH of file format
    - Explicitly blocks dangerous formats (EXE, ZIP, etc.)

DEFENSE IN DEPTH:
    This is the THIRD layer of file type validation:
        1. Extension whitelist (fast, rejects obvious attacks)
        2. MIME detection (content-based, catches renamed files)
        3. Magic bytes (exact binary match, catches edge cases)
"""

from pathlib import Path
from typing import Optional

from .config import MAGIC_BYTES, BLOCKED_MAGIC_BYTES
from .exceptions import InvalidMagicBytesError


# Maximum bytes to read for magic detection
# Most magic signatures are in the first 16 bytes
MAGIC_READ_SIZE = 32


def read_magic_bytes(file_path: Path, num_bytes: int = MAGIC_READ_SIZE) -> bytes:
    """
    Read the first N bytes of a file for magic byte analysis.
    
    Args:
        file_path: Path to the file to read.
        num_bytes: Number of bytes to read (default: 32).
    
    Returns:
        The first N bytes of the file, or fewer if file is smaller.
    
    Raises:
        FileNotFoundError: If file does not exist.
        PermissionError: If file is not readable.
    """
    with open(file_path, "rb") as f:
        return f.read(num_bytes)


def check_blocked_magic_bytes(file_path: Path) -> Optional[str]:
    """
    Check if a file starts with any BLOCKED magic byte signature.
    
    This function checks for dangerous file types that should NEVER
    be accepted regardless of extension or MIME type.
    
    Args:
        file_path: Path to the file to check.
    
    Returns:
        Name of the blocked format if found, None if file is safe.
    
    Example:
        >>> blocked = check_blocked_magic_bytes(Path("/path/to/malware.onnx"))
        >>> if blocked:
        ...     print(f"Blocked format detected: {blocked}")
        'exe_mz'  # File is actually an EXE
    """
    magic = read_magic_bytes(file_path)
    
    for format_name, signature in BLOCKED_MAGIC_BYTES.items():
        if magic.startswith(signature):
            return format_name
    
    return None


def validate_magic_bytes(file_path: Path, expected_format: str) -> bool:
    """
    Validate that a file's magic bytes match the expected format.
    
    This function performs TWO checks:
        1. Verify file does NOT match any BLOCKED signatures
        2. Verify file DOES match expected format signature (if applicable)
    
    Args:
        file_path: Path to the file to validate.
        expected_format: Expected format key (e.g., "hdf5", "onnx").
    
    Returns:
        True if validation passes.
    
    Raises:
        InvalidMagicBytesError: If magic bytes don't match expected format
                                or if blocked format is detected.
    
    Security Notes:
        - Files with blocked magic bytes are ALWAYS rejected
        - ONNX files don't have fixed magic bytes (protobuf format varies)
          so we only check for blocked signatures
    """
    magic = read_magic_bytes(file_path)
    
    # Step 1: Check if file matches any BLOCKED signatures
    blocked_format = check_blocked_magic_bytes(file_path)
    if blocked_format:
        raise InvalidMagicBytesError(
            filename=file_path.name,
            expected_format=expected_format,
            actual_bytes=magic
        )
    
    # Step 2: For formats with known magic bytes, verify they match
    expected_magic = MAGIC_BYTES.get(expected_format.lower())
    
    if expected_magic is not None:
        if not magic.startswith(expected_magic):
            raise InvalidMagicBytesError(
                filename=file_path.name,
                expected_format=expected_format,
                actual_bytes=magic
            )
    
    # Note: ONNX doesn't have fixed magic bytes (protobuf can start with
    # various bytes depending on the schema). Validation is done via the
    # ONNX library parser instead.
    
    return True


def get_format_from_magic(file_path: Path) -> Optional[str]:
    """
    Attempt to identify file format from magic bytes.
    
    This is the inverse of validate_magic_bytes - it tries to GUESS
    the format based on known signatures.
    
    Args:
        file_path: Path to the file to identify.
    
    Returns:
        Format name if recognized, None if unknown.
    
    Note:
        This function checks BLOCKED formats too and will return their
        names. Callers should check if the returned format is allowed.
    """
    magic = read_magic_bytes(file_path)
    
    # Check allowed formats first
    for format_name, signature in MAGIC_BYTES.items():
        if magic.startswith(signature):
            return format_name
    
    # Check blocked formats (useful for logging what was attempted)
    for format_name, signature in BLOCKED_MAGIC_BYTES.items():
        if magic.startswith(signature):
            return f"BLOCKED:{format_name}"
    
    return None


def is_hdf5_file(file_path: Path) -> bool:
    """
    Check if a file is a valid HDF5 file based on magic bytes.
    
    HDF5 files (including Keras .h5) start with: \x89HDF\r\n\x1a\n
    
    Args:
        file_path: Path to the file to check.
    
    Returns:
        True if file starts with HDF5 magic bytes, False otherwise.
    """
    magic = read_magic_bytes(file_path, 8)
    return magic == MAGIC_BYTES.get("hdf5", b"")


def is_potentially_executable(file_path: Path) -> bool:
    """
    Check if a file appears to be an executable.
    
    This checks for common executable magic bytes:
        - MZ (DOS/Windows EXE)
        - ELF (Linux binary)
        - Mach-O (macOS binary)
    
    Args:
        file_path: Path to the file to check.
    
    Returns:
        True if file appears to be executable, False otherwise.
    
    Use Case:
        Quick check before more expensive validation steps.
        If this returns True, reject immediately.
    """
    magic = read_magic_bytes(file_path, 8)
    
    executable_signatures = [
        b"MZ",              # DOS/Windows
        b"\x7fELF",         # Linux ELF
        b"\xfe\xed\xfa\xce",  # Mach-O 32-bit
        b"\xfe\xed\xfa\xcf",  # Mach-O 64-bit
        b"\xca\xfe\xba\xbe",  # Universal binary / Java class
    ]
    
    for sig in executable_signatures:
        if magic.startswith(sig):
            return True
    
    return False


def is_archive(file_path: Path) -> bool:
    """
    Check if a file appears to be an archive.
    
    Archives are dangerous because:
        - They can contain nested malicious files
        - Zip bombs can exhaust disk space
        - They bypass single-file validation
    
    Args:
        file_path: Path to the file to check.
    
    Returns:
        True if file appears to be an archive, False otherwise.
    """
    magic = read_magic_bytes(file_path, 8)
    
    archive_signatures = [
        b"PK",                      # ZIP/JAR/DOCX/etc
        b"Rar!",                    # RAR
        b"\x52\x61\x72\x21\x1a\x07",  # RAR5
        b"7z\xbc\xaf\x27\x1c",      # 7-Zip
        b"\x1f\x8b",                # GZIP
        b"BZ",                      # BZIP2
        b"\xfd7zXZ",                # XZ
    ]
    
    for sig in archive_signatures:
        if magic.startswith(sig):
            return True
    
    return False
