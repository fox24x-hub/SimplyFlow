from sqlalchemy import String, Text, ForeignKey, Numeric, Integer, Boolean, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date
from decimal import Decimal

from app.core.database import Base
from app.core.enums import RequestStatus


class SupplyRequest(Base):
    """
    Заявка на материалы от мастера.
    Главная сущность SimplyFlow — всё вращается вокруг неё.

    Жизненный цикл:
    draft → submitted → sent_to_supplier → invoice_received
    → invoice_approved → confirmed → delivery_scheduled
    → delivered → completed
    """
    __tablename__ = "supply_requests"

    id:         Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(index=True, nullable=False)

    # Номер заявки — человекочитаемый (например SF-2026-001)
    request_number: Mapped[str|None] = mapped_column(String(50), unique=True, nullable=True)

    # Привязка к объекту
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id"), nullable=False, index=True)

    # Статус
    status: Mapped[RequestStatus] = mapped_column(
        nullable=False, default=RequestStatus.draft, index=True
    )

    # Люди
    created_by_id:  Mapped[int]      = mapped_column(ForeignKey("users.id"), nullable=False)
    manager_id:     Mapped[int|None] = mapped_column(ForeignKey("users.id"), nullable=True)
    supervisor_id:  Mapped[int|None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Описание задачи (что делает мастер на объекте)
    task_description: Mapped[str|None] = mapped_column(Text, nullable=True)
    notes:            Mapped[str|None] = mapped_column(Text, nullable=True)

    # Приоритет: low / medium / high
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)

    # Сроки
    required_by:    Mapped[date|None] = mapped_column(Date, nullable=True)  # нужно к дате
    delivery_date:  Mapped[date|None] = mapped_column(Date, nullable=True)  # дата доставки
    delivery_time:  Mapped[str|None]  = mapped_column(String(50), nullable=True)  # время доставки

    # Данные водителя (для пропуска на объект)
    driver_name:    Mapped[str|None] = mapped_column(String(255), nullable=True)
    vehicle_number: Mapped[str|None] = mapped_column(String(50),  nullable=True)
    vehicle_model:  Mapped[str|None] = mapped_column(String(100), nullable=True)

    # Финансы
    total_amount: Mapped[Decimal|None] = mapped_column(Numeric(12, 2), nullable=True)

    # AI-контекст для агентов (Phase 2)
    ai_context_snapshot: Mapped[str|None] = mapped_column(Text, nullable=True)

    # Relationships
    object:     Mapped["Object"]      = relationship("Object",  back_populates="requests")                    # noqa: F821
    created_by: Mapped["User"]        = relationship("User", foreign_keys=[created_by_id])                    # noqa: F821
    manager:    Mapped["User|None"]   = relationship("User", foreign_keys=[manager_id])                       # noqa: F821
    supervisor: Mapped["User|None"]   = relationship("User", foreign_keys=[supervisor_id])                    # noqa: F821
    items:      Mapped[list["SupplyRequestItem"]]   = relationship("SupplyRequestItem",  back_populates="request", cascade="all, delete-orphan")   # noqa: F821
    orders:     Mapped[list["SupplierOrder"]]       = relationship("SupplierOrder",      back_populates="request", cascade="all, delete-orphan")   # noqa: F821
    comments:   Mapped[list["RequestComment"]]      = relationship("RequestComment",     back_populates="request", cascade="all, delete-orphan")   # noqa: F821
    event_logs: Mapped[list["EventLog"]]            = relationship("EventLog",           back_populates="request")                                 # noqa: F821

    def __repr__(self) -> str:
        return f"<SupplyRequest id={self.id} number={self.request_number} status={self.status}>"


class SupplyRequestItem(Base):
    """Позиция в заявке — конкретный материал с количеством."""

    __tablename__ = "supply_request_items"

    id:         Mapped[int] = mapped_column(primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("supply_requests.id"), nullable=False, index=True)

    # Товар
    name:      Mapped[str]          = mapped_column(String(500),    nullable=False)
    unit:      Mapped[str|None]     = mapped_column(String(50),     nullable=True)   # шт, м², кг, пог.м
    quantity:  Mapped[Decimal|None] = mapped_column(Numeric(10, 3), nullable=True)
    unit_price:Mapped[Decimal|None] = mapped_column(Numeric(12, 2), nullable=True)
    total_price:Mapped[Decimal|None]= mapped_column(Numeric(12, 2), nullable=True)

    notes: Mapped[str|None] = mapped_column(Text, nullable=True)

    # Relationship
    request: Mapped["SupplyRequest"] = relationship("SupplyRequest", back_populates="items")  # noqa: F821

    def __repr__(self) -> str:
        return f"<SupplyRequestItem id={self.id} name={self.name[:40]!r}>"