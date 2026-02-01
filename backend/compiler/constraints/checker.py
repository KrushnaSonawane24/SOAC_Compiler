"""
SOAC Constraint Checker
=======================

Orchestrates constraint checking for variant selection.
"""

from typing import List, Dict, Any, Tuple, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
import logging

from .base import Constraint, ConstraintResult

if TYPE_CHECKING:
    from backend.optimizer.metadata import OptimizedVariant

logger = logging.getLogger(__name__)


@dataclass
class ConstraintCheckSummary:
    """
    Summary of constraint checking for a single variant.
    
    Attributes:
        variant_id: ID of the checked variant
        passed: True if all constraints passed
        results: List of individual constraint results
        failed_constraints: Names of failed constraints
    """
    variant_id: str
    passed: bool
    results: List[ConstraintResult]
    failed_constraints: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "variant_id": self.variant_id,
            "passed": self.passed,
            "results": [r.to_dict() for r in self.results],
            "failed_constraints": self.failed_constraints,
        }
    
    def format(self) -> str:
        """Format as human-readable string."""
        status = "PASS" if self.passed else "FAIL"
        lines = [f"{self.variant_id}: {status}"]
        for r in self.results:
            lines.append(f"  {r.format()}")
        return "\n".join(lines)


@dataclass
class FilterResult:
    """
    Result of filtering variants by constraints.
    
    Attributes:
        valid: Variants that passed all constraints
        rejected: Variants that failed at least one constraint
        summaries: Per-variant constraint check summaries
    """
    valid: List["OptimizedVariant"]
    rejected: List[Tuple["OptimizedVariant", ConstraintCheckSummary]]
    summaries: Dict[str, ConstraintCheckSummary]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "valid_count": len(self.valid),
            "rejected_count": len(self.rejected),
            "valid_ids": [v.variant_id for v in self.valid],
            "rejected_ids": [v.variant_id for v, _ in self.rejected],
            "summaries": {k: v.to_dict() for k, v in self.summaries.items()},
        }


class ConstraintChecker:
    """
    Orchestrates constraint checking.
    
    Applies all constraints to variants and filters based on results.
    
    Properties:
        - All constraints evaluated (no short-circuit)
        - Failed constraints are recorded for explainability
        - Order-independent (deterministic regardless of constraint order)
    
    Example:
        >>> checker = ConstraintChecker([
        ...     AccuracyConstraint(max_drop=0.02),
        ...     MemoryConstraint(max_memory_mb=512),
        ... ])
        >>> result = checker.filter(variants)
        >>> print(f"Valid: {len(result.valid)}, Rejected: {len(result.rejected)}")
    """
    
    def __init__(self, constraints: List[Constraint]):
        """
        Initialize constraint checker.
        
        Args:
            constraints: List of constraints to apply.
        """
        self.constraints = constraints
    
    def check_variant(
        self, 
        variant: "OptimizedVariant",
        context: Optional[Dict[str, Any]] = None
    ) -> ConstraintCheckSummary:
        """
        Check all constraints against a single variant.
        
        Args:
            variant: The variant to check.
            context: Optional context for constraints.
        
        Returns:
            ConstraintCheckSummary with all results.
        """
        results = []
        failed = []
        
        for constraint in self.constraints:
            result = constraint.check(variant, context)
            results.append(result)
            
            if not result.passed:
                failed.append(constraint.name)
        
        return ConstraintCheckSummary(
            variant_id=variant.variant_id,
            passed=len(failed) == 0,
            results=results,
            failed_constraints=failed,
        )
    
    def filter(
        self, 
        variants: List["OptimizedVariant"],
        context: Optional[Dict[str, Any]] = None
    ) -> FilterResult:
        """
        Filter variants by all constraints.
        
        Args:
            variants: List of variants to filter.
            context: Optional context for constraints.
        
        Returns:
            FilterResult with valid and rejected variants.
        """
        valid = []
        rejected = []
        summaries = {}
        
        for variant in variants:
            summary = self.check_variant(variant, context)
            summaries[variant.variant_id] = summary
            
            if summary.passed:
                valid.append(variant)
            else:
                rejected.append((variant, summary))
                logger.info(
                    f"Rejected {variant.variant_id}: "
                    f"failed {', '.join(summary.failed_constraints)}"
                )
        
        logger.info(f"Constraint filter: {len(valid)} valid, {len(rejected)} rejected")
        
        return FilterResult(
            valid=valid,
            rejected=rejected,
            summaries=summaries,
        )
    
    def explain_all(self) -> str:
        """Get explanations for all constraints."""
        lines = ["CONSTRAINT DEFINITIONS:"]
        for c in self.constraints:
            lines.append(f"\n{c.explain()}")
        return "\n".join(lines)
    
    @classmethod
    def default(cls) -> "ConstraintChecker":
        """
        Create default constraint checker with standard constraints.
        
        Returns:
            ConstraintChecker with AccuracyConstraint (2%).
        """
        from .accuracy import AccuracyConstraint
        from .memory import MemoryConstraint
        
        return cls([
            AccuracyConstraint(),
            MemoryConstraint(),
        ])
