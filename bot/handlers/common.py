from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User

router = Router()


async def get_user_by_telegram(telegram_id: int) -> User | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


@router.message(Command("start"))
async def cmd_start(message: Message):
    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "👋 Привет! Я бот SimplyFlow.\n\n"
            "Для привязки аккаунта введи:\n"
            "/start ваш@email.ru"
        )
        return

    email = args[1].lower().strip()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer(
                f"❌ Пользователь с email {email} не найден.\n"
                "Обратись к администратору."
            )
            return

        user.telegram_id       = message.from_user.id
        user.telegram_username = message.from_user.username
        await db.commit()

    role_names = {
        "admin":      "Администратор",
        "manager":    "Снабженец",
        "master":     "Мастер",
        "supervisor": "Руководитель проекта",
        "supplier":   "Поставщик",
    }

    await message.answer(
        f"✅ Аккаунт привязан!\n\n"
        f"Привет, {user.full_name}!\n"
        f"Роль: {role_names.get(user.role.value, user.role.value)}\n\n"
        f"/help — список команд"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    user = await get_user_by_telegram(message.from_user.id)
    if not user:
        await message.answer("Сначала привяжи аккаунт: /start ваш@email.ru")
        return

    if user.role.value in ["admin", "manager"]:
        text = (
            "📋 Команды снабженца:\n\n"
            "/requests — активные заявки\n"
            "/request [номер] — детали заявки\n"
            "/suppliers — список поставщиков\n"
        )
    elif user.role.value == "master":
        text = (
            "📋 Команды мастера:\n\n"
            "/my — мои заявки\n"
            "/new — создать заявку\n"
            "/request [номер] — детали заявки\n"
        )
    elif user.role.value == "supervisor":
        text = (
            "📋 Команды РП:\n\n"
            "/requests — все заявки\n"
            "/request [номер] — детали заявки\n"
        )
    else:
        text = "/requests — заявки\n/help — помощь"

    await message.answer(text)