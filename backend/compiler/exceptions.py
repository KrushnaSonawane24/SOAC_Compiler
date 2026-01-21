"""
SOAC Compiler Exceptions
========================

Custom exception hierarchy for conversion and canonicalization failures.
"""

from typing import Optional, Any, List


class CompilerError(Exception):
    """
    Base exception for ALL compiler-related failures.
    
    Attributes:
        message: Human-readable error description
        error_code: Machine-readable code
        context: Additional details
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        context: Optional[dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "error": self.message,
            "error_code": self.error_code,
            "context": self.context,
        }


class ConversionError(CompilerError):
    """
    Raised when model format conversion fails.
    
    Common causes:
        - Unsupported format
        - Corrupt input file
        - Missing converter dependency
    """
    
    def __init__(
        self,
        source_format: str,
        target_format: str,
        reason: str,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            f"Failed to convert from {source_format} to {target_format}: {reason}",
            error_code="CONVERSION_FAILED",
            context={
                "source_format": source_format,
                "target_format": target_format,
                "reason": reason,
                "original_error": str(original_error) if original_error else None
            }
        )
        self.source_format = source_format
        self.target_format = target_format
        self.original_error = original_error


class UnsupportedFormatError(CompilerError):
    """
    Raised when input format is not supported for conversion.
    """
    
    def __init__(self, file_path: str, extension: str):
        super().__init__(
            f"Cannot convert format: {extension}",
            error_code="FORMAT_NOT_CONVERTIBLE",
            context={"file_path": file_path, "extension": extension}
        )
        self.extension = extension


class CanonializationError(CompilerError):
    """
    Raised when graph canonicalization fails.
    """
    
    def __init__(self, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"Canonicalization failed: {reason}",
            error_code="CANONICALIZATION_FAILED",
            context={
                "reason": reason,
                "original_error": str(original_error) if original_error else None
            }
        )
        self.original_error = original_error


class UnsupportedOpError(CompilerError):
    """
    Raised when graph contains unsupported operators.
    
    SOAC only supports standard ONNX operators.
    Custom or framework-specific ops are rejected.
    """
    
    def __init__(self, unsupported_ops: List[str]):
        super().__init__(
            f"Unsupported operators: {', '.join(unsupported_ops[:5])}",
            error_code="UNSUPPORTED_OPS",
            context={"unsupported_ops": unsupported_ops}
        )
        self.unsupported_ops = unsupported_ops


class ShapeInferenceError(CompilerError):
    """
    Raised when shape inference fails.
    """
    
    def __init__(self, reason: str, node_name: Optional[str] = None):
        super().__init__(
            f"Shape inference failed: {reason}",
            error_code="SHAPE_INFERENCE_FAILED",
            context={"reason": reason, "node_name": node_name}
        )


class GraphValidationError(CompilerError):
    """
    Raised when ONNX graph validation fails.
    """
    
    def __init__(self, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"Graph validation failed: {reason}",
            error_code="GRAPH_VALIDATION_FAILED",
            context={
                "reason": reason,
                "original_error": str(original_error) if original_error else None
            }
        )
        self.original_error = original_error


class OpsetConversionError(CompilerError):
    """
    Raised when opset conversion fails.
    """
    
    def __init__(self, source_opset: int, target_opset: int, reason: str):
        super().__init__(
            f"Cannot convert opset {source_opset} to {target_opset}: {reason}",
            error_code="OPSET_CONVERSION_FAILED",
            context={
                "source_opset": source_opset,
                "target_opset": target_opset,
                "reason": reason
            }
        )
