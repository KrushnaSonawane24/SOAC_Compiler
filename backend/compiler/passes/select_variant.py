"""
SOAC Select Variant Pass
========================

Selects the best variant using ALO (Adaptive Learning Optimizer).

This pass wraps the existing ALO engine for IR compatibility.
"""

from datetime import datetime, timezone
from typing import List
from dataclasses import dataclass
import logging

from .base import BasePass, PassContext, PassResult, TraceEntry
from backend.optimizer.metadata import OptimizedVariant
from backend.optimizer import select_best_variant as og_select_best_variant
from backend.optimizer.decision_trace import SelectedVariant
from backend.optimizer.metadata import MAX_ACCURACY_DROP

logger = logging.getLogger(__name__)


@dataclass
class SelectionInput:
    """Input for variant selection pass."""
    variants: List[OptimizedVariant]
    input_hash: str
    accuracy_threshold: float = MAX_ACCURACY_DROP


class SelectVariantPass(BasePass):
    """
    Select optimal variant using ALO.
    
    Decision rules (non-negotiable):
        1. REJECT any variant with accuracy_drop > 2%
        2. Among valid variants:
           a. Select LOWEST latency
           b. Tie-breaker: SMALLEST size
           c. Tie-breaker: Prefer INT8 > FP16 > Baseline > Pruned
        3. Decision is deterministic and auditable
    """
    
    name = "select_variant"
    description = "Select best variant using ALO"
    
    def run(
        self, 
        input: SelectionInput, 
        ctx: PassContext
    ) -> PassResult[SelectedVariant]:
        """Execute selection pass."""
        start_time = datetime.now(timezone.utc)
        
        ctx.log(f"ALO: Selecting from {len(input.variants)} variants")
        
        # Use existing ALO engine
        selection = og_select_best_variant(
            variants=input.variants,
            input_hash=input.input_hash,
            accuracy_threshold=input.accuracy_threshold,
        )
        
        selected = selection.variant
        ctx.log(f"ALO: Selected {selected.variant_id}")
        ctx.log(f"ALO: Reason: {selection.decision_trace.selection_reason}")
        
        # Store selection info
        ctx.set_metadata("selected_variant_id", selected.variant_id)
        ctx.set_metadata("selection_reason", selection.decision_trace.selection_reason)
        ctx.set_metadata("rejected_count", len(selection.rejected_variants))
        
        trace = TraceEntry(
            pass_name=self.name,
            timestamp=start_time.isoformat(),
            action="selected",
            details={
                "selected_id": selected.variant_id,
                "selected_type": selected.variant_type.value,
                "selection_reason": selection.decision_trace.selection_reason,
                "rejected_count": len(selection.rejected_variants),
                "total_variants": len(input.variants),
            },
        )
        
        return PassResult(
            success=True,
            output=selection,
            duration_ms=0.0,
            trace=trace,
        )
