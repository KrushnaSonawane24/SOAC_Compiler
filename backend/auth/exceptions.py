"""
SOAC Auth Exceptions
====================

Authentication and authorization errors.
"""

from typing import Optional


class AuthError(Exception):
    """Base authentication error."""
    
    def __init__(self, message: str, error_code: str):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


class InvalidCredentialsError(AuthError):
    """Invalid email or password."""
    
    def __init__(self):
        super().__init__(
            "Invalid email or password",
            error_code="INVALID_CREDENTIALS",
        )


class UserExistsError(AuthError):
    """User with email already exists."""
    
    def __init__(self, email: str):
        super().__init__(
            f"User with email already exists",
            error_code="USER_EXISTS",
        )


class UserNotFoundError(AuthError):
    """User not found."""
    
    def __init__(self, identifier: str):
        super().__init__(
            f"User not found",
            error_code="USER_NOT_FOUND",
        )


class InvalidTokenError(AuthError):
    """JWT token is invalid or expired."""
    
    def __init__(self, reason: str = "Invalid token"):
        super().__init__(
            reason,
            error_code="INVALID_TOKEN",
        )


class TokenExpiredError(AuthError):
    """JWT token has expired."""
    
    def __init__(self):
        super().__init__(
            "Token has expired",
            error_code="TOKEN_EXPIRED",
        )


class OAuthError(AuthError):
    """OAuth authentication failed."""
    
    def __init__(self, provider: str, reason: str):
        super().__init__(
            f"{provider} authentication failed: {reason}",
            error_code="OAUTH_FAILED",
        )


class InvalidStateError(AuthError):
    """OAuth state parameter invalid."""
    
    def __init__(self):
        super().__init__(
            "Invalid OAuth state parameter",
            error_code="INVALID_STATE",
        )


class UnauthorizedError(AuthError):
    """User not authorized."""
    
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            message,
            error_code="UNAUTHORIZED",
        )
