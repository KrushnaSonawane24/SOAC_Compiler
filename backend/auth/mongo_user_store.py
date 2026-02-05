from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from .exceptions import InvalidCredentialsError, UserExistsError, UserNotFoundError
from .models import AuthProvider, User, create_user
from .password import hash_password, verify_password


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_from_doc(doc: dict) -> User:
    provider_raw = doc.get("provider", AuthProvider.LOCAL.value)
    try:
        provider = AuthProvider(provider_raw)
    except Exception:
        provider = AuthProvider.LOCAL

    return User(
        user_id=str(doc.get("_id") or doc.get("user_id")),
        email=str(doc.get("email") or ""),
        created_at=str(doc.get("created_at") or _utc_iso()),
        updated_at=str(doc.get("updated_at") or doc.get("created_at") or _utc_iso()),
        provider=provider,
        provider_id=doc.get("provider_id"),
        password_hash=doc.get("password_hash"),
        display_name=doc.get("display_name"),
        avatar_url=doc.get("avatar_url"),
        is_active=bool(doc.get("is_active", True)),
        email_verified=bool(doc.get("email_verified", False)),
    )


class MongoUserStore:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db
        self._col = db["users"]

    async def ensure_indexes(self) -> None:
        await self._col.create_index("email_lower", unique=True)
        index_name = "provider_1_provider_id_1"
        try:
            async for idx in self._col.list_indexes():
                if idx.get("name") == index_name and not idx.get("partialFilterExpression"):
                    await self._col.drop_index(index_name)
                    break
        except Exception:
            pass

        await self._col.create_index(
            [("provider", 1), ("provider_id", 1)],
            unique=True,
            name=index_name,
            partialFilterExpression={"provider_id": {"$type": "string"}},
        )

    async def get(self, user_id: str) -> User:
        doc = await self._col.find_one({"_id": user_id})
        if not doc:
            raise UserNotFoundError(user_id)
        return _user_from_doc(doc)

    async def get_by_email(self, email: str) -> Optional[User]:
        email_lower = normalize_email(email)
        doc = await self._col.find_one({"email_lower": email_lower})
        return _user_from_doc(doc) if doc else None

    async def exists_email(self, email: str) -> bool:
        email_lower = normalize_email(email)
        doc = await self._col.find_one({"email_lower": email_lower}, {"_id": 1})
        return doc is not None

    async def register(self, email: str, password: str, display_name: Optional[str] = None) -> User:
        email_lower = normalize_email(email)

        user = create_user(
            email=email_lower,
            password_hash=hash_password(password),
            provider=AuthProvider.LOCAL,
            display_name=display_name,
        )

        now = _utc_iso()
        doc: dict = {
            "_id": user.user_id,
            "email": user.email,
            "email_lower": email_lower,
            "created_at": user.created_at,
            "updated_at": now,
            "provider": user.provider.value,
            "password_hash": user.password_hash,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "last_login_at": None,
        }
        if user.provider_id is not None:
            doc["provider_id"] = user.provider_id

        try:
            await self._col.insert_one(doc)
        except DuplicateKeyError:
            raise UserExistsError(email_lower)

        return user

    async def authenticate(self, email: str, password: str) -> User:
        email_lower = normalize_email(email)
        doc = await self._col.find_one({"email_lower": email_lower})
        if not doc:
            raise InvalidCredentialsError()

        password_hash_value = doc.get("password_hash")
        if not password_hash_value or not verify_password(password, password_hash_value):
            raise InvalidCredentialsError()

        now = _utc_iso()
        await self._col.update_one({"_id": doc["_id"]}, {"$set": {"updated_at": now, "last_login_at": now}})
        return _user_from_doc({**doc, "updated_at": now, "last_login_at": now})

    async def find_or_create_oauth_user(
        self,
        provider: AuthProvider,
        provider_id: str,
        email: str,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> User:
        email_lower = normalize_email(email)
        now = _utc_iso()

        existing = await self._col.find_one({"provider": provider.value, "provider_id": provider_id})
        if existing:
            await self._col.update_one({"_id": existing["_id"]}, {"$set": {"updated_at": now, "last_login_at": now}})
            return _user_from_doc({**existing, "updated_at": now, "last_login_at": now})

        by_email = await self._col.find_one({"email_lower": email_lower})
        if by_email:
            await self._col.update_one(
                {"_id": by_email["_id"]},
                {
                    "$set": {
                        "provider": provider.value,
                        "provider_id": provider_id,
                        "display_name": display_name or by_email.get("display_name"),
                        "avatar_url": avatar_url or by_email.get("avatar_url"),
                        "email_verified": True,
                        "updated_at": now,
                        "last_login_at": now,
                    }
                },
            )
            return _user_from_doc(
                {
                    **by_email,
                    "provider": provider.value,
                    "provider_id": provider_id,
                    "display_name": display_name or by_email.get("display_name"),
                    "avatar_url": avatar_url or by_email.get("avatar_url"),
                    "email_verified": True,
                    "updated_at": now,
                    "last_login_at": now,
                }
            )

        user = create_user(
            email=email_lower,
            provider=provider,
            provider_id=provider_id,
            display_name=display_name,
            avatar_url=avatar_url,
            email_verified=True,
        )

        doc = {
            "_id": user.user_id,
            "email": user.email,
            "email_lower": email_lower,
            "created_at": user.created_at,
            "updated_at": now,
            "provider": provider.value,
            "provider_id": provider_id,
            "password_hash": None,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "last_login_at": now,
        }

        try:
            await self._col.insert_one(doc)
        except DuplicateKeyError:
            raise UserExistsError(email_lower)

        return user


async def ensure_auth_indexes(db: Optional[AsyncIOMotorDatabase]) -> None:
    if db is None:
        return
    await MongoUserStore(db).ensure_indexes()
