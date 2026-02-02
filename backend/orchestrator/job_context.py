"""
SOAC Job Context
================

Job configuration and context management.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timezone
import tempfile
import shutil
import uuid
import logging
import json

from .exceptions import PipelineStage


logger = logging.getLogger(__name__)


@dataclass
class JobConfig:
    """
    Configuration for a SOAC job.
    
    Attributes:
        accuracy_threshold: Maximum allowed accuracy drop (default 2%).
        generate_all_targets: Generate all deployment targets.
        deployment_targets: Specific targets to generate.
        warmup_runs: Latency warmup runs.
        measured_runs: Latency measured runs.
        cleanup_on_complete: Remove temp files after completion.
        build_mode: "normal" or "reproducible".
        reproducible_seed: Seed for reproducible builds.
        simulate_accuracy_drop: Inject accuracy drop (0.0-1.0).
        simulate_latency_spike: Inject latency multiplier.
        simulate_memory_exceed: Inject memory usage (MB).
    """
    accuracy_threshold: float = 0.01
    max_model_size_mb: int = 200
    max_stage_attempts: int = 2
    retry_backoff_ms: int = 600
    generate_all_targets: bool = True
    deployment_targets: Optional[List[str]] = None
    warmup_runs: int = 5
    measured_runs: int = 20
    cleanup_on_complete: bool = True
    build_mode: str = "normal"  # "normal" or "reproducible"
    reproducible_seed: int = 42
    # Failure simulation flags
    simulate_accuracy_drop: Optional[float] = None  # e.g., 0.05 = 5% drop
    simulate_latency_spike: Optional[float] = None  # e.g., 2.0 = 2x latency
    simulate_memory_exceed: Optional[float] = None  # e.g., 10000 = 10GB
    # Compilation policy
    compilation_policy: str = "balanced"  # balanced, accuracy_first, latency_first, mobile_first
    
    @property
    def is_reproducible(self) -> bool:
        """Check if reproducible mode is enabled."""
        return self.build_mode == "reproducible"
    
    @property
    def has_simulated_failures(self) -> bool:
        """Check if failure simulation is enabled."""
        return any([
            self.simulate_accuracy_drop is not None,
            self.simulate_latency_spike is not None,
            self.simulate_memory_exceed is not None,
        ])
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "accuracy_threshold": self.accuracy_threshold,
            "max_model_size_mb": self.max_model_size_mb,
            "max_stage_attempts": self.max_stage_attempts,
            "retry_backoff_ms": self.retry_backoff_ms,
            "generate_all_targets": self.generate_all_targets,
            "deployment_targets": self.deployment_targets,
            "warmup_runs": self.warmup_runs,
            "measured_runs": self.measured_runs,
            "cleanup_on_complete": self.cleanup_on_complete,
            "build_mode": self.build_mode,
            "reproducible_seed": self.reproducible_seed,
            "simulate_accuracy_drop": self.simulate_accuracy_drop,
            "simulate_latency_spike": self.simulate_latency_spike,
            "simulate_memory_exceed": self.simulate_memory_exceed,
            "compilation_policy": self.compilation_policy,
        }


@dataclass
class JobContext:
    """
    Runtime context for a SOAC job.
    
    Manages temporary directories and tracks artifacts.
    """
    job_id: str
    input_path: Path
    config: JobConfig
    work_dir: Path
    created_at: str
    current_stage: PipelineStage = PipelineStage.PENDING
    artifacts: Dict[str, Path] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    log_callback: Optional[Any] = None
    audit_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.audit_path = self.work_dir / "audit.jsonl"
        self._audit(
            event="job_created",
            job_id=self.job_id,
            input_path=str(self.input_path),
            config=self.config.to_dict(),
        )

    def _audit(self, **payload: Any) -> None:
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        payload["stage"] = self.current_stage.value
        try:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass
    
    @property
    def canonical_dir(self) -> Path:
        """Directory for canonical ONNX."""
        d = self.work_dir / "canonical"
        d.mkdir(exist_ok=True)
        return d
    
    @property
    def variants_dir(self) -> Path:
        """Directory for optimized variants."""
        d = self.work_dir / "variants"
        d.mkdir(exist_ok=True)
        return d
    
    @property
    def deployment_dir(self) -> Path:
        """Directory for deployment artifacts."""
        d = self.work_dir / "deployment"
        d.mkdir(exist_ok=True)
        return d
    
    def log(self, message: str):
        """Add log entry."""
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = f"[{timestamp}] [{self.current_stage.value}] {message}"
        self.logs.append(entry)
        logger.info(f"[{self.job_id}] {message}")
        if self.log_callback:
            try:
                self.log_callback(self.job_id, self.current_stage.value, message)
            except Exception:
                pass  # Ignore callback errors to avoid crashing pipeline
    
    def set_stage(self, stage: PipelineStage):
        """Update current stage."""
        self.current_stage = stage
        self._audit(event="stage_transition", to_stage=stage.value)
        self.log(f"Stage: {stage.value}")
    
    def add_artifact(self, name: str, path: Path):
        """Register an artifact."""
        self.artifacts[name] = path
        self._audit(event="artifact_added", name=name, path=str(path))
        self.log(f"Artifact: {name} -> {path}")
    
    def cleanup(self):
        """Remove temporary work directory."""
        if self.config.cleanup_on_complete and self.work_dir.exists():
            try:
                shutil.rmtree(self.work_dir)
                logger.info(f"[{self.job_id}] Cleaned up work directory")
            except Exception as e:
                logger.warning(f"[{self.job_id}] Cleanup failed: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "input_path": str(self.input_path),
            "config": self.config.to_dict(),
            "work_dir": str(self.work_dir),
            "created_at": self.created_at,
            "current_stage": self.current_stage.value,
            "artifacts": {k: str(v) for k, v in self.artifacts.items()},
            "metadata": self.metadata,
        }


def create_job_context(
    input_path: Path,
    config: Optional[JobConfig] = None,
    job_id: Optional[str] = None,
    work_dir: Optional[Path] = None,
    log_callback: Optional[Any] = None,
) -> JobContext:
    """
    Create a new job context.
    
    Args:
        input_path: Path to uploaded model.
        config: Job configuration.
        job_id: Optional job ID (generated if not provided).
        work_dir: Optional work directory (temp if not provided).
        log_callback: Optional callback for real-time logging.
    
    Returns:
        Initialized JobContext.
    """
    if job_id is None:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
    
    if config is None:
        config = JobConfig()
    
    if work_dir is None:
        work_dir = Path(tempfile.mkdtemp(prefix=f"soac_{job_id}_"))
    else:
        work_dir = Path(work_dir) / job_id
        work_dir.mkdir(parents=True, exist_ok=True)
    
    return JobContext(
        job_id=job_id,
        input_path=Path(input_path),
        config=config,
        work_dir=work_dir,
        created_at=datetime.now(timezone.utc).isoformat(),
        log_callback=log_callback,
    )
