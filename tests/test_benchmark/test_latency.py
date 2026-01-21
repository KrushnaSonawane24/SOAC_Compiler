"""
Tests for Latency Measurement
=============================

Tests for latency benchmarking.
"""

import pytest

try:
    import onnxruntime
    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ONNXRUNTIME_AVAILABLE = False

from backend.benchmark import (
    measure_latency,
    create_sample_input,
    LatencyResult,
)


class TestLatencyResult:
    """Tests for LatencyResult structure."""
    
    def test_result_serializable(self, mock_latency_result):
        """LatencyResult can be serialized."""
        result_dict = mock_latency_result.to_dict()
        
        assert "median_ms" in result_dict
        assert "mean_ms" in result_dict
        assert "warmup_runs" in result_dict
    
    def test_result_is_frozen(self):
        """LatencyResult is immutable."""
        result = LatencyResult(
            median_ms=10.0, mean_ms=10.5, min_ms=8.0,
            max_ms=15.0, std_ms=2.0, warmup_runs=5, measured_runs=50
        )
        
        with pytest.raises(AttributeError):
            result.median_ms = 5.0


class TestLatencyMeasurement:
    """Tests for latency measurement."""
    
    @pytest.mark.skipif(not ONNXRUNTIME_AVAILABLE, reason="onnxruntime not available")
    def test_measure_with_warmup(self, simple_onnx_model, sample_input):
        """Latency measured after warmup runs."""
        result = measure_latency(
            simple_onnx_model,
            sample_input,
            warmup_runs=3,
            measured_runs=10,
        )
        
        assert result.warmup_runs == 3
        assert result.measured_runs == 10
        assert result.median_ms > 0
    
    @pytest.mark.skipif(not ONNXRUNTIME_AVAILABLE, reason="onnxruntime not available")
    def test_statistics_computed(self, simple_onnx_model, sample_input):
        """All statistics are computed."""
        result = measure_latency(simple_onnx_model, sample_input)
        
        assert result.median_ms > 0
        assert result.mean_ms > 0
        assert result.min_ms <= result.median_ms
        assert result.max_ms >= result.median_ms
        assert result.std_ms >= 0
    
    @pytest.mark.skipif(not ONNXRUNTIME_AVAILABLE, reason="onnxruntime not available")
    def test_measurement_is_reproducible(self, simple_onnx_model, sample_input):
        """Measurements are reasonably stable."""
        result1 = measure_latency(simple_onnx_model, sample_input, measured_runs=20)
        result2 = measure_latency(simple_onnx_model, sample_input, measured_runs=20)
        
        # Within 50% of each other (accounting for system variance)
        ratio = result1.median_ms / result2.median_ms
        assert 0.5 < ratio < 2.0


class TestSampleInput:
    """Tests for sample input creation."""
    
    @pytest.mark.skipif(not ONNXRUNTIME_AVAILABLE, reason="onnxruntime not available")
    def test_creates_correct_shape(self, simple_onnx_model):
        """Sample input has correct shape."""
        sample = create_sample_input(simple_onnx_model)
        
        assert sample.shape[0] == 1  # Batch
        assert sample.dtype.name == 'float32'
