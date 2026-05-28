from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, ManagerUser, StaffUser, DBSession
from app.core.enums import EventActionType, RequestStatus, REQUEST_STATUS_TRANSITIONS, UserRole
from app.models.supply_request import SupplyRequest, SupplyRequestItem
from app.schemas.supply_request import (
    SupplyRequestCreate,
    SupplyRequestUpdate,
    SupplyRequestStatusChange,
    SupplyRequestItemCreate,
    SupplyRequestResponse,
    SupplyRequestListItem,
    SupplyRequestItemResponse,
)
from app.services.event_log import EventLogService

router = APIRouter(prefix="/supply-requests", tags=["Заявки на материалы"])


def _generate_number(request_id: int) -> str:
    """Генерирует номер заявки: SF-2026-001"""
    from datetime import datetime
    year = datetime.now().year
    return f"SF-{year}-{request_id:03d}"


async def _get_or_404(request_id: int, db, user) -> SupplyRequest:
    result = await db.execute(
        select(SupplyRequest)
        .options(selectinload(SupplyRequest.items))
        .where(
            SupplyRequest.id == request_id,
            SupplyRequest.company_id == user.company_id,
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return req


@router.post(
    "/",
    response_model=SupplyRequestResponse,
    status_code=201,
    summary="Создать заявку на материалы",
)
async def create_request(
    data: SupplyRequestCreate,
    user: StaffUser,
    db:   DBSession,
):
    """Мастер создаёт заявку на материалы для объекта."""
    req = SupplyRequest(
        company_id=user.company_id,
        created_by_id=user.id,
        status=RequestStatus.draft,
        **data.model_dump(exclude_none=True),
    )
    db.add(req)
    await db.flush()

    # Генерируем номер заявки
    req.request_number = _generate_number(req.id)

    await EventLogService(db).log(
        company_id=user.company_id,
        action_type=EventActionType.request_created,
        user_id=user.id,
        request_id=req.id,
        payload={"object_id": data.object_id, "priority": data.priority},
        description=f"Заявка создана: {req.request_number}",
    )

    # Перезагружаем с items
    result = await db.execute(
        select(SupplyRequest)
        .options(selectinload(SupplyRequest.items))
        .where(SupplyRequest.id == req.id)
    )
    return result.scalar_one()


@router.get(
    "/",
    response_model=list[SupplyRequestListItem],
    summary="Список заявок",
)
async def list_requests(
    user:          StaffUser,
    db:            DBSession,
    status_filter: RequestStatus|None = Query(None, alias="status"),
    object_id:     int|None           = Query(None),
    limit:         int                = Query(50, le=200),
    offset:        int                = Query(0,  ge=0),
):
    """Список заявок с фильтрами."""
    q = select(SupplyRequest).where(
        SupplyRequest.company_id == user.company_id
    )

    # Мастер видит только свои заявки
    if user.role == UserRole.master:
        q = q.where(SupplyRequest.created_by_id == user.id)

    if status_filter:
        q = q.where(SupplyRequest.status == status_filter)
    if object_id:
        q = q.where(SupplyRequest.object_id == object_id)

    q = q.order_by(SupplyRequest.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.get(
    "/{request_id}",
    response_model=SupplyRequestResponse,
    summary="Получить заявку",
)
async def get_request(
    request_id: int,
    user:       StaffUser,
    db:         DBSession,
):
    return await _get_or_404(request_id, db, user)


@router.patch(
    "/{request_id}",
    response_model=SupplyRequestResponse,
    summary="Обновить заявку",
)
async def update_request(
    request_id: int,
    data:       SupplyRequestUpdate,
    user:       StaffUser,
    db:         DBSession,
):
    req = await _get_or_404(request_id, db, user)
    changes = data.model_dump(exclude_none=True)
    for field, value in changes.items():
        setattr(req, field, value)

    await EventLogService(db).log(
        company_id=user.company_id,
        action_type=EventActionType.request_updated,
        user_id=user.id,
        request_id=req.id,
        payload={"updated_fields": list(changes.keys())},
        description="Заявка обновлена",
    )

    # Перезагружаем с items
    result = await db.execute(
        select(SupplyRequest)
        .options(selectinload(SupplyRequest.items))
        .where(SupplyRequest.id == req.id)
    )
    return result.scalar_one()


@router.post(
    "/{request_id}/status",
    response_model=SupplyRequestResponse,
    summary="Изменить статус заявки",
)
async def change_status(
    request_id: int,
    data:       SupplyRequestStatusChange,
    user:       StaffUser,
    db:         DBSession,
):
    req = await _get_or_404(request_id, db, user)

    allowed = REQUEST_STATUS_TRANSITIONS.get(req.status, [])
    if data.new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый переход: {req.status} → {data.new_status}. "
                   f"Разрешено: {[s.value for s in allowed]}",
        )

    old_status = req.status
    req.status = data.new_status

    await EventLogService(db).log(
        company_id=user.company_id,
        action_type=EventActionType.request_status_changed,
        user_id=user.id,
        request_id=req.id,
        payload={
            "from_status": old_status.value,
            "to_status":   data.new_status.value,
            "reason":      data.reason,
        },
        description=f"Статус: {old_status.value} → {data.new_status.value}",
    )

    # Перезагружаем с items
    result = await db.execute(
        select(SupplyRequest)
        .options(selectinload(SupplyRequest.items))
        .where(SupplyRequest.id == req.id)
    )
    return result.scalar_one()


@router.post(
    "/{request_id}/items",
    response_model=SupplyRequestItemResponse,
    status_code=201,
    summary="Добавить материал в заявку",
)
async def add_item(
    request_id: int,
    data:       SupplyRequestItemCreate,
    user:       StaffUser,
    db:         DBSession,
):
    """Мастер добавляет материал в заявку."""
    req = await _get_or_404(request_id, db, user)

    item = SupplyRequestItem(
        request_id=req.id,
        **data.model_dump(exclude_none=True),
    )
    # Считаем total_price
    if data.quantity and data.unit_price:
        item.total_price = data.quantity * data.unit_price

    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.get(
    "/{request_id}/items",
    response_model=list[SupplyRequestItemResponse],
    summary="Список материалов в заявке",
)
async def list_items(
    request_id: int,
    user:       StaffUser,
    db:         DBSession,
):
    await _get_or_404(request_id, db, user)
    result = await db.execute(
        select(SupplyRequestItem)
        .where(SupplyRequestItem.request_id == request_id)
        .order_by(SupplyRequestItem.id.asc())
    )
    return list(result.scalars().all())