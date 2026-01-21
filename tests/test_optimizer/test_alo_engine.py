"""
Tests for ALO Engine
====================

Tests for variant selection using ALO rules.
"""

import pytest

from backend.optimizer import (
    select_best_variant,
    filter_valid_variants,
    rank_variants,
    VariantType,
    VariantStatus,
    MAX_ACCURACY_DROP,
    NoValidVariantsError,
)


class TestAccuracyConstraint:
    """Tests for accuracy threshold enforcement."""
    
    def test_variant_within_threshold_accepted(self, mock_fp16_variant):
        """Variants within 2% accuracy drop are accepted."""
        valid, rejected = filter_valid_variants([mock_fp16_variant])
        
        assert len(valid) == 1
        assert len(rejected) == 0
    
    def test_variant_exceeding_threshold_rejected(self, mock_rejected_variant):
        """Variants exceeding 2% accuracy drop are rejected."""
        valid, rejected = filter_valid_variants([mock_rejected_variant])
        
        assert len(valid) == 0
        assert len(rejected) == 1
        assert "5.00%" in rejected[0].rejection_reason or "Accuracy drop" in rejected[0].rejection_reason
    
    def test_generation_failures_rejected(self, mock_failed_variant):
        """Failed generations are rejected."""
        valid, rejected = filter_valid_variants([mock_failed_variant])
        
        assert len(valid) == 0
        assert len(rejected) == 1
        assert "Generation failed" in rejected[0].rejection_reason


class TestVariantRanking:
    """Tests for variant ranking logic."""
    
    def test_lowest_latency_ranked_first(self, all_valid_variants):
        """Lowest latency variant is ranked first."""
        ranking = rank_variants(all_valid_variants)
        
        assert ranking[0].variant_type == VariantType.INT8  # 5ms
        assert ranking[0].rank == 1
    
    def test_ranking_is_deterministic(self, all_valid_variants):
        """Ranking is deterministic across calls."""
        ranking1 = rank_variants(all_valid_variants)
        ranking2 = rank_variants(all_valid_variants)
        
        for r1, r2 in zip(ranking1, ranking2):
            assert r1.variant_id == r2.variant_id
            assert r1.rank == r2.rank
    
    def test_preference_order_for_ties(self, temp_dir):
        """INT8 > FP16 > Baseline when latency/size are equal."""
        from backend.optimizer.metadata import OptimizedVariant, BenchmarkMetrics
        
        # Create variants with same latency and size
        same_metrics = BenchmarkMetrics(
            latency_ms=10.0,
            throughput=100.0,
            memory_mb=256.0,
            accuracy=0.98,
            accuracy_drop=0.01,
        )
        
        path = temp_dir / "test.onnx"
        path.write_bytes(b"test" * 100)
        
        fp16 = OptimizedVariant(
            variant_id="fp16_tie",
            variant_type=VariantType.FP16,
            onnx_path=path,
            graph_hash="hash1",
            size_bytes=path.stat().st_size,
            metrics=same_metrics,
        )
        
        baseline = OptimizedVariant(
            variant_id="baseline_tie",
            variant_type=VariantType.BASELINE,
            onnx_path=path,
            graph_hash="hash2",
            size_bytes=path.stat().st_size,
            metrics=same_metrics,
        )
        
        int8 = OptimizedVariant(
            variant_id="int8_tie",
            variant_type=VariantType.INT8,
            onnx_path=path,
            graph_hash="hash3",
            size_bytes=path.stat().st_size,
            metrics=same_metrics,
        )
        
        ranking = rank_variants([baseline, fp16, int8])
        
        # INT8 should be first (highest preference)
        assert ranking[0].variant_type == VariantType.INT8


class TestBestVariantSelection:
    """Tests for select_best_variant function."""
    
    def test_selects_best_variant(self, all_valid_variants):
        """Correctly selects best variant."""
        result = select_best_variant(all_valid_variants, "test_hash")
        
        # INT8 should win (lowest latency)
        assert result.variant.variant_type == VariantType.INT8
        assert result.variant.variant_id == "int8_abc123"
    
    def test_excludes_rejected_variants(self, variants_with_rejected):
        """Rejected variants are excluded from selection."""
        result = select_best_variant(variants_with_rejected, "test_hash")
        
        # Should not select the rejected variant
        assert result.variant.variant_type != VariantType.INT8
        # Should select FP16 (faster than baseline)
        assert result.variant.variant_type == VariantType.FP16
    
    def test_raises_when_no_valid_variants(self, mock_rejected_variant, mock_failed_variant):
        """Raises error when no valid variants."""
        with pytest.raises(NoValidVariantsError) as exc_info:
            select_best_variant([mock_rejected_variant, mock_failed_variant], "test_hash")
        
        assert exc_info.value.error_code == "NO_VALID_VARIANTS"
    
    def test_decision_trace_complete(self, all_valid_variants):
        """Decision trace contains all required fields."""
        result = select_best_variant(all_valid_variants, "test_hash")
        
        trace = result.decision_trace
        
        assert trace.timestamp is not None
        assert trace.input_hash == "test_hash"
        assert trace.variants_generated == 4
        assert trace.variants_valid == 4
        assert trace.final_selection == result.variant.variant_id
        assert len(trace.ranking) == 4
        assert len(trace.decision_rules) > 0
    
    def test_decision_trace_serializable(self, all_valid_variants):
        """Decision trace can be serialized to JSON."""
        result = select_best_variant(all_valid_variants, "test_hash")
        
        json_str = result.decision_trace.to_json()
        
        assert isinstance(json_str, str)
        assert "final_selection" in json_str
        assert "ranking" in json_str
    
    def test_selection_reason_is_explanatory(self, all_valid_variants):
        """Selection reason explains the decision."""
        result = select_best_variant(all_valid_variants, "test_hash")
        
        reason = result.decision_trace.selection_reason
        
        assert "int8" in reason.lower() or "latency" in reason.lower()


class TestDeterminism:
    """Tests for deterministic behavior."""
    
    def test_selection_is_deterministic(self, all_valid_variants):
        """Same input always produces same output."""
        result1 = select_best_variant(all_valid_variants, "hash1")
        result2 = select_best_variant(all_valid_variants, "hash1")
        
        assert result1.variant.variant_id == result2.variant.variant_id
        assert result1.decision_trace.final_selection == result2.decision_trace.final_selection
    
    def test_ranking_order_is_stable(self, all_valid_variants):
        """Ranking order is stable across calls."""
        ranking1 = rank_variants(all_valid_variants)
        ranking2 = rank_variants(all_valid_variants)
        
        ids1 = [r.variant_id for r in ranking1]
        ids2 = [r.variant_id for r in ranking2]
        
        assert ids1 == ids2
