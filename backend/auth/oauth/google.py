"""
SOAC Google OAuth
=================

Google OAuth provider implementation.
"""

import os
from typing import Optional
import httpx

from .provider_base import OAuthProvider, OAuthUserInfo


# Configuration (use environment variables)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


class GoogleProvider(OAuthProvider):
    """Google OAuth provider."""
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self.client_id = client_id or GOOGLE_CLIENT_ID
        self.client_secret = client_secret or GOOGLE_CLIENT_SECRET
    
    @property
    def name(self) -> str:
        return "google"
    
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Get Google OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{GOOGLE_AUTHORIZE_URL}?{query}"
    
    async def exchange_code(self, code: str, redirect_uri: str) -> str:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            
            data = response.json()
            
            if "error" in data:
                raise ValueError(data.get("error_description", data["error"]))
            
            return data["access_token"]
    
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user info from Google API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            data = response.json()
            
            return OAuthUserInfo(
                provider_id=data["id"],
                email=data.get("email", f"{data['id']}@google.local"),
                display_name=data.get("name"),
                avatar_url=data.get("picture"),
                email_verified=data.get("verified_email", False),
            )


# Singleton
_google_provider: Optional[GoogleProvider] = None


def get_google_provider() -> GoogleProvider:
    """Get Google provider instance."""
    global _google_provider
    if _google_provider is None:
        _google_provider = GoogleProvider()
    return _google_provider
