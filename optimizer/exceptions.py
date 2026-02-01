"""
SOAC Optimizer Exceptions
=========================

Custom exception hierarchy for optimization failures.
"""

from typing import Optional, Any, List


class OptimizerError(Exception):
    """
    Base exception for ALL optimizer-related failures.
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
        return {
            "error": self.message,
            "error_code": self.error_code,
            "context": self.context,
        }


class VariantGenerationError(OptimizerError):
    """
    Raised when variant generation fails.
    """
    
    def __init__(self, variant_type: str, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"Failed to generate {variant_type} variant: {reason}",
            error_code="VARIANT_GENERATION_FAILED",
            context={
                "variant_type": variant_type,
                "reason": reason,
                "original_error": str(original_error) if original_error else None
            }
        )
        self.variant_type = variant_type
        self.original_error = original_error


class QuantizationError(OptimizerError):
    """
    Raised when quantization fails.
    """
    
    def __init__(self, method: str, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"Quantization ({method}) failed: {reason}",
            error_code="QUANTIZATION_FAILED",
            context={
                "method": method,
                "reason": reason,
                "original_error": str(original_error) if original_error else None
            }
        )
        self.method = method
        self.original_error = original_error


class PruningError(OptimizerError):
    """
    Raised when pruning fails.
    """
    
    def __init__(self, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"Pruning failed: {reason}",
            error_code="PRUNING_FAILED",
            context={
                "reason": reason,
                "original_error": str(original_error) if original_error else None
            }
        )
        self.original_error = original_error


class AccuracyConstraintViolation(OptimizerError):
    """
    Raised when variant exceeds accuracy drop threshold.
    
    This is NOT necessarily an error - it means the variant was rejected.
    """
    
    def __init__(self, variant_id: str, accuracy_drop: float, threshold: float):
        super().__init__(
            f"Variant {variant_id} rejected: accuracy drop {accuracy_drop:.2%} > threshold {threshold:.2%}",
            error_code="ACCURACY_CONSTRAINT_VIOLATED",
            context={
                "variant_id": variant_id,
                "accuracy_drop": accuracy_drop,
                "threshold": threshold
            }
        )
        self.accuracy_drop = accuracy_drop
        self.threshold = threshold


class NoValidVariantsError(OptimizerError):
    """
    Raised when NO variants pass accuracy validation.
    """
    
    def __init__(self, total_variants: int, reasons: List[str]):
        super().__init__(
            f"All {total_variants} variants failed validation",
            error_code="NO_VALID_VARIANTS",
            context={
                "total_variants": total_variants,
                "rejection_reasons": reasons
            }
        )


class BenchmarkError(OptimizerError):
    """
    Raised when benchmarking fails.
    """
    
    def __init__(self, variant_id: str, reason: str, original_error: Optional[Exception] = None):
        super().__init__(
            f"Benchmark failed for {variant_id}: {reason}",
            error_code="BENCHMARK_FAILED",
            context={
                "variant_id": variant_id,
                "reason": reason,
                "original_error": str(original_error) if original_error else None
            }
        )
        self.original_error = original_error
