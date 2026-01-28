"""
Pytest Fixtures for Benchmark Tests
====================================

Creates mock models and datasets for testing.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import numpy as np

try:
    import onnx
    from onnx import helper, TensorProto
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

from backend.benchmark.dataset import ReferenceDataset, DatasetSample, create_synthetic_dataset
from backend.benchmark.result import AccuracyResult, LatencyResult, MemoryResult, SizeResult


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    dir_path = Path(tempfile.mkdtemp(prefix="test_benchmark_"))
    yield dir_path
    if dir_path.exists():
        shutil.rmtree(dir_path)


@pytest.fixture
def simple_onnx_model(temp_dir) -> Path:
    """Create a simple ONNX model for testing."""
    if not ONNX_AVAILABLE:
        pytest.skip("ONNX not available")
    
    # Create simple model: input -> Relu -> output
    X = helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 3, 224, 224])
    Y = helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, 150528])
    
    # Create nodes
    nodes = [
        helper.make_node('Flatten', ['input'], ['flat']),
        helper.make_node('Relu', ['flat'], ['output']),
    ]
    
    graph = helper.make_graph(nodes, 'test', [X], [Y])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 13)])
    model.ir_version = 7
    
    path = temp_dir / "test_model.onnx"
    onnx.save(model, str(path))
    return path


@pytest.fixture
def synthetic_dataset() -> ReferenceDataset:
    """Create synthetic dataset for testing."""
    return create_synthetic_dataset(
        num_samples=20,
        input_shape=(1, 3, 224, 224),
        num_classes=1000,
        seed=42,
    )


@pytest.fixture
def sample_input() -> np.ndarray:
    """Create sample input tensor."""
    np.random.seed(42)
    return np.random.randn(1, 3, 224, 224).astype(np.float32)


@pytest.fixture
def mock_accuracy_result() -> AccuracyResult:
    """Create mock accuracy result."""
    return AccuracyResult(
        accuracy=0.95,
        correct=95,
        total=100,
        accuracy_drop=0.0,
        is_baseline=True,
    )


@pytest.fixture
def mock_latency_result() -> LatencyResult:
    """Create mock latency result."""
    return LatencyResult(
        median_ms=10.0,
        mean_ms=10.5,
        min_ms=8.0,
        max_ms=15.0,
        std_ms=2.0,
        warmup_runs=5,
        measured_runs=50,
    )


@pytest.fixture
def mock_memory_result() -> MemoryResult:
    """Create mock memory result."""
    return MemoryResult(
        peak_mb=256.0,
        before_mb=100.0,
        after_mb=150.0,
        delta_mb=50.0,
    )


@pytest.fixture
def mock_size_result() -> SizeResult:
    """Create mock size result."""
    return SizeResult(
        file_size_bytes=50_000_000,
        file_size_mb=47.68,
        parameter_count=1_000_000,
    )
