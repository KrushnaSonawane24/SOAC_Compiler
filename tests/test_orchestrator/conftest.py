"""
Pytest Fixtures for Orchestrator Tests
======================================

Creates mock models for E2E testing.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

try:
    import onnx
    from onnx import helper, TensorProto, numpy_helper
    import numpy as np
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

from backend.orchestrator import JobConfig


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    dir_path = Path(tempfile.mkdtemp(prefix="test_orchestrator_"))
    yield dir_path
    if dir_path.exists():
        shutil.rmtree(dir_path)


@pytest.fixture
def simple_onnx_model(temp_dir) -> Path:
    """Create a simple valid ONNX model."""
    if not ONNX_AVAILABLE:
        pytest.skip("ONNX not available")
    
    # Create simple model: input -> MatMul -> Relu -> output
    X = helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 3, 224, 224])
    Y = helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, 1000])
    
    nodes = [
        helper.make_node('Flatten', ['input'], ['flat']),
        helper.make_node('Relu', ['flat'], ['output']),
    ]
    
    graph = helper.make_graph(nodes, 'test_model', [X], [Y])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 17)])
    
    path = temp_dir / "test_model.onnx"
    onnx.save(model, str(path))
    return path


@pytest.fixture
def test_config() -> JobConfig:
    """Create test job config."""
    return JobConfig(
        accuracy_threshold=0.02,
        warmup_runs=2,
        measured_runs=5,
        cleanup_on_complete=False,  # Keep for inspection
    )
