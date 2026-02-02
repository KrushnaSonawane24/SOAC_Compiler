"""
SOAC Auth Router
================

Authentication endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
from urllib.parse import quote, urlparse

from .models import User, AuthProvider
from .password import hash_password
from .jwt import create_access_token
from .user_store import UserStore, get_user_store
from .exceptions import (
    InvalidCredentialsError,
    UserExistsError,
    InvalidStateError,
    OAuthError,
)
from .dependencies import get_current_user
from .oauth import (
    get_github_provider,
    get_google_provider,
    generate_oauth_state,
    verify_oauth_state,
)
from backend.audit import AuditEvent


router = APIRouter(prefix="/auth", tags=["auth"])


def _public_callback_uri(request: Request, endpoint_name: str) -> str:
    public_api = os.getenv("SOAC_PUBLIC_API_URL", "").rstrip("/")
    if public_api:
        path = urlparse(str(request.url_for(endpoint_name))).path
        return f"{public_api}{path}"
    return str(request.url_for(endpoint_name))


def _frontend_success_redirect(token: str) -> str:
    frontend = os.getenv("SOAC_FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return f"{frontend}/dashboard?token={quote(token)}"


# ============================================================================
# SCHEMAS
# ============================================================================

class RegisterRequest(BaseModel):
    """Registration request."""
    email: EmailStr
    password: str
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class UserResponse(BaseModel):
    """User info response."""
    user_id: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: str
    email_verified: bool


class OAuthLoginResponse(BaseModel):
    """OAuth login redirect URL."""
    authorization_url: str


# ============================================================================
# LOCAL AUTH ENDPOINTS
# ============================================================================

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    http_request: Request,
    request: RegisterRequest,
    store: UserStore = Depends(get_user_store),
):
    """
    Register a new user.
    
    Creates account and returns JWT token.
    """
    try:
        user = store.register(
            email=request.email,
            password=request.password,
            display_name=request.display_name,
        )
        
        token = create_access_token(user)
        audit_logger = getattr(http_request.app.state, "audit_logger", None)
        if audit_logger is not None:
            await audit_logger.log(
                http_request,
                AuditEvent(
                    action="AUTH_REGISTER",
                    user_id=user.user_id,
                    metadata={"email": user.email, "provider": AuthProvider.LOCAL.value},
                ),
            )
        
        return TokenResponse(
            access_token=token,
            user_id=user.user_id,
            email=user.email,
        )
    
    except UserExistsError:
        audit_logger = getattr(http_request.app.state, "audit_logger", None)
        if audit_logger is not None:
            await audit_logger.log(
                http_request,
                AuditEvent(
                    action="AUTH_REGISTER_FAILED",
                    user_id=None,
                    metadata={"email": request.email, "reason": "USER_EXISTS"},
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "Email already registered", "error_code": "USER_EXISTS"},
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    http_request: Request,
    request: LoginRequest,
    store: UserStore = Depends(get_user_store),
):
    """
    Login with email and password.
    
    Returns JWT token if credentials are valid.
    """
    try:
        user = store.authenticate(request.email, request.password)
        token = create_access_token(user)
        audit_logger = getattr(http_request.app.state, "audit_logger", None)
        if audit_logger is not None:
            await audit_logger.log(
                http_request,
                AuditEvent(
                    action="AUTH_LOGIN",
                    user_id=user.user_id,
                    metadata={"email": user.email, "provider": user.provider.value},
                ),
            )
        
        return TokenResponse(
            access_token=token,
            user_id=user.user_id,
            email=user.email,
        )
    
    except InvalidCredentialsError:
        audit_logger = getattr(http_request.app.state, "audit_logger", None)
        if audit_logger is not None:
            await audit_logger.log(
                http_request,
                AuditEvent(
                    action="AUTH_LOGIN_FAILED",
                    user_id=None,
                    metadata={"email": request.email, "reason": "INVALID_CREDENTIALS"},
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid email or password", "error_code": "INVALID_CREDENTIALS"},
        )


@router.post("/logout")
async def logout(
    http_request: Request,
    current_user: User = Depends(get_current_user),
):
    audit_logger = getattr(http_request.app.state, "audit_logger", None)
    if audit_logger is not None:
        await audit_logger.log(
            http_request,
            AuditEvent(
                action="AUTH_LOGOUT",
                user_id=current_user.user_id,
                metadata={"email": current_user.email, "provider": current_user.provider.value},
            ),
        )
    return {"status": "ok"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Get current authenticated user info."""
    return UserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        provider=current_user.provider.value,
        email_verified=current_user.email_verified,
    )


# ============================================================================
# GITHUB OAUTH ENDPOINTS
# ============================================================================

@router.get("/github/login")
async def github_login(
    request: Request,
):
    """
    Start GitHub OAuth flow.
    
    Redirects to GitHub authorization page.
    """
    provider = get_github_provider()
    if not getattr(provider, "client_id", ""):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Missing GITHUB_CLIENT_ID", "error_code": "OAUTH_CONFIG_MISSING"},
        )
    state = generate_oauth_state()

    callback_uri = _public_callback_uri(request, "github_callback")
    auth_url = provider.get_authorization_url(state, callback_uri)
    return RedirectResponse(auth_url)


@router.get("/github/callback")
async def github_callback(
    code: str,
    state: str,
    request: Request,
    store: UserStore = Depends(get_user_store),
):
    """
    GitHub OAuth callback.
    
    Exchanges code for token and creates/finds user.
    """
    # Verify state
    if not verify_oauth_state(state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid state parameter", "error_code": "INVALID_STATE"},
        )
    
    try:
        provider = get_github_provider()
        callback_uri = _public_callback_uri(request, "github_callback")
        
        # Exchange code for token
        access_token = await provider.exchange_code(code, callback_uri)
        
        # Get user info
        user_info = await provider.get_user_info(access_token)
        
        # Find or create user
        user = store.find_or_create_oauth_user(
            provider=AuthProvider.GITHUB,
            provider_id=user_info.provider_id,
            email=user_info.email,
            display_name=user_info.display_name,
            avatar_url=user_info.avatar_url,
        )
        
        # Issue SOAC JWT
        token = create_access_token(user)
        audit_logger = getattr(request.app.state, "audit_logger", None)
        if audit_logger is not None:
            await audit_logger.log(
                request,
                AuditEvent(
                    action="AUTH_OAUTH_LOGIN",
                    user_id=user.user_id,
                    metadata={"email": user.email, "provider": AuthProvider.GITHUB.value},
                ),
            )

        return RedirectResponse(_frontend_success_redirect(token))
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e), "error_code": "OAUTH_FAILED"},
        )


# ============================================================================
# GOOGLE OAUTH ENDPOINTS
# ============================================================================

@router.get("/google/login")
async def google_login(
    request: Request,
):
    """
    Start Google OAuth flow.
    
    Redirects to Google authorization page.
    """
    provider = get_google_provider()
    if not getattr(provider, "client_id", ""):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Missing GOOGLE_CLIENT_ID", "error_code": "OAUTH_CONFIG_MISSING"},
        )
    state = generate_oauth_state()

    callback_uri = _public_callback_uri(request, "google_callback")
    auth_url = provider.get_authorization_url(state, callback_uri)
    return RedirectResponse(auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    request: Request,
    store: UserStore = Depends(get_user_store),
):
    """
    Google OAuth callback.
    
    Exchanges code for token and creates/finds user.
    """
    if not verify_oauth_state(state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid state parameter", "error_code": "INVALID_STATE"},
        )
    
    try:
        provider = get_google_provider()
        callback_uri = _public_callback_uri(request, "google_callback")
        
        access_token = await provider.exchange_code(code, callback_uri)
        user_info = await provider.get_user_info(access_token)
        
        user = store.find_or_create_oauth_user(
            provider=AuthProvider.GOOGLE,
            provider_id=user_info.provider_id,
            email=user_info.email,
            display_name=user_info.display_name,
            avatar_url=user_info.avatar_url,
        )
        
        token = create_access_token(user)
        audit_logger = getattr(request.app.state, "audit_logger", None)
        if audit_logger is not None:
            await audit_logger.log(
                request,
                AuditEvent(
                    action="AUTH_OAUTH_LOGIN",
                    user_id=user.user_id,
                    metadata={"email": user.email, "provider": AuthProvider.GOOGLE.value},
                ),
            )

        return RedirectResponse(_frontend_success_redirect(token))
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e), "error_code": "OAUTH_FAILED"},
        )
