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
import shutil
from pathlib import Path
from typing import Optional, Any

from .exceptions import (
    PipelineStage,
    PipelineError,
    ValidationFailedError,
    NormalizationFailedError,
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
from backend.compiler.onnx_converter import detect_format, convert_to_onnx, InputFormat
from backend.compiler.exceptions import UnsupportedFormatError, ConversionError, UnsupportedOpError
from backend.compiler.hashing import compute_graph_hash
from backend.optimizer import (
    generate_variants,
    select_best_variant,
    add_benchmark_metrics,
    VariantType,
    NoValidVariantsError,
    filter_valid_variants,
    rank_variants,
    create_decision_trace,
    SelectedVariant,
)
from backend.benchmark import measure_latency, measure_memory, measure_size, create_sample_input, create_synthetic_dataset, evaluate_accuracy
from backend.benchmark.dataset import ReferenceDataset, DatasetSample
from backend.benchmark.accuracy import create_inference_session, run_inference, get_prediction
from backend.deployment import generate_deployment_artifacts, TargetPlatform


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

    def run_normalization(self) -> bool:
        """Stage 0: Normalize uploaded model into an ONNX baseline."""
        self._transition(PipelineStage.NORMALIZING)
        start = time.perf_counter()
        try:
            self._ensure_onnx_input()
            duration = (time.perf_counter() - start) * 1000
            self._record_stage(PipelineStage.NORMALIZING, True, duration, "ONNX baseline ready")
            self.ctx.metadata["normalization"] = {
                "success": True,
                "duration_ms": duration,
                "onnx_path": str(self.ctx.input_path),
            }
            return True
        except NormalizationFailedError:
            raise
        except Exception as e:
            raise NormalizationFailedError(self.ctx.job_id, str(e), e)

    def _ensure_onnx_input(self) -> None:
        """Normalize uploaded model into an ONNX file inside the job work directory."""
        input_path = Path(self.ctx.input_path)
        input_dir = self.ctx.work_dir / "input"
        input_dir.mkdir(exist_ok=True)

        ext = input_path.suffix.lower()
        detected_format = None
        try:
            detected_format = detect_format(input_path).value
        except Exception:
            detected_format = ext.lstrip(".") or "unknown"

        self.ctx.metadata.setdefault("pipeline_levels", [])
        if "level0_readiness_audit" not in self.ctx.metadata["pipeline_levels"]:
            self.ctx.metadata["pipeline_levels"].append("level0_readiness_audit")
            self.ctx.metadata["input_detected_format"] = detected_format
            self.ctx.log(f"[LEVEL 0] readiness audit: detected_format={detected_format}")

        if ext == ".onnx":
            normalized_path = input_dir / "input.onnx"
            if input_path.resolve() != normalized_path.resolve():
                shutil.copyfile(input_path, normalized_path)
            self.ctx.input_path = normalized_path
            self.ctx.add_artifact("input_onnx", normalized_path)
            self.ctx.metadata["normalization_estimate_seconds"] = 0
            return

        try:
            size_bytes = 0
            if input_path.is_file():
                size_bytes = input_path.stat().st_size
            elif input_path.is_dir():
                size_bytes = sum(p.stat().st_size for p in input_path.rglob("*") if p.is_file())
            size_mb = size_bytes / (1024 * 1024) if size_bytes else 0.0
            base = 4.0
            per_mb = 0.35
            if detected_format in ("savedmodel",):
                base, per_mb = 8.0, 0.45
            elif detected_format in ("tflite",):
                base, per_mb = 5.0, 0.25
            elif detected_format in ("keras", "keras_h5", "h5", "keras_native"):
                base, per_mb = 6.0, 0.40
            est = 0.0 if size_mb == 0.0 else base + (size_mb * per_mb)
            low = max(1.0, est * 0.7) if est else 0.0
            high = max(2.0, est * 1.6) if est else 0.0
            self.ctx.metadata["normalization_estimate_seconds"] = est
            self.ctx.log(f"[LEVEL 1] converting to ONNX baseline (estimated {low:.0f}-{high:.0f}s)")
        except Exception:
            self.ctx.log("[LEVEL 1] converting to ONNX baseline")

        try:
            model_format = detect_format(input_path)
        except Exception as e:
            raise NormalizationFailedError(
                self.ctx.job_id,
                f"Could not detect model format for {input_path.name}: {e}",
                e,
            )

        if model_format == InputFormat.PYTORCH:
            raise NormalizationFailedError(
                self.ctx.job_id,
                "PyTorch .pt/.pth export requires a model signature. Upload ONNX or Keras/SavedModel/TFLite instead.",
            )

        output_path = input_dir / "normalized.onnx"
        try:
            onnx_model, _fmt = convert_to_onnx(input_path)
            import onnx

            onnx.save(onnx_model, str(output_path))
        except (UnsupportedFormatError, ConversionError) as e:
            raise NormalizationFailedError(self.ctx.job_id, str(e), e)
        except Exception as e:
            raise NormalizationFailedError(self.ctx.job_id, f"ONNX export failed: {e}", e)

        self.ctx.input_path = output_path
        self.ctx.add_artifact("normalized_onnx", output_path)
        self.ctx.metadata["pipeline_levels"].append("level1_normalization")
    
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
        except UnsupportedOpError as e:
            unsupported = [op.lower() for op in e.unsupported_ops]
            control_flow = {"loop", "scan", "if"}
            if any(op.split(".")[-1].lower() in control_flow for op in unsupported):
                # Fallback: use normalized ONNX as canonical to continue pipeline
                import onnx
                canonical_path = self.ctx.input_path
                try:
                    model = onnx.load(str(canonical_path))
                    graph_hash = compute_graph_hash(model)
                except Exception:
                    graph_hash = "unknown"
                self.ctx.add_artifact("canonical_onnx", canonical_path)
                self.ctx.metadata["canonical_hash"] = graph_hash
                duration = (time.perf_counter() - start) * 1000
                self._record_stage(
                    PipelineStage.CANONICALIZING,
                    True,
                    duration,
                    "Control-flow ops detected (Loop/Scan/If); skipping canonicalization",
                    {"canonical": str(canonical_path), "unsupported_ops": e.unsupported_ops},
                )
                return canonical_path
            raise CanonicalizationFailedError(self.ctx.job_id, str(e), e)
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
        max_attempts = max(1, int(self.ctx.config.max_stage_attempts))

        for attempt in range(1, max_attempts + 1):
            start = time.perf_counter()
            self.ctx._audit(event="stage_attempt_start", stage=PipelineStage.BENCHMARKING.value, attempt=attempt)
            try:
                self.ctx.log(f"Benchmarking variants (attempt {attempt}/{max_attempts})")
                baseline_variant = next((v for v in variants if getattr(v, "variant_type", None) == VariantType.BASELINE and v.is_valid), None)
                dataset: ReferenceDataset
                if baseline_variant is not None:
                    sample_input = create_sample_input(baseline_variant.onnx_path)
                    session = create_inference_session(baseline_variant.onnx_path)
                    samples: list[DatasetSample] = []
                    import numpy as np
                    rng = np.random.RandomState(42)
                    shape = tuple(int(d) for d in sample_input.shape)
                    dtype = sample_input.dtype
                    for i in range(20):
                        if i == 0:
                            x = sample_input
                        else:
                            if dtype.kind in {"i", "u"}:
                                x = rng.randint(0, 10, size=shape, dtype=dtype)
                            else:
                                x = rng.randn(*shape).astype(dtype)
                        y = get_prediction(run_inference(session, x))
                        samples.append(DatasetSample(input_data=x, label=int(y), sample_id=f"baseline_pseudo_{i}"))
                    dataset = ReferenceDataset(samples=samples, name="baseline_pseudo_dataset", num_classes=1000)
                else:
                    dataset = create_synthetic_dataset(num_samples=20, seed=42)

                benchmarked = []
                baseline_accuracy = None

                ordered_variants = sorted(
                    variants,
                    key=lambda v: 0 if getattr(v, "variant_type", None) == VariantType.BASELINE else 1,
                )

                for variant in ordered_variants:
                    if not variant.is_valid:
                        benchmarked.append(variant)
                        continue

                    try:
                        sample_input = create_sample_input(variant.onnx_path)

                        latency = measure_latency(
                            variant.onnx_path,
                            sample_input,
                            warmup_runs=self.ctx.config.warmup_runs,
                            measured_runs=self.ctx.config.measured_runs,
                        )

                        memory = measure_memory(variant.onnx_path, sample_input)

                        acc_result = evaluate_accuracy(
                            variant.onnx_path,
                            dataset,
                            baseline_accuracy=baseline_accuracy,
                        )

                        if baseline_accuracy is None:
                            baseline_accuracy = acc_result.accuracy

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
                self.ctx._audit(event="stage_attempt_success", stage=PipelineStage.BENCHMARKING.value, attempt=attempt, duration_ms=duration)
                self._record_stage(
                    PipelineStage.BENCHMARKING,
                    True,
                    duration,
                    f"Benchmarked {len(benchmarked)} variants",
                )

                return benchmarked

            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                self.ctx._audit(event="stage_attempt_failed", stage=PipelineStage.BENCHMARKING.value, attempt=attempt, duration_ms=duration, error=str(e))
                if attempt < max_attempts:
                    backoff = (self.ctx.config.retry_backoff_ms / 1000.0) * attempt
                    self.ctx.log(f"Benchmarking failed (attempt {attempt}). Retrying in {backoff:.1f}s")
                    time.sleep(backoff)
                    continue
                raise BenchmarkingFailedError(self.ctx.job_id, str(e), e)
    
    def run_selection(self, variants: list):
        """Stage 5: Select best variant using ALO."""
        self._transition(PipelineStage.SELECTING)
        start = time.perf_counter()
        
        try:
            self.ctx.log("Running ALO selection")
            
            input_hash = self.ctx.metadata.get("canonical_hash", "unknown")

            max_size_bytes = int(self.ctx.config.max_model_size_mb) * 1024 * 1024
            effective_accuracy = self.ctx.config.accuracy_threshold
            if self.ctx.config.compilation_policy == "accuracy_first":
                effective_accuracy = min(effective_accuracy, 0.0)
            
            try:
                selection = select_best_variant(
                    variants,
                    input_hash,
                    accuracy_threshold=effective_accuracy,
                    max_size_bytes=max_size_bytes,
                    compilation_policy=self.ctx.config.compilation_policy,
                )
            except NoValidVariantsError as e:
                self.ctx.log("No optimized variants met constraints; attempting baseline rollback")

                baseline = next((v for v in variants if v.variant_type == VariantType.BASELINE and v.is_valid), None)
                if not baseline:
                    raise

                if baseline.size_bytes > max_size_bytes:
                    raise SelectionFailedError(
                        self.ctx.job_id,
                        f"Baseline model exceeds size limit ({baseline.size_bytes}B > {max_size_bytes}B).",
                        e,
                    )

                valid_variants, rejected = filter_valid_variants(
                    variants,
                    accuracy_threshold=effective_accuracy,
                    max_size_bytes=max_size_bytes,
                )
                ranking = rank_variants([baseline])
                trace = create_decision_trace(
                    input_hash=input_hash,
                    all_variants=variants,
                    valid_variants=[baseline],
                    rejected=rejected,
                    ranking=ranking,
                    selected_id=baseline.variant_id,
                    selection_reason="Rolled back to baseline for stability and constraints compliance",
                    accuracy_threshold=effective_accuracy,
                )
                selection = SelectedVariant(
                    variant=baseline,
                    decision_trace=trace,
                    all_variants=variants,
                    rejected_variants=rejected,
                )
            
            # Calculate summary metrics for frontend
            try:
                # Find baseline (Original or Canonical)
                baseline = next((v for v in variants if v.variant_type == VariantType.BASELINE and v.is_valid), None)
                if not baseline:
                     # Fallback to first one if no explicit baseline
                     baseline = variants[0] if variants else None
                
                selected = selection.variant
                
                summary = {
                    "baseline_latency": None,
                    "selected_latency": None,
                    "speedup": None,
                    "baseline_size": None,
                    "selected_size": None,
                    "size_reduction": None,
                    "baseline_accuracy": None,
                    "selected_accuracy": None,
                    "accuracy_drop": None
                }

                if baseline and baseline.metrics:
                    summary["baseline_latency"] = baseline.metrics.latency_ms
                    summary["baseline_size"] = baseline.size_bytes
                    summary["baseline_accuracy"] = baseline.metrics.accuracy
                
                if selected and selected.metrics:
                    summary["selected_latency"] = selected.metrics.latency_ms
                    summary["selected_size"] = selected.size_bytes
                    summary["selected_accuracy"] = selected.metrics.accuracy
                    summary["accuracy_drop"] = selected.metrics.accuracy_drop

                # Calculate improvements
                if summary["baseline_latency"] and summary["selected_latency"] and summary["selected_latency"] > 0:
                     summary["speedup"] = round(summary["baseline_latency"] / summary["selected_latency"], 2)
                
                if summary["baseline_size"] and summary["selected_size"] and summary["baseline_size"] > 0:
                     summary["size_reduction"] = round((summary["baseline_size"] - summary["selected_size"]) / summary["baseline_size"] * 100, 1)

                self.ctx.metadata["benchmark_summary"] = summary
                
            except Exception as e:
                logger.warning(f"Failed to calculate benchmark summary: {e}")

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
    
    def run_deployment(self, selection, canonical_path: Optional[Path] = None) -> Path:
        """Stage 6: Generate deployment artifacts."""
        self._transition(PipelineStage.DEPLOYING)
        max_attempts = max(1, int(self.ctx.config.max_stage_attempts))
        target_map = {
            "android": TargetPlatform.ANDROID,
            "ios": TargetPlatform.IOS,
            "cpu": TargetPlatform.CPU,
            "gpu": TargetPlatform.GPU,
            "onnx": TargetPlatform.ONNX,
        }
        requested_targets = None
        if self.ctx.config.deployment_targets:
            requested_targets = [target_map[t] for t in self.ctx.config.deployment_targets if t in target_map]

        for attempt in range(1, max_attempts + 1):
            start = time.perf_counter()
            self.ctx._audit(event="stage_attempt_start", stage=PipelineStage.DEPLOYING.value, attempt=attempt)
            try:
                self.ctx.log(f"Generating deployment artifacts (attempt {attempt}/{max_attempts})")

                bundle = generate_deployment_artifacts(
                    selection.variant.onnx_path,
                    variant_id=selection.variant.variant_id,
                    source_hash=selection.variant.graph_hash,
                    output_dir=self.ctx.deployment_dir,
                    targets=requested_targets,
                    canonical_path=canonical_path,
                    policy=self.ctx.config.compilation_policy,
                    original_input_path=Path(self.ctx.metadata.get("original_input_path", self.ctx.input_path)),
                )

                self.ctx.add_artifact("deployment", bundle.output_dir)
                self.ctx.metadata["deployment_summary"] = {
                    "successful": bundle.successful_count,
                    "skipped": bundle.skipped_count,
                    "failed": bundle.failed_count,
                }

                duration = (time.perf_counter() - start) * 1000
                self.ctx._audit(event="stage_attempt_success", stage=PipelineStage.DEPLOYING.value, attempt=attempt, duration_ms=duration)
                self._record_stage(
                    PipelineStage.DEPLOYING,
                    True,
                    duration,
                    f"Deployment: {bundle.successful_count} success, {bundle.skipped_count} skipped",
                    {"bundle": str(bundle.output_dir)},
                )

                return bundle.output_dir

            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                self.ctx._audit(event="stage_attempt_failed", stage=PipelineStage.DEPLOYING.value, attempt=attempt, duration_ms=duration, error=str(e))
                if attempt < max_attempts:
                    backoff = (self.ctx.config.retry_backoff_ms / 1000.0) * attempt
                    self.ctx.log(f"Deployment failed (attempt {attempt}). Retrying in {backoff:.1f}s")
                    time.sleep(backoff)
                    continue
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

                self.ctx.add_artifact("audit_log", self.ctx.audit_path)
                
                # Hash input file
                input_hash = hash_file(self.ctx.input_path)
                self.ctx.metadata["input_hash"] = input_hash
                if self.ctx.config.deployment_targets:
                    self.ctx.metadata["targets"] = list(self.ctx.config.deployment_targets)
                self.ctx.metadata["policy"] = self.ctx.config.compilation_policy
                
                # Stage 1: Validation
                self.run_normalization()
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
                deployment_path = self.run_deployment(selection, canonical_path=canonical_path)
                
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

                try:
                    import json as _json
                    from backend.benchmark.size import count_parameters
                    from backend.compiler.hashing import compute_weights_hash
                    import onnx

                    baseline_variant = next((v for v in benchmarked if v.variant_type == VariantType.BASELINE and v.is_valid), None)
                    selected_variant = next((v for v in benchmarked if v.variant_id == selected_id and v.is_valid), None)

                    baseline_params = count_parameters(baseline_variant.onnx_path) if baseline_variant else 0
                    selected_params = count_parameters(selected_variant.onnx_path) if selected_variant else 0

                    baseline_weights_hash = None
                    selected_weights_hash = None
                    try:
                        if baseline_variant:
                            baseline_weights_hash = compute_weights_hash(onnx.load(str(baseline_variant.onnx_path)))
                        if selected_variant:
                            selected_weights_hash = compute_weights_hash(onnx.load(str(selected_variant.onnx_path)))
                    except Exception:
                        baseline_weights_hash = baseline_weights_hash

                    report = {
                        "job_id": self.ctx.job_id,
                        "original_input": {
                            "path": self.ctx.metadata.get("original_input_path"),
                            "name": self.ctx.metadata.get("original_input_name"),
                            "ext": self.ctx.metadata.get("original_input_ext"),
                            "detected_format": self.ctx.metadata.get("input_detected_format"),
                        },
                        "normalization": self.ctx.metadata.get("normalization"),
                        "validation": self.ctx.metadata.get("validation"),
                        "canonicalization": {
                            "canonical_hash": canonical_hash,
                            "canonical_path": str(canonical_path),
                        },
                        "selection": {
                            "selected_variant_id": selected_id,
                            "selection_reason": self.ctx.metadata.get("selection_reason"),
                            "policy": self.ctx.config.compilation_policy,
                        },
                        "benchmark_summary": self.ctx.metadata.get("benchmark_summary"),
                        "deployment": {
                            "bundle_dir": str(deployment_path),
                            "manifest_path": str(Path(deployment_path) / "manifest.json"),
                            "targets": list(self.ctx.config.deployment_targets or []),
                            "summary": self.ctx.metadata.get("deployment_summary"),
                        },
                        "variants": [
                            {
                                "variant_id": v.variant_id,
                                "variant_type": v.variant_type.value,
                                "status": v.status.value,
                                "size_bytes": v.size_bytes,
                                "graph_hash": v.graph_hash,
                                "metrics": v.metrics.to_dict() if v.metrics else None,
                                "error_message": v.error_message,
                            }
                            for v in benchmarked
                        ],
                        "weights": {
                            "baseline_parameters": baseline_params,
                            "selected_parameters": selected_params,
                            "baseline_weights_hash": baseline_weights_hash,
                            "selected_weights_hash": selected_weights_hash,
                        },
                        "fingerprint": self.ctx.metadata.get("fingerprint"),
                    }

                    report_json_path = self.ctx.work_dir / "conversion_report.json"
                    report_json_path.write_text(_json.dumps(report, indent=2), encoding="utf-8")
                    self.ctx.add_artifact("conversion_report_json", report_json_path)

                    def _pct(value: float | None) -> str:
                        if value is None:
                            return "-"
                        return f"{value * 100:.2f}%"

                    summary = self.ctx.metadata.get("benchmark_summary") or {}
                    acc_drop = summary.get("accuracy_drop") if isinstance(summary, dict) else None
                    loss_text = _pct(acc_drop) if isinstance(acc_drop, (int, float)) else "-"

                    report_md = "\n".join([
                        "# SOAC Conversion Report",
                        "",
                        f"Job: {self.ctx.job_id}",
                        "",
                        "## Input",
                        f"- Name: {self.ctx.metadata.get('original_input_name')}",
                        f"- Format: {self.ctx.metadata.get('input_detected_format')}",
                        "",
                        "## Output",
                        f"- Selected Variant: {selected_id}",
                        f"- Policy: {self.ctx.config.compilation_policy}",
                        "",
                        "## Lossless Check",
                        f"- Loss (prediction mismatch): {loss_text}",
                        "",
                        "## Weights",
                        f"- Baseline params: {baseline_params}",
                        f"- Selected params: {selected_params}",
                        f"- Baseline weights hash: {baseline_weights_hash or '-'}",
                        f"- Selected weights hash: {selected_weights_hash or '-'}",
                        "",
                        "## Deployment",
                        f"- Targets: {', '.join(self.ctx.config.deployment_targets or []) or '-'}",
                        f"- Bundle: {deployment_path}",
                    ])
                    report_md_path = self.ctx.work_dir / "conversion_report.md"
                    report_md_path.write_text(report_md, encoding="utf-8")
                    self.ctx.add_artifact("conversion_report_md", report_md_path)
                except Exception:
                    pass
                
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
                    artifacts={k: str(v) for k, v in self.ctx.artifacts.items()},
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
    log_callback: Optional[Any] = None,
) -> JobResult:
    """
    Run a SOAC optimization job.
    
    THE SINGLE PUBLIC API for SOAC.
    
    Args:
        uploaded_model_path: Path to uploaded model.
        config: Job configuration.
        job_id: Optional job ID.
        work_dir: Optional work directory.
        log_callback: Optional callback for real-time logging.
    
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
        log_callback=log_callback,
    )
    
    pipeline = SOACPipeline(ctx)
    return pipeline.run()
