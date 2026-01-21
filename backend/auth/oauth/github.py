"""
SOAC GitHub OAuth
=================

GitHub OAuth provider implementation.
"""

import os
from typing import Optional
import httpx

from .provider_base import OAuthProvider, OAuthUserInfo


# Configuration (use environment variables)
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


class GitHubProvider(OAuthProvider):
    """GitHub OAuth provider."""
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self.client_id = client_id or GITHUB_CLIENT_ID
        self.client_secret = client_secret or GITHUB_CLIENT_SECRET
    
    @property
    def name(self) -> str:
        return "github"
    
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Get GitHub OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "user:email",
            "state": state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{GITHUB_AUTHORIZE_URL}?{query}"
    
    async def exchange_code(self, code: str, redirect_uri: str) -> str:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            
            data = response.json()
            
            if "error" in data:
                raise ValueError(data.get("error_description", data["error"]))
            
            return data["access_token"]
    
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user info from GitHub API."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        async with httpx.AsyncClient() as client:
            # Get user profile
            user_response = await client.get(GITHUB_USER_URL, headers=headers)
            user_data = user_response.json()
            
            # Get user emails
            email_response = await client.get(GITHUB_EMAILS_URL, headers=headers)
            emails = email_response.json()
            
            # Find primary email
            email = None
            email_verified = False
            for e in emails:
                if e.get("primary"):
                    email = e.get("email")
                    email_verified = e.get("verified", False)
                    break
            
            if not email:
                email = user_data.get("email") or f"{user_data['id']}@github.local"
            
            return OAuthUserInfo(
                provider_id=str(user_data["id"]),
                email=email,
                display_name=user_data.get("name") or user_data.get("login"),
                avatar_url=user_data.get("avatar_url"),
                email_verified=email_verified,
            )


# Singleton
_github_provider: Optional[GitHubProvider] = None


def get_github_provider() -> GitHubProvider:
    """Get GitHub provider instance."""
    global _github_provider
    if _github_provider is None:
        _github_provider = GitHubProvider()
    return _github_provider
