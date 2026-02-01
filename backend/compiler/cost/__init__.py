"""
SOAC Cost Model Package
=======================

Formal cost estimation interface for the SOAC compiler.

This package provides:
    - CostModel: Abstract base class for cost estimation
    - CostEstimate: Immutable cost result dataclass
    - CostExplanation: Human-readable cost breakdown
    - EmpiricalCostModel: Uses measured benchmark data

REQUIREMENTS:
    - All cost models must be deterministic
    - All cost models must be side-effect free
    - All cost models must be serializable

Example:
    >>> from backend.compiler.cost import EmpiricalCostModel
    >>> model = EmpiricalCostModel()
    >>> estimate = model.estimate(variant)
    >>> print(f"Latency: {estimate.latency_ms}ms")
"""

from .types import CostEstimate, CostExplanation
from .base import CostModel
from .empirical import EmpiricalCostModel
from .analytical import AnalyticalCostModel

__all__ = [
    "CostModel",
    "CostEstimate",
    "CostExplanation",
    "EmpiricalCostModel",
    "AnalyticalCostModel",
]

