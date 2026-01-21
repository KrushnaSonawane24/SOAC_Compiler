"""SOAC OAuth Providers Package."""

from .provider_base import OAuthProvider, OAuthUserInfo, generate_oauth_state, verify_oauth_state
from .github import GitHubProvider, get_github_provider
from .google import GoogleProvider, get_google_provider

__all__ = [
    "OAuthProvider",
    "OAuthUserInfo",
    "generate_oauth_state",
    "verify_oauth_state",
    "GitHubProvider",
    "get_github_provider",
    "GoogleProvider",
    "get_google_provider",
]
