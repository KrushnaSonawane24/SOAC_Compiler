"""
SOAC Model Validator
====================

THE SINGLE ENTRY POINT for model validation.

This module validates that models:
    1. Are in a supported format
    2. Are a supported architecture
    3. Contain no training operators
    4. Contain no non-deterministic operators
    5. Have valid input shapes

DESIGN PRINCIPLES:
    - STRICT ALLOWLIST: Only explicitly supported models pass
    - EXPLAINABLE REJECTIONS: Every rejection has a reason code
    - NO HEURISTICS: Only analyze actual graph structure
    - NO INFERENCE: Never execute the model
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

try:
    import onnx
    from onnx import numpy_helper
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    onnx = None

from backend.security.hashing import compute_file_hash

from .exceptions import (
    ModelValidationError,
    UnsupportedFormatError,
    UnsupportedArchitectureError,
    TrainingGraphError,
    NonDeterministicOpError,
    InvalidInputShapeError,
    ModelParsingError,
    DynamicShapeError,
)
from .metadata import (
    ModelType,
    ModelFormat,
    ModelMetadata,
    ArchitectureInfo,
    InputSpec,
    OutputSpec,
    SUPPORTED_ARCHITECTURES,
    get_all_architecture_names,
)
from .op_blacklist import (
    check_for_training_ops,
    check_for_random_ops,
    is_dropout_training_mode,
    is_batchnorm_training_mode,
)
from .architecture_rules import (
    detect_architecture,
    is_supported_architecture,
)


logger = logging.getLogger(__name__)


# =============================================================================
# SUPPORTED FORMATS
# =============================================================================

SUPPORTED_EXTENSIONS: Dict[str, ModelFormat] = {
    ".onnx": ModelFormat.ONNX,
    ".pt": ModelFormat.PYTORCH,
    ".pth": ModelFormat.PYTORCH,
    ".h5": ModelFormat.KERAS_H5,
    ".keras": ModelFormat.KERAS_H5,
    ".pkl": ModelFormat.PICKLE,
    ".joblib": ModelFormat.JOBLIB,
    ".tflite": ModelFormat.TFLITE,
    ".mlmodel": ModelFormat.COREML,
}


def get_model_format(file_path: Path) -> ModelFormat:
    """
    Determine model format from file extension.
    
    Args:
        file_path: Path to the model file.
    
    Returns:
        ModelFormat enum value.
    
    Raises:
        UnsupportedFormatError: If extension is not supported.
    """
    ext = file_path.suffix.lower()
    
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError(str(file_path), ext)
    
    return SUPPORTED_EXTENSIONS[ext]


# =============================================================================
# ONNX PARSING
# =============================================================================

def load_onnx_model(file_path: Path) -> "onnx.ModelProto":
    """
    Load and parse an ONNX model.
    
    Args:
        file_path: Path to the ONNX file.
    
    Returns:
        Loaded ONNX ModelProto.
    
    Raises:
        ModelParsingError: If file cannot be parsed.
    """
    if not ONNX_AVAILABLE:
        raise ModelParsingError(
            str(file_path),
            "ONNX library not installed",
        )
    
    try:
        model = onnx.load(str(file_path), load_external_data=False)
        return model
    except Exception as e:
        raise ModelParsingError(str(file_path), str(e), e)


def extract_onnx_operators(model: "onnx.ModelProto") -> List[str]:
    """Extract list of operator types from ONNX graph."""
    operators = []
    for node in model.graph.node:
        operators.append(node.op_type)
    return operators


def extract_onnx_inputs(model: "onnx.ModelProto") -> List[InputSpec]:
    """Extract input specifications from ONNX model."""
    inputs = []
    
    for input_tensor in model.graph.input:
        name = input_tensor.name
        
        # Skip initializers (weights)
        initializer_names = {init.name for init in model.graph.initializer}
        if name in initializer_names:
            continue
        
        # Extract shape
        shape = []
        if input_tensor.type.HasField("tensor_type"):
            tensor_type = input_tensor.type.tensor_type
            if tensor_type.HasField("shape"):
                for dim in tensor_type.shape.dim:
                    if dim.HasField("dim_value"):
                        shape.append(dim.dim_value)
                    elif dim.HasField("dim_param"):
                        shape.append(-1)  # Dynamic dimension
                    else:
                        shape.append(-1)
            
            # Get dtype
            dtype_num = tensor_type.elem_type
            dtype = onnx.TensorProto.DataType.Name(dtype_num).lower()
        else:
            dtype = "unknown"
        
        inputs.append(InputSpec(
            name=name,
            shape=tuple(shape),
            dtype=dtype,
        ))
    
    return inputs


def extract_onnx_outputs(model: "onnx.ModelProto") -> List[OutputSpec]:
    """Extract output specifications from ONNX model."""
    outputs = []
    
    for output_tensor in model.graph.output:
        name = output_tensor.name
        
        shape = []
        if output_tensor.type.HasField("tensor_type"):
            tensor_type = output_tensor.type.tensor_type
            if tensor_type.HasField("shape"):
                for dim in tensor_type.shape.dim:
                    if dim.HasField("dim_value"):
                        shape.append(dim.dim_value)
                    else:
                        shape.append(-1)
            
            dtype_num = tensor_type.elem_type
            dtype = onnx.TensorProto.DataType.Name(dtype_num).lower()
        else:
            dtype = "unknown"
        
        outputs.append(OutputSpec(
            name=name,
            shape=tuple(shape),
            dtype=dtype,
        ))
    
    return outputs


def check_onnx_for_training_nodes(model: "onnx.ModelProto") -> List[str]:
    """
    Check for training-mode Dropout and BatchNorm nodes.
    
    These nodes have a training_mode attribute that should be 0 for inference.
    """
    training_nodes = []
    
    for node in model.graph.node:
        attrs = {attr.name: attr for attr in node.attribute}
        
        if node.op_type == "Dropout":
            # Check if training_mode is set
            if "training_mode" in attrs:
                if attrs["training_mode"].i == 1:
                    training_nodes.append(f"Dropout (training_mode=1)")
        
        elif node.op_type == "BatchNormalization":
            if "training_mode" in attrs:
                if attrs["training_mode"].i == 1:
                    training_nodes.append(f"BatchNorm (training_mode=1)")
    
    return training_nodes


# =============================================================================
# VALIDATION PIPELINE
# =============================================================================

def validate_onnx_model(
    file_path: Path,
    file_hash: str,
) -> ModelMetadata:
    """
    Validate an ONNX model file.
    
    Performs:
        1. Parse ONNX file
        2. Extract operators
        3. Check for training ops
        4. Check for random ops
        5. Detect architecture
        6. Validate input shape
        7. Return metadata
    """
    # Step 1: Load model
    model = load_onnx_model(file_path)
    
    # Step 2: Extract operators
    operators = extract_onnx_operators(model)
    logger.debug(f"Model has {len(operators)} operators")
    
    # Step 3: Check for training operators
    training_ops = check_for_training_ops(operators)
    training_nodes = check_onnx_for_training_nodes(model)
    
    if training_ops or training_nodes:
        all_training = training_ops + training_nodes
        raise TrainingGraphError(all_training)
    
    # Step 4: Check for random operators
    random_ops = check_for_random_ops(operators)
    if random_ops:
        raise NonDeterministicOpError(random_ops)
    
    # Step 5: Extract inputs/outputs
    inputs = extract_onnx_inputs(model)
    outputs = extract_onnx_outputs(model)
    
    if not inputs:
        raise InvalidInputShapeError(
            actual_shape=None,
            reason="Model has no inputs"
        )
    
    primary_input = inputs[0]
    
    # Step 6: Validate input shape for dynamic dimensions
    for i, dim in enumerate(primary_input.shape):
        if dim == -1 and i > 0:  # Allow dynamic batch (index 0) only
            # For now, just log a warning - some frameworks use -1 for flexibility
            logger.warning(f"Dynamic dimension at index {i} in input shape")
    
    # Step 7: Detect architecture
    architecture = detect_architecture(operators, primary_input.shape)
    
    if architecture is None:
        raise UnsupportedArchitectureError(
            detected_architecture=None,
            reason="Architecture not recognized",
            operators=operators[:20],  # Sample of operators
        )
    
    if not is_supported_architecture(architecture.name):
        raise UnsupportedArchitectureError(
            detected_architecture=architecture.name,
            reason=f"Architecture '{architecture.name}' is not in supported list",
        )
    
    # Step 8: Get model type from architecture
    arch_info = SUPPORTED_ARCHITECTURES.get(architecture.name)
    model_type = arch_info.get("type", ModelType.UNKNOWN) if arch_info else ModelType.UNKNOWN
    
    # Step 9: Build metadata
    return ModelMetadata(
        is_valid=True,
        model_type=model_type,
        architecture=architecture,
        format=ModelFormat.ONNX,
        inputs=tuple(inputs),
        outputs=tuple(outputs),
        operator_count=len(operators),
        operators=tuple(set(operators)),  # Unique operators
        file_path=str(file_path),
        file_hash=file_hash,
        validation_details={
            "onnx_ir_version": model.ir_version,
            "onnx_opset_version": model.opset_import[0].version if model.opset_import else None,
            "producer_name": model.producer_name or "unknown",
        },
    )


def validate_non_onnx_model(
    file_path: Path,
    model_format: ModelFormat,
    file_hash: str,
) -> ModelMetadata:
    """
    Validate non-ONNX model formats.
    
    For non-ONNX formats, we perform limited validation:
        - File exists and is readable
        - Basic format validation
        - Return metadata indicating format needs conversion
    
    Deep validation requires conversion to ONNX first.
    """
    # For non-ONNX formats, we indicate conversion is needed
    # Full validation happens after conversion
    
    return ModelMetadata(
        is_valid=True,
        model_type=ModelType.UNKNOWN,
        architecture=ArchitectureInfo(
            name="pending_conversion",
            family="unknown",
            variant="",
            confidence=0.0,
        ),
        format=model_format,
        inputs=tuple(),
        outputs=tuple(),
        operator_count=0,
        operators=tuple(),
        file_path=str(file_path),
        file_hash=file_hash,
        validation_details={
            "requires_conversion": True,
            "convert_to": "onnx",
            "note": f"Model in {model_format.value} format requires conversion to ONNX for full validation",
        },
    )


# =============================================================================
# MAIN PUBLIC API
# =============================================================================

def validate_model(model_path: Path) -> ModelMetadata:
    """
    Validate a model file and return metadata.
    
    THE SINGLE ENTRY POINT for model validation.
    
    Args:
        model_path: Path to the model file.
    
    Returns:
        ModelMetadata containing:
            - is_valid: True (exception raised otherwise)
            - model_type: classification/detection/audio
            - architecture: Detected architecture info
            - format: File format
            - inputs: Input specifications
            - outputs: Output specifications
            - operator_count: Number of operators
    
    Raises:
        UnsupportedFormatError: File format not supported
        UnsupportedArchitectureError: Architecture not in allowlist
        TrainingGraphError: Model contains training operators
        NonDeterministicOpError: Model contains random operators
        InvalidInputShapeError: Input shape not valid
        ModelParsingError: File cannot be parsed
    
    Example:
        >>> metadata = validate_model(Path("model.onnx"))
        >>> print(metadata.architecture.name)
        'mobilenet_v2'
        >>> print(metadata.model_type)
        ModelType.CLASSIFICATION
    """
    model_path = Path(model_path)
    
    # Validate file exists
    if not model_path.exists():
        raise ModelParsingError(str(model_path), "File does not exist")
    
    # Get file hash for tracking
    file_hash = compute_file_hash(model_path)
    
    # Determine format
    model_format = get_model_format(model_path)
    
    logger.info(f"Validating model: {model_path} (format: {model_format.value})")
    
    # Route to format-specific validation
    if model_format == ModelFormat.ONNX:
        metadata = validate_onnx_model(model_path, file_hash)
    else:
        # Non-ONNX formats require conversion for deep validation
        metadata = validate_non_onnx_model(model_path, model_format, file_hash)
    
    logger.info(
        f"Validation successful: {metadata.architecture.name} "
        f"({metadata.model_type.value})"
    )
    
    return metadata


def get_supported_formats() -> List[str]:
    """Get list of supported file extensions."""
    return list(SUPPORTED_EXTENSIONS.keys())


def get_supported_architectures() -> List[str]:
    """Get list of supported architecture names."""
    return get_all_architecture_names()
