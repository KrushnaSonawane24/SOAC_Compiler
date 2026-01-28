"""
SOAC Job Models
===============

Data models for job management.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum
import uuid


class JobState(str, Enum):
    """Job lifecycle states."""
    CREATED = "created"
    VALIDATING = "validating"
    CANONICALIZING = "canonicalizing"
    OPTIMIZING = "optimizing"
    BENCHMARKING = "benchmarking"
    SELECTING = "selecting"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"


# Progress percentages for each state
STATE_PROGRESS: Dict[JobState, int] = {
    JobState.CREATED: 0,
    JobState.VALIDATING: 10,
    JobState.CANONICALIZING: 20,
    JobState.OPTIMIZING: 40,
    JobState.BENCHMARKING: 60,
    JobState.SELECTING: 80,
    JobState.DEPLOYING: 90,
    JobState.COMPLETED: 100,
    JobState.FAILED: -1,
}


@dataclass
class LogEntry:
    """Single log entry."""
    timestamp: str
    stage: str
    message: str
    level: str = "info"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "stage": self.stage,
            "message": self.message,
            "level": self.level,
        }


@dataclass
class StageInfo:
    """Information about a pipeline stage."""
    name: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None
    success: bool = False
    message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "message": self.message,
        }


@dataclass
class ArtifactInfo:
    """Artifact metadata (no paths exposed)."""
    artifact_id: str
    name: str
    platform: str
    format: str
    size_bytes: int
    status: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "name": self.name,
            "platform": self.platform,
            "format": self.format,
            "size_bytes": self.size_bytes,
            "status": self.status,
        }


@dataclass
class Job:
    """
    Complete job record.
    
    NOTE: Internal paths are stored but never exposed to API.
    """
    job_id: str
    user_id: str
    state: JobState
    created_at: str
    updated_at: str
    
    # Input info
    original_filename: str
    file_size_bytes: int
    
    # Internal paths (never exposed)
    input_path: Optional[Path] = None
    work_dir: Optional[Path] = None
    
    # Progress
    progress: int = 0
    current_stage: Optional[str] = None
    
    # Results
    selected_variant: Optional[str] = None
    selection_reason: Optional[str] = None
    
    # Artifacts (internal mapping)
    artifacts: Dict[str, Path] = field(default_factory=dict)
    artifact_metadata: List[ArtifactInfo] = field(default_factory=list)
    
    # Stages
    stages: List[StageInfo] = field(default_factory=list)
    
    # Logs
    logs: List[LogEntry] = field(default_factory=list)
    
    # Error info
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    failed_stage: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self, include_logs: bool = False) -> Dict[str, Any]:
        """Convert to API-safe dict (no internal paths)."""
        result = {
            "job_id": self.job_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "original_filename": self.original_filename,
            "file_size_bytes": self.file_size_bytes,
            "progress": self.progress,
            "current_stage": self.current_stage,
            "selected_variant": self.selected_variant,
            "selection_reason": self.selection_reason,
            "stages": [s.to_dict() for s in self.stages],
            "artifacts": [a.to_dict() for a in self.artifact_metadata],
        }
        
        if self.state == JobState.FAILED:
            result["error"] = {
                "code": self.error_code,
                "message": self.error_message,
                "stage": self.failed_stage,
            }
        
        if include_logs:
            result["logs"] = [l.to_dict() for l in self.logs]
        
        return result


def create_job(
    user_id: str,
    original_filename: str,
    file_size_bytes: int,
    input_path: Path,
    metadata: Optional[Dict[str, Any]] = None,
) -> Job:
    """Create a new job."""
    now = datetime.now(timezone.utc).isoformat()
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    
    return Job(
        job_id=job_id,
        user_id=user_id,
        state=JobState.CREATED,
        created_at=now,
        updated_at=now,
        original_filename=original_filename,
        file_size_bytes=file_size_bytes,
        input_path=input_path,
        progress=0,
        metadata=metadata or {},
    )
