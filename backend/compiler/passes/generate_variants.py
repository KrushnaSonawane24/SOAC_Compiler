"""
SOAC Generate Variants Pass
===========================

Generates optimized model variants from the IR.

This pass wraps the existing variant generator for IR compatibility.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
import logging

from .base import BasePass, PassContext, PassResult, TraceEntry
from backend.compiler.ir import IRGraph
from backend.optimizer import generate_variants as og_generate_variants
from backend.optimizer.metadata import OptimizedVariant

logger = logging.getLogger(__name__)


@dataclass
class VariantGenerationInput:
    """Input for variant generation pass."""
    ir_graph: IRGraph
    canonical_onnx_path: Path
    input_hash: str
    output_dir: Optional[Path] = None


class GenerateVariantsPass(BasePass):
    """
    Generate optimized variants from SOAC IR.
    
    Creates:
        1. Baseline - Original model
        2. FP16 - 16-bit floating point
        3. INT8 - 8-bit integer quantization
        4. Pruned - Structured pruning
    
    Note: This pass operates on the ONNX file corresponding to the IR,
    as quantization tools require ONNX format.
    """
    
    name = "generate_variants"
    description = "Generate optimized model variants"
    
    def run(
        self, 
        input: VariantGenerationInput, 
        ctx: PassContext
    ) -> PassResult[List[OptimizedVariant]]:
        """Execute variant generation pass."""
        start_time = datetime.now(timezone.utc)
        
        # Use existing variant generator
        variants = og_generate_variants(
            canonical_onnx_path=input.canonical_onnx_path,
            input_hash=input.input_hash,
            output_dir=input.output_dir,
        )
        
        # Count results
        valid_count = sum(1 for v in variants if v.is_valid)
        failed_count = len(variants) - valid_count
        
        ctx.log(f"Generated {len(variants)} variants: {valid_count} valid, {failed_count} failed")
        
        # Store variant info
        ctx.set_metadata("variants_generated", len(variants))
        ctx.set_metadata("variants_valid", valid_count)
        
        trace = TraceEntry(
            pass_name=self.name,
            timestamp=start_time.isoformat(),
            action="generated",
            details={
                "total_variants": len(variants),
                "valid_variants": valid_count,
                "failed_variants": failed_count,
                "variant_types": [v.variant_type.value for v in variants],
            },
        )
        
        return PassResult(
            success=True,
            output=variants,
            duration_ms=0.0,
            trace=trace,
        )
