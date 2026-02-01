"""
SOAC Constraint Base
====================

Abstract base class for formal constraints.

CONSTRAINT RULES:
    - Constraints are evaluated BEFORE selection
    - Failed constraints = variant REJECTED
    - Rejections MUST be explainable
    - No silent fallback allowed
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.optimizer.metadata import OptimizedVariant


@dataclass(frozen=True)
class ConstraintResult:
    """
    Result of a constraint check.
    
    Immutable and serializable.
    
    Attributes:
        passed: True if constraint is satisfied
        constraint_name: Name of the constraint
        message: Human-readable result message
        details: Additional details for debugging/audit
        threshold: The threshold value used (if applicable)
        actual_value: The actual value compared (if applicable)
    """
    passed: bool
    constraint_name: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    threshold: Optional[float] = None
    actual_value: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "passed": self.passed,
            "constraint_name": self.constraint_name,
            "message": self.message,
            "details": self.details,
            "threshold": self.threshold,
            "actual_value": self.actual_value,
        }
    
    def format(self) -> str:
        """Format as human-readable string."""
        status = "[PASS]" if self.passed else "[FAIL]"
        return f"{status} {self.constraint_name}: {self.message}"


class Constraint(ABC):
    """
    Abstract base class for constraints.
    
    Constraints enforce correctness rules declaratively.
    A variant that fails ANY constraint is rejected.
    
    Properties:
        - Deterministic: Same input always produces same result
        - Explainable: Every decision can be explained
        - Side-effect free: No mutations
    
    Example:
        >>> constraint = AccuracyConstraint(max_drop=0.02)
        >>> result = constraint.check(variant)
        >>> if not result.passed:
        ...     print(f"Rejected: {result.message}")
    """
    
    # Constraint name for identification
    name: str = "base_constraint"
    
    # Description of what this constraint enforces
    description: str = "Base constraint"
    
    @abstractmethod
    def check(
        self, 
        variant: "OptimizedVariant", 
        context: Optional[Dict[str, Any]] = None
    ) -> ConstraintResult:
        """
        Check if variant satisfies this constraint.
        
        Args:
            variant: The variant to check.
            context: Optional context (target device, memory limits, etc.)
        
        Returns:
            ConstraintResult with pass/fail and explanation.
        """
        pass
    
    @abstractmethod
    def explain(self) -> str:
        """
        Return human-readable explanation of this constraint.
        
        Should describe:
            - What the constraint enforces
            - The threshold/criteria
            - Consequences of failure
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
