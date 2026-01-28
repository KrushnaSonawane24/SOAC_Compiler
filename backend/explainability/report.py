"""
SOAC Explainability Report
==========================

Generates explainable optimization reports.
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum


class VariantStatus(str, Enum):
    """Variant evaluation status."""
    SELECTED = "selected"
    REJECTED = "rejected"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class VariantExplanation:
    """Explanation for a single variant."""
    variant_id: str
    variant_type: str
    status: VariantStatus
    
    # Metrics
    latency_ms: Optional[float] = None
    throughput: Optional[float] = None
    memory_mb: Optional[float] = None
    accuracy: Optional[float] = None
    accuracy_drop: Optional[float] = None
    
    # Evaluation
    meets_accuracy: bool = True
    meets_latency: bool = True
    is_valid: bool = True
    
    # Rejection
    rejection_reason: Optional[str] = None
    rejection_constraint: Optional[str] = None
    
    # Scoring
    composite_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "variant_type": self.variant_type,
            "status": self.status.value,
            "metrics": {
                "latency_ms": self.latency_ms,
                "throughput": self.throughput,
                "memory_mb": self.memory_mb,
                "accuracy": self.accuracy,
                "accuracy_drop": self.accuracy_drop,
            },
            "evaluation": {
                "meets_accuracy": self.meets_accuracy,
                "meets_latency": self.meets_latency,
                "is_valid": self.is_valid,
            },
            "rejection": {
                "reason": self.rejection_reason,
                "constraint": self.rejection_constraint,
            } if self.rejection_reason else None,
            "composite_score": self.composite_score,
        }


@dataclass
class SelectionExplanation:
    """Explanation for variant selection."""
    selected_variant_id: str
    selection_reason: str
    policy_applied: str
    
    # Comparison
    compared_variants: int
    rejected_count: int
    failed_count: int
    
    # Constraints
    accuracy_threshold: float
    accuracy_met: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_variant_id": self.selected_variant_id,
            "selection_reason": self.selection_reason,
            "policy_applied": self.policy_applied,
            "comparison": {
                "compared_variants": self.compared_variants,
                "rejected_count": self.rejected_count,
                "failed_count": self.failed_count,
            },
            "constraints": {
                "accuracy_threshold": self.accuracy_threshold,
                "accuracy_met": self.accuracy_met,
            },
        }


@dataclass
class ExplainabilityReport:
    """Complete explainability report."""
    job_id: str
    created_at: str
    
    # Variants
    variants: List[VariantExplanation] = field(default_factory=list)
    
    # Selection
    selection: Optional[SelectionExplanation] = None
    
    # Summary
    total_variants: int = 0
    successful_variants: int = 0
    rejected_variants: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "created_at": self.created_at,
            "summary": {
                "total_variants": self.total_variants,
                "successful_variants": self.successful_variants,
                "rejected_variants": self.rejected_variants,
            },
            "variants": [v.to_dict() for v in self.variants],
            "selection": self.selection.to_dict() if self.selection else None,
        }
    
    def save_json(self, output_dir: Path) -> Path:
        """Save as JSON."""
        path = output_dir / "explainability.json"
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        return path
    
    def save_markdown(self, output_dir: Path) -> Path:
        """Save as Markdown."""
        path = output_dir / "explainability.md"
        md = generate_markdown(self)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(md)
        return path
    
    def save(self, output_dir: Path) -> tuple[Path, Path]:
        """Save both formats."""
        return self.save_json(output_dir), self.save_markdown(output_dir)


def generate_markdown(report: ExplainabilityReport) -> str:
    """Generate human-readable markdown report."""
    lines = [
        f"# Optimization Report: {report.job_id}",
        f"",
        f"Generated: {report.created_at}",
        f"",
        f"## Summary",
        f"",
        f"- **Total variants:** {report.total_variants}",
        f"- **Successful:** {report.successful_variants}",
        f"- **Rejected:** {report.rejected_variants}",
        f"",
    ]
    
    # Selection
    if report.selection:
        lines.extend([
            f"## Selection Decision",
            f"",
            f"**Selected:** `{report.selection.selected_variant_id}`",
            f"",
            f"**Reason:** {report.selection.selection_reason}",
            f"",
            f"**Policy:** {report.selection.policy_applied}",
            f"",
            f"**Accuracy threshold:** {report.selection.accuracy_threshold * 100:.1f}%",
            f"",
        ])
    
    # Variants
    lines.extend([
        f"## Variant Analysis",
        f"",
    ])
    
    for v in report.variants:
        status_emoji = {
            VariantStatus.SELECTED: "✅",
            VariantStatus.REJECTED: "❌",
            VariantStatus.FAILED: "💥",
            VariantStatus.SKIPPED: "⏭️",
        }.get(v.status, "❓")
        
        lines.extend([
            f"### {status_emoji} {v.variant_id} ({v.variant_type})",
            f"",
            f"**Status:** {v.status.value}",
            f"",
        ])
        
        if v.latency_ms is not None:
            lines.append(f"- Latency: {v.latency_ms:.2f}ms")
        if v.accuracy is not None:
            lines.append(f"- Accuracy: {v.accuracy:.4f}")
        if v.accuracy_drop is not None:
            lines.append(f"- Accuracy drop: {v.accuracy_drop * 100:.2f}%")
        if v.memory_mb is not None:
            lines.append(f"- Memory: {v.memory_mb:.1f}MB")
        
        if v.rejection_reason:
            lines.extend([
                f"",
                f"> **Rejection:** {v.rejection_reason}",
                f"> **Constraint violated:** `{v.rejection_constraint}`",
            ])
        
        lines.append("")
    
    return "\n".join(lines)


def create_explainability_report(
    job_id: str,
    variants: list,
    selection,
    accuracy_threshold: float,
) -> ExplainabilityReport:
    """Create explainability report from variants and selection."""
    now = datetime.now(timezone.utc).isoformat()
    
    report = ExplainabilityReport(
        job_id=job_id,
        created_at=now,
    )
    
    # Process variants
    for v in variants:
        status = VariantStatus.SKIPPED
        rejection_reason = None
        rejection_constraint = None
        
        if not v.is_valid:
            status = VariantStatus.FAILED
            rejection_reason = getattr(v, 'failure_reason', 'Variant invalid')
            rejection_constraint = "is_valid"
        elif selection and v.variant_id == selection.variant.variant_id:
            status = VariantStatus.SELECTED
        elif hasattr(v, 'accuracy_drop') and v.accuracy_drop is not None:
            if v.accuracy_drop > accuracy_threshold:
                status = VariantStatus.REJECTED
                rejection_reason = f"Accuracy drop ({v.accuracy_drop * 100:.2f}%) exceeds threshold ({accuracy_threshold * 100:.1f}%)"
                rejection_constraint = "accuracy_threshold"
            else:
                status = VariantStatus.REJECTED
                rejection_reason = "Not optimal (lower composite score)"
                rejection_constraint = "composite_score"
        
        exp = VariantExplanation(
            variant_id=v.variant_id,
            variant_type=v.variant_type.value if hasattr(v.variant_type, 'value') else str(v.variant_type),
            status=status,
            latency_ms=getattr(v, 'latency_ms', None),
            throughput=getattr(v, 'throughput', None),
            memory_mb=getattr(v, 'memory_mb', None),
            accuracy=getattr(v, 'accuracy', None),
            accuracy_drop=getattr(v, 'accuracy_drop', None),
            is_valid=v.is_valid,
            meets_accuracy=getattr(v, 'accuracy_drop', 0) <= accuracy_threshold if hasattr(v, 'accuracy_drop') else True,
            rejection_reason=rejection_reason,
            rejection_constraint=rejection_constraint,
            composite_score=getattr(v, 'composite_score', None),
        )
        
        report.variants.append(exp)
        report.total_variants += 1
        
        if status == VariantStatus.SELECTED:
            report.successful_variants += 1
        elif status == VariantStatus.REJECTED:
            report.rejected_variants += 1
    
    # Selection explanation
    if selection:
        trace = selection.decision_trace
        compared_variants = getattr(trace, "variants_valid", None)
        if compared_variants is None:
            compared_variants = getattr(trace, "valid_variants", None)
        if compared_variants is None:
            compared_variants = sum(1 for v in report.variants if v.is_valid)

        report.selection = SelectionExplanation(
            selected_variant_id=selection.variant.variant_id,
            selection_reason=trace.selection_reason,
            policy_applied="ALO (Adaptive Learning Optimizer)",
            compared_variants=int(compared_variants),
            rejected_count=report.rejected_variants,
            failed_count=sum(1 for v in report.variants if v.status == VariantStatus.FAILED),
            accuracy_threshold=accuracy_threshold,
            accuracy_met=True,
        )
    
    return report
