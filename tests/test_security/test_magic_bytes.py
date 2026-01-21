"""
Tests for Magic Bytes Validation Module
=======================================

Tests verify:
    - Blocked magic bytes (EXE, ZIP, etc.) are detected
    - Valid HDF5 files pass magic byte checks
    - Disguised executables are caught
"""

import pytest
from pathlib import Path

from backend.security.magic_bytes import (
    read_magic_bytes,
    check_blocked_magic_bytes,
    validate_magic_bytes,
    get_format_from_magic,
    is_hdf5_file,
    is_potentially_executable,
    is_archive,
)
from backend.security.exceptions import InvalidMagicBytesError


class TestReadMagicBytes:
    """Tests for read_magic_bytes function."""
    
    def test_read_first_bytes(self, temp_dir: Path):
        """Reads the correct number of bytes from file start."""
        test_file = temp_dir / "test.bin"
        test_file.write_bytes(b"ABCDEFGHIJ0123456789")
        
        magic = read_magic_bytes(test_file, 5)
        
        assert magic == b"ABCDE"
    
    def test_read_default_size(self, temp_dir: Path):
        """Default read size is 32 bytes."""
        content = b"X" * 100
        test_file = temp_dir / "test.bin"
        test_file.write_bytes(content)
        
        magic = read_magic_bytes(test_file)
        
        assert len(magic) == 32
    
    def test_read_small_file(self, temp_dir: Path):
        """Smaller files return whatever is available."""
        test_file = temp_dir / "small.bin"
        test_file.write_bytes(b"ABC")
        
        magic = read_magic_bytes(test_file, 32)
        
        assert magic == b"ABC"


class TestCheckBlockedMagicBytes:
    """Tests for check_blocked_magic_bytes function."""
    
    def test_exe_detected(self, exe_as_onnx_file: Path):
        """Windows executable magic bytes are detected."""
        result = check_blocked_magic_bytes(exe_as_onnx_file)
        
        assert result == "exe_mz"
    
    def test_zip_detected(self, zip_as_onnx_file: Path):
        """ZIP archive magic bytes are detected."""
        result = check_blocked_magic_bytes(zip_as_onnx_file)
        
        assert result == "zip"
    
    def test_elf_detected(self, temp_dir: Path, elf_bytes: bytes):
        """Linux ELF executable is detected."""
        elf_file = temp_dir / "binary.onnx"
        elf_file.write_bytes(elf_bytes)
        
        result = check_blocked_magic_bytes(elf_file)
        
        assert result == "elf"
    
    def test_valid_hdf5_not_blocked(self, valid_h5_file: Path):
        """Valid HDF5 file is NOT blocked."""
        result = check_blocked_magic_bytes(valid_h5_file)
        
        assert result is None
    
    def test_random_bytes_not_blocked(self, temp_dir: Path):
        """Random bytes that don't match any signature are not blocked."""
        random_file = temp_dir / "random.bin"
        random_file.write_bytes(b"\x42\x43\x44\x45" * 10)
        
        result = check_blocked_magic_bytes(random_file)
        
        assert result is None


class TestValidateMagicBytes:
    """Tests for validate_magic_bytes function."""
    
    def test_valid_hdf5_passes(self, valid_h5_file: Path):
        """Valid HDF5 file passes magic byte validation."""
        result = validate_magic_bytes(valid_h5_file, "hdf5")
        
        assert result is True
    
    def test_exe_as_hdf5_fails(self, exe_as_onnx_file: Path):
        """EXE disguised as HDF5 fails validation."""
        with pytest.raises(InvalidMagicBytesError):
            validate_magic_bytes(exe_as_onnx_file, "hdf5")
    
    def test_zip_as_onnx_fails(self, zip_as_onnx_file: Path):
        """ZIP disguised as ONNX fails validation."""
        with pytest.raises(InvalidMagicBytesError):
            validate_magic_bytes(zip_as_onnx_file, "onnx")


class TestGetFormatFromMagic:
    """Tests for get_format_from_magic function."""
    
    def test_identifies_hdf5(self, valid_h5_file: Path):
        """Correctly identifies HDF5 format."""
        fmt = get_format_from_magic(valid_h5_file)
        
        assert fmt == "hdf5"
    
    def test_identifies_blocked_exe(self, exe_as_onnx_file: Path):
        """Identifies blocked EXE format."""
        fmt = get_format_from_magic(exe_as_onnx_file)
        
        assert fmt == "BLOCKED:exe_mz"
    
    def test_identifies_blocked_zip(self, zip_as_onnx_file: Path):
        """Identifies blocked ZIP format."""
        fmt = get_format_from_magic(zip_as_onnx_file)
        
        assert fmt == "BLOCKED:zip"


class TestIsHdf5File:
    """Tests for is_hdf5_file function."""
    
    def test_valid_hdf5_true(self, valid_h5_file: Path):
        """Returns True for valid HDF5 files."""
        assert is_hdf5_file(valid_h5_file) is True
    
    def test_exe_false(self, exe_as_onnx_file: Path):
        """Returns False for EXE files."""
        assert is_hdf5_file(exe_as_onnx_file) is False


class TestIsPotentiallyExecutable:
    """Tests for is_potentially_executable function."""
    
    def test_exe_detected(self, exe_as_onnx_file: Path):
        """Windows EXE is detected as executable."""
        assert is_potentially_executable(exe_as_onnx_file) is True
    
    def test_elf_detected(self, temp_dir: Path, elf_bytes: bytes):
        """Linux ELF is detected as executable."""
        elf_file = temp_dir / "binary"
        elf_file.write_bytes(elf_bytes)
        
        assert is_potentially_executable(elf_file) is True
    
    def test_hdf5_not_executable(self, valid_h5_file: Path):
        """HDF5 files are NOT detected as executable."""
        assert is_potentially_executable(valid_h5_file) is False


class TestIsArchive:
    """Tests for is_archive function."""
    
    def test_zip_detected(self, zip_as_onnx_file: Path):
        """ZIP files are detected as archives."""
        assert is_archive(zip_as_onnx_file) is True
    
    def test_hdf5_not_archive(self, valid_h5_file: Path):
        """HDF5 files are NOT detected as archives."""
        assert is_archive(valid_h5_file) is False
