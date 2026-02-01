"""
SOAC Extended IR Metadata
=========================

Optional metadata extensions for advanced optimizations.

These metadata types are OPT-IN only and do NOT affect default compilation.
They are ignored unless explicitly enabled via `use_extended_metadata=True`.

GUARANTEES:
    - Does NOT affect IR hash by default
    - Serializable and hash-stable when enabled
    - Thread-safe and immutable
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, FrozenSet, Tuple
from enum import Enum
import json
import hashlib


# =============================================================================
# DATA LAYOUT SEMANTICS
# =============================================================================

class DataLayout(str, Enum):
    """
    Tensor memory layout formats.
    
    These hints guide backend optimizations for memory access patterns.
    """
    NCHW = "nchw"          # Batch, Channel, Height, Width (default for PyTorch)
    NHWC = "nhwc"          # Batch, Height, Width, Channel (default for TensorFlow)
    NCHW4 = "nchw4"        # Blocked format for vectorization
    NCHW8 = "nchw8"        # 8-wide blocked format
    NCHW16 = "nchw16"      # 16-wide blocked format (for AVX-512)
    NC4HW4 = "nc4hw4"      # Apple Metal format
    ANY = "any"            # Backend chooses optimal layout


@dataclass(frozen=True)
class DataLayoutHint:
    """
    Memory layout hint for a tensor or operator.
    
    Attributes:
        tensor_name: Target tensor (or None for operator-level)
        preferred_layout: Desired memory layout
        allow_transpose: Whether layout conversion is acceptable
        priority: Hint strength (0-10, higher = stronger preference)
    """
    tensor_name: Optional[str] = None
    preferred_layout: DataLayout = DataLayout.ANY
    allow_transpose: bool = True
    priority: int = 5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tensor_name": self.tensor_name,
            "preferred_layout": self.preferred_layout.value,
            "allow_transpose": self.allow_transpose,
            "priority": self.priority,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataLayoutHint":
        return cls(
            tensor_name=data.get("tensor_name"),
            preferred_layout=DataLayout(data.get("preferred_layout", "any")),
            allow_transpose=data.get("allow_transpose", True),
            priority=data.get("priority", 5),
        )


# =============================================================================
# OPERATOR FUSION HINTS
# =============================================================================

class FusionStrategy(str, Enum):
    """Fusion strategies for operator sequences."""
    NONE = "none"              # Do not fuse
    HORIZONTAL = "horizontal"  # Fuse parallel ops
    VERTICAL = "vertical"      # Fuse sequential ops
    AGGRESSIVE = "aggressive"  # Maximum fusion
    CONSERVATIVE = "conservative"  # Only safe fusions


@dataclass(frozen=True)
class FusionHint:
    """
    Operator fusion hint.
    
    Suggests which operators can/should be fused together.
    
    Attributes:
        operator_ids: Tuple of operator IDs that can be fused
        strategy: Fusion strategy to apply
        required: Whether fusion is required (vs optional)
        benefit_estimate: Estimated speedup factor (1.0 = no change)
    """
    operator_ids: Tuple[str, ...] = field(default_factory=tuple)
    strategy: FusionStrategy = FusionStrategy.NONE
    required: bool = False
    benefit_estimate: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "operator_ids": list(self.operator_ids),
            "strategy": self.strategy.value,
            "required": self.required,
            "benefit_estimate": self.benefit_estimate,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FusionHint":
        return cls(
            operator_ids=tuple(data.get("operator_ids", [])),
            strategy=FusionStrategy(data.get("strategy", "none")),
            required=data.get("required", False),
            benefit_estimate=data.get("benefit_estimate", 1.0),
        )


# =============================================================================
# HARDWARE AFFINITY TAGS
# =============================================================================

class HardwareTarget(str, Enum):
    """Hardware target types."""
    CPU = "cpu"
    GPU = "gpu"
    TPU = "tpu"
    NPU = "npu"
    MOBILE_GPU = "mobile_gpu"
    MOBILE_NPU = "mobile_npu"
    FPGA = "fpga"
    ANY = "any"


class AffinityLevel(str, Enum):
    """Strength of hardware affinity."""
    REQUIRED = "required"      # Must run on this hardware
    PREFERRED = "preferred"    # Prefer but allow fallback
    AVOID = "avoid"            # Try to avoid this hardware
    FORBIDDEN = "forbidden"    # Must not run on this hardware


@dataclass(frozen=True)
class HardwareAffinityTag:
    """
    Hardware affinity tag for operators.
    
    Specifies hardware preferences for operator execution.
    
    Attributes:
        operator_id: Target operator (or None for graph-level)
        target: Hardware target
        affinity: Affinity level
        reason: Explanation for the affinity
    """
    operator_id: Optional[str] = None
    target: HardwareTarget = HardwareTarget.ANY
    affinity: AffinityLevel = AffinityLevel.PREFERRED
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "target": self.target.value,
            "affinity": self.affinity.value,
            "reason": self.reason,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HardwareAffinityTag":
        return cls(
            operator_id=data.get("operator_id"),
            target=HardwareTarget(data.get("target", "any")),
            affinity=AffinityLevel(data.get("affinity", "preferred")),
            reason=data.get("reason", ""),
        )


# =============================================================================
# EXTENDED METADATA CONTAINER
# =============================================================================

@dataclass
class ExtendedMetadata:
    """
    Container for all extended IR metadata.
    
    This is the main class that holds all opt-in metadata extensions.
    
    IMPORTANT:
        - Does NOT affect default IR hash
        - Only included in hash when `include_in_hash=True`
        - Safely ignored by all default compilation paths
    
    Attributes:
        layout_hints: Data layout preferences
        fusion_hints: Operator fusion suggestions
        affinity_tags: Hardware affinity specifications
        custom_annotations: User-defined key-value pairs
        include_in_hash: Whether to include in IR hash computation
    """
    layout_hints: List[DataLayoutHint] = field(default_factory=list)
    fusion_hints: List[FusionHint] = field(default_factory=list)
    affinity_tags: List[HardwareAffinityTag] = field(default_factory=list)
    custom_annotations: Dict[str, Any] = field(default_factory=dict)
    include_in_hash: bool = False
    
    def __post_init__(self):
        """Validate metadata."""
        # Ensure layout hints are valid
        for hint in self.layout_hints:
            if not isinstance(hint, DataLayoutHint):
                raise TypeError(f"Expected DataLayoutHint, got {type(hint)}")
        
        # Ensure fusion hints are valid
        for hint in self.fusion_hints:
            if not isinstance(hint, FusionHint):
                raise TypeError(f"Expected FusionHint, got {type(hint)}")
        
        # Ensure affinity tags are valid
        for tag in self.affinity_tags:
            if not isinstance(tag, HardwareAffinityTag):
                raise TypeError(f"Expected HardwareAffinityTag, got {type(tag)}")
    
    def is_empty(self) -> bool:
        """Check if metadata is empty."""
        return (
            len(self.layout_hints) == 0 and
            len(self.fusion_hints) == 0 and
            len(self.affinity_tags) == 0 and
            len(self.custom_annotations) == 0
        )
    
    def compute_hash(self) -> str:
        """
        Compute deterministic hash of extended metadata.
        
        Only called when include_in_hash=True.
        
        Returns:
            SHA-256 hash of metadata.
        """
        data = self.to_dict()
        # Sort for determinism
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()
    
    def get_layout_for_tensor(self, tensor_name: str) -> Optional[DataLayoutHint]:
        """Get layout hint for a specific tensor."""
        for hint in self.layout_hints:
            if hint.tensor_name == tensor_name:
                return hint
        return None
    
    def get_affinity_for_operator(self, operator_id: str) -> List[HardwareAffinityTag]:
        """Get all affinity tags for a specific operator."""
        return [
            tag for tag in self.affinity_tags
            if tag.operator_id == operator_id or tag.operator_id is None
        ]
    
    def get_fusion_candidates(self) -> List[FusionHint]:
        """Get fusion hints that suggest operator merging."""
        return [
            hint for hint in self.fusion_hints
            if hint.strategy != FusionStrategy.NONE
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "layout_hints": [h.to_dict() for h in self.layout_hints],
            "fusion_hints": [h.to_dict() for h in self.fusion_hints],
            "affinity_tags": [t.to_dict() for t in self.affinity_tags],
            "custom_annotations": self.custom_annotations,
            "include_in_hash": self.include_in_hash,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtendedMetadata":
        """Deserialize from dictionary."""
        return cls(
            layout_hints=[
                DataLayoutHint.from_dict(h) 
                for h in data.get("layout_hints", [])
            ],
            fusion_hints=[
                FusionHint.from_dict(h) 
                for h in data.get("fusion_hints", [])
            ],
            affinity_tags=[
                HardwareAffinityTag.from_dict(t) 
                for t in data.get("affinity_tags", [])
            ],
            custom_annotations=data.get("custom_annotations", {}),
            include_in_hash=data.get("include_in_hash", False),
        )
    
    def merge_with(self, other: "ExtendedMetadata") -> "ExtendedMetadata":
        """
        Merge with another ExtendedMetadata instance.
        
        Creates a new instance with combined metadata.
        Later hints take precedence for conflicts.
        """
        return ExtendedMetadata(
            layout_hints=self.layout_hints + other.layout_hints,
            fusion_hints=self.fusion_hints + other.fusion_hints,
            affinity_tags=self.affinity_tags + other.affinity_tags,
            custom_annotations={**self.custom_annotations, **other.custom_annotations},
            include_in_hash=self.include_in_hash or other.include_in_hash,
        )
    
    def __repr__(self) -> str:
        return (
            f"ExtendedMetadata(layouts={len(self.layout_hints)}, "
            f"fusions={len(self.fusion_hints)}, "
            f"affinities={len(self.affinity_tags)})"
        )


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_gpu_affinity(operator_id: Optional[str] = None) -> HardwareAffinityTag:
    """Create a GPU-preferred affinity tag."""
    return HardwareAffinityTag(
        operator_id=operator_id,
        target=HardwareTarget.GPU,
        affinity=AffinityLevel.PREFERRED,
        reason="GPU acceleration recommended for this operator",
    )


def create_mobile_affinity(operator_id: Optional[str] = None) -> HardwareAffinityTag:
    """Create a mobile-optimized affinity tag."""
    return HardwareAffinityTag(
        operator_id=operator_id,
        target=HardwareTarget.MOBILE_NPU,
        affinity=AffinityLevel.PREFERRED,
        reason="Optimized for mobile NPU execution",
    )


def create_fusion_group(*operator_ids: str) -> FusionHint:
    """Create a fusion hint for a group of operators."""
    return FusionHint(
        operator_ids=tuple(operator_ids),
        strategy=FusionStrategy.VERTICAL,
        required=False,
        benefit_estimate=1.2,  # 20% estimated speedup
    )


def create_nhwc_layout(tensor_name: str) -> DataLayoutHint:
    """Create an NHWC layout hint (TensorFlow-style)."""
    return DataLayoutHint(
        tensor_name=tensor_name,
        preferred_layout=DataLayout.NHWC,
        allow_transpose=True,
        priority=5,
    )


def create_nchw_layout(tensor_name: str) -> DataLayoutHint:
    """Create an NCHW layout hint (PyTorch-style)."""
    return DataLayoutHint(
        tensor_name=tensor_name,
        preferred_layout=DataLayout.NCHW,
        allow_transpose=True,
        priority=5,
    )
