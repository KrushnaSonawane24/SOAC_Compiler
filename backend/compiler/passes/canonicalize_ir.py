"""
SOAC Canonicalize IR Pass
=========================

Normalizes IR to a canonical form for consistent hashing.
"""

from datetime import datetime, timezone
from typing import Dict
import logging

from .base import BasePass, PassContext, PassResult, TraceEntry
from backend.compiler.ir import IRGraph, IROperator, IRTensor

logger = logging.getLogger(__name__)


class CanonicalizeIRPass(BasePass):
    """
    Canonicalize SOAC IR.
    
    Normalizations:
        1. Rename operators to sequential IDs (op_0, op_1, ...)
        2. Rename intermediate tensors consistently
        3. Sort operator attributes by key
        4. Ensure consistent ordering
    
    This ensures the same logical graph always produces the same hash.
    """
    
    name = "canonicalize_ir"
    description = "Normalize IR to canonical form"
    
    def run(self, input: IRGraph, ctx: PassContext) -> PassResult[IRGraph]:
        """Execute canonicalization pass."""
        start_time = datetime.now(timezone.utc)
        
        # Create name mappings
        op_name_map: Dict[str, str] = {}
        tensor_name_map: Dict[str, str] = {}
        
        # Keep input/output names unchanged
        for name in input.inputs:
            tensor_name_map[name] = name
        for name in input.outputs:
            tensor_name_map[name] = name
        
        # Keep initializer names unchanged
        for name, tensor in input.tensors.items():
            if tensor.is_initializer:
                tensor_name_map[name] = name
        
        # Rename operators and intermediate tensors
        intermediate_counter = 0
        canonical_ops = []
        
        for idx, op in enumerate(input.operators):
            new_op_id = f"op_{idx}"
            op_name_map[op.op_id] = new_op_id
            
            # Map output tensors
            new_outputs = []
            for out in op.outputs:
                if out not in tensor_name_map:
                    tensor_name_map[out] = f"t_{intermediate_counter}"
                    intermediate_counter += 1
                new_outputs.append(tensor_name_map[out])
            
            # Map input tensors
            new_inputs = tuple(
                tensor_name_map.get(inp, inp) for inp in op.inputs
            )
            
            # Sort attributes for determinism
            sorted_attrs = dict(sorted(op.attributes.items()))
            
            canonical_op = IROperator(
                op_id=new_op_id,
                op_type=op.op_type,
                inputs=new_inputs,
                outputs=tuple(new_outputs),
                attributes=sorted_attrs,
                supported_backends=op.supported_backends,
                domain=op.domain,
                metadata=op.metadata,
            )
            canonical_ops.append(canonical_op)
        
        # Update tensor names
        canonical_tensors = {}
        for old_name, tensor in input.tensors.items():
            new_name = tensor_name_map.get(old_name, old_name)
            canonical_tensors[new_name] = IRTensor(
                name=new_name,
                shape=tensor.shape,
                dtype=tensor.dtype,
                layout=tensor.layout,
                is_initializer=tensor.is_initializer,
                memory_bytes=tensor.memory_bytes,
                metadata=tensor.metadata,
            )
        
        # Update input/output names
        canonical_inputs = tuple(
            tensor_name_map.get(inp, inp) for inp in input.inputs
        )
        canonical_outputs = tuple(
            tensor_name_map.get(out, out) for out in input.outputs
        )
        
        # Create canonical graph
        canonical_graph = IRGraph(
            operators=tuple(canonical_ops),
            tensors=canonical_tensors,
            inputs=canonical_inputs,
            outputs=canonical_outputs,
            metadata=input.metadata,
        )
        
        ctx.log(f"Canonicalized IR: renamed {len(op_name_map)} ops, {len(tensor_name_map)} tensors")
        ctx.log(f"Canonical hash: {canonical_graph.hash()[:16]}...")
        
        ctx.set_metadata("canonical_ir_hash", canonical_graph.hash())
        
        trace = TraceEntry(
            pass_name=self.name,
            timestamp=start_time.isoformat(),
            action="canonicalized",
            details={
                "ops_renamed": len(op_name_map),
                "tensors_renamed": len(tensor_name_map),
                "canonical_hash": canonical_graph.hash(),
            },
        )
        
        return PassResult(
            success=True,
            output=canonical_graph,
            duration_ms=0.0,
            trace=trace,
        )
