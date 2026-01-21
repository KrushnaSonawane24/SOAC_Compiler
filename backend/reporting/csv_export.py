"""
SOAC CSV Export
===============

CSV export for job results.
"""

import csv
from pathlib import Path
from typing import Dict, List

from .models import ReportData, VariantResult


def export_benchmark_metrics(data: ReportData, output_dir: Path) -> Path:
    """Export benchmark metrics to CSV."""
    path = output_dir / "benchmark_metrics.csv"
    
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            "Stage",
            "Duration (ms)",
            "Success",
            "Message",
        ])
        
        # Rows
        for b in data.benchmarks:
            writer.writerow([
                b.stage,
                round(b.duration_ms, 2),
                "Yes" if b.success else "No",
                b.message,
            ])
    
    return path


def export_variant_comparison(data: ReportData, output_dir: Path) -> Path:
    """Export variant comparison to CSV."""
    path = output_dir / "variant_comparison.csv"
    
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            "Variant ID",
            "Variant Type",
            "Accuracy",
            "Latency (ms)",
            "Size (MB)",
            "Memory (MB)",
            "Status",
            "Rejection Reason",
        ])
        
        # Rows
        for v in data.variants:
            writer.writerow([
                v.variant_id,
                v.variant_type,
                round(v.accuracy, 4),
                round(v.latency_ms, 2),
                round(v.size_bytes / 1024 / 1024, 2),
                round(v.memory_mb, 2),
                v.status.upper(),
                v.rejection_reason or "",
            ])
    
    return path


def export_all_csv(data: ReportData, output_dir: Path) -> Dict[str, Path]:
    """Export all CSV files."""
    return {
        "benchmark_metrics": export_benchmark_metrics(data, output_dir),
        "variant_comparison": export_variant_comparison(data, output_dir),
    }
