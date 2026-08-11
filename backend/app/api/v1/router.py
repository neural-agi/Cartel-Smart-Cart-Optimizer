from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.cost_intelligence import router as cost_intelligence_router
from app.api.routes.scrape import router as scrape_router


router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(cost_intelligence_router)
router.include_router(scrape_router)
