"""
SOAC Auth Models
================

User models for authentication.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
import uuid


class AuthProvider(str, Enum):
    """Authentication provider."""
    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"


@dataclass
class User:
    """
    SOAC user record.
    
    NOTE: Internal IDs are UUIDs, never exposed directly.
    """
    user_id: str
    email: str
    created_at: str
    updated_at: str
    
    # Auth info
    provider: AuthProvider = AuthProvider.LOCAL
    provider_id: Optional[str] = None  # External provider user ID
    
    # Local auth (hashed)
    password_hash: Optional[str] = None
    
    # Profile
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Status
    is_active: bool = True
    email_verified: bool = False
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to API-safe dict."""
        result = {
            "user_id": self.user_id,
            "email": self.email,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "provider": self.provider.value,
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "created_at": self.created_at,
        }
        return result


@dataclass
class TokenPayload:
    """JWT token payload."""
    user_id: str
    email: str
    exp: int
    iat: int
    provider: str = "local"


def create_user(
    email: str,
    password_hash: Optional[str] = None,
    provider: AuthProvider = AuthProvider.LOCAL,
    provider_id: Optional[str] = None,
    display_name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    email_verified: bool = False,
) -> User:
    """Create a new user."""
    now = datetime.now(timezone.utc).isoformat()
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    
    return User(
        user_id=user_id,
        email=email,
        created_at=now,
        updated_at=now,
        provider=provider,
        provider_id=provider_id,
        password_hash=password_hash,
        display_name=display_name or email.split("@")[0],
        avatar_url=avatar_url,
        email_verified=email_verified,
    )
