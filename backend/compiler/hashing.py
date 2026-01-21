"""
SOAC Graph Hashing
==================

Deterministic hashing for ONNX graphs.

CRITICAL REQUIREMENT:
    Same model input MUST always produce the same hash.
    This enables caching and reproducibility.
"""

import hashlib
from typing import List, Tuple

try:
    import onnx
    from onnx import numpy_helper
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False


def compute_graph_hash(model: "onnx.ModelProto") -> str:
    """
    Compute deterministic hash of an ONNX model.
    
    The hash is computed over:
        - Serialized graph structure
        - All tensor values (weights)
        - Graph metadata (opset, ir_version)
    
    Args:
        model: ONNX ModelProto object.
    
    Returns:
        Lowercase hex SHA-256 hash string.
    
    DETERMINISM GUARANTEE:
        Identical models always produce identical hashes.
        This is ensured by serializing the canonical protobuf form.
    """
    hasher = hashlib.sha256()
    
    # Add IR version
    hasher.update(str(model.ir_version).encode())
    
    # Add opset version(s)
    for opset in model.opset_import:
        hasher.update(f"{opset.domain}:{opset.version}".encode())
    
    # Serialize and hash the graph
    # Use SerializeToString which produces deterministic output
    graph_bytes = model.graph.SerializeToString()
    hasher.update(graph_bytes)
    
    return hasher.hexdigest()


def compute_structure_hash(model: "onnx.ModelProto") -> str:
    """
    Compute hash of graph STRUCTURE only (no weights).
    
    Useful for comparing graph topology without weight values.
    
    Args:
        model: ONNX ModelProto object.
    
    Returns:
        Lowercase hex SHA-256 hash of structure.
    """
    hasher = hashlib.sha256()
    
    # Add IR and opset
    hasher.update(str(model.ir_version).encode())
    for opset in model.opset_import:
        hasher.update(f"{opset.domain}:{opset.version}".encode())
    
    # Add input specs
    for input_tensor in model.graph.input:
        hasher.update(input_tensor.name.encode())
        if input_tensor.type.HasField("tensor_type"):
            shape_str = ",".join(
                str(d.dim_value) if d.HasField("dim_value") else "?"
                for d in input_tensor.type.tensor_type.shape.dim
            )
            hasher.update(shape_str.encode())
    
    # Add node structure (op types and connections)
    for node in model.graph.node:
        node_repr = f"{node.op_type}:{','.join(node.input)}:{','.join(node.output)}"
        hasher.update(node_repr.encode())
    
    # Add output specs
    for output_tensor in model.graph.output:
        hasher.update(output_tensor.name.encode())
    
    return hasher.hexdigest()


def compute_weights_hash(model: "onnx.ModelProto") -> str:
    """
    Compute hash of weights (initializers) only.
    
    Args:
        model: ONNX ModelProto object.
    
    Returns:
        Lowercase hex SHA-256 hash of all weights.
    """
    hasher = hashlib.sha256()
    
    # Sort initializers by name for determinism
    initializers = sorted(model.graph.initializer, key=lambda x: x.name)
    
    for init in initializers:
        hasher.update(init.name.encode())
        # Include raw data
        if init.raw_data:
            hasher.update(init.raw_data)
        else:
            # Fallback to serialized tensor
            hasher.update(init.SerializeToString())
    
    return hasher.hexdigest()


def get_node_signatures(model: "onnx.ModelProto") -> List[Tuple[str, str, str]]:
    """
    Get list of node signatures for debugging.
    
    Returns:
        List of (op_type, inputs, outputs) tuples.
    """
    signatures = []
    for node in model.graph.node:
        signatures.append((
            node.op_type,
            ",".join(node.input),
            ",".join(node.output),
        ))
    return signatures


def verify_hash_stability(model: "onnx.ModelProto", expected_hash: str) -> bool:
    """
    Verify model hash matches expected value.
    
    Uses constant-time comparison to prevent timing attacks.
    
    Args:
        model: ONNX model to hash.
        expected_hash: Expected hash value.
    
    Returns:
        True if hashes match.
    """
    import hmac
    actual_hash = compute_graph_hash(model)
    return hmac.compare_digest(actual_hash.lower(), expected_hash.lower())
