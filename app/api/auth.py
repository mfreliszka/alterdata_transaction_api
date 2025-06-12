"""Authentication API endpoints (bonus feature)."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies import AuthSvc
from app.core.config import settings
from app.schemas.schemas import AuthToken


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Login request schema."""
    
    token: str


@router.post("/login", response_model=AuthToken)
async def login(
    request: LoginRequest,
    auth_service: AuthSvc,
) -> AuthToken:
    """
    Simple token-based authentication endpoint.
    
    For demo purposes only. In production, implement proper authentication.
    """
    if not settings.REQUIRE_AUTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication is not enabled",
        )
    
    # Validate token (in real app, check against database/auth service)
    if request.token != settings.SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    return AuthToken(
        token=settings.SECRET_KEY,
        token_type="Bearer",
    )
