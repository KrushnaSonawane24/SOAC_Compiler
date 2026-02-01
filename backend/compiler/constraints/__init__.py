"""
SOAC Constraint Package
=======================

Formal constraint system for the SOAC compiler.

This package provides:
    - Constraint: Abstract base class for constraints
    - ConstraintResult: Immutable result with pass/fail and explanation
    - AccuracyConstraint: Enforces maximum accuracy drop (≤2%)
    - MemoryConstraint: Enforces memory limits
    - BackendSupportConstraint: Enforces backend compatibility
    - ConstraintChecker: Orchestrates constraint checking

RULES:
    - Constraints are evaluated BEFORE selection
    - Failed constraints = variant REJECTED
    - Rejections MUST be explainable
    - No silent fallback allowed

Example:
    >>> from backend.compiler.constraints import ConstraintChecker
    >>> checker = ConstraintChecker.default()
    >>> result = checker.filter(variants)
    >>> for v in result.valid:
    ...     print(f"Valid: {v.variant_id}")
"""

from .base import Constraint, ConstraintResult
from .accuracy import AccuracyConstraint, DEFAULT_MAX_ACCURACY_DROP
from .memory import MemoryConstraint, DEFAULT_MAX_MEMORY_MB
from .backend_support import BackendSupportConstraint
from .checker import ConstraintChecker, ConstraintCheckSummary, FilterResult

__all__ = [
    # Base classes
    "Constraint",
    "ConstraintResult",
    
    # Constraints
    "AccuracyConstraint",
    "MemoryConstraint",
    "BackendSupportConstraint",
    
    # Orchestration
    "ConstraintChecker",
    "ConstraintCheckSummary",
    "FilterResult",
    
    # Constants
    "DEFAULT_MAX_ACCURACY_DROP",
    "DEFAULT_MAX_MEMORY_MB",
]
