"""
SOAC Shape Inference
====================

ONNX shape inference for completing partial shape information.

Uses onnxruntime for accurate shape inference when available,
falls back to onnx.shape_inference otherwise.
"""

import logging
from typing import Optional, List, Tuple

try:
    import onnx
    from onnx import shape_inference as onnx_shape_inference
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    onnx = None
    onnx_shape_inference = None

try:
    import onnxruntime as ort
    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ONNXRUNTIME_AVAILABLE = False
    ort = None

from .exceptions import ShapeInferenceError


logger = logging.getLogger(__name__)


def infer_shapes(model: "onnx.ModelProto") -> "onnx.ModelProto":
    """
    Run shape inference on ONNX model.
    
    Attempts to infer shapes for all intermediate tensors.
    Uses ONNX's built-in shape inference.
    
    Args:
        model: ONNX ModelProto with potentially incomplete shapes.
    
    Returns:
        Model with inferred shapes.
    
    Raises:
        ShapeInferenceError: If inference fails.
    """
    if not ONNX_AVAILABLE:
        raise ShapeInferenceError("ONNX library not available")
    
    try:
        # Use ONNX shape inference
        inferred_model = onnx_shape_inference.infer_shapes(
            model,
            check_type=True,
            strict_mode=False,
            data_prop=True,
        )
        return inferred_model
    except Exception as e:
        logger.warning(f"Shape inference failed: {e}")
        raise ShapeInferenceError(str(e))


def get_input_shapes(model: "onnx.ModelProto") -> List[Tuple[str, List[int]]]:
    """
    Extract input shapes from model.
    
    Returns:
        List of (name, shape) tuples.
        -1 indicates dynamic dimension.
    """
    shapes = []
    
    # Get names of initializers (weights) to exclude them
    initializer_names = {init.name for init in model.graph.initializer}
    
    for input_tensor in model.graph.input:
        if input_tensor.name in initializer_names:
            continue
        
        shape = []
        if input_tensor.type.HasField("tensor_type"):
            tensor_type = input_tensor.type.tensor_type
            if tensor_type.HasField("shape"):
                for dim in tensor_type.shape.dim:
                    if dim.HasField("dim_value"):
                        shape.append(dim.dim_value)
                    else:
                        shape.append(-1)  # Dynamic
        
        shapes.append((input_tensor.name, shape))
    
    return shapes


def get_output_shapes(model: "onnx.ModelProto") -> List[Tuple[str, List[int]]]:
    """
    Extract output shapes from model.
    
    Returns:
        List of (name, shape) tuples.
    """
    shapes = []
    
    for output_tensor in model.graph.output:
        shape = []
        if output_tensor.type.HasField("tensor_type"):
            tensor_type = output_tensor.type.tensor_type
            if tensor_type.HasField("shape"):
                for dim in tensor_type.shape.dim:
                    if dim.HasField("dim_value"):
                        shape.append(dim.dim_value)
                    else:
                        shape.append(-1)
        
        shapes.append((output_tensor.name, shape))
    
    return shapes


def freeze_batch_dimension(
    model: "onnx.ModelProto",
    batch_size: int = 1
) -> "onnx.ModelProto":
    """
    Freeze dynamic batch dimensions to a fixed size.
    
    Args:
        model: Model with potentially dynamic batch.
        batch_size: Fixed batch size to use.
    
    Returns:
        Model with fixed batch dimension.
    """
    if not ONNX_AVAILABLE:
        raise ShapeInferenceError("ONNX library not available")
    
    # Clone model to avoid mutating original
    model_copy = onnx.ModelProto()
    model_copy.CopyFrom(model)
    
    # Get initializer names
    initializer_names = {init.name for init in model_copy.graph.initializer}
    
    # Update input shapes
    for input_tensor in model_copy.graph.input:
        if input_tensor.name in initializer_names:
            continue
        
        if input_tensor.type.HasField("tensor_type"):
            tensor_type = input_tensor.type.tensor_type
            if tensor_type.HasField("shape") and len(tensor_type.shape.dim) > 0:
                first_dim = tensor_type.shape.dim[0]
                if not first_dim.HasField("dim_value"):
                    # Set batch dimension
                    first_dim.dim_value = batch_size
    
    # Update output shapes similarly
    for output_tensor in model_copy.graph.output:
        if output_tensor.type.HasField("tensor_type"):
            tensor_type = output_tensor.type.tensor_type
            if tensor_type.HasField("shape") and len(tensor_type.shape.dim) > 0:
                first_dim = tensor_type.shape.dim[0]
                if not first_dim.HasField("dim_value"):
                    first_dim.dim_value = batch_size
    
    return model_copy


def validate_shapes(model: "onnx.ModelProto") -> List[str]:
    """
    Validate that all tensor shapes are complete.
    
    Returns:
        List of tensors with incomplete shapes (empty if all valid).
    """
    incomplete = []
    
    # Check value_info (intermediate tensors)
    for vi in model.graph.value_info:
        if vi.type.HasField("tensor_type"):
            tensor_type = vi.type.tensor_type
            if not tensor_type.HasField("shape"):
                incomplete.append(vi.name)
            else:
                for i, dim in enumerate(tensor_type.shape.dim):
                    if not dim.HasField("dim_value") and not dim.HasField("dim_param"):
                        incomplete.append(f"{vi.name}[dim{i}]")
    
    return incomplete
