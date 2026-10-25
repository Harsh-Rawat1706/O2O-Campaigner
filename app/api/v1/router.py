from fastapi import APIRouter

from app.api.v1.endpoints import auth, offers, stores

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(stores.router, tags=["Merchant Stores"])
api_router.include_router(stores.admin_router, tags=["Admin Stores"])
api_router.include_router(offers.router)