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
    
    X = helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 3, 224, 224])
    Y = helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, 1000])
    
    nodes = []
    initializers = []
    prev_output = 'input'
    for i in range(35):
        weight_shape = [64, 3 if i == 0 else 64, 3, 3]
        weight_name = f'weight_{i}'
        weight = helper.make_tensor(
            weight_name,
            TensorProto.FLOAT,
            weight_shape,
            [0.0] * (weight_shape[0] * weight_shape[1] * weight_shape[2] * weight_shape[3]),
        )
        conv_out = f'conv_{i}'
        relu_out = f'relu_{i}'
        add_out = f'add_{i}'

        nodes.append(helper.make_node('Conv', [prev_output, weight_name], [conv_out], kernel_shape=[3, 3], pads=[1, 1, 1, 1]))
        nodes.append(helper.make_node('Relu', [conv_out], [relu_out]))
        nodes.append(helper.make_node('Add', [relu_out, relu_out], [add_out]))
        prev_output = add_out
        initializers.append(weight)

    nodes.append(helper.make_node('GlobalAveragePool', [prev_output], ['gap']))
    nodes.append(helper.make_node('Flatten', ['gap'], ['output'], axis=1))
    
    graph = helper.make_graph(nodes, 'test_model', [X], [Y], initializer=initializers)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 13)])
    model.ir_version = 7
    
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
        cleanup_on_complete=False,
    )
