"""
Pytest Fixtures for Sandbox Tests
=================================

Shared fixtures for Docker testing.

NOTE: These tests require Docker to be running.
Tests will be skipped if Docker is unavailable.
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Generator
import pytest

# Check if Docker is available
try:
    import docker
    _client = docker.from_env()
    _client.ping()
    DOCKER_AVAILABLE = True
except Exception:
    DOCKER_AVAILABLE = False

# Skip all tests in this module if Docker unavailable
pytestmark = pytest.mark.skipif(
    not DOCKER_AVAILABLE,
    reason="Docker is not available"
)


@pytest.fixture(scope="session")
def docker_client():
    """Get Docker client for the test session."""
    if not DOCKER_AVAILABLE:
        pytest.skip("Docker not available")
    
    import docker
    return docker.from_env()


@pytest.fixture(scope="session")
def ensure_test_image(docker_client):
    """Ensure test image is available."""
    image = "python:3.11-slim"
    try:
        docker_client.images.get(image)
    except Exception:
        pytest.skip(f"Image {image} not available and cannot pull")
    return image


@pytest.fixture
def temp_job_dirs() -> Generator[tuple[Path, Path], None, None]:
    """Create temporary input and output directories for a job."""
    base_dir = Path(tempfile.mkdtemp(prefix="test_sandbox_"))
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"
    
    input_dir.mkdir()
    output_dir.mkdir()
    
    yield input_dir, output_dir
    
    # Cleanup
    if base_dir.exists():
        shutil.rmtree(base_dir)


@pytest.fixture
def test_job_id() -> str:
    """Generate a unique test job ID."""
    import uuid
    return f"test_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def simple_script_file(temp_job_dirs: tuple[Path, Path]) -> Path:
    """Create a simple Python script for testing."""
    input_dir, _ = temp_job_dirs
    script = input_dir / "test_script.py"
    script.write_text("""
import sys
print("Hello from container!")
print("Args:", sys.argv[1:])
sys.exit(0)
""")
    return script


@pytest.fixture
def write_output_script(temp_job_dirs: tuple[Path, Path]) -> Path:
    """Create a script that writes to output directory."""
    input_dir, _ = temp_job_dirs
    script = input_dir / "write_output.py"
    script.write_text("""
import sys
output_path = "/workspace/output/result.txt"
with open(output_path, 'w') as f:
    f.write("Output from container")
print(f"Wrote to {output_path}")
""")
    return script


@pytest.fixture
def network_test_script(temp_job_dirs: tuple[Path, Path]) -> Path:
    """Create a script that attempts network access."""
    input_dir, _ = temp_job_dirs
    script = input_dir / "network_test.py"
    script.write_text("""
import socket
import sys

try:
    # Try to connect to Google DNS
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect(('8.8.8.8', 53))
    print("ERROR: Network access succeeded!")
    sys.exit(1)
except (socket.error, socket.timeout, OSError) as e:
    print(f"Network blocked as expected: {e}")
    sys.exit(0)
""")
    return script


@pytest.fixture
def filesystem_escape_script(temp_job_dirs: tuple[Path, Path]) -> Path:
    """Create a script that attempts to write outside workspace."""
    input_dir, _ = temp_job_dirs
    script = input_dir / "escape_test.py"
    script.write_text("""
import sys

paths_to_try = [
    '/etc/test_escape.txt',
    '/root/test_escape.txt',
    '/home/test_escape.txt',
    '/var/test_escape.txt',
]

for path in paths_to_try:
    try:
        with open(path, 'w') as f:
            f.write('escaped!')
        print(f"ERROR: Could write to {path}")
        sys.exit(1)
    except (PermissionError, OSError, IOError) as e:
        print(f"Blocked write to {path}: {e}")

print("All escape attempts blocked!")
sys.exit(0)
""")
    return script


@pytest.fixture
def infinite_loop_script(temp_job_dirs: tuple[Path, Path]) -> Path:
    """Create a script with infinite loop for timeout testing."""
    input_dir, _ = temp_job_dirs
    script = input_dir / "infinite.py"
    script.write_text("""
import time
while True:
    time.sleep(1)
""")
    return script


@pytest.fixture
def failing_script(temp_job_dirs: tuple[Path, Path]) -> Path:
    """Create a script that fails."""
    input_dir, _ = temp_job_dirs
    script = input_dir / "fail.py"
    script.write_text("""
import sys
print("About to fail!", file=sys.stderr)
sys.exit(42)
""")
    return script
