from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.enums import UserRole
from app.models.user import User
from app.models.supply_request import SupplyRequest
from bot.handlers.common import get_user_by_telegram

router = Router()


@router.message(Command("my"))
async def cmd_my_requests(message: Message):
    """Мои заявки — для мастера."""
    user = await get_user_by_telegram(message.from_user.id)
    if not user:
        await message.answer("❌ Аккаунт не привязан. Введи /start ваш@email.ru")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SupplyRequest).where(
                SupplyRequest.created_by_id == user.id,
                SupplyRequest.status.notin_(["completed", "cancelled"])
            ).order_by(SupplyRequest.created_at.desc()).limit(10)
        )
        requests = result.scalars().all()

    if not requests:
        await message.answer("📭 У тебя нет активных заявок.\n\n/new — создать новую")
        return

    text = "📋 Мои активные заявки:\n\n"
    for req in requests:
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(req.priority, "⚪")
        text += (
            f"{priority_icon} {req.request_number} — {req.task_description[:40]}\n"
            f"   Статус: {req.status.value}\n\n"
        )
    text += "Подробнее: /request [номер]"
    await message.answer(text)


@router.message(Command("request"))
async def cmd_request_detail(message: Message):
    """Детали заявки."""
    user = await get_user_by_telegram(message.from_user.id)
    if not user:
        await message.answer("❌ Аккаунт не привязан.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Укажи номер: /request SF-2026-001")
        return

    number = args[1].upper()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SupplyRequest).where(
                SupplyRequest.request_number == number,
                SupplyRequest.company_id == user.company_id,
            )
        )
        req = result.scalar_one_or_none()

    if not req:
        await message.answer(f"❌ Заявка {number} не найдена.")
        return

    priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(req.priority, "⚪")

    await message.answer(
        f"📄 Заявка {req.request_number}\n\n"
        f"📌 Задача: {req.task_description}\n"
        f"{priority_icon} Приоритет: {req.priority}\n"
        f"🔄 Статус: {req.status.value}\n"
        f"📅 Нужно к: {req.required_by or '—'}\n"
        f"💰 Сумма: {req.total_amount or '—'} руб\n"
    )