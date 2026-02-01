"""
SOAC Empirical Cost Model
=========================

Cost model using measured benchmark data.

NO learning. NO randomness. Pure empirical measurement.
"""

from typing import TYPE_CHECKING
import logging

from .base import CostModel
from .types import CostEstimate, CostExplanation

if TYPE_CHECKING:
    from backend.optimizer.metadata import OptimizedVariant

logger = logging.getLogger(__name__)


class EmpiricalCostModel(CostModel):
    """
    Cost model based on empirical measurements.
    
    Uses benchmark data attached to variants.
    Falls back to heuristic estimates when no data available.
    
    Properties:
        - Deterministic: Same variant always produces same cost
        - No learning: Uses only measured data
        - No randomness: No stochastic elements
    """
    
    name = "empirical_cost_model"
    
    # Default estimates when no data available
    DEFAULT_LATENCY_MS = float('inf')
    DEFAULT_MEMORY_BYTES = 0
    
    def estimate_latency(self, variant: "OptimizedVariant") -> float:
        """
        Get latency from benchmark metrics.
        
        Returns measured latency if available, else infinity.
        """
        if variant.metrics is not None:
            return variant.metrics.latency_ms
        return self.DEFAULT_LATENCY_MS
    
    def estimate_memory(self, variant: "OptimizedVariant") -> int:
        """
        Get memory usage from benchmark metrics.
        
        Returns measured memory if available, else 0.
        """
        if variant.metrics is not None:
            # Convert MB to bytes
            return int(variant.metrics.memory_mb * 1024 * 1024)
        return self.DEFAULT_MEMORY_BYTES
    
    def estimate_size(self, variant: "OptimizedVariant") -> int:
        """
        Get model file size.
        
        Uses the size_bytes attribute directly.
        """
        return variant.size_bytes
    
    def estimate_accuracy_drop(self, variant: "OptimizedVariant") -> float:
        """
        Get accuracy drop from benchmark metrics.
        
        Returns measured accuracy drop if available, else 0.
        """
        if variant.metrics is not None:
            return variant.metrics.accuracy_drop
        return 0.0
    
    def explain(self, variant: "OptimizedVariant") -> CostExplanation:
        """
        Generate detailed cost explanation.
        
        Shows source of each cost metric (measured vs estimated).
        """
        has_metrics = variant.metrics is not None
        source = "measured" if has_metrics else "estimated"
        
        latency = self.estimate_latency(variant)
        memory = self.estimate_memory(variant)
        size = self.estimate_size(variant)
        accuracy_drop = self.estimate_accuracy_drop(variant)
        
        # Format summary
        if latency < float('inf'):
            summary = f"{variant.variant_type.value}: {latency:.2f}ms latency, {size/(1024*1024):.2f}MB size"
        else:
            summary = f"{variant.variant_type.value}: no benchmark data available"
        
        # Format breakdowns
        latency_breakdown = (
            f"{latency:.2f}ms ({source})" if latency < float('inf')
            else "N/A (no benchmark data)"
        )
        
        memory_breakdown = (
            f"{memory/(1024*1024):.2f}MB ({source})" if memory > 0
            else "N/A (no benchmark data)"
        )
        
        size_breakdown = f"{size/(1024*1024):.2f}MB (actual file size)"
        
        accuracy_note = (
            f"{accuracy_drop:.2%} drop from baseline ({source})" if has_metrics
            else "N/A (no benchmark data)"
        )
        
        return CostExplanation(
            variant_id=variant.variant_id,
            summary=summary,
            latency_breakdown=latency_breakdown,
            memory_breakdown=memory_breakdown,
            size_breakdown=size_breakdown,
            accuracy_note=accuracy_note,
            details={
                "has_metrics": has_metrics,
                "source": source,
                "variant_type": variant.variant_type.value,
            },
        )
