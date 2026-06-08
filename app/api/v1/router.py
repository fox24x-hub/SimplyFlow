from fastapi import APIRouter

from app.api.v1.endpoints.auth            import router as auth_router
from app.api.v1.endpoints.objects         import router as objects_router
from app.api.v1.endpoints.supply_requests import router as supply_requests_router
from app.api.v1.endpoints.suppliers       import router as suppliers_router
from app.api.v1.endpoints.supplier_orders import router as supplier_orders_router
from app.api.v1.endpoints.ai              import router as ai_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(objects_router)
api_router.include_router(supply_requests_router)
api_router.include_router(suppliers_router)
api_router.include_router(supplier_orders_router)
api_router.include_router(ai_router)