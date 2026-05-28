from sqlalchemy import String, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Object(Base):
    """
    Строительный объект — квартира, дом, офис.
    К объекту привязаны все заявки на материалы.
    """
    __tablename__ = "objects"

    id:         Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(index=True, nullable=False)

    # Основное
    name:        Mapped[str]      = mapped_column(String(500), nullable=False)
    address:     Mapped[str]      = mapped_column(String(500), nullable=False)
    description: Mapped[str|None] = mapped_column(Text,        nullable=True)

    # Ответственные
    master_id:     Mapped[int|None] = mapped_column(ForeignKey("users.id"), nullable=True)
    supervisor_id: Mapped[int|None] = mapped_column(ForeignKey("users.id"), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    master:     Mapped["User|None"] = relationship("User", foreign_keys=[master_id])      # noqa: F821
    supervisor: Mapped["User|None"] = relationship("User", foreign_keys=[supervisor_id])  # noqa: F821
    requests:   Mapped[list["SupplyRequest"]] = relationship("SupplyRequest", back_populates="object")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Object id={self.id} name={self.name[:40]!r}>"