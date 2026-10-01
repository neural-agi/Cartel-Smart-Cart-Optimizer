from fastapi import APIRouter, Request

from app.schemas.auth import AuthSessionResponse


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/session", response_model=AuthSessionResponse)
async def get_auth_session(request: Request) -> AuthSessionResponse:
    authenticated = bool(getattr(request.state, "authenticated", False))
    return AuthSessionResponse(
        authenticated=authenticated,
        user_id=request.state.user_id if authenticated else None,
    )
