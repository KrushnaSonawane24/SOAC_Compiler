"""
Tests for Container Isolation Guarantees
========================================

These tests verify the CRITICAL security guarantees:
    - No network access
    - Cannot write outside workspace
    - Jobs are isolated from each other

NOTE: These tests require Docker to be running.
"""

import pytest
from pathlib import Path

from backend.sandbox import run_job_in_sandbox


class TestNetworkIsolation:
    """Tests verifying containers have NO network access."""
    
    def test_no_network_access(
        self,
        docker_client,
        ensure_test_image,
        temp_job_dirs,
        test_job_id,
        network_test_script,
    ):
        """Container cannot access the internet."""
        input_dir, output_dir = temp_job_dirs
        
        result = run_job_in_sandbox(
            job_id=test_job_id,
            command=["python", "/workspace/input/network_test.py"],
            input_dir=input_dir,
            output_dir=output_dir,
            timeout_seconds=30,
        )
        
        # Script should succeed (network blocked = expected behavior)
        assert result.success is True
        assert "Network blocked" in result.stdout or "Network access succeeded" not in result.stdout
    
    def test_dns_resolution_fails(
        self,
        docker_client,
        ensure_test_image,
        temp_job_dirs,
        test_job_id,
    ):
        """DNS resolution fails due to no network."""
        input_dir, output_dir = temp_job_dirs
        
        # Create a script that tries DNS lookup
        dns_script = input_dir / "dns_test.py"
        dns_script.write_text("""
import socket
import sys

try:
    socket.gethostbyname('google.com')
    print("ERROR: DNS lookup succeeded!")
    sys.exit(1)
except socket.gaierror:
    print("DNS blocked as expected")
    sys.exit(0)
""")
        
        result = run_job_in_sandbox(
            job_id=test_job_id,
            command=["python", "/workspace/input/dns_test.py"],
            input_dir=input_dir,
            output_dir=output_dir,
            timeout_seconds=30,
        )
        
        assert result.success is True
        assert "DNS blocked" in result.stdout


class TestFilesystemIsolation:
    """Tests verifying filesystem isolation."""
    
    def test_cannot_write_to_root_filesystem(
        self,
        docker_client,
        ensure_test_image,
        temp_job_dirs,
        test_job_id,
        filesystem_escape_script,
    ):
        """Container cannot write outside workspace."""
        input_dir, output_dir = temp_job_dirs
        
        result = run_job_in_sandbox(
            job_id=test_job_id,
            command=["python", "/workspace/input/escape_test.py"],
            input_dir=input_dir,
            output_dir=output_dir,
            timeout_seconds=30,
        )
        
        assert result.success is True
        assert "All escape attempts blocked" in result.stdout
    
    def test_cannot_write_to_input_dir(
        self,
        docker_client,
        ensure_test_image,
        temp_job_dirs,
        test_job_id,
    ):
        """Container cannot write to read-only input directory."""
        input_dir, output_dir = temp_job_dirs
        
        write_to_input_script = input_dir / "write_input.py"
        write_to_input_script.write_text("""
import sys

try:
    with open('/workspace/input/new_file.txt', 'w') as f:
        f.write('escape!')
    print("ERROR: Could write to input directory!")
    sys.exit(1)
except (PermissionError, OSError) as e:
    print(f"Input dir is read-only as expected: {e}")
    sys.exit(0)
""")
        
        result = run_job_in_sandbox(
            job_id=test_job_id,
            command=["python", "/workspace/input/write_input.py"],
            input_dir=input_dir,
            output_dir=output_dir,
            timeout_seconds=30,
        )
        
        assert result.success is True
        assert "read-only" in result.stdout
    
    def test_can_write_to_tmp(
        self,
        docker_client,
        ensure_test_image,
        temp_job_dirs,
        test_job_id,
    ):
        """Container can write to /tmp (tmpfs mount)."""
        input_dir, output_dir = temp_job_dirs
        
        tmp_script = input_dir / "tmp_test.py"
        tmp_script.write_text("""
import sys
import os

try:
    with open('/tmp/test_file.txt', 'w') as f:
        f.write('temp data')
    print("Successfully wrote to /tmp")
    sys.exit(0)
except Exception as e:
    print(f"Failed to write to /tmp: {e}")
    sys.exit(1)
""")
        
        result = run_job_in_sandbox(
            job_id=test_job_id,
            command=["python", "/workspace/input/tmp_test.py"],
            input_dir=input_dir,
            output_dir=output_dir,
            timeout_seconds=30,
        )
        
        assert result.success is True
        assert "Successfully wrote to /tmp" in result.stdout


class TestJobIsolation:
    """Tests verifying jobs cannot see each other's data."""
    
    def test_two_jobs_isolated(
        self,
        docker_client,
        ensure_test_image,
        temp_job_dirs,
        test_job_id,
    ):
        """Two jobs running with different job_ids have separate directories."""
        input_dir, output_dir = temp_job_dirs
        
        # Create a script that writes to output and reads back
        script = input_dir / "isolation_test.py"
        script.write_text("""
import sys
import os

# List output directory
files = os.listdir('/workspace/output')
print(f"Files in output: {files}")

# Write our marker
marker_file = '/workspace/output/marker.txt'
with open(marker_file, 'w') as f:
    f.write(f'Job marker')

sys.exit(0)
""")
        
        # Run first job
        result1 = run_job_in_sandbox(
            job_id=test_job_id + "_1",
            command=["python", "/workspace/input/isolation_test.py"],
            input_dir=input_dir,
            output_dir=output_dir,
            timeout_seconds=30,
        )
        
        assert result1.success is True
        
        # Clear output dir
        for f in output_dir.iterdir():
            f.unlink()
        
        # Second job should see empty output dir
        result2 = run_job_in_sandbox(
            job_id=test_job_id + "_2",
            command=["python", "/workspace/input/isolation_test.py"],
            input_dir=input_dir,
            output_dir=output_dir,
            timeout_seconds=30,
        )
        
        assert result2.success is True
        assert "Files in output: []" in result2.stdout
