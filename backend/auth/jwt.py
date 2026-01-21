"""
SOAC JWT Handling
=================

JWT token creation and verification.
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from jose import jwt, JWTError

from .models import User, TokenPayload
from .exceptions import InvalidTokenError, TokenExpiredError


# Configuration (use environment variables in production)
SECRET_KEY = os.getenv("SOAC_JWT_SECRET", "soac-dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def create_access_token(user: User, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token for user.
    
    Args:
        user: User to create token for.
        expires_delta: Optional custom expiration.
    
    Returns:
        JWT token string.
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    payload = {
        "sub": user.user_id,
        "email": user.email,
        "provider": user.provider.value,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> TokenPayload:
    """
    Verify JWT token and extract payload.
    
    Args:
        token: JWT token string.
    
    Returns:
        TokenPayload with user info.
    
    Raises:
        InvalidTokenError: If token is invalid.
        TokenExpiredError: If token has expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        user_id = payload.get("sub")
        if user_id is None:
            raise InvalidTokenError("Missing user ID in token")
        
        return TokenPayload(
            user_id=user_id,
            email=payload.get("email", ""),
            provider=payload.get("provider", "local"),
            iat=payload.get("iat", 0),
            exp=payload.get("exp", 0),
        )
    
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError as e:
        raise InvalidTokenError(str(e))


def decode_token_unsafe(token: str) -> dict:
    """Decode token without verification (for debugging)."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_signature": False})
    except JWTError:
        return {}
