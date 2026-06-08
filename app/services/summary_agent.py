"""
app/services/summary_agent.py

Summary Agent: given a supply request with its items and recent events,
returns a short Russian-language summary (2-4 sentences) for the detail page.
"""
from __future__ import annotations
from typing import Any
from .ai import get_ai_client, MODEL, MAX_TOKENS

# Status labels in Russian
STATUS_LABELS: dict[str, str] = {
    "draft":              "черновик",
    "submitted":          "подана",
    "sent_to_supplier":   "отправлена поставщику",
    "invoice_received":   "счёт получен",
    "invoice_approved":   "счёт согласован",
    "confirmed":          "подтверждена",
    "delivery_scheduled": "доставка назначена",
    "delivered":          "доставлено",
    "completed":          "завершена",
}

SYSTEM_PROMPT = """\
Ты — ассистент системы управления снабжением строительных объектов SimplyFlow.
Твоя задача — написать краткое резюме заявки на снабжение (2-4 предложения) для прораба или снабженца.

Правила:
- Пиши по-русски, деловой но простой язык
- Укажи: что заказано (кратко), текущий статус, что нужно сделать дальше
- Не повторяй очевидное (не пиши "это заявка на...")
- Если есть задержки или ожидающие действия — выдели их
- Максимум 4 предложения
- Отвечай только резюме, без заголовков и лишних слов
"""


def _build_prompt(request: dict[str, Any], items: list[dict], events: list[dict]) -> str:
    status = STATUS_LABELS.get(request.get("status", ""), request.get("status", "неизвестен"))
    title = request.get("title") or "Без названия"
    obj = request.get("object_name") or "не указан"
    author = request.get("author_name") or "не указан"
    description = request.get("description") or ""

    # Items summary
    if items:
        items_text = ", ".join(
            f"{it.get('name', '?')} — {it.get('quantity', '?')} {it.get('unit', 'шт')}"
            for it in items[:10]  # limit to 10
        )
        if len(items) > 10:
            items_text += f" (и ещё {len(items) - 10} позиций)"
    else:
        items_text = "позиции не указаны"

    # Recent events (last 5)
    if events:
        events_text = "\n".join(
            f"- {e.get('action', '?')}: {e.get('description', '')} ({e.get('created_at', '')[:10]})"
            for e in events[-5:]
        )
    else:
        events_text = "нет событий"

    return f"""Заявка: {title}
Объект: {obj}
Автор: {author}
Статус: {status}
{"Описание: " + description if description else ""}

Позиции ({len(items)}):
{items_text}

Последние события:
{events_text}

Напиши краткое резюме этой заявки."""


async def generate_summary(
    request: dict[str, Any],
    items: list[dict],
    events: list[dict],
) -> str:
    """
    Returns a short Russian summary string.
    Raises RuntimeError if ANTHROPIC_API_KEY is missing.
    """
    client = get_ai_client()
    prompt = _build_prompt(request, items, events)

    message = await client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text.strip()
