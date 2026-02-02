from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from .dependencies import get_current_user


router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEventResponse(BaseModel):
    ts: datetime
    action: str
    user_id: Optional[str] = None
    path: str
    method: str
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any]


class AuditListResponse(BaseModel):
    events: List[AuditEventResponse]


@router.get("/events", response_model=AuditListResponse)
async def list_my_events(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    user_id: str = Depends(get_current_user),
):
    db = getattr(request.app.state, "mongo_db", None)
    if db is None:
        return AuditListResponse(events=[])
    cursor = db["audit_events"].find({"user_id": user_id}).sort("ts", -1).limit(limit)
    events: List[AuditEventResponse] = []
    async for doc in cursor:
        events.append(
            AuditEventResponse(
                ts=doc.get("ts"),
                action=doc.get("action"),
                user_id=doc.get("user_id"),
                path=doc.get("path") or "",
                method=doc.get("method") or "",
                ip=doc.get("ip"),
                user_agent=doc.get("user_agent"),
                metadata=doc.get("metadata") or {},
            )
        )
    return AuditListResponse(events=events)
