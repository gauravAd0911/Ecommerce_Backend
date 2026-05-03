"""API v1 router: assembles all endpoint sub-routers."""

from fastapi import APIRouter

from app.api.v1.endpoints.categories import router as categories_router
from app.api.v1.endpoints.home import router as home_router
from app.api.v1.endpoints.products import (
    admin_router as admin_products_router,
    compat_admin_router,
    router as products_router,
)

api_router = APIRouter()

api_router.include_router(home_router, tags=["Home"])
api_router.include_router(products_router)
api_router.include_router(admin_products_router)
api_router.include_router(categories_router)

compat_router = APIRouter()
compat_router.include_router(compat_admin_router)
