"""
SOAC Build Fingerprint
======================

Generates reproducible build fingerprints for audit and verification.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum


class BuildMode(str, Enum):
    """Build mode."""
    NORMAL = "normal"
    REPRODUCIBLE = "reproducible"


@dataclass
class BuildFingerprint:
    """
    Reproducible build fingerprint.
    
    Contains all hashes needed to verify build reproducibility.
    """
    # Build info
    build_mode: BuildMode
    job_id: str
    created_at: str
    
    # Input hashes
    input_file_hash: str
    canonical_onnx_hash: str
    
    # Variant hashes (ordered)
    variant_hashes: Dict[str, str] = field(default_factory=dict)
    
    # Selection
    selected_variant_hash: str = ""
    selected_variant_id: str = ""
    
    # Config hash
    config_hash: str = ""
    
    # Combined fingerprint
    fingerprint: str = ""
    
    def compute_fingerprint(self) -> str:
        """Compute combined fingerprint from all components."""
        components = [
            self.input_file_hash,
            self.canonical_onnx_hash,
            self.config_hash,
            self.selected_variant_hash,
        ]
        
        # Add variant hashes in sorted order
        for key in sorted(self.variant_hashes.keys()):
            components.append(self.variant_hashes[key])
        
        combined = ":".join(components)
        self.fingerprint = hashlib.sha256(combined.encode()).hexdigest()
        return self.fingerprint
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "build_mode": self.build_mode.value,
            "job_id": self.job_id,
            "created_at": self.created_at,
            "input_file_hash": self.input_file_hash,
            "canonical_onnx_hash": self.canonical_onnx_hash,
            "variant_hashes": self.variant_hashes,
            "selected_variant_hash": self.selected_variant_hash,
            "selected_variant_id": self.selected_variant_id,
            "config_hash": self.config_hash,
            "fingerprint": self.fingerprint,
        }
    
    def save(self, output_dir: Path) -> Path:
        """Save fingerprint to JSON file."""
        path = output_dir / "build_fingerprint.json"
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        return path
    
    @classmethod
    def load(cls, path: Path) -> "BuildFingerprint":
        """Load fingerprint from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        
        fp = cls(
            build_mode=BuildMode(data["build_mode"]),
            job_id=data["job_id"],
            created_at=data["created_at"],
            input_file_hash=data["input_file_hash"],
            canonical_onnx_hash=data["canonical_onnx_hash"],
            variant_hashes=data.get("variant_hashes", {}),
            selected_variant_hash=data.get("selected_variant_hash", ""),
            selected_variant_id=data.get("selected_variant_id", ""),
            config_hash=data.get("config_hash", ""),
            fingerprint=data.get("fingerprint", ""),
        )
        return fp


def hash_config(config: Any) -> str:
    """Hash job configuration deterministically."""
    if hasattr(config, 'to_dict'):
        config_dict = config.to_dict()
    elif isinstance(config, dict):
        config_dict = config
    else:
        config_dict = {"repr": repr(config)}
    
    # Sort keys for determinism
    config_str = json.dumps(config_dict, sort_keys=True)
    return hashlib.sha256(config_str.encode()).hexdigest()


def hash_file(path: Path) -> str:
    """Hash file contents."""
    sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def create_build_fingerprint(
    job_id: str,
    build_mode: BuildMode,
    input_file_hash: str,
    canonical_hash: str,
    variant_hashes: Dict[str, str],
    selected_variant_id: str,
    selected_variant_hash: str,
    config_hash: str,
) -> BuildFingerprint:
    """Create a build fingerprint."""
    fp = BuildFingerprint(
        build_mode=build_mode,
        job_id=job_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        input_file_hash=input_file_hash,
        canonical_onnx_hash=canonical_hash,
        variant_hashes=variant_hashes,
        selected_variant_id=selected_variant_id,
        selected_variant_hash=selected_variant_hash,
        config_hash=config_hash,
    )
    fp.compute_fingerprint()
    return fp
