"""
SOAC Infer Memory Pass
======================

Computes memory estimates for all tensors in the IR graph.
"""

from datetime import datetime, timezone
from typing import Dict
import logging

from .base import BasePass, PassContext, PassResult, TraceEntry
from backend.compiler.ir import IRGraph, IRTensor
from backend.compiler.ir.types import compute_num_elements

logger = logging.getLogger(__name__)


class InferMemoryPass(BasePass):
    """
    Compute memory estimates for SOAC IR.
    
    Calculates:
        1. Memory footprint per tensor
        2. Total activation memory
        3. Total weight memory
        4. Peak memory estimate
    """
    
    name = "infer_memory"
    description = "Compute memory footprint estimates"
    
    def run(self, input: IRGraph, ctx: PassContext) -> PassResult[IRGraph]:
        """Execute memory inference pass."""
        start_time = datetime.now(timezone.utc)
        
        total_weight_bytes = 0
        total_activation_bytes = 0
        tensors_updated = 0
        
        # Update tensor memory estimates
        updated_tensors: Dict[str, IRTensor] = {}
        
        for name, tensor in input.tensors.items():
            memory_bytes = tensor.memory_bytes
            
            # Compute if not already set
            if memory_bytes is None:
                num_elements = compute_num_elements(tensor.shape)
                if num_elements is not None:
                    memory_bytes = num_elements * tensor.dtype.byte_size
                    tensors_updated += 1
            
            # Track totals
            if memory_bytes:
                if tensor.is_initializer:
                    total_weight_bytes += memory_bytes
                else:
                    total_activation_bytes += memory_bytes
            
            # Create updated tensor with memory info
            if memory_bytes != tensor.memory_bytes:
                updated_tensors[name] = IRTensor(
                    name=tensor.name,
                    shape=tensor.shape,
                    dtype=tensor.dtype,
                    layout=tensor.layout,
                    is_initializer=tensor.is_initializer,
                    memory_bytes=memory_bytes,
                    metadata=tensor.metadata,
                )
            else:
                updated_tensors[name] = tensor
        
        # Create updated graph
        result_graph = IRGraph(
            operators=input.operators,
            tensors=updated_tensors,
            inputs=input.inputs,
            outputs=input.outputs,
            metadata=input.metadata,
        )
        
        # Store memory summary
        memory_summary = {
            "total_weight_bytes": total_weight_bytes,
            "total_activation_bytes": total_activation_bytes,
            "total_bytes": total_weight_bytes + total_activation_bytes,
            "weight_mb": round(total_weight_bytes / (1024 * 1024), 2),
            "activation_mb": round(total_activation_bytes / (1024 * 1024), 2),
        }
        
        ctx.set_metadata("memory_summary", memory_summary)
        ctx.log(f"Memory inference: weights={memory_summary['weight_mb']}MB, activations={memory_summary['activation_mb']}MB")
        
        trace = TraceEntry(
            pass_name=self.name,
            timestamp=start_time.isoformat(),
            action="computed",
            details={
                "tensors_updated": tensors_updated,
                **memory_summary,
            },
        )
        
        return PassResult(
            success=True,
            output=result_graph,
            duration_ms=0.0,
            trace=trace,
        )
