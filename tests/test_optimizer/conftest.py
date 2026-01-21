"""
Pytest Fixtures for Optimizer Tests
====================================

Creates mock variants and benchmark data for testing ALO logic.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from backend.optimizer.metadata import (
    VariantType,
    VariantStatus,
    OptimizedVariant,
    BenchmarkMetrics,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    dir_path = Path(tempfile.mkdtemp(prefix="test_optimizer_"))
    yield dir_path
    if dir_path.exists():
        shutil.rmtree(dir_path)


@pytest.fixture
def mock_baseline_variant(temp_dir) -> OptimizedVariant:
    """Create mock baseline variant."""
    path = temp_dir / "baseline.onnx"
    path.write_bytes(b"mock baseline model content" * 100)
    
    return OptimizedVariant(
        variant_id="baseline_abc123",
        variant_type=VariantType.BASELINE,
        onnx_path=path,
        graph_hash="abc123def456",
        size_bytes=path.stat().st_size,
        status=VariantStatus.VALID,
        metrics=BenchmarkMetrics(
            latency_ms=10.0,
            throughput=100.0,
            memory_mb=256.0,
            accuracy=0.98,
            accuracy_drop=0.0,  # Baseline is reference
        ),
    )


@pytest.fixture
def mock_fp16_variant(temp_dir) -> OptimizedVariant:
    """Create mock FP16 variant."""
    path = temp_dir / "fp16.onnx"
    path.write_bytes(b"mock fp16 model" * 50)  # Smaller
    
    return OptimizedVariant(
        variant_id="fp16_abc123",
        variant_type=VariantType.FP16,
        onnx_path=path,
        graph_hash="fp16hash123",
        size_bytes=path.stat().st_size,
        status=VariantStatus.VALID,
        metrics=BenchmarkMetrics(
            latency_ms=8.0,  # Faster
            throughput=125.0,
            memory_mb=128.0,
            accuracy=0.975,
            accuracy_drop=0.005,  # 0.5% drop - OK
        ),
    )


@pytest.fixture
def mock_int8_variant(temp_dir) -> OptimizedVariant:
    """Create mock INT8 variant."""
    path = temp_dir / "int8.onnx"
    path.write_bytes(b"mock int8" * 25)  # Even smaller
    
    return OptimizedVariant(
        variant_id="int8_abc123",
        variant_type=VariantType.INT8,
        onnx_path=path,
        graph_hash="int8hash456",
        size_bytes=path.stat().st_size,
        status=VariantStatus.VALID,
        metrics=BenchmarkMetrics(
            latency_ms=5.0,  # Fastest
            throughput=200.0,
            memory_mb=64.0,
            accuracy=0.97,
            accuracy_drop=0.01,  # 1% drop - OK
        ),
    )


@pytest.fixture
def mock_pruned_variant(temp_dir) -> OptimizedVariant:
    """Create mock pruned variant."""
    path = temp_dir / "pruned.onnx"
    path.write_bytes(b"mock pruned" * 80)
    
    return OptimizedVariant(
        variant_id="pruned_abc123",
        variant_type=VariantType.PRUNED,
        onnx_path=path,
        graph_hash="prunedhash789",
        size_bytes=path.stat().st_size,
        status=VariantStatus.VALID,
        metrics=BenchmarkMetrics(
            latency_ms=9.0,
            throughput=110.0,
            memory_mb=200.0,
            accuracy=0.96,
            accuracy_drop=0.02,  # 2% drop - at limit
        ),
    )


@pytest.fixture
def mock_rejected_variant(temp_dir) -> OptimizedVariant:
    """Create variant that exceeds accuracy threshold."""
    path = temp_dir / "rejected.onnx"
    path.write_bytes(b"mock rejected" * 20)
    
    return OptimizedVariant(
        variant_id="rejected_abc123",
        variant_type=VariantType.INT8,
        onnx_path=path,
        graph_hash="rejectedhash",
        size_bytes=path.stat().st_size,
        status=VariantStatus.VALID,
        metrics=BenchmarkMetrics(
            latency_ms=4.0,  # Very fast but...
            throughput=250.0,
            memory_mb=32.0,
            accuracy=0.93,
            accuracy_drop=0.05,  # 5% drop - REJECTED!
        ),
    )


@pytest.fixture
def mock_failed_variant(temp_dir) -> OptimizedVariant:
    """Create variant that failed generation."""
    path = temp_dir / "failed.onnx"
    
    return OptimizedVariant(
        variant_id="failed_abc123",
        variant_type=VariantType.FP16,
        onnx_path=path,
        graph_hash="",
        size_bytes=0,
        status=VariantStatus.GENERATION_FAILED,
        error_message="Quantization not supported",
    )


@pytest.fixture
def all_valid_variants(
    mock_baseline_variant,
    mock_fp16_variant,
    mock_int8_variant,
    mock_pruned_variant,
):
    """List of all valid variants."""
    return [
        mock_baseline_variant,
        mock_fp16_variant,
        mock_int8_variant,
        mock_pruned_variant,
    ]


@pytest.fixture
def variants_with_rejected(
    mock_baseline_variant,
    mock_fp16_variant,
    mock_rejected_variant,
):
    """Variants including one that should be rejected."""
    return [
        mock_baseline_variant,
        mock_fp16_variant,
        mock_rejected_variant,
    ]
