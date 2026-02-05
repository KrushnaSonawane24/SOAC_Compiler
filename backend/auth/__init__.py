"""
SOAC Auth Package
=================

Authentication and authorization for SOAC.
"""

from .models import User, AuthProvider, TokenPayload, create_user
from .exceptions import (
    AuthError,
    InvalidCredentialsError,
    UserExistsError,
    UserNotFoundError,
    InvalidTokenError,
    TokenExpiredError,
    OAuthError,
    InvalidStateError,
    UnauthorizedError,
)
from .password import hash_password, verify_password
from .jwt import create_access_token, verify_token
from .user_store import InMemoryUserStore as UserStore, get_user_store
from .dependencies import get_current_user, get_current_user_id, get_optional_user
from .auth_router import router as auth_router

__all__ = [
    # Models
    "User",
    "AuthProvider",
    "TokenPayload",
    "create_user",
    
    # Store
    "UserStore",
    "get_user_store",
    
    # Auth
    "hash_password",
    "verify_password",
    "create_access_token",
    "verify_token",
    
    # Dependencies
    "get_current_user",
    "get_current_user_id",
    "get_optional_user",
    
    # Router
    "auth_router",
    
    # Exceptions
    "AuthError",
    "InvalidCredentialsError",
    "UserExistsError",
    "UserNotFoundError",
    "InvalidTokenError",
    "TokenExpiredError",
    "OAuthError",
    "InvalidStateError",
    "UnauthorizedError",
]
