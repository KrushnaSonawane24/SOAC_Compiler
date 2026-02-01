"""
SOAC Latency-First Policy
=========================

Selection policy that prioritizes lowest latency.
"""

from typing import TYPE_CHECKING

from .base import SelectionPolicy, PolicyScore

if TYPE_CHECKING:
    from backend.optimizer.metadata import OptimizedVariant
    from backend.compiler.cost import CostEstimate


class LatencyFirstPolicy(SelectionPolicy):
    """
    Select variant with lowest latency.
    
    Scoring:
        - Primary: latency_ms (lower is better)
        - Secondary: size_bytes (smaller is better for ties)
        - Tertiary: variant type preference
    
    This is the DEFAULT policy for SOAC.
    """
    
    name = "latency_first"
    description = "Prioritizes lowest execution latency"
    
    # Weight factors for scoring
    LATENCY_WEIGHT = 1000.0
    SIZE_WEIGHT = 0.001
    TYPE_WEIGHT = 0.0001
    
    # Type preference (lower = more preferred)
    TYPE_PREFERENCE = {
        "int8": 1,
        "fp16": 2,
        "baseline": 3,
        "pruned": 4,
    }
    
    def compute_score(
        self, 
        variant: "OptimizedVariant",
        cost: "CostEstimate"
    ) -> PolicyScore:
        """
        Compute latency-first score.
        
        Score = latency * 1000 + size * 0.001 + type_pref * 0.0001
        """
        type_pref = self.TYPE_PREFERENCE.get(variant.variant_type.value, 10)
        
        # Compute weighted score
        latency_component = cost.latency_ms * self.LATENCY_WEIGHT
        size_component = cost.size_bytes * self.SIZE_WEIGHT
        type_component = type_pref * self.TYPE_WEIGHT
        
        score = latency_component + size_component + type_component
        
        breakdown = {
            "latency_component": latency_component,
            "size_component": size_component,
            "type_component": type_component,
        }
        
        explanation = (
            f"latency={cost.latency_ms:.2f}ms (primary), "
            f"size={cost.size_bytes/(1024*1024):.2f}MB, "
            f"type={variant.variant_type.value}"
        )
        
        return PolicyScore(
            variant_id=variant.variant_id,
            score=score,
            breakdown=breakdown,
            explanation=explanation,
        )
