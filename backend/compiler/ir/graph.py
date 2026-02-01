"""
SOAC IR Graph
=============

Immutable graph representation for the SOAC IR.

The IRGraph is the central data structure for the SOAC compiler.
It represents a complete computation graph after lowering from ONNX.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional, FrozenSet
from collections import OrderedDict
import json

from .types import IRDataType, IRLayout, IRShape
from .tensor import IRTensor
from .operator import IROperator


@dataclass(frozen=True)
class IRGraph:
    """
    Immutable graph representation in SOAC IR.
    
    The graph consists of:
        - Operators: Ordered sequence of operations
        - Tensors: All tensors (inputs, outputs, intermediates, weights)
        - Edges: Implicit via tensor name references in operators
    
    Attributes:
        operators: Ordered tuple of operators (topologically sorted)
        tensors: Dictionary of all tensors by name
        inputs: Names of graph input tensors (in order)
        outputs: Names of graph output tensors (in order)
        metadata: Graph-level metadata (opset, source format, etc.)
        _hash: Cached deterministic hash
    
    IMMUTABILITY:
        This is a frozen dataclass - cannot be modified after creation.
        All modifications return a new IRGraph.
    
    DETERMINISM:
        The hash() method produces a deterministic SHA-256 hash.
        Same graph always produces the same hash.
    """
    
    operators: Tuple[IROperator, ...] = field(default_factory=tuple)
    tensors: Dict[str, IRTensor] = field(default_factory=dict)
    inputs: Tuple[str, ...] = field(default_factory=tuple)
    outputs: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Dict[str, Any] = field(default_factory=dict)
    _hash: Optional[str] = field(default=None, compare=False, repr=False)
    
    def __post_init__(self):
        """Compute hash if not provided."""
        if self._hash is None:
            from .hashing import compute_ir_hash
            computed_hash = compute_ir_hash(self)
            object.__setattr__(self, "_hash", computed_hash)
    
    @property
    def num_operators(self) -> int:
        """Number of operators in the graph."""
        return len(self.operators)
    
    @property
    def num_tensors(self) -> int:
        """Number of tensors in the graph."""
        return len(self.tensors)
    
    @property
    def num_inputs(self) -> int:
        """Number of input tensors."""
        return len(self.inputs)
    
    @property
    def num_outputs(self) -> int:
        """Number of output tensors."""
        return len(self.outputs)
    
    @property
    def initializers(self) -> Dict[str, IRTensor]:
        """Get all initializer (weight) tensors."""
        return {
            name: tensor
            for name, tensor in self.tensors.items()
            if tensor.is_initializer
        }
    
    @property
    def operator_types(self) -> FrozenSet[str]:
        """Get unique operator types in the graph."""
        return frozenset(op.op_type for op in self.operators)
    
    def hash(self) -> str:
        """
        Get the deterministic hash of this graph.
        
        GUARANTEE: Same graph structure always produces same hash.
        
        Returns:
            Lowercase hex SHA-256 hash string.
        """
        if self._hash is None:
            from .hashing import compute_ir_hash
            return compute_ir_hash(self)
        return self._hash
    
    def topological_order(self) -> List[str]:
        """
        Get operators in topological order.
        
        Returns:
            List of operator IDs in execution order.
        """
        return [op.op_id for op in self.operators]
    
    def get_operator(self, op_id: str) -> Optional[IROperator]:
        """Get operator by ID."""
        for op in self.operators:
            if op.op_id == op_id:
                return op
        return None
    
    def get_tensor(self, name: str) -> Optional[IRTensor]:
        """Get tensor by name."""
        return self.tensors.get(name)
    
    def get_input_tensors(self) -> List[IRTensor]:
        """Get all input tensors in order."""
        return [self.tensors[name] for name in self.inputs if name in self.tensors]
    
    def get_output_tensors(self) -> List[IRTensor]:
        """Get all output tensors in order."""
        return [self.tensors[name] for name in self.outputs if name in self.tensors]
    
    def get_producers(self, tensor_name: str) -> List[IROperator]:
        """Get operators that produce a tensor."""
        return [op for op in self.operators if tensor_name in op.outputs]
    
    def get_consumers(self, tensor_name: str) -> List[IROperator]:
        """Get operators that consume a tensor."""
        return [op for op in self.operators if tensor_name in op.inputs]
    
    def total_memory_bytes(self) -> int:
        """Estimate total memory footprint of all tensors."""
        total = 0
        for tensor in self.tensors.values():
            if tensor.memory_bytes is not None:
                total += tensor.memory_bytes
        return total
    
    def supports_backend(self, backend: str) -> bool:
        """Check if all operators support a given backend."""
        return all(op.supports_backend(backend) for op in self.operators)
    
    def unsupported_ops_for_backend(self, backend: str) -> List[str]:
        """Get list of operators that don't support a backend."""
        return [
            op.op_type
            for op in self.operators
            if not op.supports_backend(backend)
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary."""
        return {
            "operators": [op.to_dict() for op in self.operators],
            "tensors": {name: t.to_dict() for name, t in self.tensors.items()},
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "metadata": self.metadata,
            "hash": self._hash,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IRGraph":
        """Deserialize graph from dictionary."""
        operators = tuple(IROperator.from_dict(op) for op in data.get("operators", []))
        tensors = {name: IRTensor.from_dict(t) for name, t in data.get("tensors", {}).items()}
        
        return cls(
            operators=operators,
            tensors=tensors,
            inputs=tuple(data.get("inputs", [])),
            outputs=tuple(data.get("outputs", [])),
            metadata=data.get("metadata", {}),
            _hash=data.get("hash"),
        )
    
    def serialize(self) -> bytes:
        """Serialize graph to bytes."""
        return json.dumps(self.to_dict(), sort_keys=True).encode("utf-8")
    
    @classmethod
    def deserialize(cls, data: bytes) -> "IRGraph":
        """Deserialize graph from bytes."""
        return cls.from_dict(json.loads(data.decode("utf-8")))
    
    @classmethod
    def from_onnx(cls, model: "onnx.ModelProto") -> "IRGraph":
        """
        Create IRGraph from ONNX ModelProto.
        
        This is the primary lowering function from ONNX to SOAC IR.
        
        Args:
            model: ONNX ModelProto
        
        Returns:
            IRGraph representing the ONNX model
        """
        try:
            import onnx
            from onnx import TensorProto
        except ImportError:
            raise RuntimeError("ONNX is required for from_onnx()")
        
        graph = model.graph
        
        # Build tensor dictionary
        tensors: Dict[str, IRTensor] = {}
        
        # Get initializer names
        initializer_names = {init.name for init in graph.initializer}
        
        # Process inputs (excluding initializers)
        input_names = []
        for inp in graph.input:
            if inp.name in initializer_names:
                continue  # Skip weights/biases
            input_names.append(inp.name)
            
            shape = []
            dtype = IRDataType.FLOAT32
            
            if inp.type.HasField("tensor_type"):
                tt = inp.type.tensor_type
                dtype = IRDataType.from_onnx(tt.elem_type)
                if tt.HasField("shape"):
                    for dim in tt.shape.dim:
                        if dim.HasField("dim_value"):
                            shape.append(dim.dim_value)
                        else:
                            shape.append(None)  # Dynamic dimension
            
            tensors[inp.name] = IRTensor(
                name=inp.name,
                shape=tuple(shape),
                dtype=dtype,
                is_initializer=False,
            )
        
        # Process initializers (weights/biases)
        for init in graph.initializer:
            dtype = IRDataType.from_onnx(init.data_type)
            shape = tuple(init.dims)
            
            tensors[init.name] = IRTensor(
                name=init.name,
                shape=shape,
                dtype=dtype,
                is_initializer=True,
            )
        
        # Process outputs
        output_names = []
        for out in graph.output:
            output_names.append(out.name)
            
            shape = []
            dtype = IRDataType.FLOAT32
            
            if out.type.HasField("tensor_type"):
                tt = out.type.tensor_type
                dtype = IRDataType.from_onnx(tt.elem_type)
                if tt.HasField("shape"):
                    for dim in tt.shape.dim:
                        if dim.HasField("dim_value"):
                            shape.append(dim.dim_value)
                        else:
                            shape.append(None)
            
            if out.name not in tensors:
                tensors[out.name] = IRTensor(
                    name=out.name,
                    shape=tuple(shape),
                    dtype=dtype,
                    is_initializer=False,
                )
        
        # Process operators
        operators = []
        for idx, node in enumerate(graph.node):
            op = IROperator.from_onnx_node(node, idx)
            operators.append(op)
            
            # Create tensor entries for intermediate outputs
            for output_name in node.output:
                if output_name and output_name not in tensors:
                    tensors[output_name] = IRTensor(
                        name=output_name,
                        shape=(),  # Will be inferred later
                        dtype=IRDataType.FLOAT32,
                        is_initializer=False,
                    )
        
        # Build metadata
        metadata = {
            "opset_version": max(
                (op.version for op in model.opset_import if op.domain in ("", "ai.onnx")), 
                default=17
            ),
            "ir_version": model.ir_version,
            "producer": model.producer_name,
            "source_format": "onnx",
        }
        
        return cls(
            operators=tuple(operators),
            tensors=tensors,
            inputs=tuple(input_names),
            outputs=tuple(output_names),
            metadata=metadata,
        )
    
    def __repr__(self) -> str:
        return (
            f"IRGraph(ops={self.num_operators}, tensors={self.num_tensors}, "
            f"in={self.num_inputs}, out={self.num_outputs}, hash={self._hash[:12] if self._hash else 'N/A'}...)"
        )
