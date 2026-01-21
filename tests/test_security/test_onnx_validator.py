"""
Tests for ONNX Model Validator
==============================

Tests verify:
    - Valid ONNX models pass validation
    - Corrupt ONNX files are rejected
    - Non-ONNX files are rejected
"""

import pytest
from pathlib import Path

# Import will fail gracefully if onnx not installed
try:
    from backend.security.onnx_validator import (
        validate_onnx_model,
        get_onnx_model_info,
        is_valid_onnx_file,
        ONNX_AVAILABLE,
    )
    from backend.security.exceptions import OnnxValidationError
except ImportError:
    ONNX_AVAILABLE = False


@pytest.mark.skipif(not ONNX_AVAILABLE, reason="onnx library not installed")
class TestValidateOnnxModel:
    """Tests for validate_onnx_model function."""
    
    def test_valid_onnx_passes(self, valid_onnx_file: Path):
        """Valid ONNX model passes validation."""
        model = validate_onnx_model(valid_onnx_file)
        
        assert model is not None
        assert hasattr(model, 'graph')
        assert len(model.graph.node) > 0
    
    def test_corrupt_onnx_fails(self, corrupt_onnx_file: Path):
        """Corrupt ONNX file fails validation."""
        with pytest.raises(OnnxValidationError) as exc_info:
            validate_onnx_model(corrupt_onnx_file)
        
        assert "ONNX" in str(exc_info.value)
    
    def test_exe_as_onnx_fails(self, exe_as_onnx_file: Path):
        """EXE disguised as ONNX fails validation."""
        with pytest.raises(OnnxValidationError):
            validate_onnx_model(exe_as_onnx_file)
    
    def test_random_bytes_fail(self, temp_dir: Path):
        """Random bytes fail ONNX validation."""
        random_file = temp_dir / "random.onnx"
        random_file.write_bytes(b"\x00\x01\x02\x03" * 100)
        
        with pytest.raises(OnnxValidationError):
            validate_onnx_model(random_file)


@pytest.mark.skipif(not ONNX_AVAILABLE, reason="onnx library not installed")
class TestGetOnnxModelInfo:
    """Tests for get_onnx_model_info function."""
    
    def test_extracts_model_info(self, valid_onnx_file: Path):
        """Extracts metadata from valid ONNX model."""
        model = validate_onnx_model(valid_onnx_file)
        info = get_onnx_model_info(model)
        
        assert "ir_version" in info
        assert "num_nodes" in info
        assert "num_inputs" in info
        assert "num_outputs" in info
        
        assert info["num_nodes"] == 1  # Our test model has 1 Identity node
        assert info["num_inputs"] == 1
        assert info["num_outputs"] == 1


@pytest.mark.skipif(not ONNX_AVAILABLE, reason="onnx library not installed")
class TestIsValidOnnxFile:
    """Tests for is_valid_onnx_file function."""
    
    def test_valid_onnx_returns_true(self, valid_onnx_file: Path):
        """Returns True for valid ONNX files."""
        assert is_valid_onnx_file(valid_onnx_file) is True
    
    def test_corrupt_onnx_returns_false(self, corrupt_onnx_file: Path):
        """Returns False for corrupt ONNX files."""
        assert is_valid_onnx_file(corrupt_onnx_file) is False
    
    def test_exe_returns_false(self, exe_as_onnx_file: Path):
        """Returns False for EXE disguised as ONNX."""
        assert is_valid_onnx_file(exe_as_onnx_file) is False
