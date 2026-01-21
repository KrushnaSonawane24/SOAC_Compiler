"""
SOAC Reporting Package
======================

Generate reports, exports, and audit artifacts.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from .models import (
    ReportData, ReportBundle, ReportVerdict,
    ModelInfo, VariantResult, AccuracyVerification, BenchmarkResult,
)
from .json_export import export_all_json
from .csv_export import export_all_csv
from .charts import generate_all_charts
from .pdf_report import generate_pdf_report
from .exceptions import ReportingError

logger = logging.getLogger(__name__)


def extract_report_data(job_result: Dict[str, Any]) -> ReportData:
    """Extract report data from job result."""
    metadata = job_result.get('metadata', {})
    config = job_result.get('config', {})
    
    # Extract model info
    model_info = ModelInfo(
        model_type=metadata.get('model_type', 'ONNX'),
        architecture=metadata.get('architecture', 'Unknown'),
        original_size_bytes=metadata.get('original_size', 0),
        task_type=metadata.get('task_type', 'classification'),
    )
    
    # Extract variants
    variants = []
    raw_variants = metadata.get('variants', [])
    for v in raw_variants:
        variants.append(VariantResult(
            variant_id=v.get('variant_id', 'unknown'),
            variant_type=v.get('variant_type', 'unknown'),
            accuracy=v.get('accuracy', 0.0),
            latency_ms=v.get('latency_ms', 0.0),
            memory_mb=v.get('memory_mb', 0.0),
            size_bytes=v.get('size_bytes', 0),
            status=v.get('status', 'rejected'),
            rejection_reason=v.get('rejection_reason'),
        ))
    
    # Extract accuracy verification
    baseline_acc = metadata.get('baseline_accuracy', 0.95)
    optimized_acc = metadata.get('optimized_accuracy', 0.95)
    threshold = config.get('accuracy_threshold', 0.02)
    acc_delta = abs(baseline_acc - optimized_acc)
    
    accuracy_verification = AccuracyVerification(
        baseline_accuracy=baseline_acc,
        optimized_accuracy=optimized_acc,
        accuracy_delta=acc_delta,
        threshold=threshold,
        passed=acc_delta <= threshold,
    )
    
    # Extract benchmarks
    benchmarks = []
    for stage in job_result.get('stage_results', []):
        benchmarks.append(BenchmarkResult(
            stage=stage.get('stage', 'unknown'),
            duration_ms=stage.get('duration_ms', 0.0),
            success=stage.get('success', True),
            message=stage.get('message', ''),
        ))
    
    # Determine verdict
    job_success = job_result.get('success', False)
    verdict = ReportVerdict.PASSED if job_success and accuracy_verification.passed else ReportVerdict.FAILED
    
    # Build mode and policy
    build_mode = config.get('build_mode', 'normal')
    policy = config.get('compilation_policy', 'balanced')
    
    # Deterministic guarantee
    if build_mode == 'reproducible':
        deterministic_guarantee = "This build is deterministic. Running with identical inputs and configuration will produce identical outputs and fingerprint."
    else:
        deterministic_guarantee = "Normal build mode. Results may vary between runs."
    
    # Deployment readiness
    if verdict == ReportVerdict.PASSED:
        deployment_readiness = "Model is optimized and ready for deployment. All accuracy and performance constraints have been met."
    else:
        deployment_readiness = "Model optimization failed. Review rejected variants and accuracy violations before deployment."
    
    return ReportData(
        job_id=job_result.get('job_id', 'unknown'),
        user_id=f"user_{hash(job_result.get('user_id', 'unknown')) % 10000:04d}",  # Anonymized
        timestamp=job_result.get('timestamp', datetime.now().isoformat()),
        build_mode=build_mode,
        compilation_policy=policy,
        model_info=model_info,
        variants=variants,
        selected_variant_id=metadata.get('selected_variant_id'),
        accuracy_verification=accuracy_verification,
        benchmarks=benchmarks,
        selection_reason=metadata.get('selection_reason', 'Best composite score within accuracy constraints'),
        policy_influence=f"Applied {policy.replace('_', ' ')} policy with weighted scoring",
        constraint_statement=f"Accuracy drop constrained to ≤{threshold*100:.1f}%",
        build_fingerprint=metadata.get('fingerprint'),
        deterministic_guarantee=deterministic_guarantee,
        verdict=verdict,
        deployment_readiness=deployment_readiness,
    )


def generate_job_reports(job_result: Dict[str, Any], output_dir: Path) -> ReportBundle:
    """
    Generate all reports for a job.
    
    Args:
        job_result: Job result dictionary.
        output_dir: Directory to save reports.
    
    Returns:
        ReportBundle with paths to all generated files.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    bundle = ReportBundle()
    
    try:
        # Extract data
        data = extract_report_data(job_result)
        
        # Generate JSON exports
        logger.info("Generating JSON exports...")
        json_paths = export_all_json(data, output_dir)
        bundle.json_paths = {k: str(v) for k, v in json_paths.items()}
        
        # Generate CSV exports
        logger.info("Generating CSV exports...")
        csv_paths = export_all_csv(data, output_dir)
        bundle.csv_paths = {k: str(v) for k, v in csv_paths.items()}
        
        # Generate charts
        logger.info("Generating charts...")
        chart_paths = generate_all_charts(data, output_dir)
        bundle.chart_paths = {k: str(v) for k, v in chart_paths.items()}
        
        # Generate PDF report
        logger.info("Generating PDF report...")
        pdf_path = generate_pdf_report(data, output_dir, chart_paths)
        if pdf_path:
            bundle.pdf_path = str(pdf_path)
        
        logger.info(f"Report generation complete: {len(bundle.json_paths)} JSON, {len(bundle.csv_paths)} CSV, {len(bundle.chart_paths)} charts, PDF={bundle.pdf_path is not None}")
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise ReportingError(f"Failed to generate reports: {e}")
    
    return bundle


__all__ = [
    "generate_job_reports",
    "extract_report_data",
    "ReportData",
    "ReportBundle",
    "ReportVerdict",
    "ModelInfo",
    "VariantResult",
    "AccuracyVerification",
    "BenchmarkResult",
    "ReportingError",
]
