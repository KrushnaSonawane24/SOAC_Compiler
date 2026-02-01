"""
SOAC Selection Policies Package
===============================

Policy-driven variant selection for the SOAC compiler.

This package provides:
    - SelectionPolicy: Abstract base class for policies
    - PolicyScore: Score result with breakdown
    - LatencyFirstPolicy: Prioritizes lowest latency (DEFAULT)
    - AccuracyFirstPolicy: Prioritizes lowest accuracy drop
    - MobileFirstPolicy: Prioritizes smallest size

CRITICAL RULE:
    Policies MUST NOT access raw metrics directly.
    They ONLY consume cost model outputs.

Example:
    >>> from backend.compiler.policies import LatencyFirstPolicy
    >>> from backend.compiler.cost import EmpiricalCostModel
    >>> 
    >>> policy = LatencyFirstPolicy()
    >>> cost_model = EmpiricalCostModel()
    >>> 
    >>> costs = [cost_model.estimate(v) for v in variants]
    >>> result = policy.select(variants, costs)
    >>> print(f"Selected: {result.selected.variant_id}")
"""

from .base import SelectionPolicy, PolicyScore, SelectionResult
from .latency_first import LatencyFirstPolicy
from .accuracy_first import AccuracyFirstPolicy
from .mobile_first import MobileFirstPolicy

__all__ = [
    # Base classes
    "SelectionPolicy",
    "PolicyScore",
    "SelectionResult",
    
    # Policies
    "LatencyFirstPolicy",
    "AccuracyFirstPolicy",
    "MobileFirstPolicy",
]


def get_policy(name: str) -> SelectionPolicy:
    """
    Get policy by name.
    
    Args:
        name: Policy name ('latency_first', 'accuracy_first', 'mobile_first')
    
    Returns:
        Policy instance.
    
    Raises:
        ValueError: If policy name is unknown.
    """
    policies = {
        "latency_first": LatencyFirstPolicy,
        "accuracy_first": AccuracyFirstPolicy,
        "mobile_first": MobileFirstPolicy,
    }
    
    if name not in policies:
        raise ValueError(f"Unknown policy: {name}. Available: {list(policies.keys())}")
    
    return policies[name]()
