from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.core.enums import UserRole
from app.models.user import User


class AuthService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(
        self,
        email: str,
        password: str,
        full_name: str,
        role: UserRole = UserRole.master,
        phone: str | None = None,
        company_id: int | None = None,
    ) -> User:
        existing = await self.db.execute(
            select(User).where(User.email == email)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Email уже зарегистрирован: {email}")

        user = User(
            company_id=company_id or settings.DEFAULT_COMPANY_ID,
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            phone=phone,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def authenticate(self, email: str, password: str) -> User:
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        dummy = "$2b$12$KIX/rHFMEiXqaFc0yQgGxu6FpR1n1dJTR4X8YyHJYtCqDAFQ5vAiK"
        valid = verify_password(password, user.hashed_password if user else dummy)

        if not user or not valid:
            raise ValueError("Неверный email или пароль")
        if not user.is_active:
            raise ValueError("Аккаунт деактивирован")
        return user

    @staticmethod
    def mint_token(user: User) -> str:
        return create_access_token(
            subject=user.id,
            company_id=user.company_id,
            role=user.role.value,
        )