"""
app/services/status_guard_agent.py

Status Guard Agent: checks whether a status transition is safe to perform.

Returns:
  { "allowed": bool, "warnings": [str], "explanation": str }

- allowed=True, warnings=[]       → all good, proceed
- allowed=True, warnings=[...]    → soft warnings, user can still proceed
- allowed=False, explanation=str  → hard block with reason
"""
from __future__ import annotations
import json
from typing import Any
from .ai import get_ai_client, MODEL, MAX_TOKENS

SYSTEM_PROMPT = """\
Ты — контролёр переходов статусов в системе управления снабжением SimplyFlow.
Тебе дают заявку и желаемый переход статуса. Ты должен проверить, безопасно ли делать этот переход прямо сейчас.

Верни ТОЛЬКО валидный JSON без markdown и пояснений:
{
  "allowed": true | false,
  "warnings": ["предупреждение 1", "предупреждение 2"],
  "explanation": "краткое объяснение решения (1-2 предложения, по-русски)"
}

Правила принятия решений:
- allowed=false (жёсткая блокировка) только если переход технически невозможен или создаёт серьёзный риск:
  * нет ни одной позиции в заявке при переходе из draft/submitted
  * нет объекта назначения при переходе из draft
  * переход "завершить" когда нет подтверждения доставки
- allowed=true с warnings (мягкие предупреждения) если:
  * позиций меньше 1 при отправке поставщику
  * отсутствует комментарий при отклонении счёта
  * переход делается быстро (менее часа после создания) — возможно не все позиции добавлены
  * нет описания/комментария к заявке
- allowed=true без предупреждений во всех остальных случаях
- Будь лаконичен, не придумывай лишних блокировок
- explanation всегда заполнен (даже если allowed=true и warnings=[])
"""


def _build_prompt(
    request: dict[str, Any],
    items: list[dict],
    current_status: str,
    target_status: str,
) -> str:
    from .summary_agent import STATUS_LABELS
    current_label = STATUS_LABELS.get(current_status, current_status)
    target_label  = STATUS_LABELS.get(target_status, target_status)

    items_text = (
        "\n".join(f"  - {it['name']}: {it['quantity']} {it.get('unit','шт')}" for it in items)
        if items else "  (позиций нет)"
    )

    created_at = request.get("created_at", "")
    description = request.get("description") or "(не заполнено)"

    return f"""Заявка: {request.get('title', 'Без названия')}
Объект: {request.get('object_name') or '(не указан)'}
Описание: {description}
Создана: {created_at}
Текущий статус: {current_label}
Желаемый статус: {target_label}

Позиции ({len(items)}):
{items_text}

Проверь, можно ли выполнить этот переход."""


async def check_status_transition(
    request: dict[str, Any],
    items: list[dict],
    current_status: str,
    target_status: str,
) -> dict[str, Any]:
    """
    Returns dict: { allowed: bool, warnings: list[str], explanation: str }
    Raises RuntimeError if ANTHROPIC_API_KEY missing.
    Raises ValueError if response not valid JSON.
    """
    client = get_ai_client()
    prompt = _build_prompt(request, items, current_status, target_status)

    message = await client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = "\n".join(
            line for line in raw.splitlines()
            if not line.startswith("```")
        ).strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI вернул невалидный JSON: {e}")

    # Normalise
    return {
        "allowed":     bool(result.get("allowed", True)),
        "warnings":    [str(w) for w in result.get("warnings", [])],
        "explanation": str(result.get("explanation", "")),
    }
