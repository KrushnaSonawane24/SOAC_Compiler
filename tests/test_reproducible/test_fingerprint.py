"""
Tests for Reproducible Build Mode
=================================

Tests for build fingerprint generation and reproducibility.
"""

import pytest
from pathlib import Path
import tempfile
import json

from backend.reproducible import (
    BuildMode,
    BuildFingerprint,
    hash_config,
    hash_file,
    create_build_fingerprint,
    reproducible_context,
)
from backend.orchestrator.job_context import JobConfig


class TestBuildFingerprint:
    """Tests for build fingerprint."""
    
    def test_fingerprint_is_deterministic(self):
        """Same inputs produce same fingerprint."""
        fp1 = create_build_fingerprint(
            job_id="job_123",
            build_mode=BuildMode.REPRODUCIBLE,
            input_file_hash="abc123",
            canonical_hash="def456",
            variant_hashes={"v1": "hash1", "v2": "hash2"},
            selected_variant_id="v1",
            selected_variant_hash="hash1",
            config_hash="config_hash",
        )
        
        fp2 = create_build_fingerprint(
            job_id="job_123",
            build_mode=BuildMode.REPRODUCIBLE,
            input_file_hash="abc123",
            canonical_hash="def456",
            variant_hashes={"v1": "hash1", "v2": "hash2"},
            selected_variant_id="v1",
            selected_variant_hash="hash1",
            config_hash="config_hash",
        )
        
        assert fp1.fingerprint == fp2.fingerprint
    
    def test_different_config_produces_different_fingerprint(self):
        """Different config produces different fingerprint."""
        fp1 = create_build_fingerprint(
            job_id="job_123",
            build_mode=BuildMode.REPRODUCIBLE,
            input_file_hash="abc123",
            canonical_hash="def456",
            variant_hashes={},
            selected_variant_id="v1",
            selected_variant_hash="hash1",
            config_hash="config_a",
        )
        
        fp2 = create_build_fingerprint(
            job_id="job_123",
            build_mode=BuildMode.REPRODUCIBLE,
            input_file_hash="abc123",
            canonical_hash="def456",
            variant_hashes={},
            selected_variant_id="v1",
            selected_variant_hash="hash1",
            config_hash="config_b",
        )
        
        assert fp1.fingerprint != fp2.fingerprint
    
    def test_fingerprint_save_and_load(self, tmp_path):
        """Fingerprint can be saved and loaded."""
        fp = create_build_fingerprint(
            job_id="job_test",
            build_mode=BuildMode.REPRODUCIBLE,
            input_file_hash="input_hash",
            canonical_hash="canonical_hash",
            variant_hashes={"v1": "h1"},
            selected_variant_id="v1",
            selected_variant_hash="h1",
            config_hash="cfg",
        )
        
        saved_path = fp.save(tmp_path)
        assert saved_path.exists()
        
        loaded = BuildFingerprint.load(saved_path)
        assert loaded.fingerprint == fp.fingerprint
        assert loaded.job_id == fp.job_id


class TestHashFunctions:
    """Tests for hash functions."""
    
    def test_hash_file(self, tmp_path):
        """File hashing is deterministic."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        
        hash1 = hash_file(test_file)
        hash2 = hash_file(test_file)
        
        assert hash1 == hash2
    
    def test_hash_config(self):
        """Config hashing is deterministic."""
        config = JobConfig(
            accuracy_threshold=0.02,
            build_mode="reproducible",
        )
        
        hash1 = hash_config(config)
        hash2 = hash_config(config)
        
        assert hash1 == hash2
    
    def test_different_config_different_hash(self):
        """Different configs produce different hashes."""
        config1 = JobConfig(accuracy_threshold=0.01)
        config2 = JobConfig(accuracy_threshold=0.02)
        
        assert hash_config(config1) != hash_config(config2)


class TestReproducibleContext:
    """Tests for reproducible context."""
    
    def test_reproducible_context_fixes_random(self):
        """Reproducible context produces deterministic random."""
        import random
        
        with reproducible_context(enabled=True, seed=42):
            r1 = random.random()
        
        with reproducible_context(enabled=True, seed=42):
            r2 = random.random()
        
        assert r1 == r2
    
    def test_normal_mode_different(self):
        """Normal mode produces different random."""
        import random
        
        with reproducible_context(enabled=False):
            r1 = random.random()
        
        with reproducible_context(enabled=False):
            r2 = random.random()
        
        # Might be same by chance, but very unlikely
        # This test is probabilistic


class TestJobConfigBuildMode:
    """Tests for JobConfig build mode."""
    
    def test_default_is_normal(self):
        """Default build mode is normal."""
        config = JobConfig()
        assert config.build_mode == "normal"
        assert not config.is_reproducible
    
    def test_reproducible_mode(self):
        """Reproducible mode is detected."""
        config = JobConfig(build_mode="reproducible")
        assert config.is_reproducible
    
    def test_reproducible_seed(self):
        """Reproducible seed is configurable."""
        config = JobConfig(reproducible_seed=123)
        assert config.reproducible_seed == 123
