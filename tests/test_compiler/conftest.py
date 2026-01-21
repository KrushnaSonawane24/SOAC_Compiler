"""
Pytest Fixtures for Compiler Tests
==================================

Creates synthetic ONNX models for testing canonicalization.
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
    """Create a temporary directory for test files."""
    dir_path = Path(tempfile.mkdtemp(prefix="test_compiler_"))
    yield dir_path
    if dir_path.exists():
        shutil.rmtree(dir_path)


def create_simple_onnx(
    node_count: int = 5,
    input_shape: tuple = (1, 3, 224, 224),
) -> "onnx.ModelProto":
    """
    Create a simple valid ONNX model for testing.
    """
    if not ONNX_AVAILABLE:
        pytest.skip("ONNX not available")
    
    # Create input
    X = helper.make_tensor_value_info('input', TensorProto.FLOAT, list(input_shape))
    Y = helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, 1000])
    
    # Create simple chain of Relu nodes
    nodes = []
    prev = 'input'
    
    for i in range(node_count):
        output_name = 'output' if i == node_count - 1 else f'relu_{i}'
        node = helper.make_node(
            'Relu',
            inputs=[prev],
            outputs=[output_name],
            name=f'relu_node_{i}'
        )
        nodes.append(node)
        prev = output_name
    
    graph = helper.make_graph(
        nodes,
        'test_graph',
        [X],
        [Y],
    )
    
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 17)])
    model.ir_version = 8
    
    return model


@pytest.fixture
def simple_onnx_file(temp_dir) -> Path:
    """Create a simple ONNX model file."""
    if not ONNX_AVAILABLE:
        pytest.skip("ONNX not available")
    
    model = create_simple_onnx()
    path = temp_dir / "simple_model.onnx"
    onnx.save(model, str(path))
    return path


@pytest.fixture
def simple_onnx_model() -> "onnx.ModelProto":
    """Create a simple ONNX model in memory."""
    if not ONNX_AVAILABLE:
        pytest.skip("ONNX not available")
    return create_simple_onnx()


@pytest.fixture
def onnx_with_identity(temp_dir) -> Path:
    """Create ONNX model with Identity nodes."""
    if not ONNX_AVAILABLE:
        pytest.skip("ONNX not available")
    
    X = helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 3, 224, 224])
    Y = helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, 3, 224, 224])
    
    nodes = [
        helper.make_node('Relu', ['input'], ['relu_out']),
        helper.make_node('Identity', ['relu_out'], ['identity_out']),  # Should be removed
        helper.make_node('Relu', ['identity_out'], ['output']),
    ]
    
    graph = helper.make_graph(nodes, 'test', [X], [Y])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 17)])
    
    path = temp_dir / "identity_model.onnx"
    onnx.save(model, str(path))
    return path


@pytest.fixture
def onnx_with_custom_op(temp_dir) -> Path:
    """Create ONNX model with unsupported custom operator."""
    if not ONNX_AVAILABLE:
        pytest.skip("ONNX not available")
    
    X = helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 3, 224, 224])
    Y = helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, 3, 224, 224])
    
    nodes = [
        helper.make_node('Relu', ['input'], ['relu_out']),
        helper.make_node('CustomUnsupportedOp', ['relu_out'], ['custom_out']),
        helper.make_node('Relu', ['custom_out'], ['output']),
    ]
    
    graph = helper.make_graph(nodes, 'test', [X], [Y])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 17)])
    
    path = temp_dir / "custom_op_model.onnx"
    onnx.save(model, str(path))
    return path


@pytest.fixture
def older_opset_model(temp_dir) -> Path:
    """Create ONNX model with older opset version."""
    if not ONNX_AVAILABLE:
        pytest.skip("ONNX not available")
    
    model = create_simple_onnx()
    
    # Change opset to older version
    del model.opset_import[:]
    model.opset_import.append(helper.make_opsetid('', 13))  # Older opset
    
    path = temp_dir / "old_opset_model.onnx"
    onnx.save(model, str(path))
    return path


@pytest.fixture 
def unsupported_format_file(temp_dir) -> Path:
    """Create file with unsupported extension."""
    path = temp_dir / "model.pt"  # PyTorch not directly supported
    path.write_bytes(b"dummy content")
    return path
