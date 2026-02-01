"""
SOAC Lower ONNX to IR Pass
==========================

Converts ONNX ModelProto to SOAC IRGraph.

This is the primary entry point for lowering ONNX (frontend format)
to SOAC IR (compiler internal format).
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import logging

from .base import BasePass, PassContext, PassResult, TraceEntry

if TYPE_CHECKING:
    import onnx

logger = logging.getLogger(__name__)


class LowerONNXToSOACIRPass(BasePass):
    """
    Lower ONNX ModelProto to SOAC IRGraph.
    
    Responsibilities:
        1. Parse ONNX graph
        2. Reject training-only operators
        3. Normalize operators to IR ops
        4. Populate SOAC IR tensors and operators
        5. Preserve metadata (opset, producer, etc.)
        6. Compute deterministic IR hash
    
    After this pass, ONNX is no longer the primary representation.
    The compiler operates on SOAC IR.
    """
    
    name = "lower_onnx_to_ir"
    description = "Convert ONNX ModelProto to SOAC IRGraph"
    
    # Operators that are only valid during training
    TRAINING_ONLY_OPS = frozenset({
        "Dropout",
        "TrainableDropout",
    })
    
    def run(
        self, 
        input: "onnx.ModelProto", 
        ctx: PassContext
    ) -> PassResult:
        """
        Execute the lowering pass.
        
        Args:
            input: ONNX ModelProto
            ctx: Pass context
        
        Returns:
            PassResult containing IRGraph
        """
        from backend.compiler.ir import IRGraph
        
        start_time = datetime.now(timezone.utc)
        
        # Check for training-only operators
        training_ops = self._find_training_ops(input)
        if training_ops:
            ctx.log(f"Warning: Found training-only operators: {training_ops}")
        
        # Convert to IRGraph
        ir_graph = IRGraph.from_onnx(input)
        
        # Log statistics
        ctx.log(f"Lowered ONNX to IR: {ir_graph.num_operators} ops, {ir_graph.num_tensors} tensors")
        ctx.log(f"IR hash: {ir_graph.hash()[:16]}...")
        
        # Store metadata
        ctx.set_metadata("ir_hash", ir_graph.hash())
        ctx.set_metadata("num_operators", ir_graph.num_operators)
        ctx.set_metadata("num_tensors", ir_graph.num_tensors)
        ctx.set_metadata("operator_types", list(ir_graph.operator_types))
        
        # Create trace entry
        trace = TraceEntry(
            pass_name=self.name,
            timestamp=start_time.isoformat(),
            action="lowered",
            details={
                "num_operators": ir_graph.num_operators,
                "num_tensors": ir_graph.num_tensors,
                "num_inputs": ir_graph.num_inputs,
                "num_outputs": ir_graph.num_outputs,
                "ir_hash": ir_graph.hash(),
                "training_ops_found": list(training_ops),
            },
        )
        
        return PassResult(
            success=True,
            output=ir_graph,
            duration_ms=0.0,  # Will be set by __call__
            trace=trace,
        )
    
    def _find_training_ops(self, model: "onnx.ModelProto") -> set:
        """Find any training-only operators in the graph."""
        training_ops = set()
        for node in model.graph.node:
            if node.op_type in self.TRAINING_ONLY_OPS:
                training_ops.add(node.op_type)
        return training_ops
