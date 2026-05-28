from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.deps import ManagerUser, StaffUser, DBSession
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierResponse

router = APIRouter(prefix="/suppliers", tags=["Поставщики"])


@router.post(
    "/",
    response_model=SupplierResponse,
    status_code=201,
    summary="Добавить поставщика",
)
async def create_supplier(
    data: SupplierCreate,
    user: ManagerUser,
    db:   DBSession,
):
    """Добавить нового поставщика. Admin или менеджер."""
    supplier = Supplier(
        company_id=user.company_id,
        **data.model_dump(exclude_none=True),
    )
    db.add(supplier)
    await db.flush()
    await db.refresh(supplier)
    return supplier


@router.get(
    "/",
    response_model=list[SupplierResponse],
    summary="Список поставщиков",
)
async def list_suppliers(
    user: StaffUser,
    db:   DBSession,
):
    """Все активные поставщики компании."""
    result = await db.execute(
        select(Supplier)
        .where(
            Supplier.company_id == user.company_id,
            Supplier.is_active == True,
        )
        .order_by(Supplier.name.asc())
    )
    return list(result.scalars().all())


@router.get(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Получить поставщика",
)
async def get_supplier(
    supplier_id: int,
    user:        StaffUser,
    db:          DBSession,
):
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.company_id == user.company_id,
        )
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Поставщик не найден")
    return supplier


@router.patch(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Обновить поставщика",
)
async def update_supplier(
    supplier_id: int,
    data:        SupplierUpdate,
    user:        ManagerUser,
    db:          DBSession,
):
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.company_id == user.company_id,
        )
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Поставщик не найден")

    changes = data.model_dump(exclude_none=True)
    for field, value in changes.items():
        setattr(supplier, field, value)

    await db.flush()
    await db.refresh(supplier)
    return supplier