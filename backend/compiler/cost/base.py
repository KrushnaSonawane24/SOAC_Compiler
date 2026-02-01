"""
SOAC Cost Model Base
====================

Abstract base class for cost models.

REQUIREMENTS:
    - Deterministic: Same input always produces same output
    - Serializable: Can be saved/loaded
    - Side-effect free: No mutations, no I/O
    - Read-only: Only reads from IR & benchmark data
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from .types import CostEstimate, CostExplanation

if TYPE_CHECKING:
    from backend.optimizer.metadata import OptimizedVariant


class CostModel(ABC):
    """
    Abstract base class for cost estimation.
    
    Cost models provide estimates for:
        - Latency (execution time)
        - Memory (peak usage)
        - Size (model file size)
        - Accuracy (degradation from baseline)
    
    All implementations MUST be:
        - Deterministic
        - Side-effect free
        - Thread-safe
    
    Example:
        >>> model = EmpiricalCostModel()
        >>> estimate = model.estimate(variant)
        >>> print(f"Latency: {estimate.latency_ms}ms")
    """
    
    # Model name for identification
    name: str = "base_cost_model"
    
    @abstractmethod
    def estimate_latency(self, variant: "OptimizedVariant") -> float:
        """
        Estimate execution latency in milliseconds.
        
        Args:
            variant: The optimized variant to estimate.
        
        Returns:
            Estimated latency in milliseconds.
        """
        pass
    
    @abstractmethod
    def estimate_memory(self, variant: "OptimizedVariant") -> int:
        """
        Estimate peak memory usage in bytes.
        
        Args:
            variant: The optimized variant to estimate.
        
        Returns:
            Estimated memory usage in bytes.
        """
        pass
    
    @abstractmethod
    def estimate_size(self, variant: "OptimizedVariant") -> int:
        """
        Get/estimate model file size in bytes.
        
        Args:
            variant: The optimized variant.
        
        Returns:
            Model size in bytes.
        """
        pass
    
    @abstractmethod
    def estimate_accuracy_drop(self, variant: "OptimizedVariant") -> float:
        """
        Estimate accuracy degradation from baseline.
        
        Args:
            variant: The optimized variant.
        
        Returns:
            Accuracy drop as a fraction (0.0 = no drop, 0.02 = 2% drop).
        """
        pass
    
    def estimate(self, variant: "OptimizedVariant") -> CostEstimate:
        """
        Compute complete cost estimate for a variant.
        
        This is the primary method for getting all cost metrics.
        
        Args:
            variant: The optimized variant to estimate.
        
        Returns:
            Complete CostEstimate with all metrics.
        """
        latency = self.estimate_latency(variant)
        memory = self.estimate_memory(variant)
        size = self.estimate_size(variant)
        accuracy_drop = self.estimate_accuracy_drop(variant)
        
        # Calculate throughput if latency is valid
        throughput = None
        if latency > 0:
            throughput = 1000.0 / latency  # ops per second
        
        return CostEstimate(
            latency_ms=latency,
            memory_bytes=memory,
            size_bytes=size,
            accuracy_drop=accuracy_drop,
            throughput=throughput,
            metadata={
                "cost_model": self.name,
                "variant_id": variant.variant_id,
            },
        )
    
    @abstractmethod
    def explain(self, variant: "OptimizedVariant") -> CostExplanation:
        """
        Generate human-readable cost explanation.
        
        Args:
            variant: The optimized variant.
        
        Returns:
            CostExplanation with breakdown of all costs.
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
