"""
SOAC User Store
===============

In-memory user storage (production: replace with database).
"""

from __future__ import annotations

from typing import Dict, Optional, Protocol
from threading import Lock

from fastapi import Request

from .models import User, AuthProvider, create_user
from .password import hash_password, verify_password
from .exceptions import UserExistsError, UserNotFoundError, InvalidCredentialsError
from .mongo_user_store import MongoUserStore, normalize_email


class InMemoryUserStore:
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._email_index: Dict[str, str] = {}  # email -> user_id
        self._provider_index: Dict[str, str] = {}  # provider:provider_id -> user_id
        self._lock = Lock()
    
    def add(self, user: User) -> None:
        """Add a new user."""
        with self._lock:
            email_lower = normalize_email(user.email)
            if email_lower in self._email_index:
                raise UserExistsError(email_lower)
            
            self._users[user.user_id] = user
            self._email_index[email_lower] = user.user_id
            
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
            user_id = self._email_index.get(normalize_email(email))
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
            return normalize_email(email) in self._email_index
    
    def register(
        self,
        email: str,
        password: str,
        display_name: Optional[str] = None,
    ) -> User:
        """Register a new local user."""
        with self._lock:
            email_lower = normalize_email(email)
            if email_lower in self._email_index:
                raise UserExistsError(email_lower)
            
            user = create_user(
                email=email_lower,
                password_hash=hash_password(password),
                provider=AuthProvider.LOCAL,
                display_name=display_name,
            )
            
            self._users[user.user_id] = user
            self._email_index[email_lower] = user.user_id
            
            return user
    
    def authenticate(self, email: str, password: str) -> User:
        """Authenticate with email and password."""
        with self._lock:
            user_id = self._email_index.get(normalize_email(email))
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
            email_lower = normalize_email(email)
            user_id = self._email_index.get(email_lower)
            if user_id:
                # Link provider to existing user
                user = self._users[user_id]
                user.provider_id = provider_id
                self._provider_index[key] = user_id
                return user
            
            # Create new user
            user = create_user(
                email=email_lower,
                provider=provider,
                provider_id=provider_id,
                display_name=display_name,
                avatar_url=avatar_url,
                email_verified=True,  # OAuth emails are verified
            )
            
            self._users[user.user_id] = user
            self._email_index[email_lower] = user.user_id
            self._provider_index[key] = user.user_id
            
            return user


class AsyncUserStore(Protocol):
    async def add(self, user: User) -> None: ...
    async def get(self, user_id: str) -> User: ...
    async def get_by_email(self, email: str) -> Optional[User]: ...
    async def get_by_provider(self, provider: AuthProvider, provider_id: str) -> Optional[User]: ...
    async def exists_email(self, email: str) -> bool: ...
    async def register(self, email: str, password: str, display_name: Optional[str] = None) -> User: ...
    async def authenticate(self, email: str, password: str) -> User: ...
    async def find_or_create_oauth_user(
        self,
        provider: AuthProvider,
        provider_id: str,
        email: str,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> User: ...


class AsyncInMemoryUserStore:
    def __init__(self, store: InMemoryUserStore):
        self._store = store

    async def add(self, user: User) -> None:
        self._store.add(user)

    async def get(self, user_id: str) -> User:
        return self._store.get(user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        return self._store.get_by_email(email)

    async def get_by_provider(self, provider: AuthProvider, provider_id: str) -> Optional[User]:
        return self._store.get_by_provider(provider, provider_id)

    async def exists_email(self, email: str) -> bool:
        return self._store.exists_email(email)

    async def register(self, email: str, password: str, display_name: Optional[str] = None) -> User:
        return self._store.register(email=email, password=password, display_name=display_name)

    async def authenticate(self, email: str, password: str) -> User:
        return self._store.authenticate(email, password)

    async def find_or_create_oauth_user(
        self,
        provider: AuthProvider,
        provider_id: str,
        email: str,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> User:
        return self._store.find_or_create_oauth_user(
            provider=provider,
            provider_id=provider_id,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
        )


# Global singleton (used by tests and as fallback when Mongo is not configured)
_store: Optional[InMemoryUserStore] = None


def get_user_store() -> InMemoryUserStore:
    """Get global user store instance."""
    global _store
    if _store is None:
        _store = InMemoryUserStore()
    return _store


async def get_user_store_dep(request: Request) -> AsyncUserStore:
    db = getattr(request.app.state, "mongo_db", None)
    if db is not None:
        return MongoUserStore(db)
    return AsyncInMemoryUserStore(get_user_store())
