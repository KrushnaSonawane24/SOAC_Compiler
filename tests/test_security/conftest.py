"""
Pytest Fixtures for Security Tests
===================================

Shared fixtures for creating test files, mock uploads, and cleanup.
All fixtures are deterministic and work offline.
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Generator
from dataclasses import dataclass
from io import BytesIO

import pytest


# =============================================================================
# MOCK UPLOAD FILE
# =============================================================================

@dataclass
class MockUploadFile:
    """
    Mock FastAPI UploadFile for testing.
    
    Matches the UploadFile protocol expected by secure_save_and_validate:
        - filename: str
        - file: BinaryIO
        - async read() -> bytes
        - async seek(offset) -> None
    """
    filename: str
    content: bytes
    
    def __post_init__(self):
        self._file = BytesIO(self.content)
    
    @property
    def file(self) -> BytesIO:
        return self._file
    
    async def read(self, size: int = -1) -> bytes:
        if size == -1:
            self._file.seek(0)
            return self._file.read()
        return self._file.read(size)
    
    async def seek(self, offset: int) -> None:
        self._file.seek(offset)


# =============================================================================
# DIRECTORY FIXTURES
# =============================================================================

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory that is cleaned up after the test."""
    dir_path = Path(tempfile.mkdtemp(prefix="test_security_"))
    yield dir_path
    # Cleanup
    if dir_path.exists():
        shutil.rmtree(dir_path)


@pytest.fixture
def test_job_id() -> str:
    """Generate a consistent test job ID."""
    return "test_job_12345"


# =============================================================================
# VALID MODEL FILES
# =============================================================================

@pytest.fixture
def valid_onnx_bytes() -> bytes:
    """
    Generate minimal valid ONNX model bytes.
    
    This creates a simple ONNX model with:
        - 1 input (float32, shape [1, 3])
        - 1 output (same as input)
        - 1 Identity node
    """
    try:
        import onnx
        from onnx import helper, TensorProto
        
        # Create input tensor
        X = helper.make_tensor_value_info('X', TensorProto.FLOAT, [1, 3])
        
        # Create output tensor
        Y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, [1, 3])
        
        # Create Identity node
        identity_node = helper.make_node(
            'Identity',
            inputs=['X'],
            outputs=['Y'],
            name='identity_node'
        )
        
        # Create graph
        graph = helper.make_graph(
            [identity_node],
            'test_graph',
            [X],
            [Y]
        )
        
        # Create model
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 13)])
        model.ir_version = 7
        
        # Serialize to bytes
        return model.SerializeToString()
        
    except ImportError:
        pytest.skip("onnx library not installed")


@pytest.fixture
def valid_onnx_file(temp_dir: Path, valid_onnx_bytes: bytes) -> Path:
    """Create a valid ONNX file in the temp directory."""
    file_path = temp_dir / "valid_model.onnx"
    file_path.write_bytes(valid_onnx_bytes)
    return file_path


@pytest.fixture  
def valid_h5_bytes() -> bytes:
    """
    Generate minimal valid HDF5 bytes.
    
    HDF5 files start with the magic bytes: \x89HDF\r\n\x1a\n
    followed by the HDF5 superblock.
    """
    try:
        import h5py
        import io
        
        buffer = io.BytesIO()
        with h5py.File(buffer, 'w') as f:
            # Create a simple dataset
            f.create_dataset('test_data', data=[1.0, 2.0, 3.0])
            f.attrs['format'] = 'test'
        
        return buffer.getvalue()
        
    except ImportError:
        pytest.skip("h5py library not installed")


@pytest.fixture
def valid_h5_file(temp_dir: Path, valid_h5_bytes: bytes) -> Path:
    """Create a valid HDF5 file in the temp directory."""
    file_path = temp_dir / "valid_model.h5"
    file_path.write_bytes(valid_h5_bytes)
    return file_path


# =============================================================================
# MALICIOUS FILES
# =============================================================================

@pytest.fixture
def exe_bytes() -> bytes:
    """
    Generate bytes that look like a Windows executable.
    
    Windows EXE files start with "MZ" (Mark Zbikowski signature).
    This is enough to trigger our magic byte detection.
    """
    # MZ header followed by some padding
    return b"MZ" + b"\x00" * 100


@pytest.fixture
def exe_as_onnx_file(temp_dir: Path, exe_bytes: bytes) -> Path:
    """Create an EXE file disguised with .onnx extension."""
    file_path = temp_dir / "malicious.onnx"
    file_path.write_bytes(exe_bytes)
    return file_path


@pytest.fixture
def zip_bytes() -> bytes:
    """
    Generate bytes that look like a ZIP archive.
    
    ZIP files start with "PK" (Phil Katz signature).
    """
    return b"PK\x03\x04" + b"\x00" * 100


@pytest.fixture
def zip_as_onnx_file(temp_dir: Path, zip_bytes: bytes) -> Path:
    """Create a ZIP file disguised with .onnx extension."""
    file_path = temp_dir / "archive.onnx"
    file_path.write_bytes(zip_bytes)
    return file_path


@pytest.fixture
def elf_bytes() -> bytes:
    """
    Generate bytes that look like a Linux ELF executable.
    
    ELF files start with \x7fELF.
    """
    return b"\x7fELF" + b"\x00" * 100


@pytest.fixture
def corrupt_onnx_bytes() -> bytes:
    """
    Generate bytes that look like ONNX but are corrupt.
    
    Uses protobuf-like bytes that will fail ONNX parsing.
    """
    # Random bytes that are not valid protobuf
    return b"\x08\x01\x12\x03foo" + b"\xff" * 50


@pytest.fixture
def corrupt_onnx_file(temp_dir: Path, corrupt_onnx_bytes: bytes) -> Path:
    """Create a corrupt ONNX file."""
    file_path = temp_dir / "corrupt.onnx"
    file_path.write_bytes(corrupt_onnx_bytes)
    return file_path


@pytest.fixture
def oversized_bytes() -> bytes:
    """Generate bytes larger than the 50MB limit."""
    # 51 MB of zeros
    return b"\x00" * (51 * 1024 * 1024)


# =============================================================================
# PATH TRAVERSAL ATTEMPTS
# =============================================================================

@pytest.fixture
def traversal_filenames() -> list[str]:
    """List of filenames containing path traversal attempts."""
    return [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config",
        "foo/../bar.onnx",
        "normal.onnx\x00ignored",
        "/etc/passwd",
        "C:\\Windows\\System32\\config",
        "\\\\server\\share\\file.onnx",
        "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    ]


# =============================================================================
# MOCK UPLOAD FACTORIES
# =============================================================================

@pytest.fixture
def make_mock_upload():
    """Factory fixture to create MockUploadFile objects."""
    def _make(filename: str, content: bytes) -> MockUploadFile:
        return MockUploadFile(filename=filename, content=content)
    return _make


@pytest.fixture
def valid_onnx_upload(valid_onnx_bytes: bytes) -> MockUploadFile:
    """Create a mock upload with valid ONNX content."""
    return MockUploadFile(filename="model.onnx", content=valid_onnx_bytes)


@pytest.fixture
def valid_h5_upload(valid_h5_bytes: bytes) -> MockUploadFile:
    """Create a mock upload with valid H5 content."""
    return MockUploadFile(filename="model.h5", content=valid_h5_bytes)


@pytest.fixture
def exe_upload(exe_bytes: bytes) -> MockUploadFile:
    """Create a mock upload with EXE disguised as ONNX."""
    return MockUploadFile(filename="model.onnx", content=exe_bytes)
