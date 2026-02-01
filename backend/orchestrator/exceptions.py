"""
SOAC Orchestrator Exceptions
============================

Custom exceptions for pipeline failures.
"""

from typing import Optional, Any
from enum import Enum


class PipelineStage(str, Enum):
    """Pipeline stages for error tracking."""
    PENDING = "pending"
    NORMALIZING = "normalizing"
    VALIDATING = "validating"
    CANONICALIZING = "canonicalizing"
    OPTIMIZING = "optimizing"
    BENCHMARKING = "benchmarking"
    SELECTING = "selecting"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineError(Exception):
    """Base exception for pipeline failures."""
    
    def __init__(
        self,
        message: str,
        stage: PipelineStage,
        job_id: str,
        error_code: str,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.stage = stage
        self.job_id = job_id
        self.error_code = error_code
        self.context = context or {}
        self.original_error = original_error
    
    def __str__(self) -> str:
        return f"[{self.error_code}] Job {self.job_id} failed at {self.stage.value}: {self.message}"
    
    def to_dict(self) -> dict:
        return {
            "error": self.message,
            "error_code": self.error_code,
            "stage": self.stage.value,
            "job_id": self.job_id,
            "context": self.context,
            "original_error": str(self.original_error) if self.original_error else None,
        }


class ValidationFailedError(PipelineError):
    """Model validation failed."""
    
    def __init__(self, job_id: str, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=reason,
            stage=PipelineStage.VALIDATING,
            job_id=job_id,
            error_code="VALIDATION_FAILED",
            original_error=original_error,
        )


class NormalizationFailedError(PipelineError):
    """Input model normalization (to ONNX baseline) failed."""

    def __init__(self, job_id: str, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=reason,
            stage=PipelineStage.NORMALIZING,
            job_id=job_id,
            error_code="NORMALIZATION_FAILED",
            original_error=original_error,
        )


class CanonicalizationFailedError(PipelineError):
    """Canonicalization failed."""
    
    def __init__(self, job_id: str, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=reason,
            stage=PipelineStage.CANONICALIZING,
            job_id=job_id,
            error_code="CANONICALIZATION_FAILED",
            original_error=original_error,
        )


class OptimizationFailedError(PipelineError):
    """Optimization failed."""
    
    def __init__(self, job_id: str, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=reason,
            stage=PipelineStage.OPTIMIZING,
            job_id=job_id,
            error_code="OPTIMIZATION_FAILED",
            original_error=original_error,
        )


class BenchmarkingFailedError(PipelineError):
    """Benchmarking failed."""
    
    def __init__(self, job_id: str, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=reason,
            stage=PipelineStage.BENCHMARKING,
            job_id=job_id,
            error_code="BENCHMARKING_FAILED",
            original_error=original_error,
        )


class SelectionFailedError(PipelineError):
    """ALO selection failed."""
    
    def __init__(self, job_id: str, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=reason,
            stage=PipelineStage.SELECTING,
            job_id=job_id,
            error_code="SELECTION_FAILED",
            original_error=original_error,
        )


class DeploymentFailedError(PipelineError):
    """Deployment failed."""
    
    def __init__(self, job_id: str, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=reason,
            stage=PipelineStage.DEPLOYING,
            job_id=job_id,
            error_code="DEPLOYMENT_FAILED",
            original_error=original_error,
        )


class AccuracyConstraintError(PipelineError):
    """All variants failed accuracy constraint."""
    
    def __init__(self, job_id: str, variants_tested: int, threshold: float):
        super().__init__(
            message=f"All {variants_tested} variants exceeded accuracy threshold {threshold:.2%}",
            stage=PipelineStage.SELECTING,
            job_id=job_id,
            error_code="ACCURACY_CONSTRAINT_FAILED",
            context={"variants_tested": variants_tested, "threshold": threshold},
        )
