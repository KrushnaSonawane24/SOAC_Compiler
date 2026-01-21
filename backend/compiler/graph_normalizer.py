"""
SOAC Graph Normalizer
=====================

Deterministic graph normalization for ONNX models.

NORMALIZATION STEPS:
    1. Sort nodes in topological order
    2. Normalize tensor names
    3. Remove unused initializers
    4. Remove identity nodes
    5. Deduplicate constants
    
GOAL: Same semantic model always produces identical serialization.
"""

import re
import logging
from typing import Set, List, Dict, Optional

try:
    import onnx
    from onnx import helper as onnx_helper
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

from .exceptions import CanonializationError


logger = logging.getLogger(__name__)


# =============================================================================
# NAME NORMALIZATION
# =============================================================================

# Regex for invalid characters in tensor names
INVALID_NAME_CHARS = re.compile(r'[^a-zA-Z0-9_]')


def normalize_name(name: str) -> str:
    """
    Normalize a tensor/node name to canonical form.
    
    Rules:
        - Remove framework prefixes (TF:, keras/, etc.)
        - Replace invalid characters with underscore
        - Lowercase
        - Collapse multiple underscores
    
    Args:
        name: Original tensor name.
    
    Returns:
        Normalized name.
    """
    # Remove common framework prefixes
    prefixes_to_remove = [
        "tf.", "TF:", "keras/", "Keras/",
        "StatefulPartitionedCall/", "model/", "Model/",
        "sequential/", "Sequential/",
    ]
    
    normalized = name
    for prefix in prefixes_to_remove:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    
    # Replace invalid characters
    normalized = INVALID_NAME_CHARS.sub('_', normalized)
    
    # Collapse multiple underscores
    while '__' in normalized:
        normalized = normalized.replace('__', '_')
    
    # Strip leading/trailing underscores
    normalized = normalized.strip('_')
    
    # Lowercase
    normalized = normalized.lower()
    
    # Ensure non-empty
    if not normalized:
        normalized = "tensor"
    
    return normalized


def create_name_mapping(model: "onnx.ModelProto") -> Dict[str, str]:
    """
    Create mapping from original names to normalized names.
    
    Ensures unique names by appending suffixes if needed.
    
    Args:
        model: ONNX model.
    
    Returns:
        Dict mapping old_name -> new_name.
    """
    mapping = {}
    used_names: Set[str] = set()
    
    def get_unique_name(base_name: str) -> str:
        """Get unique name, adding suffix if needed."""
        if base_name not in used_names:
            used_names.add(base_name)
            return base_name
        
        # Add numeric suffix
        counter = 1
        while f"{base_name}_{counter}" in used_names:
            counter += 1
        
        unique_name = f"{base_name}_{counter}"
        used_names.add(unique_name)
        return unique_name
    
    # Map input names
    for input_tensor in model.graph.input:
        normalized = normalize_name(input_tensor.name)
        mapping[input_tensor.name] = get_unique_name(normalized)
    
    # Map initializer names
    for init in model.graph.initializer:
        if init.name not in mapping:
            normalized = normalize_name(init.name)
            mapping[init.name] = get_unique_name(normalized)
    
    # Map node outputs (generate intermediate names)
    for node in model.graph.node:
        for output in node.output:
            if output and output not in mapping:
                # Use op_type as base for intermediate names
                base = f"{node.op_type.lower()}_out"
                mapping[output] = get_unique_name(base)
    
    # Map output names
    for output_tensor in model.graph.output:
        if output_tensor.name not in mapping:
            normalized = normalize_name(output_tensor.name)
            mapping[output_tensor.name] = get_unique_name(normalized)
    
    return mapping


def apply_name_mapping(
    model: "onnx.ModelProto",
    mapping: Dict[str, str]
) -> "onnx.ModelProto":
    """
    Apply name mapping to all tensors in the model.
    
    Args:
        model: Original model.
        mapping: Name mapping dict.
    
    Returns:
        Model with renamed tensors.
    """
    # Clone model
    new_model = onnx.ModelProto()
    new_model.CopyFrom(model)
    
    # Helper to get mapped name
    def map_name(name: str) -> str:
        return mapping.get(name, name)
    
    # Update graph inputs
    for input_tensor in new_model.graph.input:
        input_tensor.name = map_name(input_tensor.name)
    
    # Update initializers
    for init in new_model.graph.initializer:
        init.name = map_name(init.name)
    
    # Update nodes
    for node in new_model.graph.node:
        # Update node name if present
        if node.name:
            node.name = normalize_name(node.name)
        
        # Update inputs
        for i in range(len(node.input)):
            node.input[i] = map_name(node.input[i])
        
        # Update outputs
        for i in range(len(node.output)):
            node.output[i] = map_name(node.output[i])
    
    # Update graph outputs
    for output_tensor in new_model.graph.output:
        output_tensor.name = map_name(output_tensor.name)
    
    # Update value_info
    for vi in new_model.graph.value_info:
        vi.name = map_name(vi.name)
    
    return new_model


# =============================================================================
# NODE SORTING
# =============================================================================

def topological_sort_nodes(
    nodes: List["onnx.NodeProto"],
    inputs: Set[str],
    initializers: Set[str]
) -> List["onnx.NodeProto"]:
    """
    Sort nodes in topological order.
    
    For nodes at same topological level, sort alphabetically by first output.
    This ensures deterministic ordering.
    
    Args:
        nodes: List of ONNX nodes.
        inputs: Set of input tensor names.
        initializers: Set of initializer (weight) names.
    
    Returns:
        Topologically sorted node list.
    """
    # Available tensors (inputs and weights)
    available = inputs | initializers
    
    # Track which nodes we've processed
    remaining = list(nodes)
    sorted_nodes = []
    
    # Keep going until all nodes processed
    max_iterations = len(nodes) * 2
    iteration = 0
    
    while remaining and iteration < max_iterations:
        iteration += 1
        
        # Find nodes whose inputs are all available
        ready = []
        still_waiting = []
        
        for node in remaining:
            # Check if all inputs are available (empty inputs are ok)
            inputs_ready = all(
                inp in available or inp == ""
                for inp in node.input
            )
            
            if inputs_ready:
                ready.append(node)
            else:
                still_waiting.append(node)
        
        if not ready:
            # Circular dependency or missing inputs
            missing = []
            for node in still_waiting[:3]:
                for inp in node.input:
                    if inp and inp not in available:
                        missing.append(f"{node.op_type}:{inp}")
            logger.warning(f"Cannot resolve dependencies: {missing}")
            # Add remaining nodes anyway to avoid infinite loop
            sorted_nodes.extend(still_waiting)
            break
        
        # Sort ready nodes alphabetically by first output for determinism
        ready.sort(key=lambda n: n.output[0] if n.output else "")
        
        # Add to sorted list and mark outputs as available
        for node in ready:
            sorted_nodes.append(node)
            for output in node.output:
                if output:
                    available.add(output)
        
        remaining = still_waiting
    
    return sorted_nodes


# =============================================================================
# GRAPH CLEANUP
# =============================================================================

def get_used_tensors(model: "onnx.ModelProto") -> Set[str]:
    """
    Get set of all tensors that are actually used.
    """
    used = set()
    
    # Graph outputs are used
    for output in model.graph.output:
        used.add(output.name)
    
    # Node inputs/outputs are used
    for node in model.graph.node:
        for inp in node.input:
            if inp:
                used.add(inp)
        for out in node.output:
            if out:
                used.add(out)
    
    return used


def remove_unused_initializers(model: "onnx.ModelProto") -> "onnx.ModelProto":
    """
    Remove initializers that are not used by any node.
    
    Returns:
        Model with unused initializers removed.
    """
    used_tensors = get_used_tensors(model)
    
    # Clone model
    new_model = onnx.ModelProto()
    new_model.CopyFrom(model)
    
    # Filter initializers
    used_inits = []
    for init in new_model.graph.initializer:
        if init.name in used_tensors:
            used_inits.append(init)
        else:
            logger.debug(f"Removing unused initializer: {init.name}")
    
    # Clear and re-add
    del new_model.graph.initializer[:]
    new_model.graph.initializer.extend(used_inits)
    
    # Also filter inputs that are initializers
    init_names = {init.name for init in used_inits}
    used_inputs = []
    for inp in new_model.graph.input:
        if inp.name in used_tensors or inp.name not in init_names:
            used_inputs.append(inp)
    
    del new_model.graph.input[:]
    new_model.graph.input.extend(used_inputs)
    
    return new_model


def remove_identity_nodes(model: "onnx.ModelProto") -> "onnx.ModelProto":
    """
    Remove Identity nodes that just pass through tensors.
    
    Returns:
        Model with Identity nodes removed.
    """
    # Clone model
    new_model = onnx.ModelProto()
    new_model.CopyFrom(model)
    
    # Find Identity nodes
    identity_mapping = {}  # output -> input
    non_identity_nodes = []
    
    for node in new_model.graph.node:
        if node.op_type == "Identity" and len(node.input) == 1 and len(node.output) == 1:
            identity_mapping[node.output[0]] = node.input[0]
            logger.debug(f"Removing Identity node: {node.output[0]} <- {node.input[0]}")
        else:
            non_identity_nodes.append(node)
    
    if not identity_mapping:
        return new_model
    
    # Resolve transitive identity chains
    def resolve_identity(name: str, depth: int = 0) -> str:
        if depth > 100:  # Prevent infinite loops
            return name
        if name in identity_mapping:
            return resolve_identity(identity_mapping[name], depth + 1)
        return name
    
    # Update node inputs to bypass Identity nodes
    for node in non_identity_nodes:
        for i in range(len(node.input)):
            node.input[i] = resolve_identity(node.input[i])
    
    # Update graph outputs
    for output in new_model.graph.output:
        resolved = resolve_identity(output.name)
        if resolved != output.name:
            # Need to rename the output source
            output.name = resolved
    
    # Replace nodes
    del new_model.graph.node[:]
    new_model.graph.node.extend(non_identity_nodes)
    
    return new_model


# =============================================================================
# MAIN NORMALIZATION
# =============================================================================

def normalize_graph(model: "onnx.ModelProto") -> "onnx.ModelProto":
    """
    Apply all normalization steps to an ONNX model.
    
    Steps:
        1. Remove Identity nodes
        2. Remove unused initializers
        3. Normalize tensor names
        4. Sort nodes topologically
    
    Args:
        model: Input ONNX model.
    
    Returns:
        Normalized model.
    
    Raises:
        CanonializationError: If normalization fails.
    """
    if not ONNX_AVAILABLE:
        raise CanonializationError("ONNX library not available")
    
    try:
        # Step 1: Remove Identity nodes
        model = remove_identity_nodes(model)
        
        # Step 2: Remove unused initializers
        model = remove_unused_initializers(model)
        
        # Step 3: Create and apply name mapping
        name_mapping = create_name_mapping(model)
        model = apply_name_mapping(model, name_mapping)
        
        # Step 4: Sort nodes
        input_names = {inp.name for inp in model.graph.input}
        init_names = {init.name for init in model.graph.initializer}
        
        sorted_nodes = topological_sort_nodes(
            list(model.graph.node),
            input_names,
            init_names
        )
        
        # Replace nodes with sorted version
        del model.graph.node[:]
        model.graph.node.extend(sorted_nodes)
        
        return model
        
    except Exception as e:
        raise CanonializationError(f"Graph normalization failed: {e}", e)
