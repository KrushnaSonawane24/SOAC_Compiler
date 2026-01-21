"""
Tests for Accuracy Measurement
==============================

Tests for accuracy evaluation and constraint enforcement.
"""

import pytest

from backend.benchmark import (
    evaluate_accuracy,
    verify_accuracy_constraint,
    compare_accuracy,
    AccuracyResult,
    AccuracyConstraintViolation,
    MAX_ACCURACY_DROP,
)
from backend.benchmark.metrics import calculate_accuracy_drop, is_accuracy_acceptable


class TestAccuracyDelta:
    """Tests for accuracy drop calculation."""
    
    def test_calculate_drop_when_lower(self):
        """Drop is positive when accuracy decreases."""
        drop = calculate_accuracy_drop(baseline=0.95, measured=0.90)
        assert drop == pytest.approx(0.05)
    
    def test_calculate_drop_when_equal(self):
        """Drop is zero when accuracy unchanged."""
        drop = calculate_accuracy_drop(baseline=0.95, measured=0.95)
        assert drop == 0.0
    
    def test_calculate_drop_when_improved(self):
        """Drop is zero when accuracy improved."""
        drop = calculate_accuracy_drop(baseline=0.90, measured=0.95)
        assert drop == 0.0
    
    def test_threshold_exactly_2_percent(self):
        """2% drop is acceptable."""
        assert is_accuracy_acceptable(0.95, 0.93, threshold=0.02)
    
    def test_threshold_exceeded(self):
        """More than 2% drop is not acceptable."""
        assert not is_accuracy_acceptable(0.95, 0.92, threshold=0.02)


class TestAccuracyResult:
    """Tests for AccuracyResult structure."""
    
    def test_result_serializable(self, mock_accuracy_result):
        """AccuracyResult can be serialized."""
        result_dict = mock_accuracy_result.to_dict()
        
        assert "accuracy" in result_dict
        assert "correct" in result_dict
        assert "total" in result_dict
        assert result_dict["accuracy"] == 0.95
    
    def test_result_is_frozen(self):
        """AccuracyResult is immutable."""
        result = AccuracyResult(accuracy=0.9, correct=90, total=100)
        
        with pytest.raises(AttributeError):
            result.accuracy = 0.8


class TestAccuracyConstraint:
    """Tests for accuracy constraint enforcement."""
    
    def test_constraint_passes_within_threshold(self):
        """Constraint passes when drop <= 2%."""
        baseline = AccuracyResult(accuracy=0.95, correct=95, total=100, is_baseline=True)
        optimized = AccuracyResult(accuracy=0.94, correct=94, total=100, accuracy_drop=0.01)
        
        assert verify_accuracy_constraint(baseline, optimized)
    
    def test_constraint_raises_when_exceeded(self):
        """Constraint raises when drop > 2%."""
        baseline = AccuracyResult(accuracy=0.95, correct=95, total=100, is_baseline=True)
        optimized = AccuracyResult(accuracy=0.90, correct=90, total=100, accuracy_drop=0.05)
        
        with pytest.raises(AccuracyConstraintViolation) as exc_info:
            verify_accuracy_constraint(baseline, optimized)
        
        assert exc_info.value.error_code == "ACCURACY_CONSTRAINT_VIOLATED"


try:
    import onnxruntime
    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ONNXRUNTIME_AVAILABLE = False


class TestDeterminism:
    """Tests for deterministic accuracy evaluation."""
    
    @pytest.mark.skipif(not ONNXRUNTIME_AVAILABLE, reason="onnxruntime not available")
    def test_same_input_same_result(self, simple_onnx_model, synthetic_dataset):
        """Same model and dataset produce identical accuracy."""
        result1 = evaluate_accuracy(simple_onnx_model, synthetic_dataset)
        result2 = evaluate_accuracy(simple_onnx_model, synthetic_dataset)
        
        assert result1.accuracy == result2.accuracy
        assert result1.correct == result2.correct
