from dataclasses import dataclass
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.service import AuthFailure, require_csrf, resolve_session
from app.db.models import AuthSession, User
from app.db.session import get_db


@dataclass(frozen=True)
class ConsumerPrincipal:
    user: User
    session: AuthSession


def require_owner(principal: ConsumerPrincipal, resource_user_id) -> None:
    """Authorize a resource only after its persisted owner has been loaded."""
    if resource_user_id != principal.user.id:
        # Conceal whether another user's resource exists.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "resource_not_found"})


def current_consumer(request: Request, db: Session = Depends(get_db)) -> ConsumerPrincipal:
    raw = request.cookies.get("cartel_session", "")
    resolved = resolve_session(db, raw, request.app.state.settings.auth_idle_days)
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "authentication_required"})
    request.state.consumer_user_id = resolved[1].id
    return ConsumerPrincipal(user=resolved[1], session=resolved[0])


def csrf_protected(
    request: Request,
    principal: ConsumerPrincipal = Depends(current_consumer),
) -> ConsumerPrincipal:
    require_same_origin(request)
    try:
        require_csrf(principal.session, request.headers.get("X-CSRF-Token"))
    except AuthFailure as exc:
        raise HTTPException(status_code=403, detail={"code": "csrf_failed"}) from exc
    return principal


def require_same_origin(request: Request) -> None:
    from urllib.parse import urlsplit

    origin = request.headers.get("Origin")
    if not origin:
        raise HTTPException(status_code=403, detail={"code": "origin_required"})
    configured = request.app.state.settings.public_origin
    expected = urlsplit(configured)
    supplied = urlsplit(origin)
    if (supplied.scheme, supplied.netloc) != (expected.scheme, expected.netloc):
        raise HTTPException(status_code=403, detail={"code": "origin_rejected"})
