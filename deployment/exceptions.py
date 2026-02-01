"""
SOAC Deployment Exceptions
==========================

Custom exceptions for deployment failures.
"""

from typing import Optional, Any


class DeploymentError(Exception):
    """Base exception for deployment failures."""
    
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
        return {
            "error": self.message,
            "error_code": self.error_code,
            "context": self.context,
        }


class TFLiteConversionError(DeploymentError):
    """TFLite conversion failed."""
    
    def __init__(self, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"TFLite conversion failed: {reason}",
            error_code="TFLITE_CONVERSION_FAILED",
            context={"reason": reason, "original_error": str(original_error) if original_error else None}
        )


class CoreMLConversionError(DeploymentError):
    """CoreML conversion failed."""
    
    def __init__(self, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"CoreML conversion failed: {reason}",
            error_code="COREML_CONVERSION_FAILED",
            context={"reason": reason, "original_error": str(original_error) if original_error else None}
        )


class TensorRTConversionError(DeploymentError):
    """TensorRT engine build failed."""
    
    def __init__(self, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"TensorRT build failed: {reason}",
            error_code="TENSORRT_BUILD_FAILED",
            context={"reason": reason, "original_error": str(original_error) if original_error else None}
        )


class ToolchainNotAvailable(DeploymentError):
    """Required toolchain not installed."""
    
    def __init__(self, toolchain: str, install_hint: str = ""):
        super().__init__(
            f"Toolchain not available: {toolchain}",
            error_code="TOOLCHAIN_NOT_AVAILABLE",
            context={"toolchain": toolchain, "install_hint": install_hint}
        )
        self.toolchain = toolchain


class PackagingError(DeploymentError):
    """Artifact packaging failed."""
    
    def __init__(self, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"Packaging failed: {reason}",
            error_code="PACKAGING_FAILED",
            context={"reason": reason, "original_error": str(original_error) if original_error else None}
        )


class ArtifactValidationError(DeploymentError):
    """Generated artifact is invalid."""
    
    def __init__(self, artifact_type: str, reason: str):
        super().__init__(
            f"Invalid {artifact_type} artifact: {reason}",
            error_code="ARTIFACT_VALIDATION_FAILED",
            context={"artifact_type": artifact_type, "reason": reason}
        )
