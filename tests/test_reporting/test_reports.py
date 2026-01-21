"""
Tests for Reporting Module
==========================

Tests for report generation.
"""

import pytest
import json
import csv
from pathlib import Path
from datetime import datetime

from backend.reporting import (
    generate_job_reports,
    extract_report_data,
    ReportData,
    ReportBundle,
    ReportVerdict,
)


@pytest.fixture
def sample_job_result():
    """Sample job result for testing."""
    return {
        "job_id": "test_job_123",
        "user_id": "user_abc",
        "success": True,
        "timestamp": "2024-01-20T12:00:00Z",
        "config": {
            "accuracy_threshold": 0.02,
            "build_mode": "reproducible",
            "compilation_policy": "accuracy_first",
        },
        "metadata": {
            "model_type": "ONNX",
            "architecture": "ResNet50",
            "original_size": 100 * 1024 * 1024,  # 100MB
            "task_type": "classification",
            "baseline_accuracy": 0.95,
            "optimized_accuracy": 0.94,
            "selected_variant_id": "fp16_v1",
            "fingerprint": "abc123def456",
            "selection_reason": "Best accuracy within latency constraints",
            "variants": [
                {
                    "variant_id": "baseline_v1",
                    "variant_type": "baseline",
                    "accuracy": 0.95,
                    "latency_ms": 50.0,
                    "memory_mb": 200.0,
                    "size_bytes": 100 * 1024 * 1024,
                    "status": "rejected",
                    "rejection_reason": "Not optimal for accuracy_first policy",
                },
                {
                    "variant_id": "fp16_v1",
                    "variant_type": "fp16",
                    "accuracy": 0.94,
                    "latency_ms": 30.0,
                    "memory_mb": 150.0,
                    "size_bytes": 50 * 1024 * 1024,
                    "status": "selected",
                },
                {
                    "variant_id": "int8_v1",
                    "variant_type": "int8",
                    "accuracy": 0.90,
                    "latency_ms": 20.0,
                    "memory_mb": 100.0,
                    "size_bytes": 25 * 1024 * 1024,
                    "status": "rejected",
                    "rejection_reason": "Accuracy drop (5.26%) exceeds threshold (2%)",
                },
            ],
        },
        "stage_results": [
            {"stage": "validation", "duration_ms": 100, "success": True, "message": "Valid"},
            {"stage": "canonicalization", "duration_ms": 500, "success": True, "message": "OK"},
            {"stage": "optimization", "duration_ms": 2000, "success": True, "message": "Generated 3 variants"},
            {"stage": "benchmarking", "duration_ms": 5000, "success": True, "message": "Benchmarked all"},
            {"stage": "selection", "duration_ms": 50, "success": True, "message": "Selected fp16_v1"},
        ],
    }


@pytest.fixture
def failed_job_result():
    """Failed job result for testing."""
    return {
        "job_id": "failed_job_456",
        "user_id": "user_xyz",
        "success": False,
        "timestamp": "2024-01-20T13:00:00Z",
        "config": {
            "accuracy_threshold": 0.02,
            "build_mode": "normal",
            "compilation_policy": "balanced",
        },
        "metadata": {
            "model_type": "ONNX",
            "architecture": "Unknown",
            "original_size": 50 * 1024 * 1024,
            "task_type": "detection",
            "baseline_accuracy": 0.90,
            "optimized_accuracy": 0.80,  # Big drop
            "error": "All variants failed accuracy constraints",
            "variants": [],
        },
        "stage_results": [
            {"stage": "validation", "duration_ms": 100, "success": True, "message": "Valid"},
            {"stage": "optimization", "duration_ms": 1000, "success": False, "message": "Failed"},
        ],
    }


class TestExtractReportData:
    """Tests for data extraction."""
    
    def test_extract_basic_info(self, sample_job_result):
        """Extracts basic job info."""
        data = extract_report_data(sample_job_result)
        
        assert data.job_id == "test_job_123"
        assert "user_" in data.user_id  # Anonymized
        assert data.build_mode == "reproducible"
        assert data.compilation_policy == "accuracy_first"
    
    def test_extract_model_info(self, sample_job_result):
        """Extracts model info."""
        data = extract_report_data(sample_job_result)
        
        assert data.model_info.model_type == "ONNX"
        assert data.model_info.architecture == "ResNet50"
        assert data.model_info.task_type == "classification"
    
    def test_extract_variants(self, sample_job_result):
        """Extracts variants."""
        data = extract_report_data(sample_job_result)
        
        assert len(data.variants) == 3
        assert data.selected_variant_id == "fp16_v1"
    
    def test_verdict_passed(self, sample_job_result):
        """Passing job gets PASSED verdict."""
        data = extract_report_data(sample_job_result)
        assert data.verdict == ReportVerdict.PASSED
    
    def test_verdict_failed(self, failed_job_result):
        """Failed job gets FAILED verdict."""
        data = extract_report_data(failed_job_result)
        assert data.verdict == ReportVerdict.FAILED


class TestJSONExport:
    """Tests for JSON export."""
    
    def test_json_files_created(self, sample_job_result, tmp_path):
        """JSON files are created."""
        bundle = generate_job_reports(sample_job_result, tmp_path)
        
        assert "job_summary" in bundle.json_paths
        assert "benchmark_results" in bundle.json_paths
        assert "optimization_trace" in bundle.json_paths
        assert "build_fingerprint" in bundle.json_paths
        assert "explainability" in bundle.json_paths
    
    def test_json_valid(self, sample_job_result, tmp_path):
        """JSON files are valid."""
        bundle = generate_job_reports(sample_job_result, tmp_path)
        
        for name, path in bundle.json_paths.items():
            with open(path) as f:
                data = json.load(f)
            assert isinstance(data, dict)


class TestCSVExport:
    """Tests for CSV export."""
    
    def test_csv_files_created(self, sample_job_result, tmp_path):
        """CSV files are created."""
        bundle = generate_job_reports(sample_job_result, tmp_path)
        
        assert "benchmark_metrics" in bundle.csv_paths
        assert "variant_comparison" in bundle.csv_paths
    
    def test_csv_headers(self, sample_job_result, tmp_path):
        """CSV files have correct headers."""
        bundle = generate_job_reports(sample_job_result, tmp_path)
        
        with open(bundle.csv_paths["variant_comparison"]) as f:
            reader = csv.reader(f)
            headers = next(reader)
        
        assert "Variant ID" in headers
        assert "Accuracy" in headers
        assert "Latency (ms)" in headers
        assert "Status" in headers


class TestReportDeterminism:
    """Tests for report determinism."""
    
    def test_same_input_same_output(self, sample_job_result, tmp_path):
        """Same input produces same JSON output."""
        dir1 = tmp_path / "run1"
        dir2 = tmp_path / "run2"
        
        bundle1 = generate_job_reports(sample_job_result, dir1)
        bundle2 = generate_job_reports(sample_job_result, dir2)
        
        # Compare JSON files
        for name in bundle1.json_paths:
            with open(bundle1.json_paths[name]) as f1, open(bundle2.json_paths[name]) as f2:
                assert f1.read() == f2.read()


class TestFailedJobReports:
    """Tests for failed job reports."""
    
    def test_failed_job_produces_report(self, failed_job_result, tmp_path):
        """Failed job still produces reports."""
        bundle = generate_job_reports(failed_job_result, tmp_path)
        
        assert len(bundle.json_paths) > 0
        assert len(bundle.csv_paths) > 0
    
    def test_failed_verdict_in_summary(self, failed_job_result, tmp_path):
        """Failed verdict appears in summary."""
        bundle = generate_job_reports(failed_job_result, tmp_path)
        
        with open(bundle.json_paths["job_summary"]) as f:
            summary = json.load(f)
        
        assert summary["verdict"] == "FAILED"
