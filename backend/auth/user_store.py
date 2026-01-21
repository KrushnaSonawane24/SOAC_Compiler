"""
SOAC User Store
===============

In-memory user storage (production: replace with database).
"""

from typing import Dict, Optional
from threading import Lock

from .models import User, AuthProvider, create_user
from .password import hash_password, verify_password
from .exceptions import UserExistsError, UserNotFoundError, InvalidCredentialsError


class UserStore:
    """
    In-memory user store.
    
    Thread-safe for concurrent access.
    """
    
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._email_index: Dict[str, str] = {}  # email -> user_id
        self._provider_index: Dict[str, str] = {}  # provider:provider_id -> user_id
        self._lock = Lock()
    
    def add(self, user: User) -> None:
        """Add a new user."""
        with self._lock:
            if user.email in self._email_index:
                raise UserExistsError(user.email)
            
            self._users[user.user_id] = user
            self._email_index[user.email] = user.user_id
            
            if user.provider_id:
                key = f"{user.provider.value}:{user.provider_id}"
                self._provider_index[key] = user.user_id
    
    def get(self, user_id: str) -> User:
        """Get user by ID."""
        with self._lock:
            if user_id not in self._users:
                raise UserNotFoundError(user_id)
            return self._users[user_id]
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        with self._lock:
            user_id = self._email_index.get(email)
            if user_id:
                return self._users.get(user_id)
            return None
    
    def get_by_provider(self, provider: AuthProvider, provider_id: str) -> Optional[User]:
        """Get user by OAuth provider ID."""
        with self._lock:
            key = f"{provider.value}:{provider_id}"
            user_id = self._provider_index.get(key)
            if user_id:
                return self._users.get(user_id)
            return None
    
    def exists_email(self, email: str) -> bool:
        """Check if email exists."""
        with self._lock:
            return email in self._email_index
    
    def register(
        self,
        email: str,
        password: str,
        display_name: Optional[str] = None,
    ) -> User:
        """Register a new local user."""
        with self._lock:
            if email in self._email_index:
                raise UserExistsError(email)
            
            user = create_user(
                email=email,
                password_hash=hash_password(password),
                provider=AuthProvider.LOCAL,
                display_name=display_name,
            )
            
            self._users[user.user_id] = user
            self._email_index[email] = user.user_id
            
            return user
    
    def authenticate(self, email: str, password: str) -> User:
        """Authenticate with email and password."""
        with self._lock:
            user_id = self._email_index.get(email)
            if not user_id:
                raise InvalidCredentialsError()
            
            user = self._users.get(user_id)
            if not user or not user.password_hash:
                raise InvalidCredentialsError()
            
            if not verify_password(password, user.password_hash):
                raise InvalidCredentialsError()
            
            return user
    
    def find_or_create_oauth_user(
        self,
        provider: AuthProvider,
        provider_id: str,
        email: str,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> User:
        """Find existing OAuth user or create new one."""
        with self._lock:
            # Check by provider ID first
            key = f"{provider.value}:{provider_id}"
            user_id = self._provider_index.get(key)
            if user_id:
                return self._users[user_id]
            
            # Check by email
            user_id = self._email_index.get(email)
            if user_id:
                # Link provider to existing user
                user = self._users[user_id]
                user.provider_id = provider_id
                self._provider_index[key] = user_id
                return user
            
            # Create new user
            user = create_user(
                email=email,
                provider=provider,
                provider_id=provider_id,
                display_name=display_name,
                avatar_url=avatar_url,
                email_verified=True,  # OAuth emails are verified
            )
            
            self._users[user.user_id] = user
            self._email_index[email] = user.user_id
            self._provider_index[key] = user.user_id
            
            return user


# Global singleton
_store: Optional[UserStore] = None


def get_user_store() -> UserStore:
    """Get global user store instance."""
    global _store
    if _store is None:
        _store = UserStore()
    return _store
