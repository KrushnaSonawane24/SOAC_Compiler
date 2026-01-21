"""
Tests for MIME Type Detection Module
====================================

Tests verify:
    - MIME detection uses file content, not extension
    - Blocked MIME types are rejected
    - Valid model formats are accepted
"""

import pytest
from pathlib import Path

# Import will fail gracefully if python-magic not installed
try:
    from backend.security.mime import (
        detect_mime_type,
        validate_mime_type,
        is_mime_blocked,
        MAGIC_AVAILABLE,
    )
except ImportError:
    MAGIC_AVAILABLE = False


@pytest.mark.skipif(not MAGIC_AVAILABLE, reason="python-magic not installed")
class TestDetectMimeType:
    """Tests for detect_mime_type function."""
    
    def test_detect_hdf5_mime(self, valid_h5_file: Path):
        """HDF5 files are detected correctly."""
        mime = detect_mime_type(valid_h5_file)
        
        # HDF5 can be detected as various types depending on libmagic version
        valid_mimes = {"application/x-hdf5", "application/x-hdf", "application/octet-stream"}
        assert mime in valid_mimes
    
    def test_detect_generic_binary(self, temp_dir: Path):
        """Random binary data is detected as octet-stream."""
        binary_file = temp_dir / "random.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04\x05")
        
        mime = detect_mime_type(binary_file)
        
        assert mime == "application/octet-stream"
    
    def test_detect_text_file(self, temp_dir: Path):
        """Text content is detected as text/plain."""
        text_file = temp_dir / "readme.txt"
        text_file.write_text("Hello, this is plain text content.")
        
        mime = detect_mime_type(text_file)
        
        assert "text" in mime
    
    def test_ignores_extension(self, temp_dir: Path):
        """MIME detection ignores file extension."""
        # Create a text file with a .exe extension
        fake_exe = temp_dir / "fake.exe"
        fake_exe.write_text("This is actually plain text")
        
        mime = detect_mime_type(fake_exe)
        
        # Should detect as text, not executable
        assert "text" in mime or mime == "application/octet-stream"


@pytest.mark.skipif(not MAGIC_AVAILABLE, reason="python-magic not installed")
class TestValidateMimeType:
    """Tests for validate_mime_type function."""
    
    def test_valid_h5_passes(self, valid_h5_file: Path):
        """Valid H5 file passes MIME validation."""
        # Should not raise
        mime = validate_mime_type(valid_h5_file, ".h5")
        assert mime is not None
    
    def test_exe_content_rejected_as_onnx(self, exe_as_onnx_file: Path):
        """Executable content disguised as .onnx is rejected."""
        from backend.security.exceptions import InvalidMimeTypeError
        
        with pytest.raises(InvalidMimeTypeError) as exc_info:
            validate_mime_type(exe_as_onnx_file, ".onnx")
        
        assert "application" in exc_info.value.detected_mime or "msdos" in exc_info.value.detected_mime.lower()


class TestIsMimeBlocked:
    """Tests for is_mime_blocked function."""
    
    def test_executable_mime_blocked(self):
        """Executable MIME types are blocked."""
        assert is_mime_blocked("application/x-executable") is True
        assert is_mime_blocked("application/x-dosexec") is True
        assert is_mime_blocked("application/x-msdos-program") is True
    
    def test_script_mime_blocked(self):
        """Script MIME types are blocked."""
        assert is_mime_blocked("text/x-python") is True
        assert is_mime_blocked("application/javascript") is True
        assert is_mime_blocked("application/x-sh") is True
    
    def test_octet_stream_not_blocked(self):
        """Generic octet-stream is NOT blocked (used by valid models)."""
        assert is_mime_blocked("application/octet-stream") is False
    
    def test_hdf5_not_blocked(self):
        """HDF5 MIME type is NOT blocked."""
        assert is_mime_blocked("application/x-hdf5") is False
