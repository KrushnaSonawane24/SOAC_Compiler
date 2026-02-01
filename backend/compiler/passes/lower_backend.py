"""
SOAC Lower to Backend Pass
==========================

Generates deployment artifacts from the selected variant.

This pass wraps the existing deployment generator.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import logging

from .base import BasePass, PassContext, PassResult, TraceEntry
from backend.optimizer.decision_trace import SelectedVariant
from backend.deployment import generate_deployment_artifacts

logger = logging.getLogger(__name__)


@dataclass
class BackendInput:
    """Input for backend lowering pass."""
    selection: SelectedVariant
    output_dir: Path
    canonical_path: Optional[Path] = None


class LowerToBackendPass(BasePass):
    """
    Generate deployment artifacts from selected variant.
    
    Produces:
        1. Optimized ONNX model
        2. TFLite model (for mobile)
        3. TensorRT engine (for GPU)
        4. Metadata and config files
    """
    
    name = "lower_to_backend"
    description = "Generate deployment artifacts"
    
    def run(
        self, 
        input: BackendInput, 
        ctx: PassContext
    ) -> PassResult[Path]:
        """Execute deployment pass."""
        start_time = datetime.now(timezone.utc)
        
        selected = input.selection.variant
        
        ctx.log(f"Generating deployment artifacts for {selected.variant_id}")
        
        # Use existing deployment generator
        bundle = generate_deployment_artifacts(
            selected.onnx_path,
            variant_id=selected.variant_id,
            source_hash=selected.graph_hash,
            output_dir=input.output_dir,
            canonical_path=input.canonical_path,
        )
        
        ctx.log(f"Deployment: {bundle.successful_count} success, {bundle.skipped_count} skipped, {bundle.failed_count} failed")
        
        # Store deployment summary
        ctx.set_metadata("deployment_summary", {
            "successful": bundle.successful_count,
            "skipped": bundle.skipped_count,
            "failed": bundle.failed_count,
            "output_dir": str(bundle.output_dir),
        })
        
        trace = TraceEntry(
            pass_name=self.name,
            timestamp=start_time.isoformat(),
            action="generated",
            details={
                "variant_id": selected.variant_id,
                "successful": bundle.successful_count,
                "skipped": bundle.skipped_count,
                "failed": bundle.failed_count,
                "output_dir": str(bundle.output_dir),
            },
        )
        
        return PassResult(
            success=True,
            output=bundle.output_dir,
            duration_ms=0.0,
            trace=trace,
        )
