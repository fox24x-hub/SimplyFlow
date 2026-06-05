"""
Сервис уведомлений — отправляет сообщения в Telegram
когда происходят важные события в системе.

Вызывается из API эндпоинтов после ключевых действий.
"""

import logging
from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.models.supply_request import SupplyRequest
from app.core.enums import UserRole

logger = logging.getLogger(__name__)


async def get_bot() -> Bot:
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)


async def send_to_user(telegram_id: int, text: str) -> None:
    """Отправить сообщение конкретному пользователю по telegram_id."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    try:
        bot = await get_bot()
        await bot.send_message(chat_id=telegram_id, text=text)
        await bot.session.close()
    except Exception as e:
        logger.warning(f"Не удалось отправить уведомление: {e}")


async def notify_request_created(
    db:      AsyncSession,
    request: SupplyRequest,
    creator: User,
) -> None:
    """
    Мастер создал заявку → уведомляем всех снабженцев компании.
    """
    result = await db.execute(
        select(User).where(
            User.company_id == request.company_id,
            User.role == UserRole.manager,
            User.is_active == True,
            User.telegram_id.isnot(None),
        )
    )
    managers = result.scalars().all()

    text = (
        f"📦 Новая заявка на материалы!\n\n"
        f"🔢 Номер: {request.request_number}\n"
        f"👷 Мастер: {creator.full_name}\n"
        f"📌 Задача: {request.task_description[:100]}\n"
        f"🔴 Приоритет: {request.priority}\n"
        f"📅 Нужно к: {request.required_by or '—'}\n\n"
        f"Откройте приложение для обработки заявки."
    )

    for manager in managers:
        await send_to_user(manager.telegram_id, text)


async def notify_sent_to_supplier(
    db:         AsyncSession,
    request:    SupplyRequest,
    manager:    User,
    supplier_name: str,
) -> None:
    """
    Снабженец отправил заявку поставщику → уведомляем мастера и РП.
    """
    # Найти создателя заявки
    result = await db.execute(
        select(User).where(User.id == request.created_by_id)
    )
    creator = result.scalar_one_or_none()

    text = (
        f"📤 Заявка отправлена поставщику\n\n"
        f"🔢 Номер: {request.request_number}\n"
        f"🏭 Поставщик: {supplier_name}\n"
        f"👤 Снабженец: {manager.full_name}\n\n"
        f"Ожидайте счёт от поставщика."
    )

    recipients = []
    if creator and creator.telegram_id:
        recipients.append(creator.telegram_id)

    # РП если назначен
    if request.supervisor_id:
        result = await db.execute(
            select(User).where(User.id == request.supervisor_id)
        )
        supervisor = result.scalar_one_or_none()
        if supervisor and supervisor.telegram_id:
            recipients.append(supervisor.telegram_id)

    for telegram_id in recipients:
        await send_to_user(telegram_id, text)


async def notify_invoice_received(
    db:             AsyncSession,
    request:        SupplyRequest,
    invoice_number: str,
    invoice_amount: str,
    supplier_name:  str,
) -> None:
    """
    Счёт получен → уведомляем мастера и РП для согласования.
    """
    text = (
        f"🧾 Получен счёт от поставщика!\n\n"
        f"🔢 Заявка: {request.request_number}\n"
        f"🏭 Поставщик: {supplier_name}\n"
        f"📋 Счёт №: {invoice_number}\n"
        f"💰 Сумма: {invoice_amount} руб\n\n"
        f"Требуется согласование счёта."
    )

    recipients = []

    # Мастер
    result = await db.execute(
        select(User).where(User.id == request.created_by_id)
    )
    creator = result.scalar_one_or_none()
    if creator and creator.telegram_id:
        recipients.append(creator.telegram_id)

    # РП
    if request.supervisor_id:
        result = await db.execute(
            select(User).where(User.id == request.supervisor_id)
        )
        supervisor = result.scalar_one_or_none()
        if supervisor and supervisor.telegram_id:
            recipients.append(supervisor.telegram_id)

    for telegram_id in recipients:
        await send_to_user(telegram_id, text)


async def notify_invoice_reviewed(
    db:       AsyncSession,
    request:  SupplyRequest,
    reviewer: User,
    approved: bool,
) -> None:
    """
    Счёт согласован/отклонён → уведомляем снабженца.
    """
    # Найти снабженца
    result = await db.execute(
        select(User).where(
            User.company_id == request.company_id,
            User.role == UserRole.manager,
            User.is_active == True,
            User.telegram_id.isnot(None),
        )
    )
    managers = result.scalars().all()

    status_text = "✅ согласован" if approved else "❌ отклонён"
    text = (
        f"📋 Счёт {status_text}\n\n"
        f"🔢 Заявка: {request.request_number}\n"
        f"👤 Рассмотрел: {reviewer.full_name}\n\n"
        f"{'Можно подтверждать заказ поставщику.' if approved else 'Требуется корректировка.'}"
    )

    for manager in managers:
        await send_to_user(manager.telegram_id, text)