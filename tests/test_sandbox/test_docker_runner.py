"""
Tests for Docker Sandbox Runner
===============================

Integration tests for the main sandbox execution function.

NOTE: These tests require Docker to be running.
"""

import pytest
from pathlib import Path

from backend.sandbox import (
    run_job_in_sandbox,
    ExecutionResult,
    SandboxError,
    ContainerTimeoutError,
)
from backend.sandbox.docker_runner import (
    validate_job_id,
    validate_command,
)


class TestValidation:
    """Tests for input validation."""
    
    def test_valid_job_id(self):
        """Valid job IDs are accepted."""
        assert validate_job_id("job_123") == "job_123"
        assert validate_job_id("test-456") == "test-456"
        assert validate_job_id("ABC") == "ABC"
    
    def test_invalid_job_id_rejected(self):
        """Invalid job IDs are rejected."""
        with pytest.raises(ValueError):
            validate_job_id("job/../escape")
        
        with pytest.raises(ValueError):
            validate_job_id("job;rm -rf /")
        
        with pytest.raises(ValueError):
            validate_job_id("job\x00null")
    
    def test_empty_command_rejected(self):
        """Empty commands are rejected."""
        with pytest.raises(ValueError):
            validate_command([])
    
    def test_non_string_command_rejected(self):
        """Non-string command arguments are rejected."""
        with pytest.raises(ValueError):
            validate_command(["python", 123])


class TestBasicExecution:
    """Tests for basic sandbox execution."""
    
    def test_simple_echo(
        self,
        docker_client,
        ensure_test_image,
        temp_job_dirs,
        test_job_id,
    ):
        """Simple echo command works."""
        input_dir, output_dir = temp_job_dirs
        
        result = run_job_in_sandbox(
            job_id=test_job_id,
            command=["echo", "Hello, Sandbox!"],
            input_dir=input_dir,
            output_dir=output_dir,
            timeout_seconds=30,
        )
        
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.exit_code == 0
        assert "Hello, Sandbox!" in result.stdout
    
    def test_python_script_execution(
        self,
        docker_client,
        ensure_test_image,
        temp_job_dirs,
        test_job_id,
        simple_script_file,
    ):
        """Python script can be executed."""
        input_dir, output_dir = temp_job_dirs
        
        result = run_job_in_sandbox(
            job_id=test_job_id,
            command=["python", "/workspace/input/test_script.py", "arg1", "arg2"],
            input_dir=input_dir,
            output_dir=output_dir,
            timeout_seconds=30,
        )
        
        assert result.success is True
        assert "Hello from container!" in result.stdout
        assert "arg1" in result.stdout
    
    def test_write_to_output_dir(
        self,
        docker_client,
        ensure_test_image,
        temp_job_dirs,
        test_job_id,
        write_output_script,
    ):
        """Container can write to output directory."""
        input_dir, output_dir = temp_job_dirs
        
        result = run_job_in_sandbox(
            job_id=test_job_id,
            command=["python", "/workspace/input/write_output.py"],
            input_dir=input_dir,
            output_dir=output_dir,
            timeout_seconds=30,
        )
        
        assert result.success is True
        
        # Verify output file exists on host
        output_file = output_dir / "result.txt"
        assert output_file.exists()
        assert output_file.read_text() == "Output from container"
    
    def test_failing_command_returns_exit_code(
        self,
        docker_client,
        ensure_test_image,
        temp_job_dirs,
        test_job_id,
        failing_script,
    ):
        """Failing command returns correct exit code."""
        input_dir, output_dir = temp_job_dirs
        
        result = run_job_in_sandbox(
            job_id=test_job_id,
            command=["python", "/workspace/input/fail.py"],
            input_dir=input_dir,
            output_dir=output_dir,
            timeout_seconds=30,
        )
        
        assert result.success is False
        assert result.exit_code == 42


class TestResourceLimits:
    """Tests for resource limit enforcement."""
    
    def test_custom_memory_limit(
        self,
        docker_client,
        ensure_test_image,
        temp_job_dirs,
        test_job_id,
    ):
        """Custom memory limit is applied."""
        input_dir, output_dir = temp_job_dirs
        
        result = run_job_in_sandbox(
            job_id=test_job_id,
            command=["echo", "test"],
            input_dir=input_dir,
            output_dir=output_dir,
            memory_limit="256m",
            timeout_seconds=30,
        )
        
        assert result.success is True
        assert result.resource_limits.memory == "256m"
    
    def test_custom_cpu_limit(
        self,
        docker_client,
        ensure_test_image,
        temp_job_dirs,
        test_job_id,
    ):
        """Custom CPU limit is applied."""
        input_dir, output_dir = temp_job_dirs
        
        result = run_job_in_sandbox(
            job_id=test_job_id,
            command=["echo", "test"],
            input_dir=input_dir,
            output_dir=output_dir,
            cpu_limit=0.5,
            timeout_seconds=30,
        )
        
        assert result.success is True
        assert result.resource_limits.cpu == 0.5


class TestContainerLifecycle:
    """Tests for container creation, execution, and cleanup."""
    
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
            command=["echo", "cleanup test"],
            input_dir=input_dir,
            output_dir=output_dir,
            timeout_seconds=30,
        )
        
        assert result.success is True
        
        # Check container is gone
        containers = docker_client.containers.list(
            all=True,
            filters={"name": f"soac_sandbox_{test_job_id}"}
        )
        assert len(containers) == 0
    
    def test_container_removed_after_failure(
        self,
        docker_client,
        ensure_test_image,
        temp_job_dirs,
        test_job_id,
        failing_script,
    ):
        """Container is removed even after failure."""
        input_dir, output_dir = temp_job_dirs
        
        result = run_job_in_sandbox(
            job_id=test_job_id,
            command=["python", "/workspace/input/fail.py"],
            input_dir=input_dir,
            output_dir=output_dir,
            timeout_seconds=30,
        )
        
        assert result.success is False
        
        # Check container is gone
        containers = docker_client.containers.list(
            all=True,
            filters={"name": f"soac_sandbox_{test_job_id}"}
        )
        assert len(containers) == 0
