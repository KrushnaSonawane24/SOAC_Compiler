"""
SOAC Decision Trace
===================

Complete audit trail for ALO decisions.

REQUIREMENT: Every decision must be explainable and auditable.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json

from .metadata import RankedVariant, RejectedVariant, OptimizedVariant


@dataclass
class DecisionTrace:
    """
    Complete audit trail of the ALO decision process.
    
    This structure captures EVERYTHING about the decision:
    - What variants were considered
    - Why each was rejected or ranked
    - How the final selection was made
    - Timestamps and hashes for reproducibility
    
    Attributes:
        timestamp: ISO timestamp of decision
        input_hash: Hash of the input canonical ONNX
        variants_generated: Total variants attempted
        variants_valid: Variants passing accuracy threshold
        variants_rejected: Variants failing accuracy threshold
        ranking: Ordered list of valid variants by preference
        rejected: List of rejected variants with reasons
        selection_reason: Human-readable explanation
        final_selection: ID of selected variant
        accuracy_threshold: The threshold used (e.g., 0.02)
        decision_rules: Rules applied in order
    """
    timestamp: str
    input_hash: str
    variants_generated: int
    variants_valid: int
    variants_rejected: int
    ranking: List[RankedVariant]
    rejected: List[RejectedVariant]
    selection_reason: str
    final_selection: str
    accuracy_threshold: float
    decision_rules: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary."""
        return {
            "timestamp": self.timestamp,
            "input_hash": self.input_hash,
            "variants_generated": self.variants_generated,
            "variants_valid": self.variants_valid,
            "variants_rejected": self.variants_rejected,
            "ranking": [r.to_dict() for r in self.ranking],
            "rejected": [r.to_dict() for r in self.rejected],
            "selection_reason": self.selection_reason,
            "final_selection": self.final_selection,
            "accuracy_threshold": self.accuracy_threshold,
            "decision_rules": self.decision_rules,
            "metadata": self.metadata,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        return (
            f"Decision: {self.final_selection}\n"
            f"  Valid: {self.variants_valid}/{self.variants_generated}\n"
            f"  Rejected: {self.variants_rejected}\n"
            f"  Reason: {self.selection_reason}"
        )


@dataclass
class SelectedVariant:
    """
    Final result of ALO selection.
    
    Includes the selected variant AND the complete decision trace.
    """
    variant: OptimizedVariant
    decision_trace: DecisionTrace
    all_variants: List[OptimizedVariant]
    rejected_variants: List[RejectedVariant]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected": self.variant.to_dict(),
            "decision_trace": self.decision_trace.to_dict(),
            "all_variants": [v.to_dict() for v in self.all_variants],
            "rejected_variants": [r.to_dict() for r in self.rejected_variants],
        }


def create_decision_trace(
    input_hash: str,
    all_variants: List[OptimizedVariant],
    valid_variants: List[OptimizedVariant],
    rejected: List[RejectedVariant],
    ranking: List[RankedVariant],
    selected_id: str,
    selection_reason: str,
    accuracy_threshold: float,
) -> DecisionTrace:
    """
    Create a complete decision trace.
    
    Args:
        input_hash: Hash of input model.
        all_variants: All generated variants.
        valid_variants: Variants passing validation.
        rejected: Rejected variants with reasons.
        ranking: Ranked valid variants.
        selected_id: ID of selected variant.
        selection_reason: Why this variant was selected.
        accuracy_threshold: Accuracy threshold used.
    
    Returns:
        Complete DecisionTrace.
    """
    return DecisionTrace(
        timestamp=datetime.now(timezone.utc).isoformat(),
        input_hash=input_hash,
        variants_generated=len(all_variants),
        variants_valid=len(valid_variants),
        variants_rejected=len(rejected),
        ranking=ranking,
        rejected=rejected,
        selection_reason=selection_reason,
        final_selection=selected_id,
        accuracy_threshold=accuracy_threshold,
        decision_rules=[
            "RULE 1: Reject variants with accuracy_drop > 2%",
            "RULE 2: Select lowest latency among valid variants",
            "RULE 3: Tie-breaker: smallest file size",
            "RULE 4: Tie-breaker: prefer INT8 > FP16 > Baseline > Pruned",
        ],
        metadata={
            "valid_variant_ids": [v.variant_id for v in valid_variants],
            "total_generation_attempts": len(all_variants),
        },
    )
