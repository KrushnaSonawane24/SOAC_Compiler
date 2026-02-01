"""
SOAC Infer Shapes Pass
======================

Infers tensor shapes throughout the SOAC IR graph.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
import logging

from .base import BasePass, PassContext, PassResult, TraceEntry
from backend.compiler.ir import IRGraph, IRTensor, IRDataType

logger = logging.getLogger(__name__)


class InferShapesPass(BasePass):
    """
    Infer tensor shapes in SOAC IR.
    
    Propagates shape information from inputs through operators
    to determine output shapes for all intermediate tensors.
    """
    
    name = "infer_shapes"
    description = "Infer tensor shapes throughout the graph"
    
    def run(self, input: IRGraph, ctx: PassContext) -> PassResult[IRGraph]:
        """Execute shape inference pass."""
        start_time = datetime.now(timezone.utc)
        
        # Track inferred shapes
        inferred_shapes: Dict[str, Tuple[Optional[int], ...]] = {}
        shapes_inferred = 0
        
        # Start with known shapes from inputs and initializers
        for name, tensor in input.tensors.items():
            if tensor.shape:
                inferred_shapes[name] = tensor.shape
        
        # Propagate through operators
        for op in input.operators:
            output_shapes = self._infer_op_output_shapes(op, inferred_shapes)
            
            for out_name, shape in output_shapes.items():
                if out_name not in inferred_shapes or not inferred_shapes[out_name]:
                    inferred_shapes[out_name] = shape
                    shapes_inferred += 1
        
        # Update tensors with inferred shapes
        updated_tensors = {}
        for name, tensor in input.tensors.items():
            if name in inferred_shapes and inferred_shapes[name]:
                updated_tensors[name] = tensor.with_shape(inferred_shapes[name])
            else:
                updated_tensors[name] = tensor
        
        # Create new graph with updated tensors
        result_graph = IRGraph(
            operators=input.operators,
            tensors=updated_tensors,
            inputs=input.inputs,
            outputs=input.outputs,
            metadata=input.metadata,
        )
        
        ctx.log(f"Shape inference: inferred {shapes_inferred} tensor shapes")
        
        trace = TraceEntry(
            pass_name=self.name,
            timestamp=start_time.isoformat(),
            action="inferred",
            details={
                "shapes_inferred": shapes_inferred,
                "total_tensors": len(input.tensors),
            },
        )
        
        return PassResult(
            success=True,
            output=result_graph,
            duration_ms=0.0,
            trace=trace,
        )
    
    def _infer_op_output_shapes(
        self, 
        op, 
        known_shapes: Dict[str, Tuple[Optional[int], ...]]
    ) -> Dict[str, Tuple[Optional[int], ...]]:
        """Infer output shapes for an operator."""
        result = {}
        
        # Get input shapes
        input_shapes = [known_shapes.get(inp, ()) for inp in op.inputs]
        
        if not input_shapes or not any(input_shapes):
            return result
        
        first_shape = input_shapes[0] if input_shapes else ()
        
        # Shape inference rules by operator type
        if op.op_type in ("Relu", "Sigmoid", "Tanh", "LeakyRelu", "Softmax", 
                          "Dropout", "Identity", "Neg", "Abs", "Sqrt", "Exp", "Log"):
            # Element-wise ops preserve shape
            for out in op.outputs:
                result[out] = first_shape
        
        elif op.op_type in ("Add", "Sub", "Mul", "Div", "Min", "Max"):
            # Broadcasting ops - use first input shape (simplified)
            for out in op.outputs:
                result[out] = first_shape
        
        elif op.op_type == "Reshape":
            # Shape comes from second input or attribute
            shape_attr = op.get_attribute("shape")
            if shape_attr:
                for out in op.outputs:
                    result[out] = tuple(shape_attr)
        
        elif op.op_type == "Transpose":
            perm = op.get_attribute("perm")
            if perm and first_shape:
                new_shape = tuple(first_shape[i] if i < len(first_shape) else None for i in perm)
                for out in op.outputs:
                    result[out] = new_shape
        
        elif op.op_type in ("Conv", "ConvTranspose"):
            # Simplified conv output shape
            for out in op.outputs:
                if first_shape and len(first_shape) >= 2:
                    result[out] = first_shape  # Approximate - real inference is complex
        
        elif op.op_type in ("MatMul", "Gemm"):
            # Matrix multiplication
            for out in op.outputs:
                if len(input_shapes) >= 2 and input_shapes[0] and input_shapes[1]:
                    # [M, K] x [K, N] -> [M, N]
                    m = input_shapes[0][0] if input_shapes[0] else None
                    n = input_shapes[1][-1] if input_shapes[1] else None
                    result[out] = (m, n)
        
        elif op.op_type in ("GlobalAveragePool", "GlobalMaxPool"):
            # Global pooling reduces spatial dims to 1
            for out in op.outputs:
                if first_shape and len(first_shape) == 4:
                    result[out] = (first_shape[0], first_shape[1], 1, 1)
        
        elif op.op_type == "Flatten":
            for out in op.outputs:
                if first_shape:
                    axis = op.get_attribute("axis", 1)
                    if all(d is not None for d in first_shape):
                        import math
                        before = math.prod(first_shape[:axis])
                        after = math.prod(first_shape[axis:])
                        result[out] = (before, after)
        
        return result
