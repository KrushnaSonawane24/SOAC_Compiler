"""
SOAC IR Hashing
===============

Deterministic hashing for SOAC IR graphs.

CRITICAL REQUIREMENT:
    Same IR graph MUST always produce the same hash.
    This enables caching, reproducibility, and verification.
"""

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .graph import IRGraph


def compute_ir_hash(graph: "IRGraph") -> str:
    """
    Compute deterministic hash of an IRGraph.
    
    The hash is computed over:
        - All operators in topological order
        - All tensor specifications
        - Graph inputs and outputs
        - Metadata (opset, etc.)
    
    Args:
        graph: IRGraph to hash.
    
    Returns:
        Lowercase hex SHA-256 hash string.
    
    DETERMINISM GUARANTEE:
        Identical graphs always produce identical hashes.
        This is ensured by:
            1. Sorting all collections deterministically
            2. Using stable serialization
            3. Including all structural information
    """
    hasher = hashlib.sha256()
    
    # Hash graph inputs (ordered)
    hasher.update(b"INPUTS:")
    for inp in graph.inputs:
        hasher.update(inp.encode("utf-8"))
        hasher.update(b"|")
    
    # Hash graph outputs (ordered)
    hasher.update(b"OUTPUTS:")
    for out in graph.outputs:
        hasher.update(out.encode("utf-8"))
        hasher.update(b"|")
    
    # Hash operators in order
    hasher.update(b"OPERATORS:")
    for op in graph.operators:
        # Include op type
        hasher.update(op.op_type.encode("utf-8"))
        hasher.update(b":")
        
        # Include inputs
        for inp in op.inputs:
            hasher.update(inp.encode("utf-8"))
            hasher.update(b",")
        hasher.update(b"->")
        
        # Include outputs
        for out in op.outputs:
            hasher.update(out.encode("utf-8"))
            hasher.update(b",")
        hasher.update(b";")
        
        # Include sorted attributes
        for key in sorted(op.attributes.keys()):
            value = op.attributes[key]
            hasher.update(f"{key}={_serialize_value(value)}".encode("utf-8"))
            hasher.update(b",")
        hasher.update(b"|")
    
    # Hash tensors (sorted by name for determinism)
    hasher.update(b"TENSORS:")
    for name in sorted(graph.tensors.keys()):
        tensor = graph.tensors[name]
        shape_str = ",".join(str(d) if d is not None else "?" for d in tensor.shape)
        tensor_repr = f"{name}:[{shape_str}]:{tensor.dtype.value}:{tensor.is_initializer}"
        hasher.update(tensor_repr.encode("utf-8"))
        hasher.update(b"|")
    
    # Hash relevant metadata
    hasher.update(b"META:")
    for key in sorted(graph.metadata.keys()):
        if key in ("opset_version", "ir_version"):
            hasher.update(f"{key}={graph.metadata[key]}".encode("utf-8"))
            hasher.update(b",")
    
    return hasher.hexdigest()


def _serialize_value(value) -> str:
    """Serialize an attribute value for hashing."""
    if isinstance(value, (list, tuple)):
        return f"[{','.join(str(v) for v in value)}]"
    elif isinstance(value, dict):
        items = ",".join(f"{k}:{v}" for k, v in sorted(value.items()))
        return f"{{{items}}}"
    elif isinstance(value, bytes):
        return value.hex()
    else:
        return str(value)


def compute_structure_hash(graph: "IRGraph") -> str:
    """
    Compute hash of graph STRUCTURE only (no weights/data).
    
    Useful for comparing graph topology.
    
    Args:
        graph: IRGraph to hash.
    
    Returns:
        Lowercase hex SHA-256 hash of structure.
    """
    hasher = hashlib.sha256()
    
    # Hash inputs/outputs
    hasher.update(b"IN:")
    for inp in graph.inputs:
        tensor = graph.tensors.get(inp)
        if tensor:
            hasher.update(f"{inp}:{tensor.dtype.value}".encode("utf-8"))
        hasher.update(b"|")
    
    hasher.update(b"OUT:")
    for out in graph.outputs:
        tensor = graph.tensors.get(out)
        if tensor:
            hasher.update(f"{out}:{tensor.dtype.value}".encode("utf-8"))
        hasher.update(b"|")
    
    # Hash operator structure
    hasher.update(b"OPS:")
    for op in graph.operators:
        node_repr = f"{op.op_type}:{','.join(op.inputs)}:{','.join(op.outputs)}"
        hasher.update(node_repr.encode("utf-8"))
        hasher.update(b"|")
    
    return hasher.hexdigest()


def verify_hash_stability(graph: "IRGraph", expected_hash: str) -> bool:
    """
    Verify graph hash matches expected value.
    
    Uses constant-time comparison to prevent timing attacks.
    
    Args:
        graph: IRGraph to hash.
        expected_hash: Expected hash value.
    
    Returns:
        True if hashes match.
    """
    import hmac
    actual_hash = graph.hash()
    return hmac.compare_digest(actual_hash.lower(), expected_hash.lower())
