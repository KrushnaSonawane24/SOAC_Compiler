"""
SOAC Chart Generation
=====================

Generate PNG charts for reports.
"""

import logging
from pathlib import Path
from typing import Dict, List

from .models import ReportData
from .exceptions import ChartGenerationError

logger = logging.getLogger(__name__)

# Try to import matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("Matplotlib not available. Charts will not be generated.")


def generate_accuracy_chart(data: ReportData, output_dir: Path) -> Path:
    """Generate accuracy comparison chart."""
    if not MATPLOTLIB_AVAILABLE:
        raise ChartGenerationError("Matplotlib not available")
    
    path = output_dir / "accuracy_chart.png"
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Data
    variants = data.variants
    names = [v.variant_id[:15] for v in variants]
    accuracies = [v.accuracy * 100 for v in variants]
    colors = ['#10b981' if v.status == 'selected' else '#6366f1' for v in variants]
    
    # Bar chart
    bars = ax.bar(names, accuracies, color=colors, edgecolor='white', linewidth=1)
    
    # Threshold line
    threshold_line = (1 - data.accuracy_verification.threshold) * 100 + data.accuracy_verification.baseline_accuracy * 100
    ax.axhline(y=threshold_line, color='#ef4444', linestyle='--', label=f'Min Threshold ({threshold_line:.1f}%)')
    
    # Styling
    ax.set_ylabel('Accuracy (%)', fontsize=12)
    ax.set_xlabel('Variant', fontsize=12)
    ax.set_title('Accuracy Comparison', fontsize=14, fontweight='bold')
    ax.set_ylim([min(accuracies) * 0.95, 100])
    ax.legend()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(path, dpi=150, facecolor='white', edgecolor='none')
    plt.close(fig)
    
    return path


def generate_latency_chart(data: ReportData, output_dir: Path) -> Path:
    """Generate latency comparison chart."""
    if not MATPLOTLIB_AVAILABLE:
        raise ChartGenerationError("Matplotlib not available")
    
    path = output_dir / "latency_chart.png"
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Data
    variants = data.variants
    names = [v.variant_id[:15] for v in variants]
    latencies = [v.latency_ms for v in variants]
    colors = ['#10b981' if v.status == 'selected' else '#6366f1' for v in variants]
    
    # Bar chart
    bars = ax.barh(names, latencies, color=colors, edgecolor='white', linewidth=1)
    
    # Add value labels
    for bar, lat in zip(bars, latencies):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f'{lat:.1f}ms', va='center', fontsize=10)
    
    # Styling
    ax.set_xlabel('Latency (ms)', fontsize=12)
    ax.set_ylabel('Variant', fontsize=12)
    ax.set_title('Latency Comparison', fontsize=14, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.savefig(path, dpi=150, facecolor='white', edgecolor='none')
    plt.close(fig)
    
    return path


def generate_size_chart(data: ReportData, output_dir: Path) -> Path:
    """Generate model size comparison chart."""
    if not MATPLOTLIB_AVAILABLE:
        raise ChartGenerationError("Matplotlib not available")
    
    path = output_dir / "size_chart.png"
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Data
    variants = data.variants
    names = ['Original'] + [v.variant_id[:15] for v in variants]
    sizes = [data.model_info.original_size_bytes / 1024 / 1024] + [v.size_bytes / 1024 / 1024 for v in variants]
    colors = ['#6b7280'] + ['#10b981' if v.status == 'selected' else '#6366f1' for v in variants]
    
    # Bar chart
    bars = ax.bar(names, sizes, color=colors, edgecolor='white', linewidth=1)
    
    # Styling
    ax.set_ylabel('Size (MB)', fontsize=12)
    ax.set_xlabel('Model', fontsize=12)
    ax.set_title('Model Size Comparison', fontsize=14, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(path, dpi=150, facecolor='white', edgecolor='none')
    plt.close(fig)
    
    return path


def generate_all_charts(data: ReportData, output_dir: Path) -> Dict[str, Path]:
    """Generate all charts."""
    if not MATPLOTLIB_AVAILABLE:
        logger.warning("Skipping chart generation - matplotlib not available")
        return {}
    
    try:
        return {
            "accuracy_chart": generate_accuracy_chart(data, output_dir),
            "latency_chart": generate_latency_chart(data, output_dir),
            "size_chart": generate_size_chart(data, output_dir),
        }
    except Exception as e:
        logger.error(f"Chart generation failed: {e}")
        return {}
