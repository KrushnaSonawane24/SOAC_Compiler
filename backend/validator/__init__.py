"""
SOAC Model Validator Package
============================

Strict validation for supported inference models only.

PUBLIC API:
    - validate_model(model_path) -> ModelMetadata
      THE ONLY function external code should call.

SUPPORTED FORMATS:
    - .onnx (full validation)
    - .pt, .pth (PyTorch - requires conversion)
    - .h5, .keras (Keras - requires conversion)
    - .tflite (TensorFlow Lite - requires conversion)
    - .mlmodel (CoreML - requires conversion)
    - .pkl, .joblib (Pickle - requires conversion)

SUPPORTED ARCHITECTURES:
    Classification: MobileNetV2/V3, ResNet18/50, EfficientNet-B0, ShuffleNet, SqueezeNet
    Detection: SSD-MobileNet-V2, YOLOv5n/s
    Audio: YAMNet, Wav2Vec2-Tiny

REJECTION CODES:
    - FORMAT_NOT_SUPPORTED: File format not in allowed list
    - ARCHITECTURE_NOT_SUPPORTED: Model not in supported architectures
    - TRAINING_GRAPH_DETECTED: Model contains training operators
    - NON_DETERMINISTIC_OPS: Model contains random operators
    - INVALID_INPUT_SHAPE: Input shape not valid for architecture

For more details, see: backend/validator/README.md
"""

# Public API
from .model_validator import (
    validate_model,
    get_supported_formats,
    get_supported_architectures,
)

# Metadata types
from .metadata import (
    ModelType,
    ModelFormat,
    ModelMetadata,
    ArchitectureInfo,
    InputSpec,
    OutputSpec,
    SUPPORTED_ARCHITECTURES,
)

# Exceptions
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

# Version
__version__ = "1.0.0"

__all__ = [
    # Main function
    "validate_model",
    "get_supported_formats",
    "get_supported_architectures",
    
    # Types
    "ModelType",
    "ModelFormat",
    "ModelMetadata",
    "ArchitectureInfo",
    "InputSpec",
    "OutputSpec",
    "SUPPORTED_ARCHITECTURES",
    
    # Exceptions
    "ModelValidationError",
    "UnsupportedFormatError",
    "UnsupportedArchitectureError",
    "TrainingGraphError",
    "NonDeterministicOpError",
    "InvalidInputShapeError",
    "ModelParsingError",
    "DynamicShapeError",
]
