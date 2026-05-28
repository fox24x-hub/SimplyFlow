from sqlalchemy import String, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Any

from app.core.database import Base
from app.core.enums import EventActionType, EventSource


class EventLog(Base):
    """Иммутабельный лог всех действий в системе."""

    __tablename__ = "event_log"

    id:         Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(index=True, nullable=False)

    user_id:     Mapped[int|None] = mapped_column(ForeignKey("users.id"),            nullable=True)
    request_id:  Mapped[int|None] = mapped_column(ForeignKey("supply_requests.id"),  nullable=True, index=True)

    action_type:  Mapped[EventActionType] = mapped_column(nullable=False, index=True)
    payload:      Mapped[dict[str, Any]]  = mapped_column(JSON, nullable=False, default=dict)
    description:  Mapped[str|None]        = mapped_column(Text, nullable=True)
    event_source: Mapped[EventSource]     = mapped_column(nullable=False, default=EventSource.api)

    # Relationships
    user:    Mapped["User|None"]           = relationship("User")             # noqa: F821
    request: Mapped["SupplyRequest|None"]  = relationship("SupplyRequest", back_populates="event_logs")  # noqa: F821


class RequestComment(Base):
    """Комментарии к заявке на всех этапах."""

    __tablename__ = "request_comments"

    id:         Mapped[int] = mapped_column(primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("supply_requests.id"), nullable=False, index=True)
    user_id:    Mapped[int] = mapped_column(ForeignKey("users.id"),            nullable=False)

    text:         Mapped[str|None] = mapped_column(Text,        nullable=True)
    photo_urls:   Mapped[str|None] = mapped_column(Text,        nullable=True)
    comment_type: Mapped[str]      = mapped_column(String(20),  default="internal", nullable=False)

    request: Mapped["SupplyRequest"] = relationship("SupplyRequest", back_populates="comments")  # noqa: F821
    user:    Mapped["User"]          = relationship("User")                                        # noqa: F821