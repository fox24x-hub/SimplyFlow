from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, ManagerUser, StaffUser, DBSession
from app.models.object import Object
from app.schemas.object import ObjectCreate, ObjectUpdate, ObjectResponse

router = APIRouter(prefix="/objects", tags=["Объекты"])


@router.post(
    "/",
    response_model=ObjectResponse,
    status_code=201,
    summary="Создать объект",
)
async def create_object(
    data: ObjectCreate,
    user: ManagerUser,
    db:   DBSession,
) -> Object:
    """Создать строительный объект. Admin или менеджер."""
    obj = Object(
        company_id=user.company_id,
        **data.model_dump(exclude_none=True),
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.get(
    "/",
    response_model=list[ObjectResponse],
    summary="Список объектов",
)
async def list_objects(
    user: StaffUser,
    db:   DBSession,
) -> list[Object]:
    """Все активные объекты компании."""
    result = await db.execute(
        select(Object)
        .where(
            Object.company_id == user.company_id,
            Object.is_active == True,
        )
        .order_by(Object.created_at.desc())
    )
    return list(result.scalars().all())


@router.get(
    "/{object_id}",
    response_model=ObjectResponse,
    summary="Получить объект",
)
async def get_object(
    object_id: int,
    user:      StaffUser,
    db:        DBSession,
) -> Object:
    result = await db.execute(
        select(Object).where(
            Object.id == object_id,
            Object.company_id == user.company_id,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Объект не найден")
    return obj


@router.patch(
    "/{object_id}",
    response_model=ObjectResponse,
    summary="Обновить объект",
)
async def update_object(
    object_id: int,
    data:      ObjectUpdate,
    user:      ManagerUser,
    db:        DBSession,
) -> Object:
    result = await db.execute(
        select(Object).where(
            Object.id == object_id,
            Object.company_id == user.company_id,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Объект не найден")

    changes = data.model_dump(exclude_none=True)
    for field, value in changes.items():
        setattr(obj, field, value)

    await db.flush()
    await db.refresh(obj)
    return obj