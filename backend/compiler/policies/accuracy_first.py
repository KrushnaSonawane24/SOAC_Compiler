"""
SOAC Accuracy-First Policy
==========================

Selection policy that prioritizes lowest accuracy drop.
"""

from typing import TYPE_CHECKING

from .base import SelectionPolicy, PolicyScore

if TYPE_CHECKING:
    from backend.optimizer.metadata import OptimizedVariant
    from backend.compiler.cost import CostEstimate


class AccuracyFirstPolicy(SelectionPolicy):
    """
    Select variant with lowest accuracy degradation.
    
    Scoring:
        - Primary: accuracy_drop (lower is better)
        - Secondary: latency_ms (lower is better)
        - Tertiary: size_bytes (smaller is better)
    
    Use when accuracy is the primary concern.
    """
    
    name = "accuracy_first"
    description = "Prioritizes lowest accuracy degradation"
    
    # Weight factors for scoring
    ACCURACY_WEIGHT = 10000.0
    LATENCY_WEIGHT = 1.0
    SIZE_WEIGHT = 0.0000001  # Very small so accuracy/latency dominate
    
    def compute_score(
        self, 
        variant: "OptimizedVariant",
        cost: "CostEstimate"
    ) -> PolicyScore:
        """
        Compute accuracy-first score.
        
        Score = accuracy_drop * 10000 + latency * 1 + size * 0.0001
        """
        # Compute weighted score
        accuracy_component = cost.accuracy_drop * self.ACCURACY_WEIGHT
        latency_component = cost.latency_ms * self.LATENCY_WEIGHT
        size_component = cost.size_bytes * self.SIZE_WEIGHT
        
        score = accuracy_component + latency_component + size_component
        
        breakdown = {
            "accuracy_component": accuracy_component,
            "latency_component": latency_component,
            "size_component": size_component,
        }
        
        explanation = (
            f"accuracy_drop={cost.accuracy_drop:.2%} (primary), "
            f"latency={cost.latency_ms:.2f}ms, "
            f"size={cost.size_bytes/(1024*1024):.2f}MB"
        )
        
        return PolicyScore(
            variant_id=variant.variant_id,
            score=score,
            breakdown=breakdown,
            explanation=explanation,
        )
