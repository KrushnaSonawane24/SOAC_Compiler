"""
SOAC Auth Dependencies
======================

FastAPI dependencies for authentication.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from .models import User, TokenPayload
from .jwt import verify_token
from .user_store import get_user_store, UserStore
from .exceptions import InvalidTokenError, TokenExpiredError, UserNotFoundError


# Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_token_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> TokenPayload:
    """
    Extract and verify JWT token.
    
    Returns token payload if valid.
    Raises 401 if missing or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Missing authorization token", "error_code": "MISSING_TOKEN"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        return verify_token(credentials.credentials)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Token has expired", "error_code": "TOKEN_EXPIRED"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": str(e), "error_code": "INVALID_TOKEN"},
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: TokenPayload = Depends(get_token_payload),
    store: UserStore = Depends(get_user_store),
) -> User:
    """
    Get current authenticated user.
    
    Returns User if token is valid and user exists.
    Raises 401 if user not found.
    """
    try:
        return store.get(token.user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "User not found", "error_code": "USER_NOT_FOUND"},
        )


async def get_current_user_id(
    token: TokenPayload = Depends(get_token_payload),
) -> str:
    """Get current user ID from token (fast path, no DB lookup)."""
    return token.user_id


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    store: UserStore = Depends(get_user_store),
) -> Optional[User]:
    """Get user if authenticated, None otherwise."""
    if credentials is None:
        return None
    
    try:
        payload = verify_token(credentials.credentials)
        return store.get(payload.user_id)
    except (InvalidTokenError, TokenExpiredError, UserNotFoundError):
        return None
