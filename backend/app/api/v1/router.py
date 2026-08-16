from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.cost_intelligence import router as cost_intelligence_router
from app.api.routes.scrape import router as scrape_router
from app.api.routes.observations import router as observations_router
from app.api.routes.comparisons import router as comparisons_router
from app.api.routes.cart import router as cart_router
from app.api.routes.cart_candidates import router as cart_candidates_router


router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(cost_intelligence_router)
router.include_router(scrape_router)
router.include_router(observations_router)
router.include_router(comparisons_router)
router.include_router(cart_router)
router.include_router(cart_candidates_router)
