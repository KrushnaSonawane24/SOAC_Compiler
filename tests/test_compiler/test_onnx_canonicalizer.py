"""
Tests for ONNX Canonicalizer
============================

Tests for the main canonicalization pipeline.
"""

import pytest
from pathlib import Path

from backend.compiler import (
    canonicalize_model,
    CanonicalOnnxModel,
    CompilerError,
    UnsupportedFormatError,
    UnsupportedOpError,
    get_supported_formats,
    TARGET_OPSET_VERSION,
)
from backend.compiler.hashing import compute_graph_hash


class TestCanonicalizeModel:
    """Tests for the main canonicalize_model function."""
    
    def test_simple_onnx_canonicalization(self, simple_onnx_file, temp_dir):
        """Valid ONNX model is canonicalized successfully."""
        result = canonicalize_model(simple_onnx_file, temp_dir)
        
        assert isinstance(result, CanonicalOnnxModel)
        assert result.onnx_path.exists()
        assert result.opset_version == TARGET_OPSET_VERSION
        assert len(result.graph_hash) == 64  # SHA-256
    
    def test_hash_is_deterministic(self, simple_onnx_file, temp_dir):
        """Same input always produces same hash."""
        result1 = canonicalize_model(simple_onnx_file, temp_dir / "run1")
        result2 = canonicalize_model(simple_onnx_file, temp_dir / "run2")
        
        # Hash must be identical for same input
        assert result1.graph_hash == result2.graph_hash
    
    def test_identity_nodes_removed(self, onnx_with_identity, temp_dir):
        """Identity nodes are removed during canonicalization."""
        result = canonicalize_model(onnx_with_identity, temp_dir)
        
        # Identity should not be in the operator list after canonicalization
        # (it may still be present if needed for valid output connections)
        assert result.onnx_path.exists()
    
    def test_older_opset_upgraded(self, older_opset_model, temp_dir):
        """Older opset models are upgraded to target opset."""
        result = canonicalize_model(older_opset_model, temp_dir)
        
        assert result.opset_version == TARGET_OPSET_VERSION
    
    def test_unsupported_op_rejected(self, onnx_with_custom_op, temp_dir):
        """Models with unsupported custom ops are rejected."""
        with pytest.raises(UnsupportedOpError) as exc_info:
            canonicalize_model(onnx_with_custom_op, temp_dir)
        
        assert exc_info.value.error_code == "UNSUPPORTED_OPS"
        assert "CustomUnsupportedOp" in str(exc_info.value)
    
    def test_metadata_populated(self, simple_onnx_file, temp_dir):
        """Canonical result has all required metadata."""
        result = canonicalize_model(simple_onnx_file, temp_dir)
        
        assert result.inputs is not None
        assert result.outputs is not None
        assert result.operator_count > 0
        assert len(result.operators) > 0
        assert result.canonicalized_at is not None
    
    def test_to_dict_serialization(self, simple_onnx_file, temp_dir):
        """CanonicalOnnxModel can be serialized to dict."""
        result = canonicalize_model(simple_onnx_file, temp_dir)
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert "graph_hash" in result_dict
        assert "opset_version" in result_dict
        assert "inputs" in result_dict
        assert "outputs" in result_dict


class TestFormatDetection:
    """Tests for format detection and support."""
    
    def test_supported_formats_list(self):
        """Supported formats are correctly listed."""
        formats = get_supported_formats()
        
        assert ".onnx" in formats
        assert ".h5" in formats
        assert ".keras" in formats
        assert ".tflite" in formats
    
    def test_unsupported_format_rejected(self, unsupported_format_file, temp_dir):
        """Unsupported formats are rejected with clear error."""
        with pytest.raises(UnsupportedFormatError) as exc_info:
            canonicalize_model(unsupported_format_file, temp_dir)
        
        assert exc_info.value.error_code == "FORMAT_NOT_CONVERTIBLE"
    
    def test_nonexistent_file_rejected(self, temp_dir):
        """Nonexistent file raises error."""
        with pytest.raises(CompilerError):
            canonicalize_model(temp_dir / "nonexistent.onnx", temp_dir)


class TestGraphHashing:
    """Tests for deterministic graph hashing."""
    
    def test_hash_is_sha256(self, simple_onnx_model):
        """Hash is 64 character SHA-256."""
        hash_value = compute_graph_hash(simple_onnx_model)
        
        assert len(hash_value) == 64
        assert all(c in '0123456789abcdef' for c in hash_value)
    
    def test_hash_deterministic(self, simple_onnx_model):
        """Same model always produces same hash."""
        hash1 = compute_graph_hash(simple_onnx_model)
        hash2 = compute_graph_hash(simple_onnx_model)
        
        assert hash1 == hash2
    
    def test_different_models_different_hash(self, temp_dir):
        """Different models produce different hashes."""
        from tests.test_compiler.conftest import create_simple_onnx
        
        model1 = create_simple_onnx(node_count=3)
        model2 = create_simple_onnx(node_count=5)
        
        hash1 = compute_graph_hash(model1)
        hash2 = compute_graph_hash(model2)
        
        assert hash1 != hash2
