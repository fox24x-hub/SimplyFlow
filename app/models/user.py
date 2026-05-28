from sqlalchemy import String, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id:         Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(index=True, nullable=False)

    # Auth
    email:           Mapped[str]  = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str]  = mapped_column(String(255), nullable=False)
    is_active:       Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Profile
    full_name: Mapped[str]      = mapped_column(String(255), nullable=False)
    phone:     Mapped[str|None] = mapped_column(String(20),  nullable=True)
    role:      Mapped[UserRole] = mapped_column(nullable=False, default=UserRole.master)

    # Telegram
    telegram_id:       Mapped[int|None] = mapped_column(BigInteger, unique=True, nullable=True)
    telegram_username: Mapped[str|None] = mapped_column(String(64),  nullable=True)

    def __repr__(self) -> str:
        return f"<User id={self.id} role={self.role} email={self.email}>"