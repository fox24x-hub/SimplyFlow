from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.supply_request import SupplyRequest
from app.models.supplier import Supplier
from bot.handlers.common import get_user_by_telegram

router = Router()


@router.message(Command("requests"))
async def cmd_all_requests(message: Message):
    """Все активные заявки — для снабженца и РП."""
    user = await get_user_by_telegram(message.from_user.id)
    if not user:
        await message.answer("❌ Аккаунт не привязан. Введи /start ваш@email.ru")
        return

    if user.role.value not in ["admin", "manager", "supervisor"]:
        await message.answer("❌ Нет доступа.")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SupplyRequest).where(
                SupplyRequest.company_id == user.company_id,
                SupplyRequest.status.notin_(["completed", "cancelled"])
            ).order_by(SupplyRequest.created_at.desc()).limit(15)
        )
        requests = result.scalars().all()

    if not requests:
        await message.answer("📭 Активных заявок нет.")
        return

    text = "📋 Активные заявки:\n\n"
    for req in requests:
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(req.priority, "⚪")
        text += (
            f"{priority_icon} {req.request_number}\n"
            f"   {req.task_description[:40]}\n"
            f"   Статус: {req.status.value}\n\n"
        )
    text += "Подробнее: /request [номер]"
    await message.answer(text)


@router.message(Command("suppliers"))
async def cmd_suppliers(message: Message):
    """Список поставщиков."""
    user = await get_user_by_telegram(message.from_user.id)
    if not user:
        await message.answer("❌ Аккаунт не привязан.")
        return

    if user.role.value not in ["admin", "manager"]:
        await message.answer("❌ Нет доступа.")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Supplier).where(
                Supplier.company_id == user.company_id,
                Supplier.is_active == True,
            ).order_by(Supplier.name.asc())
        )
        suppliers = result.scalars().all()

    if not suppliers:
        await message.answer("📭 Поставщики не добавлены.")
        return

    text = "🏭 Поставщики:\n\n"
    for s in suppliers:
        text += (
            f"• {s.name}\n"
            f"  📞 {s.phone or '—'}\n"
            f"  ✉️ {s.email or '—'}\n\n"
        )
    await message.answer(text)