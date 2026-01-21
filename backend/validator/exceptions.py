"""
SOAC Model Validator Exceptions
===============================

Custom exception hierarchy for explainable validation failures.

DESIGN PRINCIPLE:
    Every rejection MUST include a specific reason code.
    No silent failures. No generic errors.
"""

from typing import Optional, Any, List


class ModelValidationError(Exception):
    """
    Base exception for ALL model validation failures.
    
    Attributes:
        message: Human-readable error description
        reason_code: Machine-readable rejection code
        context: Additional forensic details
    """
    
    def __init__(
        self,
        message: str,
        reason_code: str,
        context: Optional[dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.reason_code = reason_code
        self.context = context or {}
    
    def __str__(self) -> str:
        return f"[{self.reason_code}] {self.message}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "error": self.message,
            "reason_code": self.reason_code,
            "context": self.context,
        }


class UnsupportedFormatError(ModelValidationError):
    """
    Raised when file format is not supported.
    
    Supported formats: .onnx, .pt, .pth, .h5, .pkl, .joblib, .tflite, .mlmodel
    """
    
    def __init__(self, file_path: str, extension: str):
        super().__init__(
            f"Unsupported model format: {extension}",
            reason_code="FORMAT_NOT_SUPPORTED",
            context={"file_path": file_path, "extension": extension}
        )
        self.extension = extension


class UnsupportedArchitectureError(ModelValidationError):
    """
    Raised when model architecture is not in the strict allowlist.
    
    SOAC only supports specific pretrained inference models.
    Custom architectures are NOT allowed.
    """
    
    def __init__(
        self,
        detected_architecture: Optional[str] = None,
        reason: str = "Architecture not in supported list",
        operators: Optional[List[str]] = None
    ):
        super().__init__(
            f"Unsupported architecture: {reason}",
            reason_code="ARCHITECTURE_NOT_SUPPORTED",
            context={
                "detected_architecture": detected_architecture,
                "reason": reason,
                "sample_operators": operators[:10] if operators else []
            }
        )
        self.detected_architecture = detected_architecture


class TrainingGraphError(ModelValidationError):
    """
    Raised when model contains training-specific operators.
    
    SOAC only accepts INFERENCE models.
    Training graphs with optimizers, gradients, or loss functions are rejected.
    """
    
    def __init__(self, forbidden_ops: List[str]):
        super().__init__(
            f"Model contains training operators: {', '.join(forbidden_ops[:5])}",
            reason_code="TRAINING_GRAPH_DETECTED",
            context={"forbidden_operators": forbidden_ops}
        )
        self.forbidden_ops = forbidden_ops


class NonDeterministicOpError(ModelValidationError):
    """
    Raised when model contains non-deterministic operators.
    
    Random operations prevent reproducible inference and are rejected.
    """
    
    def __init__(self, random_ops: List[str]):
        super().__init__(
            f"Model contains non-deterministic operators: {', '.join(random_ops)}",
            reason_code="NON_DETERMINISTIC_OPS",
            context={"random_operators": random_ops}
        )
        self.random_ops = random_ops


class InvalidInputShapeError(ModelValidationError):
    """
    Raised when model has invalid or unsupported input shape.
    
    Causes:
        - Dynamic dimensions (except batch)
        - Shape doesn't match expected for architecture
        - Unsupported input format
    """
    
    def __init__(self, actual_shape: Any, expected_shape: Optional[Any] = None, reason: str = ""):
        super().__init__(
            f"Invalid input shape: {reason}" if reason else f"Invalid input shape: {actual_shape}",
            reason_code="INVALID_INPUT_SHAPE",
            context={
                "actual_shape": str(actual_shape),
                "expected_shape": str(expected_shape) if expected_shape else None,
                "reason": reason
            }
        )
        self.actual_shape = actual_shape
        self.expected_shape = expected_shape


class InvalidOutputShapeError(ModelValidationError):
    """
    Raised when model output doesn't match expected semantics.
    """
    
    def __init__(self, actual_shape: Any, model_type: str, reason: str = ""):
        super().__init__(
            f"Invalid output for {model_type}: {reason}",
            reason_code="INVALID_OUTPUT_SHAPE",
            context={
                "actual_shape": str(actual_shape),
                "model_type": model_type,
                "reason": reason
            }
        )


class ModelParsingError(ModelValidationError):
    """
    Raised when model file cannot be parsed.
    
    File may be corrupted or in an unexpected format.
    """
    
    def __init__(self, file_path: str, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"Failed to parse model: {reason}",
            reason_code="MODEL_PARSE_ERROR",
            context={
                "file_path": file_path,
                "reason": reason,
                "original_error": str(original_error) if original_error else None
            }
        )
        self.original_error = original_error


class DynamicShapeError(ModelValidationError):
    """
    Raised when model uses unsupported dynamic shapes.
    
    Dynamic batch dimension is allowed.
    Other dynamic dimensions are NOT supported.
    """
    
    def __init__(self, shape: Any, dimension: int):
        super().__init__(
            f"Dynamic shape not supported at dimension {dimension}",
            reason_code="DYNAMIC_SHAPE_NOT_SUPPORTED",
            context={"shape": str(shape), "dynamic_dimension": dimension}
        )
