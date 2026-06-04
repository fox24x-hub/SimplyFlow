from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import ManagerUser, StaffUser, DBSession
from app.core.enums import EventActionType
from app.models.supplier_order import SupplierOrder
from app.models.supply_request import SupplyRequest
from app.schemas.supplier_order import (
    SupplierOrderCreate,
    SupplierOrderInvoice,
    SupplierOrderReview,
    SupplierOrderResponse,
)
from app.services.event_log import EventLogService

router = APIRouter(prefix="/supply-requests", tags=["Заказы поставщикам"])


async def _get_request_or_404(request_id: int, db, user) -> SupplyRequest:
    result = await db.execute(
        select(SupplyRequest).where(
            SupplyRequest.id == request_id,
            SupplyRequest.company_id == user.company_id,
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return req


async def _get_order_or_404(order_id: int, request_id: int, db) -> SupplierOrder:
    result = await db.execute(
        select(SupplierOrder).where(
            SupplierOrder.id == order_id,
            SupplierOrder.request_id == request_id,
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order


@router.post(
    "/{request_id}/orders",
    response_model=SupplierOrderResponse,
    status_code=201,
    summary="Отправить заявку поставщику",
)
async def create_order(
    request_id: int,
    data:       SupplierOrderCreate,
    user:       ManagerUser,
    db:         DBSession,
):
    """
    Снабженец отправляет заявку конкретному поставщику.
    Одну заявку можно отправить нескольким поставщикам.
    """
    await _get_request_or_404(request_id, db, user)

    order = SupplierOrder(
        request_id=request_id,
        supplier_id=data.supplier_id,
        status="sent",
        notes=data.notes,
    )
    db.add(order)
    await db.flush()

    await EventLogService(db).log(
        company_id=user.company_id,
        action_type=EventActionType.sent_to_supplier,
        user_id=user.id,
        request_id=request_id,
        payload={
            "supplier_id": data.supplier_id,
            "order_id":    order.id,
        },
        description=f"Заявка отправлена поставщику #{data.supplier_id}",
    )

    await db.refresh(order)
    return order


@router.get(
    "/{request_id}/orders",
    response_model=list[SupplierOrderResponse],
    summary="Список заказов по заявке",
)
async def list_orders(
    request_id: int,
    user:       StaffUser,
    db:         DBSession,
):
    """Все заказы поставщикам по одной заявке."""
    await _get_request_or_404(request_id, db, user)

    result = await db.execute(
        select(SupplierOrder)
        .where(SupplierOrder.request_id == request_id)
        .order_by(SupplierOrder.created_at.asc())
    )
    return list(result.scalars().all())


@router.post(
    "/{request_id}/orders/{order_id}/invoice",
    response_model=SupplierOrderResponse,
    summary="Внести счёт от поставщика",
)
async def add_invoice(
    request_id: int,
    order_id:   int,
    data:       SupplierOrderInvoice,
    user:       ManagerUser,
    db:         DBSession,
):
    """Снабженец вносит счёт который прислал поставщик."""
    await _get_request_or_404(request_id, db, user)
    order = await _get_order_or_404(order_id, request_id, db)

    order.invoice_number = data.invoice_number
    order.invoice_amount = data.invoice_amount
    order.status         = "invoice_received"
    if data.notes:
        order.notes = data.notes

    await EventLogService(db).log(
        company_id=user.company_id,
        action_type=EventActionType.invoice_received,
        user_id=user.id,
        request_id=request_id,
        payload={
            "order_id":       order_id,
            "invoice_number": data.invoice_number,
            "invoice_amount": str(data.invoice_amount),
        },
        description=f"Счёт получен: {data.invoice_number} на {data.invoice_amount} руб",
    )

    await db.refresh(order)
    return order


@router.post(
    "/{request_id}/orders/{order_id}/review",
    response_model=SupplierOrderResponse,
    summary="Согласовать или отклонить счёт",
)
async def review_invoice(
    request_id: int,
    order_id:   int,
    data:       SupplierOrderReview,
    user:       StaffUser,
    db:         DBSession,
):
    """Мастер или РП согласовывает или отклоняет счёт от поставщика."""
    await _get_request_or_404(request_id, db, user)
    order = await _get_order_or_404(order_id, request_id, db)

    order.invoice_approved = data.approved
    order.status = "approved" if data.approved else "rejected"
    if data.notes:
        order.notes = data.notes

    action = (
        EventActionType.invoice_approved
        if data.approved
        else EventActionType.invoice_rejected
    )

    await EventLogService(db).log(
        company_id=user.company_id,
        action_type=action,
        user_id=user.id,
        request_id=request_id,
        payload={
            "order_id": order_id,
            "approved": data.approved,
        },
        description=f"Счёт {'согласован' if data.approved else 'отклонён'}",
    )

    await db.refresh(order)
    return order