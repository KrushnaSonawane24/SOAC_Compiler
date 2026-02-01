"""
SOAC Cryptographic Build Attestation
=====================================

Cryptographic signing and verification for build fingerprints.

Enables enterprise trust and audit readiness through:
    - HMAC-SHA256 signing of build fingerprints
    - Attestation verification
    - Provenance metadata generation

GUARANTEES:
    - Deterministic: Same input produces same signature
    - Tamper-evident: Any modification invalidates signature
    - Industry-standard: Uses HMAC-SHA256
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
import logging
import secrets
import base64

logger = logging.getLogger(__name__)


# =============================================================================
# ATTESTATION DATA STRUCTURES
# =============================================================================

@dataclass
class BuildAttestation:
    """
    Cryptographic attestation of a build.
    
    Contains the signature and metadata needed to verify
    the integrity and provenance of a build.
    
    Attributes:
        fingerprint_hash: SHA-256 of the build fingerprint
        signature: HMAC-SHA256 signature (hex)
        signer_id: Identifier of the signing entity
        signed_at: ISO timestamp of signing
        algorithm: Signature algorithm used
        metadata: Additional provenance metadata
    """
    fingerprint_hash: str
    signature: str
    signer_id: str
    signed_at: str
    algorithm: str = "HMAC-SHA256"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "fingerprint_hash": self.fingerprint_hash,
            "signature": self.signature,
            "signer_id": self.signer_id,
            "signed_at": self.signed_at,
            "algorithm": self.algorithm,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BuildAttestation":
        return cls(
            fingerprint_hash=data["fingerprint_hash"],
            signature=data["signature"],
            signer_id=data["signer_id"],
            signed_at=data["signed_at"],
            algorithm=data.get("algorithm", "HMAC-SHA256"),
            metadata=data.get("metadata", {}),
        )
    
    def save(self, path: Path) -> None:
        """Save attestation to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> "BuildAttestation":
        """Load attestation from JSON file."""
        with open(path, 'r') as f:
            return cls.from_dict(json.load(f))


@dataclass
class VerificationResult:
    """
    Result of attestation verification.
    
    Indicates whether the attestation is valid and provides
    details about any verification failures.
    """
    valid: bool
    attestation: Optional[BuildAttestation] = None
    expected_hash: Optional[str] = None
    actual_hash: Optional[str] = None
    reason: str = ""
    verified_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "attestation": self.attestation.to_dict() if self.attestation else None,
            "expected_hash": self.expected_hash,
            "actual_hash": self.actual_hash,
            "reason": self.reason,
            "verified_at": self.verified_at,
        }


@dataclass
class ProvenanceReport:
    """
    Full provenance report for audit purposes.
    
    Contains all information needed to verify the
    integrity and origin of a build.
    """
    job_id: str
    attestation: BuildAttestation
    build_info: Dict[str, Any]
    verification_status: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "attestation": self.attestation.to_dict(),
            "build_info": self.build_info,
            "verification_status": self.verification_status,
            "generated_at": self.generated_at,
        }
    
    def to_markdown(self) -> str:
        """Generate a markdown provenance report."""
        lines = [
            "# Build Provenance Report",
            "",
            f"**Job ID:** {self.job_id}",
            f"**Generated:** {self.generated_at}",
            f"**Verification Status:** {self.verification_status}",
            "",
            "## Attestation",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| Fingerprint Hash | `{self.attestation.fingerprint_hash[:16]}...` |",
            f"| Signature | `{self.attestation.signature[:16]}...` |",
            f"| Signer | {self.attestation.signer_id} |",
            f"| Signed At | {self.attestation.signed_at} |",
            f"| Algorithm | {self.attestation.algorithm} |",
            "",
            "## Build Information",
            "",
        ]
        
        for key, value in self.build_info.items():
            if isinstance(value, str) and len(value) > 50:
                value = f"`{value[:16]}...`"
            lines.append(f"- **{key}:** {value}")
        
        lines.extend([
            "",
            "## Integrity Statement",
            "",
            "This document certifies that the referenced build artifacts were:",
            "1. Generated by the SOAC compiler",
            "2. Cryptographically signed at the time of creation",
            "3. Not modified since signing",
            "",
            f"*Report generated by SOAC Build Attestation System*",
        ])
        
        return "\n".join(lines)


# =============================================================================
# SIGNING AND VERIFICATION
# =============================================================================

class BuildAttestationSigner:
    """
    Signs build fingerprints using HMAC-SHA256.
    
    Provides cryptographic attestation for build artifacts
    to ensure integrity and enable audit trails.
    
    Security:
        - Uses HMAC-SHA256 (industry standard)
        - Constant-time comparison for verification
        - No key material stored in attestations
    
    Example:
        >>> signer = BuildAttestationSigner(secret_key, "my-signer-id")
        >>> attestation = signer.sign(fingerprint_dict)
        >>> result = signer.verify(attestation, fingerprint_dict)
        >>> assert result.valid
    """
    
    def __init__(self, secret_key: bytes, signer_id: str):
        """
        Initialize the attestation signer.
        
        Args:
            secret_key: Secret key for HMAC (32+ bytes recommended)
            signer_id: Identifier for this signing entity
        """
        if len(secret_key) < 16:
            raise ValueError("Secret key must be at least 16 bytes")
        
        self._key = secret_key
        self._signer_id = signer_id
    
    def sign(self, fingerprint: Dict[str, Any]) -> BuildAttestation:
        """
        Sign a build fingerprint.
        
        Args:
            fingerprint: Build fingerprint dictionary
        
        Returns:
            BuildAttestation with cryptographic signature
        """
        # Compute deterministic hash of fingerprint
        fingerprint_hash = self._hash_fingerprint(fingerprint)
        
        # Compute HMAC signature
        signature = self._compute_hmac(fingerprint_hash)
        
        return BuildAttestation(
            fingerprint_hash=fingerprint_hash,
            signature=signature,
            signer_id=self._signer_id,
            signed_at=datetime.now(timezone.utc).isoformat(),
            algorithm="HMAC-SHA256",
            metadata={
                "fingerprint_keys": list(fingerprint.keys()),
            },
        )
    
    def verify(
        self, 
        attestation: BuildAttestation, 
        fingerprint: Dict[str, Any]
    ) -> VerificationResult:
        """
        Verify an attestation against a fingerprint.
        
        Args:
            attestation: The attestation to verify
            fingerprint: The fingerprint to verify against
        
        Returns:
            VerificationResult indicating validity
        """
        # Recompute fingerprint hash
        actual_hash = self._hash_fingerprint(fingerprint)
        
        # Check hash matches
        if actual_hash != attestation.fingerprint_hash:
            return VerificationResult(
                valid=False,
                attestation=attestation,
                expected_hash=attestation.fingerprint_hash,
                actual_hash=actual_hash,
                reason="Fingerprint hash mismatch - content may have been modified",
            )
        
        # Verify HMAC signature
        expected_signature = self._compute_hmac(actual_hash)
        
        if not hmac.compare_digest(expected_signature, attestation.signature):
            return VerificationResult(
                valid=False,
                attestation=attestation,
                expected_hash=attestation.fingerprint_hash,
                actual_hash=actual_hash,
                reason="Signature verification failed - attestation may be forged",
            )
        
        return VerificationResult(
            valid=True,
            attestation=attestation,
            expected_hash=attestation.fingerprint_hash,
            actual_hash=actual_hash,
            reason="Attestation verified successfully",
        )
    
    def _hash_fingerprint(self, fingerprint: Dict[str, Any]) -> str:
        """Compute deterministic hash of fingerprint."""
        # Sort keys for determinism
        serialized = json.dumps(fingerprint, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()
    
    def _compute_hmac(self, data: str) -> str:
        """Compute HMAC-SHA256 of data."""
        return hmac.new(
            self._key,
            data.encode(),
            hashlib.sha256
        ).hexdigest()


# =============================================================================
# PROVENANCE GENERATION
# =============================================================================

def generate_provenance_report(
    job_id: str,
    attestation: BuildAttestation,
    build_fingerprint: Dict[str, Any],
    signer: Optional[BuildAttestationSigner] = None,
) -> ProvenanceReport:
    """
    Generate a complete provenance report.
    
    Args:
        job_id: The job identifier
        attestation: The build attestation
        build_fingerprint: The original build fingerprint
        signer: Optional signer for verification
    
    Returns:
        ProvenanceReport for audit purposes
    """
    # Determine verification status
    if signer:
        result = signer.verify(attestation, build_fingerprint)
        status = "VERIFIED" if result.valid else "FAILED"
    else:
        status = "UNVERIFIED"
    
    # Extract build info
    build_info = {
        "input_hash": build_fingerprint.get("input_file_hash", "unknown"),
        "canonical_hash": build_fingerprint.get("canonical_onnx_hash", "unknown"),
        "selected_variant": build_fingerprint.get("selected_variant_id", "unknown"),
        "config_hash": build_fingerprint.get("config_hash", "unknown"),
        "build_mode": build_fingerprint.get("build_mode", "normal"),
    }
    
    return ProvenanceReport(
        job_id=job_id,
        attestation=attestation,
        build_info=build_info,
        verification_status=status,
    )


# =============================================================================
# KEY MANAGEMENT
# =============================================================================

def generate_signing_key() -> bytes:
    """
    Generate a cryptographically secure signing key.
    
    Returns 32 random bytes suitable for HMAC-SHA256.
    """
    return secrets.token_bytes(32)


def encode_key_base64(key: bytes) -> str:
    """Encode a key as base64 for storage."""
    return base64.b64encode(key).decode('ascii')


def decode_key_base64(encoded: str) -> bytes:
    """Decode a base64-encoded key."""
    return base64.b64decode(encoded.encode('ascii'))


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_signer(secret_key: bytes, signer_id: str = "soac-compiler") -> BuildAttestationSigner:
    """
    Create a build attestation signer.
    
    Args:
        secret_key: Secret key for signing
        signer_id: Identifier for the signer
    
    Returns:
        Configured BuildAttestationSigner
    """
    return BuildAttestationSigner(secret_key, signer_id)


def sign_build(
    fingerprint: Dict[str, Any],
    secret_key: bytes,
    signer_id: str = "soac-compiler",
) -> BuildAttestation:
    """
    Convenience function to sign a build fingerprint.
    
    Args:
        fingerprint: Build fingerprint to sign
        secret_key: Secret key for signing
        signer_id: Identifier for the signer
    
    Returns:
        Signed BuildAttestation
    """
    signer = BuildAttestationSigner(secret_key, signer_id)
    return signer.sign(fingerprint)


def verify_attestation(
    attestation: BuildAttestation,
    fingerprint: Dict[str, Any],
    secret_key: bytes,
) -> VerificationResult:
    """
    Convenience function to verify an attestation.
    
    Args:
        attestation: Attestation to verify
        fingerprint: Fingerprint to verify against
        secret_key: Secret key for verification
    
    Returns:
        VerificationResult
    """
    signer = BuildAttestationSigner(secret_key, attestation.signer_id)
    return signer.verify(attestation, fingerprint)
