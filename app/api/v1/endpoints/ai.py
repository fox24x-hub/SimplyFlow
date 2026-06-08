"""
app/api/v1/endpoints/ai.py

AI agent endpoints.
All require authentication (CurrentUser dependency from core/deps.py).

Routes:
  POST /ai/requests/{request_id}/summary        — Summary Agent
  POST /ai/extract-tasks                        — Task Extraction Agent
  POST /ai/requests/{request_id}/check-status   — Status Guard Agent
  POST /ai/requests/{request_id}/message-draft  — Message Draft Agent
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser
from app.core.database import get_db
from app.models.supply_request import SupplyRequest, SupplyRequestItem
from app.models.event_log import EventLog
from app.services.summary_agent import generate_summary
from app.services.task_extraction_agent import extract_tasks
from app.services.status_guard_agent import check_status_transition
from app.services.message_draft_agent import generate_message_draft

router = APIRouter(prefix="/ai", tags=["ai"])


class SummaryResponse(BaseModel):
    summary: str
    request_id: int


@router.post(
    "/requests/{request_id}/summary",
    response_model=SummaryResponse,
    summary="Summary Agent — краткое резюме заявки",
)
async def get_request_summary(
    request_id: int,
    current_user=Depends(CurrentUser),
    db: AsyncSession = Depends(get_db),
) -> SummaryResponse:
    """
    Generates a short AI summary for the given supply request.

    - Loads request + items + last 10 events from DB
    - Calls Claude via Anthropic API
    - Returns plain text summary (2-4 sentences in Russian)

    Access: any authenticated user belonging to the same company.
    """
    # ── 1. Load request ──────────────────────────────────────
    result = await db.execute(
        select(SupplyRequest)
        .where(
            SupplyRequest.id == request_id,
            SupplyRequest.company_id == current_user.company_id,
        )
        .options(selectinload(SupplyRequest.items))
    )
    req = result.scalar_one_or_none()

    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена",
        )

    # ── 2. Load recent events ────────────────────────────────
    events_result = await db.execute(
        select(EventLog)
        .where(EventLog.request_id == request_id)
        .order_by(EventLog.created_at.desc())
        .limit(10)
    )
    events = events_result.scalars().all()

    # ── 3. Build dicts for the agent ─────────────────────────
    request_dict = {
        "title":       req.title,
        "status":      req.status.value if hasattr(req.status, "value") else req.status,
        "object_name": getattr(req.object, "name", None) if req.object else None,
        "author_name": (
            f"{req.author.first_name or ''} {req.author.last_name or ''}".strip()
            if req.author else None
        ),
        "description": req.description,
        "created_at":  str(req.created_at),
    }

    items_list = [
        {
            "name":     item.name,
            "quantity": item.quantity,
            "unit":     item.unit,
        }
        for item in req.items
    ]

    events_list = [
        {
            "action":      e.action.value if hasattr(e.action, "value") else e.action,
            "description": e.description,
            "created_at":  str(e.created_at),
        }
        for e in reversed(events)  # chronological order
    ]

    # ── 4. Call agent ────────────────────────────────────────
    try:
        summary_text = await generate_summary(request_dict, items_list, events_list)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ошибка AI-сервиса, попробуйте позже",
        )

    return SummaryResponse(summary=summary_text, request_id=request_id)


# ── Task Extraction Agent ─────────────────────────────────────────────────────

class ExtractTasksRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Свободный текст с перечнем материалов")


class ExtractedItem(BaseModel):
    name: str
    quantity: float
    unit: str


class ExtractTasksResponse(BaseModel):
    items: list[ExtractedItem]


@router.post(
    "/extract-tasks",
    response_model=ExtractTasksResponse,
    summary="Task Extraction Agent — позиции из свободного текста",
)
async def extract_tasks_endpoint(
    body: ExtractTasksRequest,
    current_user=Depends(CurrentUser),
) -> ExtractTasksResponse:
    """
    Parses free-form Russian text and returns structured list of material items.

    Example input:
      "нужно 50 кг арматуры 12мм и 20 мешков цемента М500"

    Example output:
      { "items": [
          {"name": "Арматура 12мм", "quantity": 50, "unit": "кг"},
          {"name": "Цемент М500",   "quantity": 20, "unit": "мешков"}
      ]}

    Access: any authenticated user.
    """
    try:
        raw_items = await extract_tasks(body.text)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ошибка AI-сервиса, попробуйте позже",
        )

    return ExtractTasksResponse(
        items=[ExtractedItem(**item) for item in raw_items]
    )


# ── Status Guard Agent ────────────────────────────────────────────────────────

class CheckStatusRequest(BaseModel):
    target_status: str = Field(..., description="Желаемый новый статус")


class CheckStatusResponse(BaseModel):
    allowed: bool
    warnings: list[str]
    explanation: str


@router.post(
    "/requests/{request_id}/check-status",
    response_model=CheckStatusResponse,
    summary="Status Guard Agent — проверка перехода статуса",
)
async def check_status_endpoint(
    request_id: int,
    body: CheckStatusRequest,
    current_user=Depends(CurrentUser),
    db: AsyncSession = Depends(get_db),
) -> CheckStatusResponse:
    """
    Checks whether transitioning the given request to target_status is safe.

    Returns:
      - allowed=true, warnings=[]    → proceed freely
      - allowed=true, warnings=[...] → soft warnings, user can still proceed
      - allowed=false                → hard block with explanation

    Access: any authenticated user in the same company.
    """
    # ── Load request + items ─────────────────────────────────
    result = await db.execute(
        select(SupplyRequest)
        .where(
            SupplyRequest.id == request_id,
            SupplyRequest.company_id == current_user.company_id,
        )
        .options(selectinload(SupplyRequest.items))
    )
    req = result.scalar_one_or_none()

    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена",
        )

    request_dict = {
        "title":       req.title,
        "object_name": getattr(req.object, "name", None) if req.object else None,
        "description": req.description,
        "created_at":  str(req.created_at),
    }

    items_list = [
        {"name": item.name, "quantity": item.quantity, "unit": item.unit}
        for item in req.items
    ]

    current_status = req.status.value if hasattr(req.status, "value") else req.status

    # ── Call agent ───────────────────────────────────────────
    try:
        result_data = await check_status_transition(
            request_dict,
            items_list,
            current_status,
            body.target_status,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ошибка AI-сервиса, попробуйте позже",
        )

    return CheckStatusResponse(**result_data)


# ── Message Draft Agent ───────────────────────────────────────────────────────

VALID_RECIPIENTS = {"supplier", "master", "manager"}


class MessageDraftRequest(BaseModel):
    recipient: str = Field(
        ...,
        description="Кому пишем: supplier | master | manager",
    )
    extra_context: str = Field(
        default="",
        max_length=500,
        description="Дополнительный контекст от пользователя (опционально)",
    )


class MessageDraftResponse(BaseModel):
    draft: str
    recipient: str


@router.post(
    "/requests/{request_id}/message-draft",
    response_model=MessageDraftResponse,
    summary="Message Draft Agent — черновик сообщения",
)
async def message_draft_endpoint(
    request_id: int,
    body: MessageDraftRequest,
    current_user=Depends(CurrentUser),
    db: AsyncSession = Depends(get_db),
) -> MessageDraftResponse:
    """
    Generates a ready-to-send message for the given recipient.

    recipient values:
      - supplier — message to the supplier about the order
      - master   — message to the site master about delivery/status
      - manager  — message to the supply manager

    Access: any authenticated user in the same company.
    """
    if body.recipient not in VALID_RECIPIENTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"recipient must be one of: {', '.join(VALID_RECIPIENTS)}",
        )

    # ── Load request + items ─────────────────────────────────
    result = await db.execute(
        select(SupplyRequest)
        .where(
            SupplyRequest.id == request_id,
            SupplyRequest.company_id == current_user.company_id,
        )
        .options(selectinload(SupplyRequest.items))
    )
    req = result.scalar_one_or_none()

    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена",
        )

    request_dict = {
        "request_number": req.request_number if hasattr(req, "request_number") else None,
        "title":          req.title,
        "status":         req.status.value if hasattr(req.status, "value") else req.status,
        "object_name":    getattr(req.object, "name", None) if req.object else None,
        "author_name":    (
            f"{req.author.first_name or ''} {req.author.last_name or ''}".strip()
            if req.author else None
        ),
        "description":    req.description,
    }

    items_list = [
        {"name": item.name, "quantity": item.quantity, "unit": item.unit}
        for item in req.items
    ]

    sender_role = current_user.role.value if hasattr(current_user.role, "value") \
        else current_user.role

    # ── Call agent ───────────────────────────────────────────
    try:
        draft = await generate_message_draft(
            request_dict,
            items_list,
            body.recipient,
            sender_role,
            body.extra_context,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ошибка AI-сервиса, попробуйте позже",
        )

    return MessageDraftResponse(draft=draft, recipient=body.recipient)
