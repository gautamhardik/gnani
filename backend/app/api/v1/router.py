from fastapi import APIRouter
from backend.app.api.v1.products import router as products_router
from backend.app.api.v1.inventory import router as inventory_router
from backend.app.api.v1.orders import router as orders_router
from backend.app.api.v1.intelligence import router as intelligence_router
from backend.app.api.v1.voice import router as voice_router

api_router = APIRouter()
api_router.include_router(products_router)
api_router.include_router(inventory_router)
api_router.include_router(orders_router)
api_router.include_router(intelligence_router)
api_router.include_router(voice_router)
