from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Supplier(Base):
    """
    Поставщик материалов.
    Например: Строительный Двор, Урал Интерьер, Профи Браж.
    """
    __tablename__ = "suppliers"

    id:         Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(index=True, nullable=False)

    name:        Mapped[str]      = mapped_column(String(255), nullable=False, index=True)
    phone:       Mapped[str|None] = mapped_column(String(20),  nullable=True)
    email:       Mapped[str|None] = mapped_column(String(255), nullable=True)
    address:     Mapped[str|None] = mapped_column(String(500), nullable=True)
    description: Mapped[str|None] = mapped_column(Text,        nullable=True)

    # Telegram для уведомлений поставщику
    telegram_id:       Mapped[int|None] = mapped_column(nullable=True)
    telegram_username: Mapped[str|None] = mapped_column(String(64), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Supplier id={self.id} name={self.name!r}>"