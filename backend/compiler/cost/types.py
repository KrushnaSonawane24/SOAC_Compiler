"""
SOAC Cost Model Types
=====================

Data structures for cost estimation results.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class CostEstimate:
    """
    Complete cost estimate for a variant.
    
    Immutable and serializable.
    
    Attributes:
        latency_ms: Estimated execution latency in milliseconds
        memory_bytes: Estimated peak memory usage in bytes
        size_bytes: Model file size in bytes
        accuracy_drop: Accuracy degradation from baseline (0.0 = no drop)
        throughput: Estimated operations per second
        energy_estimate: Optional energy consumption estimate
        metadata: Additional cost-related metadata
    """
    latency_ms: float
    memory_bytes: int
    size_bytes: int
    accuracy_drop: float = 0.0
    throughput: Optional[float] = None
    energy_estimate: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def memory_mb(self) -> float:
        """Memory in megabytes."""
        return self.memory_bytes / (1024 * 1024)
    
    @property
    def size_mb(self) -> float:
        """Size in megabytes."""
        return self.size_bytes / (1024 * 1024)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "latency_ms": self.latency_ms,
            "memory_bytes": self.memory_bytes,
            "size_bytes": self.size_bytes,
            "accuracy_drop": self.accuracy_drop,
            "throughput": self.throughput,
            "energy_estimate": self.energy_estimate,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CostEstimate":
        """Deserialize from dictionary."""
        return cls(
            latency_ms=data["latency_ms"],
            memory_bytes=data["memory_bytes"],
            size_bytes=data["size_bytes"],
            accuracy_drop=data.get("accuracy_drop", 0.0),
            throughput=data.get("throughput"),
            energy_estimate=data.get("energy_estimate"),
            metadata=data.get("metadata", {}),
        )


@dataclass(frozen=True)
class CostExplanation:
    """
    Human-readable explanation of cost estimates.
    
    Provides breakdown and rationale for each cost component.
    """
    variant_id: str
    summary: str
    latency_breakdown: str
    memory_breakdown: str
    size_breakdown: str
    accuracy_note: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "variant_id": self.variant_id,
            "summary": self.summary,
            "latency_breakdown": self.latency_breakdown,
            "memory_breakdown": self.memory_breakdown,
            "size_breakdown": self.size_breakdown,
            "accuracy_note": self.accuracy_note,
            "details": self.details,
        }
    
    def format(self) -> str:
        """Format as human-readable string."""
        return (
            f"COST BREAKDOWN: {self.variant_id}\n"
            f"  Summary: {self.summary}\n"
            f"  Latency: {self.latency_breakdown}\n"
            f"  Memory:  {self.memory_breakdown}\n"
            f"  Size:    {self.size_breakdown}\n"
            f"  Accuracy: {self.accuracy_note}"
        )
