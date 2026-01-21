"""
SOAC Benchmark Exceptions
=========================

Custom exceptions for benchmarking failures.
"""

from typing import Optional, Any, List


class BenchmarkError(Exception):
    """Base exception for ALL benchmark-related failures."""
    
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


class AccuracyMeasurementError(BenchmarkError):
    """Raised when accuracy measurement fails."""
    
    def __init__(self, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"Failed to measure accuracy: {reason}",
            error_code="ACCURACY_MEASUREMENT_FAILED",
            context={
                "reason": reason,
                "original_error": str(original_error) if original_error else None
            }
        )
        self.original_error = original_error


class AccuracyConstraintViolation(BenchmarkError):
    """Raised when model exceeds accuracy drop threshold."""
    
    def __init__(self, baseline: float, measured: float, threshold: float):
        drop = baseline - measured
        super().__init__(
            f"Accuracy drop {drop:.2%} exceeds threshold {threshold:.2%}",
            error_code="ACCURACY_CONSTRAINT_VIOLATED",
            context={
                "baseline_accuracy": baseline,
                "measured_accuracy": measured,
                "accuracy_drop": drop,
                "threshold": threshold,
            }
        )
        self.baseline = baseline
        self.measured = measured
        self.threshold = threshold


class LatencyMeasurementError(BenchmarkError):
    """Raised when latency measurement fails."""
    
    def __init__(self, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"Failed to measure latency: {reason}",
            error_code="LATENCY_MEASUREMENT_FAILED",
            context={
                "reason": reason,
                "original_error": str(original_error) if original_error else None
            }
        )


class MemoryMeasurementError(BenchmarkError):
    """Raised when memory measurement fails."""
    
    def __init__(self, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"Failed to measure memory: {reason}",
            error_code="MEMORY_MEASUREMENT_FAILED",
            context={
                "reason": reason,
                "original_error": str(original_error) if original_error else None
            }
        )


class DatasetError(BenchmarkError):
    """Raised when dataset loading or processing fails."""
    
    def __init__(self, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"Dataset error: {reason}",
            error_code="DATASET_ERROR",
            context={
                "reason": reason,
                "original_error": str(original_error) if original_error else None
            }
        )


class InferenceError(BenchmarkError):
    """Raised when model inference fails."""
    
    def __init__(self, model_path: str, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"Inference failed for {model_path}: {reason}",
            error_code="INFERENCE_FAILED",
            context={
                "model_path": model_path,
                "reason": reason,
                "original_error": str(original_error) if original_error else None
            }
        )


class InvalidBenchmarkConfig(BenchmarkError):
    """Raised when benchmark configuration is invalid."""
    
    def __init__(self, reason: str):
        super().__init__(
            f"Invalid benchmark config: {reason}",
            error_code="INVALID_BENCHMARK_CONFIG",
            context={"reason": reason}
        )
