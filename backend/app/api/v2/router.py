from fastapi import APIRouter

from app.api.v2.auth import router as auth_router
from app.api.v2.me import router as me_router
from app.api.v2.lists import router as lists_router
from app.api.v2.products import router as products_router
from app.api.v2.optimizations import router as optimizations_router


router = APIRouter()
router.include_router(auth_router)
router.include_router(me_router)
router.include_router(lists_router)
router.include_router(products_router)
router.include_router(optimizations_router)
