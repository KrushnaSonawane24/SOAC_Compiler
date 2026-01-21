"""
Pytest Fixtures for Deployment Tests
=====================================

Creates mock models for deployment testing.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

try:
    import onnx
    from onnx import helper, TensorProto
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    dir_path = Path(tempfile.mkdtemp(prefix="test_deployment_"))
    yield dir_path
    if dir_path.exists():
        shutil.rmtree(dir_path)


@pytest.fixture
def simple_onnx_model(temp_dir) -> Path:
    """Create a simple ONNX model for testing."""
    if not ONNX_AVAILABLE:
        pytest.skip("ONNX not available")
    
    X = helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 3, 224, 224])
    Y = helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, 1000])
    
    nodes = [
        helper.make_node('Flatten', ['input'], ['flat']),
        helper.make_node('Relu', ['flat'], ['output']),
    ]
    
    graph = helper.make_graph(nodes, 'test', [X], [Y])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 17)])
    
    path = temp_dir / "test_model.onnx"
    onnx.save(model, str(path))
    return path
