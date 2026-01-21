"""
SOAC Compiler Package
=====================

ONNX Canonicalization & Conversion Unit.

PUBLIC API:
    - canonicalize_model(input_path) -> CanonicalOnnxModel
      THE ONLY function external code should call.

SUPPORTED INPUT FORMATS:
    - .onnx - ONNX format (normalized)
    - .h5, .keras - TensorFlow/Keras
    - .tflite - TensorFlow Lite
    - .mlmodel - CoreML
    - SavedModel directories

OUTPUT:
    - Canonical ONNX with opset 17
    - Deterministic graph hash
    - Input/output metadata

For more details, see: backend/compiler/README.md
"""

# Main public API
from .onnx_canonicalizer import (
    canonicalize_model,
    CanonicalOnnxModel,
    InputSpec,
    OutputSpec,
    TARGET_OPSET_VERSION,
    SUPPORTED_OPERATORS,
)

# Format conversion
from .onnx_converter import (
    convert_to_onnx,
    detect_format,
    get_supported_formats,
    InputFormat,
)

# Graph operations
from .graph_normalizer import normalize_graph
from .shape_inference import infer_shapes, get_input_shapes, get_output_shapes
from .hashing import compute_graph_hash, compute_structure_hash

# Exceptions
from .exceptions import (
    CompilerError,
    ConversionError,
    UnsupportedFormatError,
    CanonializationError,
    UnsupportedOpError,
    ShapeInferenceError,
    GraphValidationError,
    OpsetConversionError,
)

__version__ = "1.0.0"

__all__ = [
    # Main function
    "canonicalize_model",
    "CanonicalOnnxModel",
    "InputSpec",
    "OutputSpec",
    
    # Configuration
    "TARGET_OPSET_VERSION",
    "SUPPORTED_OPERATORS",
    
    # Conversion
    "convert_to_onnx",
    "detect_format",
    "get_supported_formats",
    "InputFormat",
    
    # Graph operations
    "normalize_graph",
    "infer_shapes",
    "get_input_shapes",
    "get_output_shapes",
    "compute_graph_hash",
    "compute_structure_hash",
    
    # Exceptions
    "CompilerError",
    "ConversionError",
    "UnsupportedFormatError",
    "CanonializationError",
    "UnsupportedOpError",
    "ShapeInferenceError",
    "GraphValidationError",
    "OpsetConversionError",
]
