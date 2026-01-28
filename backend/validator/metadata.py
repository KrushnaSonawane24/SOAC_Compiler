"""
SOAC Model Metadata Structures
==============================

Dataclasses for structured validation output.
All fields are immutable to prevent accidental modification.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ModelType(str, Enum):
    """Supported model task types."""
    CLASSIFICATION = "classification"
    DETECTION = "detection"
    AUDIO = "audio"
    UNKNOWN = "unknown"


class ModelFormat(str, Enum):
    """Supported model file formats."""
    ONNX = "onnx"
    PYTORCH = "pytorch"
    KERAS_H5 = "keras_h5"
    TFLITE = "tflite"
    TENSORRT_ENGINE = "tensorrt_engine"
    COREML = "coreml"
    PICKLE = "pickle"
    JOBLIB = "joblib"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class InputSpec:
    """
    Model input specification.
    
    Attributes:
        name: Input tensor name
        shape: Input shape (list of ints, -1 for dynamic batch)
        dtype: Data type string (e.g., "float32")
    """
    name: str
    shape: tuple
    dtype: str


@dataclass(frozen=True)
class OutputSpec:
    """
    Model output specification.
    
    Attributes:
        name: Output tensor name
        shape: Output shape (list of ints)
        dtype: Data type string
    """
    name: str
    shape: tuple
    dtype: str


@dataclass(frozen=True)
class ArchitectureInfo:
    """
    Detected architecture information.
    
    Attributes:
        name: Canonical architecture name (e.g., "mobilenet_v2")
        family: Architecture family (e.g., "mobilenet")
        variant: Specific variant (e.g., "v2", "small", "50")
        confidence: Detection confidence (0.0 to 1.0)
    """
    name: str
    family: str
    variant: str = ""
    confidence: float = 1.0


@dataclass(frozen=True)
class ModelMetadata:
    """
    Complete validated model metadata.
    
    Returned by validate_model() on successful validation.
    All fields are guaranteed to be populated.
    
    Attributes:
        is_valid: Always True if returned (exception raised otherwise)
        model_type: Task type (classification/detection/audio)
        architecture: Detected architecture info
        format: Original file format
        inputs: List of input specifications
        outputs: List of output specifications
        operator_count: Total number of operators in graph
        operators: List of unique operator types used
        file_path: Original file path
        file_hash: SHA-256 hash of the file
        validation_details: Additional validation info
    """
    is_valid: bool
    model_type: ModelType
    architecture: ArchitectureInfo
    format: ModelFormat
    inputs: tuple  # tuple of InputSpec
    outputs: tuple  # tuple of OutputSpec
    operator_count: int
    operators: tuple  # tuple of operator names
    file_path: str
    file_hash: str
    validation_details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "is_valid": self.is_valid,
            "model_type": self.model_type.value,
            "architecture": {
                "name": self.architecture.name,
                "family": self.architecture.family,
                "variant": self.architecture.variant,
                "confidence": self.architecture.confidence,
            },
            "format": self.format.value,
            "inputs": [
                {"name": i.name, "shape": list(i.shape), "dtype": i.dtype}
                for i in self.inputs
            ],
            "outputs": [
                {"name": o.name, "shape": list(o.shape), "dtype": o.dtype}
                for o in self.outputs
            ],
            "operator_count": self.operator_count,
            "operators": list(self.operators),
            "file_path": self.file_path,
            "file_hash": self.file_hash,
            "validation_details": self.validation_details,
        }


# =============================================================================
# SUPPORTED ARCHITECTURES REGISTRY
# =============================================================================

SUPPORTED_ARCHITECTURES: Dict[str, Dict[str, Any]] = {
    # Image Classification
    "mobilenet_v2": {
        "family": "mobilenet",
        "type": ModelType.CLASSIFICATION,
        "input_shapes": [(1, 3, 224, 224), (-1, 3, 224, 224)],
        "variants": ["v2"],
    },
    "mobilenet_v3_small": {
        "family": "mobilenet",
        "type": ModelType.CLASSIFICATION,
        "input_shapes": [(1, 3, 224, 224), (-1, 3, 224, 224)],
        "variants": ["v3_small", "v3-small"],
    },
    "mobilenet_v3_large": {
        "family": "mobilenet",
        "type": ModelType.CLASSIFICATION,
        "input_shapes": [(1, 3, 224, 224), (-1, 3, 224, 224)],
        "variants": ["v3_large", "v3-large"],
    },
    "resnet18": {
        "family": "resnet",
        "type": ModelType.CLASSIFICATION,
        "input_shapes": [(1, 3, 224, 224), (-1, 3, 224, 224)],
        "variants": ["18"],
    },
    "resnet50": {
        "family": "resnet",
        "type": ModelType.CLASSIFICATION,
        "input_shapes": [(1, 3, 224, 224), (-1, 3, 224, 224)],
        "variants": ["50"],
    },
    "efficientnet_b0": {
        "family": "efficientnet",
        "type": ModelType.CLASSIFICATION,
        "input_shapes": [(1, 3, 224, 224), (-1, 3, 224, 224)],
        "variants": ["b0"],
    },
    "shufflenet_v2": {
        "family": "shufflenet",
        "type": ModelType.CLASSIFICATION,
        "input_shapes": [(1, 3, 224, 224), (-1, 3, 224, 224)],
        "variants": ["v2"],
    },
    "squeezenet1_0": {
        "family": "squeezenet",
        "type": ModelType.CLASSIFICATION,
        "input_shapes": [(1, 3, 224, 224), (-1, 3, 224, 224)],
        "variants": ["1.0", "1_0"],
    },
    "squeezenet1_1": {
        "family": "squeezenet",
        "type": ModelType.CLASSIFICATION,
        "input_shapes": [(1, 3, 224, 224), (-1, 3, 224, 224)],
        "variants": ["1.1", "1_1"],
    },
    
    # Object Detection
    "ssd_mobilenet_v2": {
        "family": "ssd",
        "type": ModelType.DETECTION,
        "input_shapes": [(1, 3, 300, 300), (-1, 3, 300, 300)],
        "variants": ["mobilenet_v2"],
    },
    "yolov5n": {
        "family": "yolo",
        "type": ModelType.DETECTION,
        "input_shapes": [(1, 3, 640, 640), (-1, 3, 640, 640)],
        "variants": ["n", "nano"],
    },
    "yolov5s": {
        "family": "yolo",
        "type": ModelType.DETECTION,
        "input_shapes": [(1, 3, 640, 640), (-1, 3, 640, 640)],
        "variants": ["s", "small"],
    },
    
    # Audio
    "yamnet": {
        "family": "yamnet",
        "type": ModelType.AUDIO,
        "input_shapes": [(1, 16000), (-1, 16000)],
        "variants": [],
    },
    "wav2vec2_tiny": {
        "family": "wav2vec2",
        "type": ModelType.AUDIO,
        "input_shapes": [(1, 16000), (-1, 16000)],
        "variants": ["tiny", "inference"],
    },
}


def get_architecture_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get architecture info by canonical name."""
    return SUPPORTED_ARCHITECTURES.get(name.lower())


def get_all_architecture_names() -> List[str]:
    """Get list of all supported architecture names."""
    return list(SUPPORTED_ARCHITECTURES.keys())
