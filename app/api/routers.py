"""API router initialization and registration."""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.reports import router as reports_router
from app.api.transactions import router as transactions_router


# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(transactions_router)
api_router.include_router(reports_router)


# Export for use in main app
__all__ = ["api_router"]
