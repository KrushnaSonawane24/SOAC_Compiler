"""
SOAC Reporting Data Models
==========================

Data models for report generation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ReportVerdict(str, Enum):
    """Report verdict."""
    PASSED = "PASSED"
    FAILED = "FAILED"


@dataclass
class ModelInfo:
    """Input model information."""
    model_type: str
    architecture: str
    original_size_bytes: int
    task_type: str  # classification, detection, audio
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_type": self.model_type,
            "architecture": self.architecture,
            "original_size_bytes": self.original_size_bytes,
            "original_size_mb": round(self.original_size_bytes / 1024 / 1024, 2),
            "task_type": self.task_type,
        }


@dataclass
class VariantResult:
    """Result for a single variant."""
    variant_id: str
    variant_type: str
    accuracy: float
    latency_ms: float
    memory_mb: float
    size_bytes: int
    status: str  # selected, rejected
    rejection_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "variant_type": self.variant_type,
            "accuracy": self.accuracy,
            "latency_ms": self.latency_ms,
            "memory_mb": self.memory_mb,
            "size_bytes": self.size_bytes,
            "size_mb": round(self.size_bytes / 1024 / 1024, 2),
            "status": self.status,
            "rejection_reason": self.rejection_reason,
        }


@dataclass
class AccuracyVerification:
    """Accuracy verification result."""
    baseline_accuracy: float
    optimized_accuracy: float
    accuracy_delta: float
    threshold: float
    passed: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_accuracy": self.baseline_accuracy,
            "optimized_accuracy": self.optimized_accuracy,
            "accuracy_delta": self.accuracy_delta,
            "accuracy_delta_percent": round(self.accuracy_delta * 100, 2),
            "threshold": self.threshold,
            "threshold_percent": round(self.threshold * 100, 2),
            "passed": self.passed,
        }


@dataclass
class BenchmarkResult:
    """Benchmark result."""
    stage: str
    duration_ms: float
    success: bool
    message: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "message": self.message,
        }


@dataclass
class ReportData:
    """Complete report data."""
    # Job info
    job_id: str
    user_id: str  # anonymized
    timestamp: str
    build_mode: str
    compilation_policy: str
    
    # Model info
    model_info: ModelInfo
    
    # Variants
    variants: List[VariantResult]
    selected_variant_id: Optional[str]
    
    # Accuracy
    accuracy_verification: AccuracyVerification
    
    # Benchmarks
    benchmarks: List[BenchmarkResult]
    
    # Explainability
    selection_reason: str
    policy_influence: str
    constraint_statement: str
    
    # Reproducibility
    build_fingerprint: Optional[str]
    deterministic_guarantee: str
    
    # Verdict
    verdict: ReportVerdict
    deployment_readiness: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "build_mode": self.build_mode,
            "compilation_policy": self.compilation_policy,
            "model_info": self.model_info.to_dict(),
            "variants": [v.to_dict() for v in self.variants],
            "selected_variant_id": self.selected_variant_id,
            "accuracy_verification": self.accuracy_verification.to_dict(),
            "benchmarks": [b.to_dict() for b in self.benchmarks],
            "selection_reason": self.selection_reason,
            "policy_influence": self.policy_influence,
            "constraint_statement": self.constraint_statement,
            "build_fingerprint": self.build_fingerprint,
            "deterministic_guarantee": self.deterministic_guarantee,
            "verdict": self.verdict.value,
            "deployment_readiness": self.deployment_readiness,
        }


@dataclass
class ReportBundle:
    """Generated report bundle."""
    pdf_path: Optional[str] = None
    json_paths: Dict[str, str] = field(default_factory=dict)
    csv_paths: Dict[str, str] = field(default_factory=dict)
    chart_paths: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pdf_path": self.pdf_path,
            "json_paths": self.json_paths,
            "csv_paths": self.csv_paths,
            "chart_paths": self.chart_paths,
        }
