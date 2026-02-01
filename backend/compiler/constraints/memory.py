"""
SOAC Memory Constraint
======================

Enforces maximum allowed memory usage.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING

from .base import Constraint, ConstraintResult

if TYPE_CHECKING:
    from backend.optimizer.metadata import OptimizedVariant


# Default maximum memory (512 MB)
DEFAULT_MAX_MEMORY_MB = 512


class MemoryConstraint(Constraint):
    """
    Constraint: Peak memory usage must not exceed limit.
    
    Useful for deployment targets with limited memory.
    
    Attributes:
        max_memory_mb: Maximum allowed memory in megabytes
    """
    
    name = "memory_constraint"
    description = "Enforces maximum allowed memory usage"
    
    def __init__(self, max_memory_mb: float = DEFAULT_MAX_MEMORY_MB):
        """
        Initialize memory constraint.
        
        Args:
            max_memory_mb: Maximum memory limit in megabytes
        """
        self.max_memory_mb = max_memory_mb
    
    def check(
        self, 
        variant: "OptimizedVariant",
        context: Optional[Dict[str, Any]] = None
    ) -> ConstraintResult:
        """
        Check if variant's memory usage is within limit.
        
        Args:
            variant: The variant to check.
            context: Optional context with 'max_memory_mb' override.
        
        Returns:
            ConstraintResult indicating pass/fail.
        """
        # Get limit from context if provided
        limit_mb = self.max_memory_mb
        if context and "max_memory_mb" in context:
            limit_mb = context["max_memory_mb"]
        
        # If no metrics, assume passing
        if variant.metrics is None:
            return ConstraintResult(
                passed=True,
                constraint_name=self.name,
                message="No metrics available - assuming valid",
                details={"reason": "no_metrics"},
                threshold=limit_mb,
                actual_value=None,
            )
        
        memory_mb = variant.metrics.memory_mb
        passed = memory_mb <= limit_mb
        
        if passed:
            message = f"Memory {memory_mb:.1f}MB ≤ {limit_mb:.1f}MB limit"
        else:
            message = f"Memory {memory_mb:.1f}MB > {limit_mb:.1f}MB limit"
        
        return ConstraintResult(
            passed=passed,
            constraint_name=self.name,
            message=message,
            details={
                "variant_id": variant.variant_id,
                "variant_type": variant.variant_type.value,
            },
            threshold=limit_mb,
            actual_value=memory_mb,
        )
    
    def explain(self) -> str:
        """Explain the memory constraint."""
        return (
            f"MemoryConstraint: Rejects variants with memory usage > {self.max_memory_mb:.1f}MB.\n"
            f"  Limit: {self.max_memory_mb:.1f}MB\n"
            f"  Consequence: Variants exceeding this limit are REJECTED."
        )
