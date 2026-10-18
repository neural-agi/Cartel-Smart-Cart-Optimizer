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


def current_consumer(request: Request, db: Session = Depends(get_db)) -> ConsumerPrincipal:
    raw_token = request.cookies.get("cartel_session", "")
    resolved = resolve_session(
        db,
        raw_token,
        request.app.state.settings.auth_idle_days,
        commit=False,
    )
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "authentication_required"},
        )
    session, user = resolved
    request.state.consumer_user_id = user.id
    return ConsumerPrincipal(user=user, session=session)


def csrf_protected(
    request: Request,
    principal: ConsumerPrincipal = Depends(current_consumer),
) -> ConsumerPrincipal:
    from urllib.parse import urlsplit

    origin = request.headers.get("Origin")
    if not origin:
        raise HTTPException(status_code=403, detail={"code": "origin_required"})
    expected = urlsplit(request.app.state.settings.public_origin)
    supplied = urlsplit(origin)
    if (supplied.scheme, supplied.netloc) != (expected.scheme, expected.netloc):
        raise HTTPException(status_code=403, detail={"code": "origin_rejected"})
    try:
        require_csrf(principal.session, request.headers.get("X-CSRF-Token"))
    except AuthFailure as exc:
        raise HTTPException(status_code=403, detail={"code": "csrf_failed"}) from exc
    return principal
