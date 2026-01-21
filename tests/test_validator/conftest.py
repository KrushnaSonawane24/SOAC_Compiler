"""
Pytest Fixtures for Model Validator Tests
=========================================

Creates synthetic ONNX graphs for testing validation logic.
All fixtures are deterministic and work offline.
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
    dir_path = Path(tempfile.mkdtemp(prefix="test_validator_"))
    yield dir_path
    if dir_path.exists():
        shutil.rmtree(dir_path)


def create_simple_onnx_model(
    operators: list,
    input_shape: tuple = (1, 3, 224, 224),
    output_shape: tuple = (1, 1000),
) -> "onnx.ModelProto":
    """
    Create a synthetic ONNX model with specified operators.
    
    This creates a valid ONNX graph structure with the requested operators.
    """
    if not ONNX_AVAILABLE:
        pytest.skip("onnx not available")
    
    # Create input
    X = helper.make_tensor_value_info('input', TensorProto.FLOAT, list(input_shape))
    
    # Create output
    Y = helper.make_tensor_value_info('output', TensorProto.FLOAT, list(output_shape))
    
    # Create nodes
    nodes = []
    prev_output = 'input'
    
    for i, op_type in enumerate(operators):
        output_name = f'output_{i}' if i < len(operators) - 1 else 'output'
        
        if op_type in ['Conv', 'ConvTranspose']:
            # Conv needs weight input
            weight_shape = [64, input_shape[1] if i == 0 else 64, 3, 3]
            weight = helper.make_tensor(
                f'weight_{i}',
                TensorProto.FLOAT,
                weight_shape,
                [0.0] * (weight_shape[0] * weight_shape[1] * weight_shape[2] * weight_shape[3])
            )
            node = helper.make_node(
                op_type,
                inputs=[prev_output, f'weight_{i}'],
                outputs=[output_name],
                kernel_shape=[3, 3],
                pads=[1, 1, 1, 1],
            )
        elif op_type in ['Relu', 'Sigmoid', 'Tanh']:
            node = helper.make_node(
                op_type,
                inputs=[prev_output],
                outputs=[output_name],
            )
        elif op_type == 'Add':
            node = helper.make_node(
                op_type,
                inputs=[prev_output, prev_output],
                outputs=[output_name],
            )
        elif op_type == 'Mul':
            node = helper.make_node(
                op_type,
                inputs=[prev_output, prev_output],
                outputs=[output_name],
            )
        elif op_type == 'Concat':
            node = helper.make_node(
                op_type,
                inputs=[prev_output, prev_output],
                outputs=[output_name],
                axis=1,
            )
        elif op_type == 'GlobalAveragePool':
            node = helper.make_node(
                op_type,
                inputs=[prev_output],
                outputs=[output_name],
            )
        elif op_type == 'MaxPool':
            node = helper.make_node(
                op_type,
                inputs=[prev_output],
                outputs=[output_name],
                kernel_shape=[2, 2],
            )
        elif op_type == 'Reshape':
            shape_tensor = helper.make_tensor(
                f'shape_{i}',
                TensorProto.INT64,
                [2],
                [1, -1]
            )
            node = helper.make_node(
                op_type,
                inputs=[prev_output, f'shape_{i}'],
                outputs=[output_name],
            )
        elif op_type == 'Flatten':
            node = helper.make_node(
                op_type,
                inputs=[prev_output],
                outputs=[output_name],
                axis=1,
            )
        elif op_type == 'Gemm':
            # Gemm needs weight and bias
            weight = helper.make_tensor(
                f'gemm_weight_{i}',
                TensorProto.FLOAT,
                [1000, 512],
                [0.0] * (1000 * 512)
            )
            bias = helper.make_tensor(
                f'gemm_bias_{i}',
                TensorProto.FLOAT,
                [1000],
                [0.0] * 1000
            )
            node = helper.make_node(
                op_type,
                inputs=[prev_output, f'gemm_weight_{i}', f'gemm_bias_{i}'],
                outputs=[output_name],
            )
        elif op_type == 'Dropout':
            node = helper.make_node(
                op_type,
                inputs=[prev_output],
                outputs=[output_name, f'mask_{i}'],
                ratio=0.5,
            )
        elif op_type == 'BatchNormalization':
            # BatchNorm needs scale, B, mean, var
            scale = helper.make_tensor(f'scale_{i}', TensorProto.FLOAT, [64], [1.0] * 64)
            B = helper.make_tensor(f'B_{i}', TensorProto.FLOAT, [64], [0.0] * 64)
            mean = helper.make_tensor(f'mean_{i}', TensorProto.FLOAT, [64], [0.0] * 64)
            var = helper.make_tensor(f'var_{i}', TensorProto.FLOAT, [64], [1.0] * 64)
            node = helper.make_node(
                op_type,
                inputs=[prev_output, f'scale_{i}', f'B_{i}', f'mean_{i}', f'var_{i}'],
                outputs=[output_name],
            )
        elif op_type == 'LayerNormalization':
            scale = helper.make_tensor(f'ln_scale_{i}', TensorProto.FLOAT, [64], [1.0] * 64)
            bias = helper.make_tensor(f'ln_bias_{i}', TensorProto.FLOAT, [64], [0.0] * 64)
            node = helper.make_node(
                op_type,
                inputs=[prev_output, f'ln_scale_{i}', f'ln_bias_{i}'],
                outputs=[output_name],
            )
        else:
            # Generic unary operator
            node = helper.make_node(
                op_type,
                inputs=[prev_output],
                outputs=[output_name],
            )
        
        nodes.append(node)
        prev_output = output_name
    
    # Create graph
    graph = helper.make_graph(
        nodes,
        'test_graph',
        [X],
        [Y],
    )
    
    # Create model
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 13)])
    model.ir_version = 7
    
    return model


@pytest.fixture
def valid_mobilenet_onnx(temp_dir):
    """Create a valid MobileNet-like ONNX model."""
    if not ONNX_AVAILABLE:
        pytest.skip("onnx not available")
    
    # MobileNet-like operators
    operators = []
    for _ in range(35):  # ~35 conv blocks
        operators.extend(['Conv', 'Relu', 'Add'])
    operators.append('GlobalAveragePool')
    operators.append('Flatten')
    
    model = create_simple_onnx_model(operators)
    
    file_path = temp_dir / "mobilenet_v2.onnx"
    onnx.save(model, str(file_path))
    return file_path


@pytest.fixture
def valid_resnet18_onnx(temp_dir):
    """Create a valid ResNet18-like ONNX model."""
    if not ONNX_AVAILABLE:
        pytest.skip("onnx not available")
    
    # ResNet18 operators
    operators = []
    for _ in range(18):  # 18 residual blocks
        operators.extend(['Conv', 'Relu', 'Add'])
    operators.append('GlobalAveragePool')
    
    model = create_simple_onnx_model(operators)
    
    file_path = temp_dir / "resnet18.onnx"
    onnx.save(model, str(file_path))
    return file_path


@pytest.fixture
def training_graph_onnx(temp_dir):
    """Create an ONNX model with training operators."""
    if not ONNX_AVAILABLE:
        pytest.skip("onnx not available")
    
    # Include training operators
    operators = ['Conv', 'Relu', 'Adam', 'Conv', 'Relu']
    
    model = create_simple_onnx_model(operators)
    
    file_path = temp_dir / "training_model.onnx"
    onnx.save(model, str(file_path))
    return file_path


@pytest.fixture
def random_ops_onnx(temp_dir):
    """Create an ONNX model with random operators."""
    if not ONNX_AVAILABLE:
        pytest.skip("onnx not available")
    
    operators = ['Conv', 'Relu', 'RandomNormal', 'Conv']
    
    model = create_simple_onnx_model(operators)
    
    file_path = temp_dir / "random_model.onnx"
    onnx.save(model, str(file_path))
    return file_path


@pytest.fixture
def custom_cnn_onnx(temp_dir):
    """Create a custom CNN that doesn't match any supported architecture."""
    if not ONNX_AVAILABLE:
        pytest.skip("onnx not available")
    
    # Very simple custom CNN (no matching fingerprint)
    operators = ['Conv', 'Relu', 'Conv', 'Relu', 'Flatten']
    
    model = create_simple_onnx_model(operators)
    
    file_path = temp_dir / "custom_cnn.onnx"
    onnx.save(model, str(file_path))
    return file_path


@pytest.fixture
def unsupported_format_file(temp_dir):
    """Create a file with unsupported format."""
    file_path = temp_dir / "model.unsupported"
    file_path.write_bytes(b"dummy content")
    return file_path
