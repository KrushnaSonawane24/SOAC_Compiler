"""
SOAC Deployment Package
=======================

Deployment Artifact Generation Unit.

PUBLIC API:
    - generate_deployment_artifacts(onnx_path, ...) -> DeploymentBundle

TARGETS:
    - Android: TFLite (.tflite)
    - iOS: CoreML (.mlmodel)
    - CPU: ONNX Runtime package
    - GPU: TensorRT (.plan)
"""

# Main API
from .pipeline_packaging import (
    generate_deployment_artifacts,
    get_available_targets,
)

# Metadata
from .metadata import (
    DeploymentBundle,
    DeploymentArtifact,
    TargetPlatform,
    ArtifactStatus,
    create_timestamp,
)

# Individual converters
from .tflite import convert_onnx_to_tflite, is_tflite_available
from .onnxruntime_pkg import create_onnxruntime_package, is_onnxruntime_available
from .tensorrt import build_tensorrt_engine, is_tensorrt_available
from .coreml import convert_onnx_to_coreml, is_coreml_available

# Exceptions
from .exceptions import (
    DeploymentError,
    TFLiteConversionError,
    CoreMLConversionError,
    TensorRTConversionError,
    ToolchainNotAvailable,
    PackagingError,
    ArtifactValidationError,
)

__version__ = "1.0.0"

__all__ = [
    # Main API
    "generate_deployment_artifacts",
    "get_available_targets",
    
    # Metadata
    "DeploymentBundle",
    "DeploymentArtifact",
    "TargetPlatform",
    "ArtifactStatus",
    
    # Converters
    "convert_onnx_to_tflite",
    "create_onnxruntime_package",
    "build_tensorrt_engine",
    "convert_onnx_to_coreml",
    
    # Availability checks
    "is_tflite_available",
    "is_onnxruntime_available",
    "is_tensorrt_available",
    "is_coreml_available",
    
    # Exceptions
    "DeploymentError",
    "TFLiteConversionError",
    "CoreMLConversionError",
    "TensorRTConversionError",
    "ToolchainNotAvailable",
    "PackagingError",
]
