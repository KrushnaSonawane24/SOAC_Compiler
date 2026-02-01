"""
SOAC IR Tensor
==============

Immutable tensor representation for the SOAC IR.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from .types import IRDataType, IRLayout, IRShape, compute_num_elements


@dataclass(frozen=True)
class IRTensor:
    """
    Immutable tensor representation in SOAC IR.
    
    Captures:
        - Shape (static or dynamic dimensions)
        - Data type
        - Memory layout
        - Memory footprint estimate
    
    Attributes:
        name: Unique tensor name within the graph
        shape: Tensor dimensions (None = dynamic dimension)
        dtype: Data type (float32, int8, etc.)
        layout: Memory layout (NCHW, NHWC, etc.)
        is_initializer: True if this is a weight/constant
        memory_bytes: Estimated memory footprint in bytes
        metadata: Additional metadata (producer op, etc.)
    
    IMMUTABILITY:
        This is a frozen dataclass - cannot be modified after creation.
    """
    
    name: str
    shape: IRShape = field(default_factory=lambda: ())
    dtype: IRDataType = IRDataType.FLOAT32
    layout: IRLayout = IRLayout.UNDEFINED
    is_initializer: bool = False
    memory_bytes: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Compute memory bytes if not provided and shape is static."""
        if self.memory_bytes is None and self.shape:
            num_elements = compute_num_elements(self.shape)
            if num_elements is not None:
                # Use object.__setattr__ since frozen
                object.__setattr__(
                    self, 
                    "memory_bytes", 
                    num_elements * self.dtype.byte_size
                )
    
    @property
    def ndim(self) -> int:
        """Number of dimensions."""
        return len(self.shape)
    
    @property
    def is_static(self) -> bool:
        """True if all dimensions are static (no None values)."""
        return all(d is not None for d in self.shape)
    
    @property
    def num_elements(self) -> Optional[int]:
        """Total number of elements, or None if shape has dynamic dims."""
        return compute_num_elements(self.shape)
    
    def with_shape(self, new_shape: IRShape) -> "IRTensor":
        """Create new tensor with updated shape."""
        return IRTensor(
            name=self.name,
            shape=new_shape,
            dtype=self.dtype,
            layout=self.layout,
            is_initializer=self.is_initializer,
            metadata=self.metadata,
        )
    
    def with_dtype(self, new_dtype: IRDataType) -> "IRTensor":
        """Create new tensor with updated dtype."""
        return IRTensor(
            name=self.name,
            shape=self.shape,
            dtype=new_dtype,
            layout=self.layout,
            is_initializer=self.is_initializer,
            metadata=self.metadata,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "shape": list(self.shape),
            "dtype": self.dtype.value,
            "layout": self.layout.value,
            "is_initializer": self.is_initializer,
            "memory_bytes": self.memory_bytes,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IRTensor":
        """Deserialize from dictionary."""
        return cls(
            name=data["name"],
            shape=tuple(data.get("shape", [])),
            dtype=IRDataType(data.get("dtype", "float32")),
            layout=IRLayout(data.get("layout", "undefined")),
            is_initializer=data.get("is_initializer", False),
            memory_bytes=data.get("memory_bytes"),
            metadata=data.get("metadata", {}),
        )
    
    def __repr__(self) -> str:
        shape_str = ", ".join(str(d) if d is not None else "?" for d in self.shape)
        return f"IRTensor({self.name}: [{shape_str}] {self.dtype.value})"
