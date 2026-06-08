"""
app/services/task_extraction_agent.py

Task Extraction Agent: parses free-form Russian text describing materials
and returns a structured list of { name, quantity, unit } items.

Input example:
  "нужно 50 кг арматуры 12мм, 20 мешков цемента М500 и 5 кубов песка"

Output:
  [
    {"name": "Арматура 12мм", "quantity": 50, "unit": "кг"},
    {"name": "Цемент М500",   "quantity": 20, "unit": "мешков"},
    {"name": "Песок",          "quantity": 5,  "unit": "м³"},
  ]
"""
from __future__ import annotations
import json
from typing import Any
from .ai import get_ai_client, MODEL, MAX_TOKENS

SYSTEM_PROMPT = """\
Ты — парсер заявок на строительные материалы.
Пользователь описывает нужные материалы в свободной форме.
Твоя задача — извлечь структурированный список позиций.

Правила:
- Верни ТОЛЬКО валидный JSON массив, без пояснений и markdown-блоков
- Каждый элемент: {"name": string, "quantity": number, "unit": string}
- name — название материала, с маркой/размером если указаны, с заглавной буквы
- quantity — число (целое или дробное), если не указано явно — поставь 1
- unit — единица измерения на русском: шт, кг, т, м, м², м³, л, уп, рул, мот, мешок
  Нормализуй: "штук" → "шт", "кубов" → "м³", "метров" → "м", "литров" → "л"
- Если единица не указана — поставь "шт"
- Если материалов несколько — все в одном массиве
- Если текст не содержит материалов — верни пустой массив []
"""


async def extract_tasks(text: str) -> list[dict[str, Any]]:
    """
    Parses free-form text and returns list of material items.
    Each item: { name: str, quantity: float, unit: str }
    Raises ValueError if response is not valid JSON.
    Raises RuntimeError if ANTHROPIC_API_KEY is missing.
    """
    if not text or not text.strip():
        return []

    client = get_ai_client()

    message = await client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text.strip()}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if model added them
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(
            line for line in lines
            if not line.startswith("```")
        ).strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI вернул невалидный JSON: {e}\nОтвет: {raw[:200]}")

    if not isinstance(parsed, list):
        raise ValueError("AI вернул не массив")

    # Validate and normalise each item
    result = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        try:
            quantity = float(item.get("quantity", 1))
        except (TypeError, ValueError):
            quantity = 1.0
        unit = str(item.get("unit", "шт")).strip() or "шт"
        result.append({"name": name, "quantity": quantity, "unit": unit})

    return result
