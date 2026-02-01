"""
SOAC Backend Support Constraint
===============================

Enforces that variant supports the target backend.
"""

from typing import Dict, Any, Optional, Set, TYPE_CHECKING

from .base import Constraint, ConstraintResult

if TYPE_CHECKING:
    from backend.optimizer.metadata import OptimizedVariant


# Default target backends (all supported)
DEFAULT_TARGET_BACKENDS = frozenset({"cpu", "gpu", "mobile", "tpu", "npu"})


class BackendSupportConstraint(Constraint):
    """
    Constraint: Variant must support the target backend(s).
    
    Ensures that optimization doesn't produce a variant
    that cannot run on the intended deployment target.
    
    Attributes:
        target_backends: Set of required backend names
    """
    
    name = "backend_support_constraint"
    description = "Enforces variant compatibility with target backend"
    
    def __init__(self, target_backends: Optional[Set[str]] = None):
        """
        Initialize backend support constraint.
        
        Args:
            target_backends: Set of required backends (e.g., {"cpu", "gpu"})
        """
        self.target_backends = target_backends or set()
    
    def check(
        self, 
        variant: "OptimizedVariant",
        context: Optional[Dict[str, Any]] = None
    ) -> ConstraintResult:
        """
        Check if variant supports required backends.
        
        Args:
            variant: The variant to check.
            context: Optional context with 'target_backends' override.
        
        Returns:
            ConstraintResult indicating pass/fail.
        """
        # Get target from context if provided
        targets = self.target_backends
        if context and "target_backends" in context:
            targets = set(context["target_backends"])
        
        # If no targets specified, always pass
        if not targets:
            return ConstraintResult(
                passed=True,
                constraint_name=self.name,
                message="No specific backend required",
                details={"reason": "no_target_specified"},
            )
        
        # Check variant's supported backends
        # For now, we'll do a simple check based on variant type
        # In future, this would check against IR operator support
        variant_supports = self._get_variant_backends(variant)
        
        missing = targets - variant_supports
        passed = len(missing) == 0
        
        if passed:
            message = f"Variant supports required backends: {', '.join(sorted(targets))}"
        else:
            message = f"Variant missing backend support: {', '.join(sorted(missing))}"
        
        return ConstraintResult(
            passed=passed,
            constraint_name=self.name,
            message=message,
            details={
                "variant_id": variant.variant_id,
                "variant_type": variant.variant_type.value,
                "required_backends": list(targets),
                "supported_backends": list(variant_supports),
                "missing_backends": list(missing),
            },
        )
    
    def _get_variant_backends(self, variant: "OptimizedVariant") -> Set[str]:
        """
        Determine which backends a variant supports.
        
        Default: All variants support CPU and GPU.
        INT8 variants also support mobile.
        """
        from backend.optimizer.metadata import VariantType
        
        # Basic support - all variants support CPU
        backends = {"cpu", "gpu"}
        
        # INT8 is mobile-friendly
        if variant.variant_type == VariantType.INT8:
            backends.add("mobile")
        
        # Baseline supports everything
        if variant.variant_type == VariantType.BASELINE:
            backends.update({"mobile", "tpu", "npu"})
        
        return backends
    
    def explain(self) -> str:
        """Explain the backend support constraint."""
        if not self.target_backends:
            return "BackendSupportConstraint: No specific backend required."
        
        return (
            f"BackendSupportConstraint: Variant must support: {', '.join(sorted(self.target_backends))}.\n"
            f"  Required: {', '.join(sorted(self.target_backends))}\n"
            f"  Consequence: Incompatible variants are REJECTED."
        )
