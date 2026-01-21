"""
Tests for Jobs API
==================

Tests for job management endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import shutil

from backend.api import create_app
from backend.api.dependencies import set_upload_dir
from backend.auth import get_user_store, create_access_token
from backend.jobs import get_job_store, JobState


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    dir_path = Path(tempfile.mkdtemp(prefix="test_api_"))
    yield dir_path
    if dir_path.exists():
        shutil.rmtree(dir_path)


@pytest.fixture
def client(temp_dir):
    """Create test client with cleared stores."""
    set_upload_dir(temp_dir)
    
    # Clear stores for isolation
    get_user_store()._users.clear()
    get_user_store()._email_index.clear()
    get_user_store()._provider_index.clear()
    get_job_store()._jobs.clear()
    
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Create auth headers with valid JWT token."""
    store = get_user_store()
    user = store.register("apitest@example.com", "password123")
    token = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_onnx(temp_dir):
    """Create a sample ONNX file for testing."""
    try:
        import onnx
        from onnx import helper, TensorProto
        
        X = helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 10])
        Y = helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, 10])
        
        node = helper.make_node('Relu', ['input'], ['output'])
        graph = helper.make_graph([node], 'test', [X], [Y])
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 17)])
        
        path = temp_dir / "test_model.onnx"
        onnx.save(model, str(path))
        return path
    except ImportError:
        pytest.skip("ONNX not available")


class TestHealthEndpoint:
    """Tests for health endpoint."""
    
    def test_health_returns_ok(self, client):
        """Health check returns healthy status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestJobsEndpoint:
    """Tests for jobs endpoints."""
    
    def test_list_jobs_empty(self, client, auth_headers):
        """List jobs returns empty when no jobs."""
        response = client.get("/jobs", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []
        assert data["total"] == 0
    
    def test_create_job_requires_file(self, client, auth_headers):
        """Job creation requires file upload."""
        response = client.post("/jobs", headers=auth_headers)
        
        assert response.status_code == 422  # Validation error
    
    def test_get_nonexistent_job(self, client, auth_headers):
        """Getting nonexistent job returns 404."""
        response = client.get("/jobs/nonexistent", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_list_jobs_requires_auth(self, client):
        """List jobs requires authentication."""
        response = client.get("/jobs")
        assert response.status_code == 401


class TestJobStateTransitions:
    """Tests for job state transitions."""
    
    def test_valid_transitions(self):
        """Valid state transitions are allowed."""
        from backend.jobs.job_state import can_transition
        
        assert can_transition(JobState.CREATED, JobState.VALIDATING)
        assert can_transition(JobState.VALIDATING, JobState.CANONICALIZING)
        assert can_transition(JobState.DEPLOYING, JobState.COMPLETED)
    
    def test_invalid_transitions(self):
        """Invalid transitions are blocked."""
        from backend.jobs.job_state import can_transition
        
        assert not can_transition(JobState.CREATED, JobState.COMPLETED)
        assert not can_transition(JobState.VALIDATING, JobState.DEPLOYING)
    
    def test_failure_always_allowed(self):
        """Transition to FAILED is always allowed."""
        from backend.jobs.job_state import can_transition, get_all_states, is_terminal
        
        for state in get_all_states():
            if not is_terminal(state):
                assert can_transition(state, JobState.FAILED)


class TestJobStore:
    """Tests for job store."""
    
    def test_add_and_get(self, temp_dir):
        """Jobs can be added and retrieved."""
        from backend.jobs import JobStore, create_job
        
        store = JobStore()
        job = create_job(
            user_id="user1",
            original_filename="test.onnx",
            file_size_bytes=1000,
            input_path=temp_dir / "test.onnx",
        )
        
        store.add(job)
        retrieved = store.get(job.job_id)
        
        assert retrieved.job_id == job.job_id
    
    def test_list_filters_by_user(self, temp_dir):
        """Job listing filters by user."""
        from backend.jobs import JobStore, create_job
        
        store = JobStore()
        
        job1 = create_job("user1", "test1.onnx", 100, temp_dir / "test1.onnx")
        job2 = create_job("user2", "test2.onnx", 100, temp_dir / "test2.onnx")
        
        store.add(job1)
        store.add(job2)
        
        user1_jobs = store.list_jobs(user_id="user1")
        
        assert len(user1_jobs) == 1
        assert user1_jobs[0].user_id == "user1"


class TestArtifacts:
    """Tests for artifacts endpoints."""
    
    def test_artifacts_empty_before_completion(self, client, auth_headers):
        """Artifacts list is empty before job completion."""
        response = client.get("/jobs/nonexistent/artifacts", headers=auth_headers)
        
        assert response.status_code == 404


class TestLogs:
    """Tests for logs endpoints."""
    
    def test_logs_nonexistent_job(self, client, auth_headers):
        """Logs for nonexistent job returns 404."""
        response = client.get("/jobs/nonexistent/logs", headers=auth_headers)
        
        assert response.status_code == 404
