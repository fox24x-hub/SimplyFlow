from fastapi import APIRouter

from app.api.v1.endpoints.auth            import router as auth_router
from app.api.v1.endpoints.objects         import router as objects_router
from app.api.v1.endpoints.supply_requests import router as supply_requests_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(objects_router)
api_router.include_router(supply_requests_router)