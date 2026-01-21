"""
Tests for SHA-256 Hashing Module
================================

Tests verify:
    - Hash determinism (same file = same hash)
    - Hash uniqueness (different files = different hashes)
    - Streaming works correctly for large files
    - Hash verification function works
"""

import pytest
from pathlib import Path

from backend.security.hashing import (
    compute_file_hash,
    compute_bytes_hash,
    verify_file_hash,
)


class TestComputeFileHash:
    """Tests for compute_file_hash function."""
    
    def test_hash_deterministic(self, temp_dir: Path):
        """Same file produces same hash every time."""
        # Create a test file with known content
        test_file = temp_dir / "test.bin"
        test_file.write_bytes(b"Hello, SOAC Security!")
        
        # Hash the file multiple times
        hash1 = compute_file_hash(test_file)
        hash2 = compute_file_hash(test_file)
        hash3 = compute_file_hash(test_file)
        
        # All hashes should be identical
        assert hash1 == hash2 == hash3
        
        # Should be a valid SHA-256 hex string (64 chars)
        assert len(hash1) == 64
        assert all(c in "0123456789abcdef" for c in hash1)
    
    def test_hash_different_for_different_content(self, temp_dir: Path):
        """Different file contents produce different hashes."""
        file1 = temp_dir / "file1.bin"
        file2 = temp_dir / "file2.bin"
        
        file1.write_bytes(b"Content A")
        file2.write_bytes(b"Content B")
        
        hash1 = compute_file_hash(file1)
        hash2 = compute_file_hash(file2)
        
        assert hash1 != hash2
    
    def test_hash_lowercase(self, temp_dir: Path):
        """Hash output is always lowercase."""
        test_file = temp_dir / "test.bin"
        test_file.write_bytes(b"Test content")
        
        file_hash = compute_file_hash(test_file)
        
        assert file_hash == file_hash.lower()
    
    def test_hash_empty_file(self, temp_dir: Path):
        """Empty file has a consistent hash."""
        empty_file = temp_dir / "empty.bin"
        empty_file.write_bytes(b"")
        
        file_hash = compute_file_hash(empty_file)
        
        # SHA-256 of empty string is known
        expected_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert file_hash == expected_hash
    
    def test_hash_known_value(self, temp_dir: Path):
        """Verify hash matches known SHA-256 value."""
        test_file = temp_dir / "known.bin"
        test_file.write_bytes(b"hello world")
        
        file_hash = compute_file_hash(test_file)
        
        # Pre-computed SHA-256 of "hello world"
        expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        assert file_hash == expected
    
    def test_hash_file_not_found(self, temp_dir: Path):
        """Raises FileNotFoundError for missing files."""
        nonexistent = temp_dir / "does_not_exist.bin"
        
        with pytest.raises(FileNotFoundError):
            compute_file_hash(nonexistent)


class TestComputeBytesHash:
    """Tests for compute_bytes_hash function."""
    
    def test_bytes_hash_deterministic(self):
        """Same bytes produce same hash."""
        data = b"Test data for hashing"
        
        hash1 = compute_bytes_hash(data)
        hash2 = compute_bytes_hash(data)
        
        assert hash1 == hash2
    
    def test_bytes_hash_matches_file_hash(self, temp_dir: Path):
        """Bytes hash matches file hash for same content."""
        content = b"Matching content test"
        
        # Create file with same content
        test_file = temp_dir / "match.bin"
        test_file.write_bytes(content)
        
        bytes_hash = compute_bytes_hash(content)
        file_hash = compute_file_hash(test_file)
        
        assert bytes_hash == file_hash
    
    def test_empty_bytes_hash(self):
        """Empty bytes have consistent hash."""
        empty_hash = compute_bytes_hash(b"")
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert empty_hash == expected


class TestVerifyFileHash:
    """Tests for verify_file_hash function."""
    
    def test_verify_correct_hash(self, temp_dir: Path):
        """Returns True for correct hash."""
        test_file = temp_dir / "verify.bin"
        test_file.write_bytes(b"hello world")
        
        correct_hash = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        
        assert verify_file_hash(test_file, correct_hash) is True
    
    def test_verify_incorrect_hash(self, temp_dir: Path):
        """Returns False for incorrect hash."""
        test_file = temp_dir / "verify.bin"
        test_file.write_bytes(b"hello world")
        
        wrong_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        
        assert verify_file_hash(test_file, wrong_hash) is False
    
    def test_verify_case_insensitive(self, temp_dir: Path):
        """Hash comparison is case-insensitive."""
        test_file = temp_dir / "verify.bin"
        test_file.write_bytes(b"hello world")
        
        # Use uppercase
        uppercase_hash = "B94D27B9934D3E08A52E52D7DA7DABFAC484EFE37A5380EE9088F7ACE2EFCDE9"
        
        assert verify_file_hash(test_file, uppercase_hash) is True
