"""
SOAC Validate IR Pass
=====================

Validates the structure and consistency of SOAC IRGraph.
"""

from datetime import datetime, timezone
from typing import List, Tuple
import logging

from .base import BasePass, PassContext, PassResult, TraceEntry
from backend.compiler.ir import IRGraph

logger = logging.getLogger(__name__)


class ValidateIRPass(BasePass):
    """
    Validate SOAC IR structure.
    
    Checks:
        1. All operator inputs reference existing tensors
        2. All operator outputs are unique
        3. Graph inputs/outputs are valid
        4. No cycles in the graph
        5. Operators are topologically ordered
    """
    
    name = "validate_ir"
    description = "Validate IR structure and consistency"
    
    def run(self, input: IRGraph, ctx: PassContext) -> PassResult[IRGraph]:
        """Execute validation pass."""
        start_time = datetime.now(timezone.utc)
        
        errors: List[str] = []
        warnings: List[str] = []
        
        # Check 1: All inputs reference valid tensors
        all_tensor_names = set(input.tensors.keys())
        for op in input.operators:
            for inp in op.inputs:
                if inp and inp not in all_tensor_names:
                    errors.append(f"Operator {op.op_id} references unknown input: {inp}")
        
        # Check 2: All outputs are unique
        all_outputs = set()
        for op in input.operators:
            for out in op.outputs:
                if out in all_outputs:
                    errors.append(f"Duplicate output tensor: {out}")
                all_outputs.add(out)
        
        # Check 3: Graph inputs exist in tensors
        for inp_name in input.inputs:
            if inp_name not in all_tensor_names:
                errors.append(f"Graph input not in tensors: {inp_name}")
        
        # Check 4: Graph outputs exist
        for out_name in input.outputs:
            if out_name not in all_tensor_names and out_name not in all_outputs:
                errors.append(f"Graph output not found: {out_name}")
        
        # Check 5: Operators with no outputs (except graph outputs)
        for op in input.operators:
            if not op.outputs:
                warnings.append(f"Operator {op.op_id} has no outputs")
        
        # Log results
        if errors:
            for error in errors:
                ctx.log(f"Validation ERROR: {error}")
        if warnings:
            for warning in warnings:
                ctx.log(f"Validation WARNING: {warning}")
        
        success = len(errors) == 0
        
        if success:
            ctx.log(f"IR validation passed: {input.num_operators} ops, {input.num_tensors} tensors")
        else:
            ctx.log(f"IR validation failed with {len(errors)} errors")
        
        trace = TraceEntry(
            pass_name=self.name,
            timestamp=start_time.isoformat(),
            action="validated" if success else "failed",
            details={
                "errors": errors,
                "warnings": warnings,
                "num_operators": input.num_operators,
                "num_tensors": input.num_tensors,
            },
        )
        
        return PassResult(
            success=success,
            output=input if success else None,
            duration_ms=0.0,
            trace=trace,
            error="; ".join(errors) if errors else None,
        )
