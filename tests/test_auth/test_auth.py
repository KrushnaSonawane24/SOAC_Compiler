"""
Tests for Authentication
========================

Tests for auth endpoints and user isolation.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import shutil

from backend.api import create_app
from backend.auth import get_user_store, create_access_token, verify_token
from backend.auth.models import create_user, AuthProvider
from backend.auth.oauth.provider_base import generate_oauth_state, verify_oauth_state
from backend.jobs import get_job_store


@pytest.fixture
def client():
    """Create test client."""
    # Clear stores
    get_user_store()._users.clear()
    get_user_store()._email_index.clear()
    get_user_store()._provider_index.clear()
    get_job_store()._jobs.clear()
    
    app = create_app()
    return TestClient(app)


@pytest.fixture
def test_user(client):
    """Create a test user (depends on client to ensure stores are cleared first)."""
    store = get_user_store()
    return store.register(
        email="test@example.com",
        password="testpassword123",
        display_name="Test User",
    )


class TestRegistration:
    """Tests for user registration."""
    
    def test_register_success(self, client):
        """Registration creates user and returns token."""
        response = client.post("/auth/register", json={
            "email": "new@example.com",
            "password": "password123",
            "display_name": "New User",
        })
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["email"] == "new@example.com"
    
    def test_register_duplicate_email(self, client, test_user):
        """Registration fails for existing email."""
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "password123",
        })
        
        assert response.status_code == 409
        assert "USER_EXISTS" in str(response.json())


class TestLogin:
    """Tests for user login."""
    
    def test_login_success(self, client, test_user):
        """Login returns valid token."""
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    def test_login_invalid_email(self, client):
        """Login fails for unknown email."""
        response = client.post("/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password123",
        })
        
        assert response.status_code == 401
    
    def test_login_invalid_password(self, client, test_user):
        """Login fails for wrong password."""
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword",
        })
        
        assert response.status_code == 401


class TestCurrentUser:
    """Tests for /auth/me endpoint."""
    
    def test_me_with_token(self, client, test_user):
        """Get current user with valid token."""
        token = create_access_token(test_user)
        
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
    
    def test_me_without_token(self, client):
        """Get current user fails without token."""
        response = client.get("/auth/me")
        
        assert response.status_code == 401


class TestTokenVerification:
    """Tests for JWT tokens."""
    
    def test_valid_token(self, test_user):
        """Valid token is verified."""
        token = create_access_token(test_user)
        payload = verify_token(token)
        
        assert payload.user_id == test_user.user_id
        assert payload.email == test_user.email
    
    def test_expired_token(self, test_user):
        """Expired token is rejected."""
        from datetime import timedelta
        from backend.auth.jwt import create_access_token
        from backend.auth.exceptions import TokenExpiredError
        
        token = create_access_token(test_user, expires_delta=timedelta(seconds=-1))
        
        with pytest.raises(TokenExpiredError):
            verify_token(token)


class TestUserIsolation:
    """Tests for user isolation."""
    
    def test_user_cannot_access_other_user_jobs(self, client):
        """User cannot access another user's job."""
        # Create two users
        store = get_user_store()
        user1 = store.register("user1@example.com", "password1")
        user2 = store.register("user2@example.com", "password2")
        
        # Create job for user1 (we'll simulate this by adding to job store)
        from backend.jobs import create_job, get_job_store
        job = create_job(
            user_id=user1.user_id,
            original_filename="test.onnx",
            file_size_bytes=1000,
            input_path=Path("test.onnx"),
        )
        get_job_store().add(job)
        
        # User2 tries to access user1's job
        token2 = create_access_token(user2)
        response = client.get(
            f"/jobs/{job.job_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        
        # Should be forbidden
        assert response.status_code == 403
    
    def test_user_can_access_own_jobs(self, client):
        """User can access their own job."""
        store = get_user_store()
        user = store.register("owner@example.com", "password")
        
        from backend.jobs import create_job, get_job_store
        job = create_job(
            user_id=user.user_id,
            original_filename="test.onnx",
            file_size_bytes=1000,
            input_path=Path("test.onnx"),
        )
        get_job_store().add(job)
        
        token = create_access_token(user)
        response = client.get(
            f"/jobs/{job.job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200


class TestOAuthState:
    """Tests for OAuth state management."""
    
    def test_state_generation_and_verification(self):
        """OAuth state can be generated and verified."""
        state = generate_oauth_state()
        assert verify_oauth_state(state) == True
    
    def test_state_single_use(self):
        """OAuth state can only be used once."""
        state = generate_oauth_state()
        assert verify_oauth_state(state) == True
        assert verify_oauth_state(state) == False
    
    def test_invalid_state_rejected(self):
        """Invalid state is rejected."""
        assert verify_oauth_state("invalid-state") == False
