"""
Tests for Explainability Report
================================

Tests for explainable optimization reports.
"""

import pytest
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from backend.explainability import (
    VariantStatus,
    VariantExplanation,
    SelectionExplanation,
    ExplainabilityReport,
    generate_markdown,
    create_explainability_report,
)


class MockVariantType(str, Enum):
    """Mock variant type for testing."""
    BASELINE = "baseline"
    FP16 = "fp16"
    INT8 = "int8"


@dataclass
class MockVariant:
    """Mock variant for testing."""
    variant_id: str
    variant_type: MockVariantType
    is_valid: bool = True
    latency_ms: float = 10.0
    accuracy: float = 0.95
    accuracy_drop: float = 0.0
    graph_hash: str = "hash123"
    failure_reason: str = ""


@dataclass
class MockDecisionTrace:
    """Mock decision trace."""
    selection_reason: str = "Best composite score"
    policy_name: str = "latency_optimized"
    candidates_considered: int = 3


@dataclass
class MockSelection:
    """Mock selection."""
    variant: MockVariant
    decision_trace: MockDecisionTrace


class TestVariantExplanation:
    """Tests for variant explanations."""
    
    def test_selected_variant(self):
        """Selected variant has correct status."""
        exp = VariantExplanation(
            variant_id="v1",
            variant_type="baseline",
            status=VariantStatus.SELECTED,
        )
        
        assert exp.status == VariantStatus.SELECTED
        assert exp.to_dict()["status"] == "selected"
    
    def test_rejected_with_reason(self):
        """Rejected variant has rejection reason."""
        exp = VariantExplanation(
            variant_id="v2",
            variant_type="int8",
            status=VariantStatus.REJECTED,
            rejection_reason="Accuracy drop exceeds threshold",
            rejection_constraint="accuracy_threshold",
        )
        
        d = exp.to_dict()
        assert d["rejection"]["reason"] == "Accuracy drop exceeds threshold"
        assert d["rejection"]["constraint"] == "accuracy_threshold"


class TestExplainabilityReport:
    """Tests for explainability report."""
    
    def test_report_creation(self):
        """Report can be created from variants."""
        variants = [
            MockVariant("v1", MockVariantType.BASELINE, accuracy_drop=0.0),
            MockVariant("v2", MockVariantType.FP16, accuracy_drop=0.01),
            MockVariant("v3", MockVariantType.INT8, accuracy_drop=0.05),
        ]
        
        selection = MockSelection(
            variant=variants[0],
            decision_trace=MockDecisionTrace(),
        )
        
        report = create_explainability_report(
            job_id="test_job",
            variants=variants,
            selection=selection,
            accuracy_threshold=0.02,
        )
        
        assert report.total_variants == 3
        assert report.selection is not None
        assert report.selection.selected_variant_id == "v1"
    
    def test_int8_rejection_shows_reason(self):
        """INT8 rejection due to accuracy shows reason."""
        variants = [
            MockVariant("baseline_v1", MockVariantType.BASELINE, accuracy_drop=0.0),
            MockVariant("int8_v2", MockVariantType.INT8, accuracy_drop=0.05),  # Exceeds threshold
        ]
        
        selection = MockSelection(
            variant=variants[0],
            decision_trace=MockDecisionTrace(),
        )
        
        report = create_explainability_report(
            job_id="test_job",
            variants=variants,
            selection=selection,
            accuracy_threshold=0.02,
        )
        
        # Find INT8 variant
        int8_exp = next(v for v in report.variants if "int8" in v.variant_id)
        
        assert int8_exp.status == VariantStatus.REJECTED
        assert "Accuracy drop" in int8_exp.rejection_reason
        assert "exceeds threshold" in int8_exp.rejection_reason
        assert int8_exp.rejection_constraint == "accuracy_threshold"
    
    def test_accuracy_violation_explained(self):
        """Accuracy violation is clearly explained."""
        variants = [
            MockVariant("fp16_v1", MockVariantType.FP16, accuracy_drop=0.03),  # Exceeds 2%
        ]
        
        selection = MockSelection(
            variant=variants[0],
            decision_trace=MockDecisionTrace(selection_reason="Only viable option"),
        )
        
        report = create_explainability_report(
            job_id="test_job",
            variants=variants,
            selection=selection,
            accuracy_threshold=0.02,
        )
        
        # Even selected variant shows accuracy drop
        exp = report.variants[0]
        assert exp.accuracy_drop == 0.03
    
    def test_save_and_load(self, tmp_path):
        """Report can be saved as JSON and Markdown."""
        report = ExplainabilityReport(
            job_id="test",
            created_at="2024-01-01T00:00:00Z",
            total_variants=1,
        )
        report.variants.append(VariantExplanation(
            variant_id="v1",
            variant_type="baseline",
            status=VariantStatus.SELECTED,
        ))
        
        json_path, md_path = report.save(tmp_path)
        
        assert json_path.exists()
        assert md_path.exists()
        
        # Check JSON content
        import json
        with open(json_path) as f:
            data = json.load(f)
        assert data["job_id"] == "test"
        
        # Check markdown content
        with open(md_path) as f:
            md = f.read()
        assert "Optimization Report" in md
        assert "v1" in md


class TestMarkdownGeneration:
    """Tests for markdown generation."""
    
    def test_markdown_contains_status_emoji(self):
        """Markdown shows status with emoji."""
        report = ExplainabilityReport(
            job_id="test",
            created_at="2024-01-01T00:00:00Z",
        )
        report.variants.append(VariantExplanation(
            variant_id="v1",
            variant_type="baseline",
            status=VariantStatus.SELECTED,
        ))
        report.variants.append(VariantExplanation(
            variant_id="v2",
            variant_type="int8",
            status=VariantStatus.REJECTED,
            rejection_reason="Too slow",
            rejection_constraint="latency",
        ))
        
        md = generate_markdown(report)
        
        assert "✅" in md  # Selected
        assert "❌" in md  # Rejected
    
    def test_markdown_shows_rejection_reason(self):
        """Markdown clearly shows rejection reason."""
        report = ExplainabilityReport(
            job_id="test",
            created_at="2024-01-01T00:00:00Z",
        )
        report.variants.append(VariantExplanation(
            variant_id="int8_v1",
            variant_type="int8",
            status=VariantStatus.REJECTED,
            rejection_reason="Accuracy drop (5.00%) exceeds threshold (2.0%)",
            rejection_constraint="accuracy_threshold",
        ))
        
        md = generate_markdown(report)
        
        assert "Accuracy drop" in md
        assert "5.00%" in md
        assert "accuracy_threshold" in md
