"""
SOAC IR Operator
================

Immutable operator representation for the SOAC IR.
"""

from dataclasses import dataclass, field
from typing import Tuple, Dict, Any, FrozenSet, Optional


# Supported backend targets
SUPPORTED_BACKENDS = frozenset({"cpu", "gpu", "tpu", "npu", "mobile"})

# Operators that are only used during training (rejected)
TRAINING_ONLY_OPS = frozenset({
    "Dropout",  # In training mode
    "BatchNormalization",  # In training mode (has running_mean/var)
    "GradientOp",
    "TrainableDropout",
})

# Common operators and their default backend support
OPERATOR_BACKEND_MAP: Dict[str, FrozenSet[str]] = {
    # Universal operators - supported everywhere
    "Conv": frozenset({"cpu", "gpu", "tpu", "npu", "mobile"}),
    "MatMul": frozenset({"cpu", "gpu", "tpu", "npu", "mobile"}),
    "Gemm": frozenset({"cpu", "gpu", "tpu", "npu", "mobile"}),
    "Relu": frozenset({"cpu", "gpu", "tpu", "npu", "mobile"}),
    "Sigmoid": frozenset({"cpu", "gpu", "tpu", "npu", "mobile"}),
    "Softmax": frozenset({"cpu", "gpu", "tpu", "npu", "mobile"}),
    "Add": frozenset({"cpu", "gpu", "tpu", "npu", "mobile"}),
    "Mul": frozenset({"cpu", "gpu", "tpu", "npu", "mobile"}),
    "Reshape": frozenset({"cpu", "gpu", "tpu", "npu", "mobile"}),
    "Transpose": frozenset({"cpu", "gpu", "tpu", "npu", "mobile"}),
    
    # GPU-optimized operators
    "ConvTranspose": frozenset({"cpu", "gpu", "tpu"}),
    "LSTM": frozenset({"cpu", "gpu"}),
    "GRU": frozenset({"cpu", "gpu"}),
    
    # TPU-friendly operators
    "Einsum": frozenset({"cpu", "gpu", "tpu"}),
}


@dataclass(frozen=True)
class IROperator:
    """
    Immutable operator representation in SOAC IR.
    
    Captures:
        - Operation type and attributes
        - Input/output tensor references
        - Execution semantics
        - Backend support information
    
    Attributes:
        op_id: Unique operator ID within the graph
        op_type: Operation type (Conv, MatMul, Relu, etc.)
        inputs: Input tensor names (ordered)
        outputs: Output tensor names (ordered)
        attributes: Operator-specific attributes (kernel_size, strides, etc.)
        supported_backends: Set of backends that can execute this op
        domain: ONNX domain (default "" for standard ops)
        metadata: Additional metadata
    
    IMMUTABILITY:
        This is a frozen dataclass - cannot be modified after creation.
    """
    
    op_id: str
    op_type: str
    inputs: Tuple[str, ...] = field(default_factory=tuple)
    outputs: Tuple[str, ...] = field(default_factory=tuple)
    attributes: Dict[str, Any] = field(default_factory=dict)
    supported_backends: FrozenSet[str] = field(default_factory=lambda: SUPPORTED_BACKENDS)
    domain: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Auto-detect supported backends if not specified."""
        if self.supported_backends == SUPPORTED_BACKENDS:
            # Look up default backends for this op type
            default_backends = OPERATOR_BACKEND_MAP.get(
                self.op_type, SUPPORTED_BACKENDS
            )
            object.__setattr__(self, "supported_backends", default_backends)
    
    @property
    def is_training_only(self) -> bool:
        """True if this operator is only used during training."""
        return self.op_type in TRAINING_ONLY_OPS
    
    @property
    def num_inputs(self) -> int:
        """Number of input tensors."""
        return len(self.inputs)
    
    @property
    def num_outputs(self) -> int:
        """Number of output tensors."""
        return len(self.outputs)
    
    def supports_backend(self, backend: str) -> bool:
        """Check if this operator supports a given backend."""
        return backend.lower() in self.supported_backends
    
    def get_attribute(self, name: str, default: Any = None) -> Any:
        """Get an attribute with optional default."""
        return self.attributes.get(name, default)
    
    def with_id(self, new_id: str) -> "IROperator":
        """Create new operator with updated ID."""
        return IROperator(
            op_id=new_id,
            op_type=self.op_type,
            inputs=self.inputs,
            outputs=self.outputs,
            attributes=self.attributes,
            supported_backends=self.supported_backends,
            domain=self.domain,
            metadata=self.metadata,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "op_id": self.op_id,
            "op_type": self.op_type,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "attributes": self.attributes,
            "supported_backends": list(self.supported_backends),
            "domain": self.domain,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IROperator":
        """Deserialize from dictionary."""
        return cls(
            op_id=data["op_id"],
            op_type=data["op_type"],
            inputs=tuple(data.get("inputs", [])),
            outputs=tuple(data.get("outputs", [])),
            attributes=data.get("attributes", {}),
            supported_backends=frozenset(data.get("supported_backends", SUPPORTED_BACKENDS)),
            domain=data.get("domain", ""),
            metadata=data.get("metadata", {}),
        )
    
    @classmethod
    def from_onnx_node(cls, node, node_index: int) -> "IROperator":
        """
        Create IROperator from ONNX NodeProto.
        
        Args:
            node: ONNX NodeProto
            node_index: Index for generating unique ID
        
        Returns:
            IROperator instance
        """
        # Extract attributes from ONNX node
        attributes = {}
        for attr in node.attribute:
            if attr.type == 1:  # FLOAT
                attributes[attr.name] = attr.f
            elif attr.type == 2:  # INT
                attributes[attr.name] = attr.i
            elif attr.type == 3:  # STRING
                attributes[attr.name] = attr.s.decode("utf-8") if isinstance(attr.s, bytes) else attr.s
            elif attr.type == 6:  # FLOATS
                attributes[attr.name] = list(attr.floats)
            elif attr.type == 7:  # INTS
                attributes[attr.name] = list(attr.ints)
            elif attr.type == 8:  # STRINGS
                attributes[attr.name] = [s.decode("utf-8") if isinstance(s, bytes) else s for s in attr.strings]
        
        # Generate unique op_id
        op_id = node.name if node.name else f"{node.op_type}_{node_index}"
        
        return cls(
            op_id=op_id,
            op_type=node.op_type,
            inputs=tuple(node.input),
            outputs=tuple(node.output),
            attributes=attributes,
            domain=node.domain,
        )
    
    def __repr__(self) -> str:
        return f"IROperator({self.op_id}: {self.op_type})"
