from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from app.models.event_log import EventLog
from app.core.enums import EventActionType, EventSource


class EventLogService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        *,
        company_id:   int,
        action_type:  EventActionType,
        user_id:      int | None = None,
        request_id:   int | None = None,
        payload:      dict[str, Any] | None = None,
        description:  str | None = None,
        event_source: EventSource = EventSource.api,
    ) -> EventLog:
        entry = EventLog(
            company_id=company_id,
            user_id=user_id,
            action_type=action_type,
            request_id=request_id,
            payload=payload or {},
            description=description,
            event_source=event_source,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry