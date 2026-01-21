"""
SOAC Pipeline Orchestrator
==========================

Main orchestration engine that wires all SOAC units together.

PIPELINE ORDER (NON-NEGOTIABLE):
    1. Validation
    2. Canonicalization  
    3. Optimization (variant generation)
    4. Benchmarking
    5. ALO Selection
    6. Deployment

RULES:
    - Strict ordering - no skipping
    - Failure aborts entire pipeline
    - Cleanup guaranteed
"""

import logging
import time
from pathlib import Path
from typing import Optional

from .exceptions import (
    PipelineStage,
    PipelineError,
    ValidationFailedError,
    CanonicalizationFailedError,
    OptimizationFailedError,
    BenchmarkingFailedError,
    SelectionFailedError,
    DeploymentFailedError,
)
from .job_context import JobContext, JobConfig, create_job_context
from .state_machine import validate_transition, is_terminal_stage
from .results import JobResult, StageResult, create_success_result, create_failure_result

# Import SOAC units
from backend.validator import validate_model
from backend.compiler import canonicalize_model
from backend.optimizer import generate_variants, select_best_variant, add_benchmark_metrics, VariantType
from backend.benchmark import measure_latency, measure_memory, measure_size, create_sample_input, create_synthetic_dataset, evaluate_accuracy
from backend.deployment import generate_deployment_artifacts


logger = logging.getLogger(__name__)


class SOACPipeline:
    """
    Main SOAC pipeline orchestrator.
    
    Runs models through the complete optimization pipeline.
    """
    
    def __init__(self, ctx: JobContext):
        self.ctx = ctx
        self.stage_results: list[StageResult] = []
        self.start_time: float = 0.0
    
    def _record_stage(
        self,
        stage: PipelineStage,
        success: bool,
        duration_ms: float,
        message: str,
        artifacts: Optional[dict] = None,
    ):
        """Record stage result."""
        self.stage_results.append(StageResult(
            stage=stage,
            success=success,
            duration_ms=duration_ms,
            message=message,
            artifacts=artifacts or {},
        ))
    
    def _transition(self, to_stage: PipelineStage):
        """Transition to next stage."""
        validate_transition(self.ctx.current_stage, to_stage, self.ctx.job_id)
        self.ctx.set_stage(to_stage)
    
    def run_validation(self) -> bool:
        """Stage 1: Validate model."""
        self._transition(PipelineStage.VALIDATING)
        start = time.perf_counter()
        
        try:
            self.ctx.log(f"Validating: {self.ctx.input_path}")
            
            # Use validator module
            result = validate_model(self.ctx.input_path)
            
            if not result.is_valid:
                raise ValidationFailedError(
                    self.ctx.job_id,
                    f"Validation failed: {result.rejection_reason}"
                )
            
            duration = (time.perf_counter() - start) * 1000
            self._record_stage(PipelineStage.VALIDATING, True, duration, "Validation passed")
            self.ctx.metadata["validation"] = result.to_dict()
            
            return True
            
        except ValidationFailedError:
            raise
        except Exception as e:
            raise ValidationFailedError(self.ctx.job_id, str(e), e)
    
    def run_canonicalization(self) -> Path:
        """Stage 2: Canonicalize model."""
        self._transition(PipelineStage.CANONICALIZING)
        start = time.perf_counter()
        
        try:
            self.ctx.log("Canonicalizing model")
            
            result = canonicalize_model(
                self.ctx.input_path,
                output_dir=self.ctx.canonical_dir,
            )
            
            canonical_path = result.onnx_path  # Fixed: was canonical_path
            self.ctx.add_artifact("canonical_onnx", canonical_path)
            self.ctx.metadata["canonical_hash"] = result.graph_hash
            
            duration = (time.perf_counter() - start) * 1000
            self._record_stage(
                PipelineStage.CANONICALIZING,
                True,
                duration,
                f"Canonical hash: {result.graph_hash[:16]}",
                {"canonical": str(canonical_path)},
            )
            
            return canonical_path
            
        except Exception as e:
            raise CanonicalizationFailedError(self.ctx.job_id, str(e), e)
    
    def run_optimization(self, canonical_path: Path) -> list:
        """Stage 3: Generate optimized variants."""
        self._transition(PipelineStage.OPTIMIZING)
        start = time.perf_counter()
        
        try:
            self.ctx.log("Generating optimized variants")
            
            input_hash = self.ctx.metadata.get("canonical_hash", "unknown")
            
            variants = generate_variants(
                canonical_path,
                input_hash,
                output_dir=self.ctx.variants_dir,
            )
            
            valid_count = sum(1 for v in variants if v.is_valid)
            
            duration = (time.perf_counter() - start) * 1000
            self._record_stage(
                PipelineStage.OPTIMIZING,
                True,
                duration,
                f"Generated {len(variants)} variants ({valid_count} valid)",
            )
            
            return variants
            
        except Exception as e:
            raise OptimizationFailedError(self.ctx.job_id, str(e), e)
    
    def run_benchmarking(self, variants: list) -> list:
        """Stage 4: Benchmark all variants."""
        self._transition(PipelineStage.BENCHMARKING)
        start = time.perf_counter()
        
        try:
            self.ctx.log("Benchmarking variants")
            
            # Create synthetic dataset for accuracy (minimal for speed)
            dataset = create_synthetic_dataset(num_samples=20, seed=42)
            
            # Benchmark each variant
            benchmarked = []
            baseline_accuracy = None
            
            for variant in variants:
                if not variant.is_valid:
                    benchmarked.append(variant)
                    continue
                
                try:
                    # Create sample input
                    sample_input = create_sample_input(variant.onnx_path)
                    
                    # Measure latency
                    latency = measure_latency(
                        variant.onnx_path,
                        sample_input,
                        warmup_runs=self.ctx.config.warmup_runs,
                        measured_runs=self.ctx.config.measured_runs,
                    )
                    
                    # Measure memory
                    memory = measure_memory(variant.onnx_path, sample_input)
                    
                    # Get accuracy
                    acc_result = evaluate_accuracy(
                        variant.onnx_path,
                        dataset,
                        baseline_accuracy=baseline_accuracy,
                    )
                    
                    if baseline_accuracy is None:
                        baseline_accuracy = acc_result.accuracy
                    
                    # Add metrics to variant
                    variant = add_benchmark_metrics(
                        variant,
                        latency_ms=latency.median_ms,
                        throughput=1000 / latency.median_ms,
                        memory_mb=memory.peak_mb,
                        accuracy=acc_result.accuracy,
                        baseline_accuracy=baseline_accuracy,
                    )
                    
                    self.ctx.log(f"  {variant.variant_type.value}: {latency.median_ms:.2f}ms")
                    
                except Exception as e:
                    self.ctx.log(f"  {variant.variant_type.value}: benchmark failed - {e}")
                
                benchmarked.append(variant)
            
            duration = (time.perf_counter() - start) * 1000
            self._record_stage(
                PipelineStage.BENCHMARKING,
                True,
                duration,
                f"Benchmarked {len(benchmarked)} variants",
            )
            
            return benchmarked
            
        except Exception as e:
            raise BenchmarkingFailedError(self.ctx.job_id, str(e), e)
    
    def run_selection(self, variants: list):
        """Stage 5: Select best variant using ALO."""
        self._transition(PipelineStage.SELECTING)
        start = time.perf_counter()
        
        try:
            self.ctx.log("Running ALO selection")
            
            input_hash = self.ctx.metadata.get("canonical_hash", "unknown")
            
            selection = select_best_variant(
                variants,
                input_hash,
                accuracy_threshold=self.ctx.config.accuracy_threshold,
            )
            
            selected = selection.variant
            self.ctx.add_artifact("selected_variant", selected.onnx_path)
            self.ctx.metadata["selected_variant_id"] = selected.variant_id
            self.ctx.metadata["selection_reason"] = selection.decision_trace.selection_reason
            
            duration = (time.perf_counter() - start) * 1000
            self._record_stage(
                PipelineStage.SELECTING,
                True,
                duration,
                f"Selected: {selected.variant_id}",
                {"selected": str(selected.onnx_path)},
            )
            
            return selection
            
        except Exception as e:
            raise SelectionFailedError(self.ctx.job_id, str(e), e)
    
    def run_deployment(self, selection) -> Path:
        """Stage 6: Generate deployment artifacts."""
        self._transition(PipelineStage.DEPLOYING)
        start = time.perf_counter()
        
        try:
            self.ctx.log("Generating deployment artifacts")
            
            bundle = generate_deployment_artifacts(
                selection.variant.onnx_path,
                variant_id=selection.variant.variant_id,
                source_hash=selection.variant.graph_hash,
                output_dir=self.ctx.deployment_dir,
            )
            
            self.ctx.add_artifact("deployment", bundle.output_dir)
            self.ctx.metadata["deployment_summary"] = {
                "successful": bundle.successful_count,
                "skipped": bundle.skipped_count,
                "failed": bundle.failed_count,
            }
            
            duration = (time.perf_counter() - start) * 1000
            self._record_stage(
                PipelineStage.DEPLOYING,
                True,
                duration,
                f"Deployment: {bundle.successful_count} success, {bundle.skipped_count} skipped",
                {"bundle": str(bundle.output_dir)},
            )
            
            return bundle.output_dir
            
        except Exception as e:
            raise DeploymentFailedError(self.ctx.job_id, str(e), e)
    
    def run(self) -> JobResult:
        """
        Run the complete SOAC pipeline.
        
        Returns:
            JobResult with all artifacts and status.
        """
        self.start_time = time.perf_counter()
        
        # Import fingerprint module
        from backend.reproducible import (
            BuildMode, hash_file, hash_config, create_build_fingerprint,
            reproducible_context
        )
        
        # Determine build mode
        build_mode = BuildMode.REPRODUCIBLE if self.ctx.config.is_reproducible else BuildMode.NORMAL
        seed = self.ctx.config.reproducible_seed
        
        try:
            with reproducible_context(enabled=build_mode == BuildMode.REPRODUCIBLE, seed=seed):
                self.ctx.log(f"Starting SOAC job: {self.ctx.job_id} (mode: {build_mode.value})")
                
                # Hash input file
                input_hash = hash_file(self.ctx.input_path)
                self.ctx.metadata["input_hash"] = input_hash
                
                # Stage 1: Validation
                self.run_validation()
                
                # Stage 2: Canonicalization
                canonical_path = self.run_canonicalization()
                canonical_hash = self.ctx.metadata.get("canonical_hash", "")
                
                # Stage 3: Optimization
                variants = self.run_optimization(canonical_path)
                
                # Collect variant hashes
                variant_hashes = {}
                for v in variants:
                    if v.is_valid:
                        variant_hashes[v.variant_id] = v.graph_hash
                
                # Stage 4: Benchmarking
                benchmarked = self.run_benchmarking(variants)
                
                # Stage 5: ALO Selection
                selection = self.run_selection(benchmarked)
                selected_hash = selection.variant.graph_hash
                selected_id = selection.variant.variant_id
                
                # Stage 6: Deployment
                deployment_path = self.run_deployment(selection)
                
                # Generate build fingerprint
                config_hash = hash_config(self.ctx.config)
                fingerprint = create_build_fingerprint(
                    job_id=self.ctx.job_id,
                    build_mode=build_mode,
                    input_file_hash=input_hash,
                    canonical_hash=canonical_hash,
                    variant_hashes=variant_hashes,
                    selected_variant_id=selected_id,
                    selected_variant_hash=selected_hash,
                    config_hash=config_hash,
                )
                
                # Save fingerprint
                fingerprint_path = fingerprint.save(self.ctx.work_dir)
                self.ctx.add_artifact("build_fingerprint", fingerprint_path)
                self.ctx.metadata["fingerprint"] = fingerprint.fingerprint
                
                # Generate explainability report
                from backend.explainability import create_explainability_report
                
                explain_report = create_explainability_report(
                    job_id=self.ctx.job_id,
                    variants=benchmarked,
                    selection=selection,
                    accuracy_threshold=self.ctx.config.accuracy_threshold,
                )
                json_path, md_path = explain_report.save(self.ctx.work_dir)
                self.ctx.add_artifact("explainability_json", json_path)
                self.ctx.add_artifact("explainability_md", md_path)
                
                # Success!
                self._transition(PipelineStage.COMPLETED)
                
                total_duration = (time.perf_counter() - self.start_time) * 1000
                
                self.ctx.log(f"Job completed successfully in {total_duration:.2f}ms")
                self.ctx.log(f"Fingerprint: {fingerprint.fingerprint[:16]}...")
                
                return create_success_result(
                    job_id=self.ctx.job_id,
                    input_path=str(self.ctx.input_path),
                    selected_variant=self.ctx.metadata.get("selected_variant_id"),
                    deployment_bundle=str(deployment_path),
                    stage_results=self.stage_results,
                    total_duration_ms=total_duration,
                    logs=self.ctx.logs,
                    metadata=self.ctx.metadata,
                )
            
        except PipelineError as e:
            self.ctx.set_stage(PipelineStage.FAILED)
            total_duration = (time.perf_counter() - self.start_time) * 1000
            
            self.ctx.log(f"Job failed: {e}")
            
            return create_failure_result(
                job_id=self.ctx.job_id,
                input_path=str(self.ctx.input_path),
                error=e,
                stage_results=self.stage_results,
                total_duration_ms=total_duration,
                logs=self.ctx.logs,
            )
        
        finally:
            if self.ctx.config.cleanup_on_complete:
                self.ctx.cleanup()


def run_soac_job(
    uploaded_model_path: Path,
    config: Optional[JobConfig] = None,
    job_id: Optional[str] = None,
    work_dir: Optional[Path] = None,
) -> JobResult:
    """
    Run a SOAC optimization job.
    
    THE SINGLE PUBLIC API for SOAC.
    
    Args:
        uploaded_model_path: Path to uploaded model.
        config: Job configuration.
        job_id: Optional job ID.
        work_dir: Optional work directory.
    
    Returns:
        JobResult with all artifacts and status.
    
    Example:
        >>> result = run_soac_job(Path("model.onnx"))
        >>> print(result.success)
        True
        >>> print(result.selected_variant)
        "int8_abc123"
    """
    ctx = create_job_context(
        input_path=uploaded_model_path,
        config=config,
        job_id=job_id,
        work_dir=work_dir,
    )
    
    pipeline = SOACPipeline(ctx)
    return pipeline.run()
