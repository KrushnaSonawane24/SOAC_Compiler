"""
SOAC File Hashing Module
========================

Provides secure, deterministic SHA-256 hashing for file integrity verification.

WHY SHA-256?
    - Cryptographically secure (no known practical collisions)
    - Standardized and widely supported
    - 256-bit output provides sufficient uniqueness
    - Fast enough for large files with streaming

SECURITY CONSIDERATIONS:
    - Uses streaming to handle large files without memory exhaustion
    - Deterministic: same file always produces same hash
    - Thread-safe (no shared state)
"""

import hashlib
from pathlib import Path
from typing import BinaryIO

from .config import HASH_ALGORITHM, HASH_CHUNK_SIZE


def compute_file_hash(file_path: Path) -> str:
    """
    Compute SHA-256 hash of a file using streaming.
    
    This function reads the file in chunks to avoid loading the entire
    file into memory. This is critical for handling large model files
    without causing memory exhaustion.
    
    Args:
        file_path: Path to the file to hash. Must exist and be readable.
    
    Returns:
        Lowercase hexadecimal string of the SHA-256 hash (64 characters).
    
    Raises:
        FileNotFoundError: If file_path does not exist.
        PermissionError: If file is not readable.
        IOError: If file cannot be read.
    
    Example:
        >>> hash_value = compute_file_hash(Path("/path/to/model.onnx"))
        >>> print(hash_value)
        'a3b2c1d4e5f6...'  # 64 character hex string
    
    Security Notes:
        - This function is deterministic: same file = same hash
        - The hash can be used to detect file tampering
        - The hash can be compared against known-good values
    """
    hasher = hashlib.new(HASH_ALGORITHM)
    
    with open(file_path, "rb") as f:
        _hash_file_object(f, hasher)
    
    return hasher.hexdigest().lower()


def compute_bytes_hash(data: bytes) -> str:
    """
    Compute SHA-256 hash of raw bytes.
    
    Useful for hashing in-memory data without writing to disk first.
    
    Args:
        data: Raw bytes to hash.
    
    Returns:
        Lowercase hexadecimal string of the SHA-256 hash.
    
    Example:
        >>> hash_value = compute_bytes_hash(b"hello world")
        >>> print(hash_value)
        'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'
    """
    hasher = hashlib.new(HASH_ALGORITHM)
    hasher.update(data)
    return hasher.hexdigest().lower()


def compute_stream_hash(stream: BinaryIO) -> str:
    """
    Compute SHA-256 hash from a binary stream.
    
    Reads from the stream's current position to EOF.
    Does NOT reset the stream position after reading.
    
    Args:
        stream: Binary file-like object to read from.
    
    Returns:
        Lowercase hexadecimal string of the SHA-256 hash.
    
    Warning:
        The stream position will be at EOF after this function returns.
        If you need to re-read the stream, seek to the beginning first.
    """
    hasher = hashlib.new(HASH_ALGORITHM)
    _hash_file_object(stream, hasher)
    return hasher.hexdigest().lower()


def _hash_file_object(file_obj: BinaryIO, hasher: "hashlib._Hash") -> None:
    """
    Internal helper to hash a file object in chunks.
    
    This chunked approach ensures:
        - Memory usage is bounded by HASH_CHUNK_SIZE
        - Large files can be processed without OOM
        - I/O is efficient (64KB chunks balance syscalls vs memory)
    
    Args:
        file_obj: Open binary file object positioned at read start.
        hasher: hashlib hash object to update.
    """
    while True:
        chunk = file_obj.read(HASH_CHUNK_SIZE)
        if not chunk:
            break
        hasher.update(chunk)


def verify_file_hash(file_path: Path, expected_hash: str) -> bool:
    """
    Verify that a file matches an expected SHA-256 hash.
    
    This is useful for validating file integrity after transfer or
    comparing against known-good model hashes.
    
    Args:
        file_path: Path to the file to verify.
        expected_hash: Expected lowercase hex hash string.
    
    Returns:
        True if the file's hash matches the expected hash, False otherwise.
    
    Example:
        >>> is_valid = verify_file_hash(
        ...     Path("/path/to/model.onnx"),
        ...     "a3b2c1d4e5f6..."
        ... )
        >>> if not is_valid:
        ...     raise SecurityError("File tampering detected!")
    
    Security Notes:
        - Uses constant-time comparison to prevent timing attacks
        - Normalizes both hashes to lowercase before comparison
    """
    actual_hash = compute_file_hash(file_path)
    
    # Use compare_digest for constant-time comparison (prevents timing attacks)
    import hmac
    return hmac.compare_digest(actual_hash.lower(), expected_hash.lower())
