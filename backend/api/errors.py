"""
SOAC API Errors
===============

HTTP error handling.
"""

from fastapi import HTTPException, status
from typing import Optional


class APIError(HTTPException):
    """Base API error."""
    
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[dict] = None,
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "error": message,
                "error_code": error_code,
                "details": details,
            },
        )


class NotFoundError(APIError):
    """Resource not found."""
    
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            message=f"{resource} not found: {resource_id}",
        )


class UnauthorizedError(APIError):
    """Unauthorized access."""
    
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
            message=message,
        )


class ForbiddenError(APIError):
    """Forbidden access."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
            message=message,
        )


class BadRequestError(APIError):
    """Bad request."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BAD_REQUEST",
            message=message,
            details=details,
        )


class ConflictError(APIError):
    """Resource conflict."""
    
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            message=message,
        )


class InternalError(APIError):
    """Internal server error."""
    
    def __init__(self, message: str = "Internal server error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_ERROR",
            message=message,
        )
