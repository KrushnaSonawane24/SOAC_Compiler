"""
SOAC Demo Availability Contract
===============================

Defines explicit availability for demo artifacts.

AVAILABILITY CONTRACT:
    Target              | Guaranteed | Conditional
    --------------------|------------|-------------
    TFLite model        | ✅ Always  | ❌
    Android demo        | ✅ Always  | ❌
    TensorRT model      | ❌         | ✅ (GPU present)
    TensorRT demo       | ❌         | ✅ (GPU present)

NO SILENT SKIPPING ALLOWED - all unavailability must be explicit.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class DemoStatus(str, Enum):
    """Status of a demo artifact."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    GENERATING = "generating"
    GENERATED = "generated"
    FAILED = "failed"


class DemoType(str, Enum):
    """Types of demo artifacts."""
    ANDROID_TFLITE = "android_tflite"
    ANDROID_DEMO = "android_demo"
    TENSORRT_MODEL = "tensorrt_model"
    TENSORRT_DEMO = "tensorrt_demo"


@dataclass
class DemoArtifactStatus:
    """
    Status of a single demo artifact.
    
    Attributes:
        demo_type: Type of demo
        status: Current status
        guaranteed: Whether this is a guaranteed artifact
        reason: Explanation if unavailable
        path: Path to artifact if generated
    """
    demo_type: DemoType
    status: DemoStatus
    guaranteed: bool
    reason: Optional[str] = None
    path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "demo_type": self.demo_type.value,
            "status": self.status.value,
            "guaranteed": self.guaranteed,
            "reason": self.reason,
            "path": self.path,
        }


@dataclass
class DemoAvailability:
    """
    Complete demo availability contract.
    
    Explicitly states what demos are available and why.
    """
    android_tflite: DemoArtifactStatus
    android_demo: DemoArtifactStatus
    tensorrt_model: DemoArtifactStatus
    tensorrt_demo: DemoArtifactStatus
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "android_tflite": self.android_tflite.to_dict(),
            "android_demo": self.android_demo.to_dict(),
            "tensorrt_model": self.tensorrt_model.to_dict(),
            "tensorrt_demo": self.tensorrt_demo.to_dict(),
            "summary": {
                "guaranteed_available": self.guaranteed_count,
                "conditional_available": self.conditional_available_count,
                "unavailable": self.unavailable_count,
            }
        }
    
    @property
    def guaranteed_count(self) -> int:
        """Count of guaranteed artifacts."""
        return sum(1 for a in self.all_artifacts if a.guaranteed)
    
    @property
    def conditional_available_count(self) -> int:
        """Count of conditional artifacts that are available."""
        return sum(
            1 for a in self.all_artifacts 
            if not a.guaranteed and a.status == DemoStatus.AVAILABLE
        )
    
    @property
    def unavailable_count(self) -> int:
        """Count of unavailable artifacts."""
        return sum(
            1 for a in self.all_artifacts 
            if a.status == DemoStatus.UNAVAILABLE
        )
    
    @property
    def all_artifacts(self) -> List[DemoArtifactStatus]:
        """List of all artifact statuses."""
        return [
            self.android_tflite,
            self.android_demo,
            self.tensorrt_model,
            self.tensorrt_demo,
        ]
    
    def get_unavailable_reasons(self) -> Dict[str, str]:
        """Get reasons for all unavailable artifacts."""
        return {
            a.demo_type.value: a.reason or "Unknown reason"
            for a in self.all_artifacts
            if a.status == DemoStatus.UNAVAILABLE
        }


def is_tflite_available() -> bool:
    """Check if TFLite conversion toolchain is available."""
    from .tflite import is_tflite_available as _is_tflite
    return _is_tflite()


def is_tensorrt_available() -> bool:
    """Check if TensorRT is available (requires GPU)."""
    from .tensorrt import is_tensorrt_available as _is_trt
    return _is_trt()


def check_availability() -> DemoAvailability:
    """
    Check what demo artifacts can be generated.
    
    Returns:
        DemoAvailability contract with explicit status for each artifact.
    """
    tflite_ok = is_tflite_available()
    tensorrt_ok = is_tensorrt_available()
    
    # Android TFLite - GUARANTEED
    android_tflite = DemoArtifactStatus(
        demo_type=DemoType.ANDROID_TFLITE,
        status=DemoStatus.AVAILABLE if tflite_ok else DemoStatus.UNAVAILABLE,
        guaranteed=True,
        reason=None if tflite_ok else "TensorFlow/onnx2tf not installed",
    )
    
    # Android Demo - GUARANTEED
    android_demo = DemoArtifactStatus(
        demo_type=DemoType.ANDROID_DEMO,
        status=DemoStatus.AVAILABLE if tflite_ok else DemoStatus.UNAVAILABLE,
        guaranteed=True,
        reason=None if tflite_ok else "TFLite model required but unavailable",
    )
    
    # TensorRT Model - CONDITIONAL
    tensorrt_model = DemoArtifactStatus(
        demo_type=DemoType.TENSORRT_MODEL,
        status=DemoStatus.AVAILABLE if tensorrt_ok else DemoStatus.UNAVAILABLE,
        guaranteed=False,
        reason=None if tensorrt_ok else "TensorRT/NVIDIA GPU not available",
    )
    
    # TensorRT Demo - CONDITIONAL
    tensorrt_demo = DemoArtifactStatus(
        demo_type=DemoType.TENSORRT_DEMO,
        status=DemoStatus.AVAILABLE if tensorrt_ok else DemoStatus.UNAVAILABLE,
        guaranteed=False,
        reason=None if tensorrt_ok else "TensorRT/NVIDIA GPU not available",
    )
    
    availability = DemoAvailability(
        android_tflite=android_tflite,
        android_demo=android_demo,
        tensorrt_model=tensorrt_model,
        tensorrt_demo=tensorrt_demo,
    )
    
    logger.info(
        f"Demo availability: {availability.guaranteed_count} guaranteed, "
        f"{availability.conditional_available_count} conditional available, "
        f"{availability.unavailable_count} unavailable"
    )
    
    if availability.unavailable_count > 0:
        logger.info(f"Unavailable reasons: {availability.get_unavailable_reasons()}")
    
    return availability


def update_status(
    availability: DemoAvailability,
    demo_type: DemoType,
    status: DemoStatus,
    path: Optional[str] = None,
    reason: Optional[str] = None,
) -> DemoAvailability:
    """
    Update status of a demo artifact.
    
    Creates a new DemoAvailability with updated status.
    """
    artifacts = {
        DemoType.ANDROID_TFLITE: availability.android_tflite,
        DemoType.ANDROID_DEMO: availability.android_demo,
        DemoType.TENSORRT_MODEL: availability.tensorrt_model,
        DemoType.TENSORRT_DEMO: availability.tensorrt_demo,
    }
    
    old = artifacts[demo_type]
    artifacts[demo_type] = DemoArtifactStatus(
        demo_type=demo_type,
        status=status,
        guaranteed=old.guaranteed,
        reason=reason if reason else old.reason,
        path=path,
    )
    
    return DemoAvailability(
        android_tflite=artifacts[DemoType.ANDROID_TFLITE],
        android_demo=artifacts[DemoType.ANDROID_DEMO],
        tensorrt_model=artifacts[DemoType.TENSORRT_MODEL],
        tensorrt_demo=artifacts[DemoType.TENSORRT_DEMO],
    )
