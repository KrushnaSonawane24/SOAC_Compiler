"""
SOAC Auth Router
================

Authentication endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from typing import Optional

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


router = APIRouter(prefix="/auth", tags=["auth"])


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
        
        return TokenResponse(
            access_token=token,
            user_id=user.user_id,
            email=user.email,
        )
    
    except UserExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "Email already registered", "error_code": "USER_EXISTS"},
        )


@router.post("/login", response_model=TokenResponse)
async def login(
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
        
        return TokenResponse(
            access_token=token,
            user_id=user.user_id,
            email=user.email,
        )
    
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid email or password", "error_code": "INVALID_CREDENTIALS"},
        )


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
    redirect_uri: Optional[str] = Query(None),
):
    """
    Start GitHub OAuth flow.
    
    Redirects to GitHub authorization page.
    """
    provider = get_github_provider()
    state = generate_oauth_state()
    
    # Use provided redirect URI or construct from request
    callback_uri = redirect_uri or str(request.url_for("github_callback"))
    
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
        callback_uri = str(request.url_for("github_callback"))
        
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
        
        # Return token (frontend will capture this)
        return TokenResponse(
            access_token=token,
            user_id=user.user_id,
            email=user.email,
        )
    
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
    redirect_uri: Optional[str] = Query(None),
):
    """
    Start Google OAuth flow.
    
    Redirects to Google authorization page.
    """
    provider = get_google_provider()
    state = generate_oauth_state()
    
    callback_uri = redirect_uri or str(request.url_for("google_callback"))
    
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
        callback_uri = str(request.url_for("google_callback"))
        
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
        
        return TokenResponse(
            access_token=token,
            user_id=user.user_id,
            email=user.email,
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e), "error_code": "OAUTH_FAILED"},
        )
