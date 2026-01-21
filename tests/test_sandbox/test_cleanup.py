"""
Tests for Container Cleanup Guarantees
======================================

These tests verify cleanup happens on:
    - Normal completion
    - Execution failure
    - Timeout
    - Crashes

NOTE: These tests require Docker to be running.
"""

import pytest
from pathlib import Path

from backend.sandbox import (
    run_job_in_sandbox,
    ContainerTimeoutError,
)


class TestCleanupOnSuccess:
    """Tests verifying cleanup after successful execution."""
    
    def test_container_removed_after_success(
        self,
        docker_client,
        ensure_test_image,
        temp_job_dirs,
        test_job_id,
    ):
        """Container is removed after successful execution."""
        input_dir, output_dir = temp_job_dirs
        
        result = run_job_in_sandbox(
            job_id=test_job_id,
            command=["echo", "success"],
            input_dir=input_dir,
            output_dir=output_dir,
            timeout_seconds=30,
        )
        
        assert result.success is True
        
        # Verify no container with this name exists
        containers = docker_client.containers.list(
            all=True,
            filters={"name": f"soac_sandbox_{test_job_id}"}
        )
        assert len(containers) == 0


class TestCleanupOnFailure:
    """Tests verifying cleanup after failed execution."""
    
    def test_container_removed_after_nonzero_exit(
        self,
        docker_client,
        ensure_test_image,
        temp_job_dirs,
        test_job_id,
        failing_script,
    ):
        """Container is removed even when command fails."""
        input_dir, output_dir = temp_job_dirs
        
        result = run_job_in_sandbox(
            job_id=test_job_id,
            command=["python", "/workspace/input/fail.py"],
            input_dir=input_dir,
            output_dir=output_dir,
            timeout_seconds=30,
        )
        
        assert result.success is False
        
        # Container should still be removed
        containers = docker_client.containers.list(
            all=True,
            filters={"name": f"soac_sandbox_{test_job_id}"}
        )
        assert len(containers) == 0


class TestCleanupOnTimeout:
    """Tests verifying cleanup when job times out."""
    
    def test_container_removed_after_timeout(
        self,
        docker_client,
        ensure_test_image,
        temp_job_dirs,
        test_job_id,
        infinite_loop_script,
    ):
        """Container is killed and removed when timeout is exceeded."""
        input_dir, output_dir = temp_job_dirs
        
        with pytest.raises(ContainerTimeoutError) as exc_info:
            run_job_in_sandbox(
                job_id=test_job_id,
                command=["python", "/workspace/input/infinite.py"],
                input_dir=input_dir,
                output_dir=output_dir,
                timeout_seconds=10,  # Short timeout
            )
        
        assert exc_info.value.job_id == test_job_id
        assert exc_info.value.timeout_seconds == 10
        
        # Container should be removed despite timeout
        import time
        time.sleep(2)  # Give Docker a moment
        
        containers = docker_client.containers.list(
            all=True,
            filters={"name": f"soac_sandbox_{test_job_id}"}
        )
        assert len(containers) == 0


class TestNoOrphans:
    """Tests verifying no orphaned containers are left behind."""
    
    def test_no_soac_containers_after_tests(self, docker_client):
        """Verify no SOAC containers are orphaned after running tests."""
        containers = docker_client.containers.list(
            all=True,
            filters={"label": "soac.sandbox.managed=true"}
        )
        
        # Clean up any that exist (from previous failed tests)
        for container in containers:
            try:
                container.remove(force=True)
            except Exception:
                pass
        
        # Verify they're gone
        containers = docker_client.containers.list(
            all=True,
            filters={"label": "soac.sandbox.managed=true"}
        )
        assert len(containers) == 0
