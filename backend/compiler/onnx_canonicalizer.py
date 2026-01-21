"""
SOAC ONNX Canonicalizer
=======================

THE SINGLE ENTRY POINT for model canonicalization.

This module:
    1. Converts supported formats to ONNX
    2. Normalizes the graph to canonical form
    3. Validates the result
    4. Computes deterministic hash

GUARANTEE: Same input always produces same output hash.
"""

import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone

try:
    import onnx
    from onnx import checker as onnx_checker
    from onnx import version_converter
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

from .exceptions import (
    CompilerError,
    CanonializationError,
    GraphValidationError,
    OpsetConversionError,
    UnsupportedOpError,
)
from .onnx_converter import convert_to_onnx, InputFormat
from .graph_normalizer import normalize_graph
from .shape_inference import infer_shapes, get_input_shapes, get_output_shapes
from .hashing import compute_graph_hash


logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

TARGET_OPSET_VERSION = 17
"""
Target ONNX opset version.

Opset 17 is:
    - Stable and widely supported
    - Supports all common operations
    - Compatible with onnxruntime
"""

# Standard ONNX operators (subset - main ones)
SUPPORTED_OPERATORS = frozenset({
    # Activation
    "Relu", "LeakyRelu", "PRelu", "Sigmoid", "Tanh", "Softmax",
    "Elu", "Selu", "Softsign", "Softplus", "HardSigmoid", "HardSwish",
    "ThresholdedRelu", "Mish", "Celu", "Gelu",
    
    # Arithmetic
    "Add", "Sub", "Mul", "Div", "Neg", "Abs", "Sqrt", "Exp", "Log",
    "Pow", "Mod", "Sum", "Mean", "Max", "Min",
    
    # Comparison
    "Equal", "Greater", "Less", "GreaterOrEqual", "LessOrEqual",
    "And", "Or", "Not", "Xor",
    
    # Convolution
    "Conv", "ConvTranspose", "QLinearConv",
    
    # Pooling
    "MaxPool", "AveragePool", "GlobalMaxPool", "GlobalAveragePool",
    "MaxUnpool", "LpPool",
    
    # Normalization
    "BatchNormalization", "InstanceNormalization", "LayerNormalization",
    "LpNormalization", "GroupNormalization",
    
    # Recurrent
    "LSTM", "GRU", "RNN",
    
    # Tensor manipulation
    "Reshape", "Transpose", "Squeeze", "Unsqueeze", "Flatten",
    "Concat", "Split", "Slice", "Gather", "GatherElements", "GatherND",
    "Scatter", "ScatterElements", "ScatterND",
    "Pad", "Resize", "Tile", "Expand", "Shape", "Size",
    
    # Matrix
    "MatMul", "MatMulInteger", "Gemm", "QLinearMatMul",
    
    # Reduction
    "ReduceSum", "ReduceMean", "ReduceMax", "ReduceMin",
    "ReduceProd", "ReduceL1", "ReduceL2", "ReduceLogSum",
    "ReduceLogSumExp", "ReduceSumSquare",
    
    # Data type
    "Cast", "CastLike",
    
    # Constant
    "Constant", "ConstantOfShape", "Identity",
    
    # Other common
    "Clip", "Where", "Dropout", "Floor", "Ceil", "Round",
    "Einsum", "Gemm", "TopK", "ArgMax", "ArgMin",
    "NonMaxSuppression", "RoiAlign",
})


# =============================================================================
# OUTPUT DATA STRUCTURE
# =============================================================================

@dataclass(frozen=True)
class InputSpec:
    """Model input specification."""
    name: str
    shape: Tuple[int, ...]
    dtype: str


@dataclass(frozen=True)  
class OutputSpec:
    """Model output specification."""
    name: str
    shape: Tuple[int, ...]
    dtype: str


@dataclass(frozen=True)
class CanonicalOnnxModel:
    """
    Result of canonicalization.
    
    All fields are immutable for safety.
    
    Attributes:
        onnx_path: Path to canonical .onnx file
        graph_hash: SHA-256 hash of serialized model
        opset_version: ONNX opset version (17)
        inputs: List of input specifications
        outputs: List of output specifications
        original_format: Original input format
        operator_count: Number of operators in graph
        operators: Set of unique operator types
        canonicalized_at: ISO timestamp of canonicalization
    """
    onnx_path: Path
    graph_hash: str
    opset_version: int
    inputs: Tuple[InputSpec, ...]
    outputs: Tuple[OutputSpec, ...]
    original_format: str
    operator_count: int
    operators: Tuple[str, ...]
    canonicalized_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary."""
        return {
            "onnx_path": str(self.onnx_path),
            "graph_hash": self.graph_hash,
            "opset_version": self.opset_version,
            "inputs": [
                {"name": i.name, "shape": list(i.shape), "dtype": i.dtype}
                for i in self.inputs
            ],
            "outputs": [
                {"name": o.name, "shape": list(o.shape), "dtype": o.dtype}
                for o in self.outputs
            ],
            "original_format": self.original_format,
            "operator_count": self.operator_count,
            "operators": list(self.operators),
            "canonicalized_at": self.canonicalized_at,
        }


# =============================================================================
# VALIDATION
# =============================================================================

def check_unsupported_ops(model: "onnx.ModelProto") -> List[str]:
    """
    Check for unsupported operators.
    
    Returns:
        List of unsupported operator names (empty if all supported).
    """
    unsupported = []
    
    for node in model.graph.node:
        if node.op_type not in SUPPORTED_OPERATORS:
            # Check if it's a custom domain op
            if "." in node.op_type or node.domain:
                unsupported.append(f"{node.domain}.{node.op_type}" if node.domain else node.op_type)
            else:
                unsupported.append(node.op_type)
    
    return list(set(unsupported))


def validate_onnx_model(model: "onnx.ModelProto") -> None:
    """
    Validate ONNX model using official checker.
    
    Raises:
        GraphValidationError: If validation fails.
    """
    try:
        onnx_checker.check_model(model)
    except Exception as e:
        raise GraphValidationError(str(e), e)


def get_opset_version(model: "onnx.ModelProto") -> int:
    """Get the primary opset version from model."""
    for opset in model.opset_import:
        if opset.domain == "" or opset.domain == "ai.onnx":
            return opset.version
    return 0


def convert_opset(model: "onnx.ModelProto", target_version: int) -> "onnx.ModelProto":
    """
    Convert model to target opset version.
    
    Args:
        model: Input model.
        target_version: Target opset version.
    
    Returns:
        Model with updated opset.
    
    Raises:
        OpsetConversionError: If conversion fails.
    """
    current_version = get_opset_version(model)
    
    if current_version == target_version:
        return model
    
    logger.info(f"Converting opset {current_version} -> {target_version}")
    
    try:
        if current_version < target_version:
            # Upgrade opset
            converted = version_converter.convert_version(model, target_version)
        else:
            # Downgrade opset - less common, may fail
            converted = version_converter.convert_version(model, target_version)
        
        return converted
        
    except Exception as e:
        raise OpsetConversionError(current_version, target_version, str(e))


# =============================================================================
# MAIN CANONICALIZATION
# =============================================================================

def canonicalize_model(
    input_path: Path,
    output_dir: Optional[Path] = None,
) -> CanonicalOnnxModel:
    """
    Canonicalize a model to standard ONNX form.
    
    THE SINGLE ENTRY POINT for model canonicalization.
    
    This function:
        1. Converts input format to ONNX (if needed)
        2. Converts to target opset version
        3. Normalizes graph structure
        4. Runs shape inference
        5. Validates the result
        6. Saves canonical ONNX file
        7. Computes deterministic hash
    
    Args:
        input_path: Path to input model file.
        output_dir: Directory to save canonical ONNX (defaults to temp).
    
    Returns:
        CanonicalOnnxModel with all metadata.
    
    Raises:
        UnsupportedFormatError: If format not supported.
        ConversionError: If format conversion fails.
        CanonializationError: If canonicalization fails.
        UnsupportedOpError: If model contains unsupported ops.
        GraphValidationError: If resulting model is invalid.
    
    DETERMINISM GUARANTEE:
        Same input model always produces same graph_hash.
    
    Example:
        >>> result = canonicalize_model(Path("model.h5"))
        >>> print(result.graph_hash)  # Always same for same input
        >>> print(result.onnx_path)   # Path to canonical .onnx
    """
    if not ONNX_AVAILABLE:
        raise CanonializationError("ONNX library not available")
    
    input_path = Path(input_path)
    logger.info(f"Canonicalizing model: {input_path}")
    
    # Step 1: Convert to ONNX
    model, original_format = convert_to_onnx(input_path)
    logger.debug(f"Converted from {original_format.value}")
    
    # Step 2: Check for unsupported operators
    unsupported = check_unsupported_ops(model)
    if unsupported:
        raise UnsupportedOpError(unsupported)
    
    # Step 3: Convert to target opset
    model = convert_opset(model, TARGET_OPSET_VERSION)
    
    # Step 4: Normalize graph
    model = normalize_graph(model)
    logger.debug("Graph normalized")
    
    # Step 5: Run shape inference
    try:
        model = infer_shapes(model)
        logger.debug("Shape inference complete")
    except Exception as e:
        logger.warning(f"Shape inference failed: {e}")
        # Continue without full shape info
    
    # Step 6: Validate result
    validate_onnx_model(model)
    logger.debug("Model validated")
    
    # Step 7: Compute hash BEFORE saving (for reproducibility)
    graph_hash = compute_graph_hash(model)
    logger.info(f"Graph hash: {graph_hash[:16]}...")
    
    # Step 8: Save canonical ONNX
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="soac_canonical_"))
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / f"canonical_{graph_hash[:16]}.onnx"
    onnx.save(model, str(output_path))
    logger.info(f"Saved canonical model: {output_path}")
    
    # Step 9: Extract metadata
    inputs = []
    init_names = {init.name for init in model.graph.initializer}
    for inp in model.graph.input:
        if inp.name in init_names:
            continue
        shape = []
        dtype = "float32"
        if inp.type.HasField("tensor_type"):
            tt = inp.type.tensor_type
            if tt.HasField("shape"):
                for dim in tt.shape.dim:
                    if dim.HasField("dim_value"):
                        shape.append(dim.dim_value)
                    else:
                        shape.append(-1)
            dtype = onnx.TensorProto.DataType.Name(tt.elem_type).lower()
        inputs.append(InputSpec(inp.name, tuple(shape), dtype))
    
    outputs = []
    for out in model.graph.output:
        shape = []
        dtype = "float32"
        if out.type.HasField("tensor_type"):
            tt = out.type.tensor_type
            if tt.HasField("shape"):
                for dim in tt.shape.dim:
                    if dim.HasField("dim_value"):
                        shape.append(dim.dim_value)
                    else:
                        shape.append(-1)
            dtype = onnx.TensorProto.DataType.Name(tt.elem_type).lower()
        outputs.append(OutputSpec(out.name, tuple(shape), dtype))
    
    operators = list(set(node.op_type for node in model.graph.node))
    
    return CanonicalOnnxModel(
        onnx_path=output_path,
        graph_hash=graph_hash,
        opset_version=TARGET_OPSET_VERSION,
        inputs=tuple(inputs),
        outputs=tuple(outputs),
        original_format=original_format.value,
        operator_count=len(model.graph.node),
        operators=tuple(sorted(operators)),
        canonicalized_at=datetime.now(timezone.utc).isoformat(),
    )
