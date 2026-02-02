from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase


@dataclass(frozen=True)
class AuditEvent:
    action: str
    user_id: Optional[str]
    metadata: Dict[str, Any]


class AuditLogger:
    def __init__(self, db: Optional[AsyncIOMotorDatabase]) -> None:
        self._db = db

    async def ensure_indexes(self) -> None:
        if self._db is None:
            return
        await self._db["audit_events"].create_index([("ts", -1)])
        await self._db["audit_events"].create_index([("user_id", 1), ("ts", -1)])
        await self._db["audit_events"].create_index([("action", 1), ("ts", -1)])

    async def log(self, request: Request, event: AuditEvent) -> None:
        if self._db is None:
            return
        doc: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc),
            "action": event.action,
            "user_id": event.user_id,
            "path": request.url.path,
            "method": request.method,
            "ip": getattr(request.client, "host", None),
            "user_agent": request.headers.get("user-agent"),
            "metadata": event.metadata or {},
        }
        try:
            await self._db["audit_events"].insert_one(doc)
        except Exception:
            return
