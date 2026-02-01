"""
SOAC Mobile-First Policy
========================

Selection policy that prioritizes smallest model size.
"""

from typing import TYPE_CHECKING

from .base import SelectionPolicy, PolicyScore

if TYPE_CHECKING:
    from backend.optimizer.metadata import OptimizedVariant
    from backend.compiler.cost import CostEstimate


class MobileFirstPolicy(SelectionPolicy):
    """
    Select variant with smallest model size.
    
    Scoring:
        - Primary: size_bytes (smaller is better)
        - Secondary: memory_bytes (lower is better)
        - Tertiary: latency_ms (lower is better)
    
    Use for mobile/edge deployment where size is critical.
    """
    
    name = "mobile_first"
    description = "Prioritizes smallest model size for edge deployment"
    
    # Weight factors for scoring
    SIZE_WEIGHT = 1.0
    MEMORY_WEIGHT = 0.001
    LATENCY_WEIGHT = 0.00001
    
    def compute_score(
        self, 
        variant: "OptimizedVariant",
        cost: "CostEstimate"
    ) -> PolicyScore:
        """
        Compute mobile-first score.
        
        Score = size * 1 + memory * 0.001 + latency * 0.00001
        """
        # Compute weighted score
        size_component = cost.size_bytes * self.SIZE_WEIGHT
        memory_component = cost.memory_bytes * self.MEMORY_WEIGHT
        latency_component = cost.latency_ms * self.LATENCY_WEIGHT
        
        score = size_component + memory_component + latency_component
        
        breakdown = {
            "size_component": size_component,
            "memory_component": memory_component,
            "latency_component": latency_component,
        }
        
        explanation = (
            f"size={cost.size_bytes/(1024*1024):.2f}MB (primary), "
            f"memory={cost.memory_bytes/(1024*1024):.2f}MB, "
            f"latency={cost.latency_ms:.2f}ms"
        )
        
        return PolicyScore(
            variant_id=variant.variant_id,
            score=score,
            breakdown=breakdown,
            explanation=explanation,
        )
