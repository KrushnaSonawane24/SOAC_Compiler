"""
SOAC JSON Export
================

JSON export for job results.
"""

import json
from pathlib import Path
from typing import Dict, Any

from .models import ReportData


def export_job_summary(data: ReportData, output_dir: Path) -> Path:
    """Export job summary JSON."""
    summary = {
        "job_id": data.job_id,
        "user_id": data.user_id,
        "timestamp": data.timestamp,
        "build_mode": data.build_mode,
        "compilation_policy": data.compilation_policy,
        "model_info": data.model_info.to_dict(),
        "selected_variant_id": data.selected_variant_id,
        "verdict": data.verdict.value,
        "deployment_readiness": data.deployment_readiness,
    }
    
    path = output_dir / "job_summary.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    return path


def export_benchmark_results(data: ReportData, output_dir: Path) -> Path:
    """Export benchmark results JSON."""
    results = {
        "job_id": data.job_id,
        "benchmarks": [b.to_dict() for b in data.benchmarks],
        "total_duration_ms": sum(b.duration_ms for b in data.benchmarks),
    }
    
    path = output_dir / "benchmark_results.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, sort_keys=True)
    return path


def export_optimization_trace(data: ReportData, output_dir: Path) -> Path:
    """Export optimization trace JSON."""
    trace = {
        "job_id": data.job_id,
        "variants_generated": len(data.variants),
        "variants": [v.to_dict() for v in data.variants],
        "selected_variant_id": data.selected_variant_id,
        "selection_reason": data.selection_reason,
        "policy_influence": data.policy_influence,
        "constraint_statement": data.constraint_statement,
        "accuracy_verification": data.accuracy_verification.to_dict(),
    }
    
    path = output_dir / "optimization_trace.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(trace, f, indent=2, sort_keys=True)
    return path


def export_build_fingerprint(data: ReportData, output_dir: Path) -> Path:
    """Export build fingerprint JSON."""
    fingerprint = {
        "job_id": data.job_id,
        "build_mode": data.build_mode,
        "fingerprint": data.build_fingerprint,
        "deterministic_guarantee": data.deterministic_guarantee,
        "timestamp": data.timestamp,
    }
    
    path = output_dir / "build_fingerprint.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(fingerprint, f, indent=2, sort_keys=True)
    return path


def export_explainability(data: ReportData, output_dir: Path) -> Path:
    """Export explainability JSON."""
    explain = {
        "job_id": data.job_id,
        "selection_reason": data.selection_reason,
        "policy_influence": data.policy_influence,
        "constraint_statement": data.constraint_statement,
        "selected_variant_id": data.selected_variant_id,
        "rejected_variants": [
            {
                "variant_id": v.variant_id,
                "variant_type": v.variant_type,
                "rejection_reason": v.rejection_reason,
            }
            for v in data.variants if v.status == "rejected"
        ],
        "accuracy_verification": data.accuracy_verification.to_dict(),
    }
    
    path = output_dir / "explainability.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(explain, f, indent=2, sort_keys=True)
    return path


def export_all_json(data: ReportData, output_dir: Path) -> Dict[str, Path]:
    """Export all JSON files."""
    return {
        "job_summary": export_job_summary(data, output_dir),
        "benchmark_results": export_benchmark_results(data, output_dir),
        "optimization_trace": export_optimization_trace(data, output_dir),
        "build_fingerprint": export_build_fingerprint(data, output_dir),
        "explainability": export_explainability(data, output_dir),
    }
