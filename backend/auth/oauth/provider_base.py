"""
SOAC OAuth Provider Base
========================

Abstract base for OAuth providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import secrets
import time


@dataclass
class OAuthUserInfo:
    """User info from OAuth provider."""
    provider_id: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    email_verified: bool = False


class OAuthProvider(ABC):
    """Abstract OAuth provider."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
    
    @abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Get OAuth authorization URL."""
        pass
    
    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> str:
        """Exchange auth code for access token."""
        pass
    
    @abstractmethod
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user info from provider."""
        pass


# State management (in-memory for simplicity)
_oauth_states: dict[str, float] = {}
STATE_EXPIRY_SECONDS = 600  # 10 minutes


def generate_oauth_state() -> str:
    """Generate secure OAuth state parameter."""
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = time.time()
    return state


def verify_oauth_state(state: str) -> bool:
    """Verify OAuth state parameter."""
    if state not in _oauth_states:
        return False
    
    created_at = _oauth_states.pop(state)
    
    if time.time() - created_at > STATE_EXPIRY_SECONDS:
        return False
    
    return True
