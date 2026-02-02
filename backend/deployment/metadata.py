"""
SOAC Deployment Metadata
========================

Data structures for deployment artifacts.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum


class TargetPlatform(str, Enum):
    """Deployment target platforms."""
    ANDROID = "android"
    IOS = "ios"
    CPU = "cpu"
    GPU = "gpu"
    ONNX = "onnx"


class ArtifactStatus(str, Enum):
    """Status of artifact generation."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class DeploymentArtifact:
    """
    A single deployment artifact.
    
    Attributes:
        platform: Target platform
        format: File format (tflite, mlmodel, onnx, plan)
        path: Path to artifact file
        size_bytes: File size
        status: Generation status
        error_message: Error if failed
        metadata: Additional info
    """
    platform: TargetPlatform
    format: str
    path: Optional[Path]
    size_bytes: int
    status: ArtifactStatus
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_valid(self) -> bool:
        return self.status == ArtifactStatus.SUCCESS and self.path is not None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform.value,
            "format": self.format,
            "path": str(self.path) if self.path else None,
            "size_bytes": self.size_bytes,
            "status": self.status.value,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


@dataclass
class DeploymentBundle:
    """
    Complete deployment bundle with all artifacts.
    
    Attributes:
        source_variant_id: ID of source optimized variant
        source_hash: Hash of source model
        artifacts: Dict of platform -> artifact
        output_dir: Directory containing all artifacts
        timestamp: Generation timestamp
    """
    source_variant_id: str
    source_hash: str
    artifacts: Dict[TargetPlatform, DeploymentArtifact]
    output_dir: Path
    timestamp: str
    
    @property
    def successful_count(self) -> int:
        return sum(1 for a in self.artifacts.values() if a.is_valid)
    
    @property
    def failed_count(self) -> int:
        return sum(1 for a in self.artifacts.values() if a.status == ArtifactStatus.FAILED)
    
    @property
    def skipped_count(self) -> int:
        return sum(1 for a in self.artifacts.values() if a.status == ArtifactStatus.SKIPPED)
    
    def get_artifact(self, platform: TargetPlatform) -> Optional[DeploymentArtifact]:
        return self.artifacts.get(platform)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_variant_id": self.source_variant_id,
            "source_hash": self.source_hash,
            "artifacts": {p.value: a.to_dict() for p, a in self.artifacts.items()},
            "output_dir": str(self.output_dir),
            "timestamp": self.timestamp,
            "summary": {
                "successful": self.successful_count,
                "failed": self.failed_count,
                "skipped": self.skipped_count,
            },
        }


def create_timestamp() -> str:
    """Create ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


def create_skipped_artifact(
    platform: TargetPlatform,
    format: str,
    reason: str,
) -> DeploymentArtifact:
    """Create artifact marked as skipped."""
    return DeploymentArtifact(
        platform=platform,
        format=format,
        path=None,
        size_bytes=0,
        status=ArtifactStatus.SKIPPED,
        error_message=reason,
    )


def create_failed_artifact(
    platform: TargetPlatform,
    format: str,
    error: str,
) -> DeploymentArtifact:
    """Create artifact marked as failed."""
    return DeploymentArtifact(
        platform=platform,
        format=format,
        path=None,
        size_bytes=0,
        status=ArtifactStatus.FAILED,
        error_message=error,
    )
