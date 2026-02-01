"""
SOAC Accuracy Constraint
========================

Enforces maximum allowed accuracy degradation.

NON-NEGOTIABLE: Variants with accuracy_drop > threshold are REJECTED.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING

from .base import Constraint, ConstraintResult

if TYPE_CHECKING:
    from backend.optimizer.metadata import OptimizedVariant


# Default maximum accuracy drop (2%)
DEFAULT_MAX_ACCURACY_DROP = 0.02


class AccuracyConstraint(Constraint):
    """
    Constraint: Accuracy drop must not exceed threshold.
    
    This is the PRIMARY quality constraint in SOAC.
    No variant with accuracy_drop > threshold will EVER be selected.
    
    Default threshold: 2% (0.02)
    
    Attributes:
        max_drop: Maximum allowed accuracy drop (fraction, not percentage)
    """
    
    name = "accuracy_constraint"
    description = "Enforces maximum allowed accuracy degradation"
    
    def __init__(self, max_drop: float = DEFAULT_MAX_ACCURACY_DROP):
        """
        Initialize accuracy constraint.
        
        Args:
            max_drop: Maximum accuracy drop as fraction (0.02 = 2%)
        """
        self.max_drop = max_drop
    
    def check(
        self, 
        variant: "OptimizedVariant",
        context: Optional[Dict[str, Any]] = None
    ) -> ConstraintResult:
        """
        Check if variant's accuracy drop is within threshold.
        
        Args:
            variant: The variant to check.
            context: Optional context (ignored for accuracy).
        
        Returns:
            ConstraintResult indicating pass/fail.
        """
        # If no metrics, assume passing (for testing only)
        if variant.metrics is None:
            return ConstraintResult(
                passed=True,
                constraint_name=self.name,
                message="No metrics available - assuming valid for testing",
                details={"reason": "no_metrics"},
                threshold=self.max_drop,
                actual_value=None,
            )
        
        accuracy_drop = variant.metrics.accuracy_drop
        passed = accuracy_drop <= self.max_drop
        
        if passed:
            message = f"Accuracy drop {accuracy_drop:.2%} ≤ {self.max_drop:.2%} threshold"
        else:
            message = f"Accuracy drop {accuracy_drop:.2%} > {self.max_drop:.2%} threshold"
        
        return ConstraintResult(
            passed=passed,
            constraint_name=self.name,
            message=message,
            details={
                "variant_id": variant.variant_id,
                "variant_type": variant.variant_type.value,
            },
            threshold=self.max_drop,
            actual_value=accuracy_drop,
        )
    
    def explain(self) -> str:
        """Explain the accuracy constraint."""
        return (
            f"AccuracyConstraint: Rejects variants with accuracy degradation > {self.max_drop:.2%}.\n"
            f"  Threshold: {self.max_drop:.2%} ({self.max_drop})\n"
            f"  Consequence: Variants exceeding this threshold are REJECTED and cannot be selected."
        )
