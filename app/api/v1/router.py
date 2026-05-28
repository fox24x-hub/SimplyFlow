from fastapi import APIRouter

from app.api.v1.endpoints.auth    import router as auth_router
from app.api.v1.endpoints.objects import router as objects_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(objects_router)