"""
Tests for Compilation Policies
==============================

Tests for policy-based variant selection.
"""

import pytest
from dataclasses import dataclass
from enum import Enum

from backend.policies import (
    CompilationPolicy,
    PolicyWeights,
    get_policy_weights,
    compute_policy_score,
    get_variant_preference,
    explain_policy,
)


class TestPolicyWeights:
    """Tests for policy weights."""
    
    def test_all_policies_have_weights(self):
        """All policies have defined weights."""
        for policy in CompilationPolicy:
            weights = get_policy_weights(policy)
            assert weights is not None
            # Weights should sum to approximately 1.0
            total = weights.accuracy + weights.latency + weights.memory + weights.size
            assert total == pytest.approx(1.0)
    
    def test_accuracy_first_prioritizes_accuracy(self):
        """Accuracy-first has highest accuracy weight."""
        weights = get_policy_weights(CompilationPolicy.ACCURACY_FIRST)
        assert weights.accuracy > weights.latency
        assert weights.accuracy > weights.memory
        assert weights.accuracy > weights.size
    
    def test_latency_first_prioritizes_latency(self):
        """Latency-first has highest latency weight."""
        weights = get_policy_weights(CompilationPolicy.LATENCY_FIRST)
        assert weights.latency > weights.accuracy
        assert weights.latency > weights.memory


class TestPolicyScoring:
    """Tests for policy-based scoring."""
    
    def test_accuracy_first_prefers_high_accuracy(self):
        """Accuracy-first scores high-accuracy variants higher."""
        # High accuracy, slow
        score_accurate = compute_policy_score(
            accuracy_score=0.95,
            latency_score=0.5,
            memory_score=0.7,
            size_score=0.7,
            policy=CompilationPolicy.ACCURACY_FIRST,
        )
        
        # Low accuracy, fast
        score_fast = compute_policy_score(
            accuracy_score=0.7,
            latency_score=0.95,
            memory_score=0.7,
            size_score=0.7,
            policy=CompilationPolicy.ACCURACY_FIRST,
        )
        
        assert score_accurate > score_fast
    
    def test_latency_first_prefers_fast(self):
        """Latency-first scores fast variants higher."""
        # Slow but accurate
        score_slow = compute_policy_score(
            accuracy_score=0.95,
            latency_score=0.5,
            memory_score=0.7,
            size_score=0.7,
            policy=CompilationPolicy.LATENCY_FIRST,
        )
        
        # Fast with acceptable accuracy
        score_fast = compute_policy_score(
            accuracy_score=0.8,
            latency_score=0.95,
            memory_score=0.7,
            size_score=0.7,
            policy=CompilationPolicy.LATENCY_FIRST,
        )
        
        assert score_fast > score_slow


class TestDifferentPoliciesDifferentSelection:
    """Tests that different policies lead to different selections."""
    
    def test_same_variants_different_winner(self):
        """Same variants, different policies yield different winners."""
        # Variant A: Very high accuracy, very slow
        variant_a_metrics = {
            "accuracy_score": 1.0,
            "latency_score": 0.2,
            "memory_score": 0.5,
            "size_score": 0.5,
        }
        
        # Variant B: Much lower accuracy, very fast
        variant_b_metrics = {
            "accuracy_score": 0.5,
            "latency_score": 1.0,
            "memory_score": 0.5,
            "size_score": 0.5,
        }
        
        # Accuracy-first should prefer A
        score_a_acc = compute_policy_score(
            **variant_a_metrics,
            policy=CompilationPolicy.ACCURACY_FIRST,
        )
        score_b_acc = compute_policy_score(
            **variant_b_metrics,
            policy=CompilationPolicy.ACCURACY_FIRST,
        )
        assert score_a_acc > score_b_acc
        
        # Latency-first should prefer B
        score_a_lat = compute_policy_score(
            **variant_a_metrics,
            policy=CompilationPolicy.LATENCY_FIRST,
        )
        score_b_lat = compute_policy_score(
            **variant_b_metrics,
            policy=CompilationPolicy.LATENCY_FIRST,
        )
        assert score_b_lat > score_a_lat


class TestAccuracyFirstNeverSelectsLessAccurate:
    """Tests that accuracy-first never selects faster-but-less-accurate."""
    
    def test_accuracy_first_prefers_accurate_over_fast(self):
        """Accuracy-first always prefers more accurate variant."""
        # Test multiple scenarios
        scenarios = [
            # (accurate_score, accurate_latency, fast_score, fast_latency)
            (0.95, 0.3, 0.7, 0.95),
            (0.90, 0.4, 0.6, 0.99),
            (0.85, 0.5, 0.5, 0.95),
        ]
        
        for acc_acc, acc_lat, fast_acc, fast_lat in scenarios:
            score_accurate = compute_policy_score(
                accuracy_score=acc_acc,
                latency_score=acc_lat,
                memory_score=0.7,
                size_score=0.7,
                policy=CompilationPolicy.ACCURACY_FIRST,
            )
            
            score_fast = compute_policy_score(
                accuracy_score=fast_acc,
                latency_score=fast_lat,
                memory_score=0.7,
                size_score=0.7,
                policy=CompilationPolicy.ACCURACY_FIRST,
            )
            
            assert score_accurate > score_fast, (
                f"Accurate variant should win with accuracy_first: "
                f"acc={acc_acc} vs fast_acc={fast_acc}"
            )


class TestVariantPreference:
    """Tests for variant type preferences."""
    
    def test_accuracy_first_prefers_baseline(self):
        """Accuracy-first prefers baseline variant."""
        prefs = get_variant_preference(CompilationPolicy.ACCURACY_FIRST)
        assert prefs[0] == "baseline"
    
    def test_latency_first_prefers_int8(self):
        """Latency-first prefers INT8 variant."""
        prefs = get_variant_preference(CompilationPolicy.LATENCY_FIRST)
        assert prefs[0] == "int8"


class TestPolicyExplanation:
    """Tests for policy explanation."""
    
    def test_explanation_includes_rationale(self):
        """Policy explanation includes selection rationale."""
        exp = explain_policy(
            policy=CompilationPolicy.ACCURACY_FIRST,
            selected_variant_id="baseline_v1",
            accuracy_drop=0.01,
        )
        
        assert "accuracy" in exp.selection_rationale.lower()
        assert "baseline_v1" in exp.selection_rationale
