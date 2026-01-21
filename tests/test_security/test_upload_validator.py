"""
Tests for Upload Validator - Integration Tests
==============================================

These are the CRITICAL tests that verify the complete validation pipeline.

Tests verify ALL mandatory security requirements:
    1. Executable renamed as .onnx is rejected
    2. Corrupt ONNX graph is rejected
    3. Oversized file is rejected
    4. Valid ONNX passes
    5. Hash is deterministic
    6. Path traversal attempts fail
    7. Blocked extensions are rejected
    8. Cleanup happens on failure
"""

import pytest
import asyncio
from pathlib import Path

from backend.security.upload_validator import (
    secure_save_and_validate,
    secure_save_and_validate_sync,
    sanitize_filename,
    check_path_traversal,
    validate_extension,
    validate_file_size,
    create_job_directory,
    cleanup_job_directory,
    ValidationMetadata,
)
from backend.security.exceptions import (
    SecurityValidationError,
    InvalidFileExtensionError,
    BlockedFileExtensionError,
    FileTooLargeError,
    PathTraversalError,
    InvalidMagicBytesError,
    OnnxValidationError,
)
from backend.security.config import MAX_FILE_SIZE_BYTES

# Import MockUploadFile from conftest
from .conftest import MockUploadFile


# =============================================================================
# PATH TRAVERSAL TESTS
# =============================================================================

class TestPathTraversalProtection:
    """Tests for path traversal attack prevention."""
    
    def test_parent_directory_rejected(self):
        """Filenames with '..' are rejected."""
        with pytest.raises(PathTraversalError):
            check_path_traversal("../../../etc/passwd")
    
    def test_windows_traversal_rejected(self):
        """Windows-style path traversal is rejected."""
        with pytest.raises(PathTraversalError):
            check_path_traversal("..\\..\\windows\\system32")
    
    def test_absolute_unix_path_rejected(self):
        """Absolute Unix paths are rejected."""
        with pytest.raises(PathTraversalError):
            check_path_traversal("/etc/passwd")
    
    def test_absolute_windows_path_rejected(self):
        """Absolute Windows paths are rejected."""
        with pytest.raises(PathTraversalError):
            check_path_traversal("C:\\Windows\\System32\\config")
    
    def test_unc_path_rejected(self):
        """UNC network paths are rejected."""
        with pytest.raises(PathTraversalError):
            check_path_traversal("\\\\server\\share\\file.onnx")
    
    def test_url_encoded_traversal_rejected(self):
        """URL-encoded traversal is rejected."""
        with pytest.raises(PathTraversalError):
            check_path_traversal("%2e%2e%2fpasswd")
    
    def test_null_byte_rejected(self):
        """Null byte injection is rejected."""
        with pytest.raises(PathTraversalError):
            check_path_traversal("valid.onnx\x00.txt")
    
    def test_normal_filename_passes(self):
        """Normal filenames pass validation."""
        # Should not raise
        check_path_traversal("model.onnx")
        check_path_traversal("my_model_v1.h5")
        check_path_traversal("tensorflow-saved-model.keras")


class TestFilenameSanitization:
    """Tests for filename sanitization."""
    
    def test_preserves_normal_filename(self):
        """Normal filenames are preserved."""
        result = sanitize_filename("model.onnx")
        assert result == "model.onnx"
    
    def test_removes_dangerous_chars(self):
        """Dangerous characters are removed."""
        result = sanitize_filename("model|foo;bar.onnx")
        assert "|" not in result
        assert ";" not in result
    
    def test_normalizes_whitespace(self):
        """Multiple spaces become underscores."""
        result = sanitize_filename("my   model   here.onnx")
        assert "   " not in result
        assert "_" in result
    
    def test_strips_directory_components(self):
        """Directory components are stripped."""
        result = sanitize_filename("path/to/model.onnx")
        assert "/" not in result
        assert result == "model.onnx"


# =============================================================================
# EXTENSION VALIDATION TESTS
# =============================================================================

class TestExtensionValidation:
    """Tests for file extension whitelist/blocklist."""
    
    def test_onnx_allowed(self):
        """ONNX extension is allowed."""
        ext = validate_extension("model.onnx")
        assert ext == ".onnx"
    
    def test_h5_allowed(self):
        """H5 extension is allowed."""
        ext = validate_extension("model.h5")
        assert ext == ".h5"
    
    def test_hdf5_allowed(self):
        """HDF5 extension is allowed."""
        ext = validate_extension("model.hdf5")
        assert ext == ".hdf5"
    
    def test_keras_allowed(self):
        """Keras extension is allowed."""
        ext = validate_extension("model.keras")
        assert ext == ".keras"
    
    def test_exe_blocked(self):
        """EXE extension is blocked with high severity."""
        with pytest.raises(BlockedFileExtensionError) as exc_info:
            validate_extension("malware.exe")
        
        assert exc_info.value.extension == ".exe"
    
    def test_py_blocked(self):
        """Python extension is blocked."""
        with pytest.raises(BlockedFileExtensionError):
            validate_extension("script.py")
    
    def test_bat_blocked(self):
        """Batch extension is blocked."""
        with pytest.raises(BlockedFileExtensionError):
            validate_extension("script.bat")
    
    def test_zip_blocked(self):
        """ZIP extension is blocked."""
        with pytest.raises(BlockedFileExtensionError):
            validate_extension("archive.zip")
    
    def test_unknown_extension_rejected(self):
        """Unknown extensions are rejected (not blocked, just not allowed)."""
        with pytest.raises(InvalidFileExtensionError):
            validate_extension("file.xyz")
    
    def test_case_insensitive(self):
        """Extension validation is case-insensitive."""
        ext = validate_extension("MODEL.ONNX")
        assert ext == ".onnx"


# =============================================================================
# SIZE VALIDATION TESTS
# =============================================================================

class TestSizeValidation:
    """Tests for file size limits."""
    
    def test_normal_size_passes(self):
        """Files under 50MB pass."""
        # 10MB - should pass
        validate_file_size(10 * 1024 * 1024, "model.onnx")
    
    def test_at_limit_passes(self):
        """Files exactly at limit pass."""
        validate_file_size(MAX_FILE_SIZE_BYTES, "model.onnx")
    
    def test_over_limit_rejected(self):
        """Files over 50MB are rejected."""
        size = MAX_FILE_SIZE_BYTES + 1
        
        with pytest.raises(FileTooLargeError) as exc_info:
            validate_file_size(size, "huge.onnx")
        
        assert exc_info.value.file_size == size
        assert exc_info.value.max_size == MAX_FILE_SIZE_BYTES
    
    def test_oversized_bytes_rejected(self, oversized_bytes: bytes):
        """51MB file is rejected."""
        with pytest.raises(FileTooLargeError):
            validate_file_size(len(oversized_bytes), "huge.onnx")


# =============================================================================
# JOB DIRECTORY TESTS
# =============================================================================

class TestJobDirectory:
    """Tests for job directory management."""
    
    def test_creates_isolated_directory(self, test_job_id: str):
        """Creates a directory with job ID in the name."""
        job_dir = create_job_directory(test_job_id)
        
        try:
            assert job_dir.exists()
            assert job_dir.is_dir()
            assert test_job_id in str(job_dir)
        finally:
            cleanup_job_directory(job_dir)
    
    def test_cleanup_removes_directory(self, test_job_id: str):
        """Cleanup removes the job directory."""
        job_dir = create_job_directory(test_job_id)
        assert job_dir.exists()
        
        cleanup_job_directory(job_dir)
        
        assert not job_dir.exists()
    
    def test_invalid_job_id_rejected(self):
        """Invalid job IDs are rejected."""
        with pytest.raises(ValueError):
            create_job_directory("../../../etc")
        
        with pytest.raises(ValueError):
            create_job_directory("job;rm -rf /")


# =============================================================================
# INTEGRATION TESTS - SYNC VERSION
# =============================================================================

class TestSecureSaveAndValidateSync:
    """Integration tests for the synchronous validation function."""
    
    def test_valid_onnx_passes(self, valid_onnx_bytes: bytes, test_job_id: str):
        """Valid ONNX model passes all validation."""
        metadata = secure_save_and_validate_sync(
            file_content=valid_onnx_bytes,
            filename="model.onnx",
            job_id=test_job_id,
        )
        
        try:
            assert isinstance(metadata, ValidationMetadata)
            assert metadata.file_path.exists()
            assert metadata.model_format == "onnx"
            assert len(metadata.file_hash) == 64
            assert metadata.file_size == len(valid_onnx_bytes)
            assert metadata.job_id == test_job_id
        finally:
            cleanup_job_directory(metadata.file_path.parent)
    
    def test_valid_h5_passes(self, valid_h5_bytes: bytes, test_job_id: str):
        """Valid H5 model passes all validation."""
        metadata = secure_save_and_validate_sync(
            file_content=valid_h5_bytes,
            filename="model.h5",
            job_id=test_job_id + "_h5",
        )
        
        try:
            assert isinstance(metadata, ValidationMetadata)
            assert metadata.model_format == "h5"
        finally:
            cleanup_job_directory(metadata.file_path.parent)
    
    def test_exe_renamed_as_onnx_rejected(self, exe_bytes: bytes, test_job_id: str):
        """EXE file renamed to .onnx is rejected."""
        with pytest.raises(InvalidMagicBytesError):
            secure_save_and_validate_sync(
                file_content=exe_bytes,
                filename="malicious.onnx",
                job_id=test_job_id,
            )
    
    def test_zip_renamed_as_onnx_rejected(self, zip_bytes: bytes, test_job_id: str):
        """ZIP file renamed to .onnx is rejected."""
        with pytest.raises(InvalidMagicBytesError):
            secure_save_and_validate_sync(
                file_content=zip_bytes,
                filename="archive.onnx",
                job_id=test_job_id,
            )
    
    def test_corrupt_onnx_rejected(self, corrupt_onnx_bytes: bytes, test_job_id: str):
        """Corrupt ONNX file is rejected."""
        with pytest.raises(OnnxValidationError):
            secure_save_and_validate_sync(
                file_content=corrupt_onnx_bytes,
                filename="corrupt.onnx",
                job_id=test_job_id,
            )
    
    def test_oversized_rejected(self, test_job_id: str):
        """Oversized file is rejected BEFORE full save."""
        # Create 51MB of data
        huge_content = b"\x00" * (51 * 1024 * 1024)
        
        with pytest.raises(FileTooLargeError):
            secure_save_and_validate_sync(
                file_content=huge_content,
                filename="huge.onnx",
                job_id=test_job_id,
            )
    
    def test_blocked_extension_rejected(self, test_job_id: str):
        """Files with blocked extensions are rejected."""
        with pytest.raises(BlockedFileExtensionError):
            secure_save_and_validate_sync(
                file_content=b"print('hello')",
                filename="script.py",
                job_id=test_job_id,
            )
    
    def test_path_traversal_rejected(self, valid_onnx_bytes: bytes, test_job_id: str):
        """Path traversal in filename is rejected."""
        with pytest.raises(PathTraversalError):
            secure_save_and_validate_sync(
                file_content=valid_onnx_bytes,
                filename="../../../etc/passwd.onnx",
                job_id=test_job_id,
            )
    
    def test_hash_is_deterministic(self, valid_onnx_bytes: bytes, test_job_id: str):
        """Same content produces same hash."""
        metadata1 = secure_save_and_validate_sync(
            file_content=valid_onnx_bytes,
            filename="model1.onnx",
            job_id=test_job_id + "_1",
        )
        
        metadata2 = secure_save_and_validate_sync(
            file_content=valid_onnx_bytes,
            filename="model2.onnx",
            job_id=test_job_id + "_2",
        )
        
        try:
            assert metadata1.file_hash == metadata2.file_hash
        finally:
            cleanup_job_directory(metadata1.file_path.parent)
            cleanup_job_directory(metadata2.file_path.parent)


# =============================================================================
# INTEGRATION TESTS - ASYNC VERSION
# =============================================================================

class TestSecureSaveAndValidateAsync:
    """Integration tests for the async validation function."""
    
    @pytest.mark.asyncio
    async def test_valid_onnx_passes_async(self, valid_onnx_bytes: bytes, test_job_id: str):
        """Valid ONNX passes async validation."""
        upload = MockUploadFile(filename="model.onnx", content=valid_onnx_bytes)
        
        metadata = await secure_save_and_validate(upload, test_job_id + "_async")
        
        try:
            assert isinstance(metadata, ValidationMetadata)
            assert metadata.file_path.exists()
            assert metadata.model_format == "onnx"
        finally:
            cleanup_job_directory(metadata.file_path.parent)
    
    @pytest.mark.asyncio
    async def test_exe_rejected_async(self, exe_bytes: bytes, test_job_id: str):
        """EXE disguised as ONNX is rejected in async."""
        upload = MockUploadFile(filename="malware.onnx", content=exe_bytes)
        
        with pytest.raises(InvalidMagicBytesError):
            await secure_save_and_validate(upload, test_job_id + "_async_exe")


# =============================================================================
# CLEANUP TESTS
# =============================================================================

class TestCleanupOnFailure:
    """Tests verifying cleanup happens on validation failure."""
    
    def test_cleanup_on_validation_failure(self, exe_bytes: bytes):
        """Job directory is cleaned up when validation fails."""
        job_id = "cleanup_test_12345"
        
        # This should fail and clean up
        try:
            secure_save_and_validate_sync(
                file_content=exe_bytes,
                filename="malware.onnx",
                job_id=job_id,
            )
        except SecurityValidationError:
            pass  # Expected
        
        # Verify no orphaned directories with this job_id exist
        import tempfile
        temp_base = Path(tempfile.gettempdir())
        matching_dirs = list(temp_base.glob(f"*{job_id}*"))
        
        # All matching directories should have been cleaned up
        assert len(matching_dirs) == 0
