"""
app/services/message_draft_agent.py

Message Draft Agent: generates a ready-to-send message for a given recipient
based on the supply request context.

Recipients:
  supplier  — message to supplier about the order
  master    — message to site master about delivery/status
  manager   — message to supply manager about invoice/approval
"""
from __future__ import annotations
from typing import Any
from .ai import get_ai_client, MODEL, MAX_TOKENS
from .summary_agent import STATUS_LABELS

RECIPIENT_LABELS = {
    "supplier": "поставщику",
    "master":   "мастеру на объекте",
    "manager":  "снабженцу",
}

SYSTEM_PROMPT = """\
Ты — ассистент системы снабжения SimplyFlow. Пишешь деловые сообщения на русском языке.

Правила:
- Деловой, но живой язык — не канцелярит, не «Уважаемый коллега»
- Обращение: «Добрый день» или без обращения — по контексту
- Структура: суть → детали → что нужно сделать (call to action)
- Длина: 3-6 предложений, не больше
- Не придумывай данные которых нет (имена, цены, даты поставки)
- Не используй markdown, только обычный текст
- В конце — вежливое закрытие без подписи (подпись добавит пользователь)
- Верни ТОЛЬКО текст сообщения, никаких пояснений вокруг него
"""


def _build_prompt(
    request: dict[str, Any],
    items: list[dict],
    recipient: str,
    sender_role: str,
    extra_context: str,
) -> str:
    status_label = STATUS_LABELS.get(
        request.get("status", ""), request.get("status", "")
    )
    recipient_label = RECIPIENT_LABELS.get(recipient, recipient)

    items_text = (
        "\n".join(
            f"  - {it['name']}: {it['quantity']} {it.get('unit', 'шт')}"
            for it in items[:10]
        )
        if items else "  (позиций нет)"
    )
    if len(items) > 10:
        items_text += f"\n  ...и ещё {len(items) - 10} позиций"

    context_block = f"\nДополнительный контекст от отправителя: {extra_context}" \
        if extra_context and extra_context.strip() else ""

    return f"""Напиши сообщение {recipient_label}.

Контекст заявки:
  Номер/название: {request.get('request_number') or request.get('title') or 'не указано'}
  Объект: {request.get('object_name') or 'не указан'}
  Статус: {status_label}
  Автор заявки: {request.get('author_name') or 'не указан'}

Позиции ({len(items)}):
{items_text}

Роль отправителя: {sender_role}{context_block}

Напиши текст сообщения."""


async def generate_message_draft(
    request: dict[str, Any],
    items: list[dict],
    recipient: str,
    sender_role: str,
    extra_context: str = "",
) -> str:
    """
    Returns a ready-to-send message string.
    recipient: 'supplier' | 'master' | 'manager'
    sender_role: 'manager' | 'master' | 'supervisor' | 'supplier'
    """
    client = get_ai_client()
    prompt = _build_prompt(request, items, recipient, sender_role, extra_context)

    message = await client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text.strip()
