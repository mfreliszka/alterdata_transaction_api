"""Health check API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import DbSession
from app.core.config import settings


router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Basic health check endpoint.
    
    Returns service status without requiring authentication.
    """
    return {
        "status": "healthy",
        "service": "Transaction Processing API",
    }


@router.get("/health/db")
async def database_health_check(
    db: DbSession,
) -> dict[str, str]:
    """
    Database connectivity health check.
    
    Verifies database connection is working.
    """
    try:
        # Execute simple query
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        
        return {
            "status": "healthy",
            "database": "connected",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
        }
