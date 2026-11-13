from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.service import (
    AuthFailure,
    IssuedSession,
    csrf_token_for_session,
    login,
    logout_all,
    logout_current,
    request_password_recovery,
    resend_verification,
    reset_password,
    rotate_session,
    signup,
    verify_email,
    authenticate_external,
    begin_oauth,
    consume_oauth_state,
)
from app.auth.providers import IdentityProviderFailure, IdentityProviderUnavailable, configured_verifier, provider_configuration
from app.api.v2.dependencies import ConsumerPrincipal, current_consumer, csrf_protected, require_same_origin
from app.db.session import get_db
from app.schemas.consumer_auth import (
    AuthAcceptedResponse,
    ConsumerSessionResponse,
    LoginRequest,
    RecoveryRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SignupRequest,
    VerifyEmailRequest,
)


router = APIRouter(prefix="/auth", tags=["consumer-auth"])


def _safe_next(value: str | None) -> str:
    if not value or not value.startswith("/") or value.startswith("//") or "\\" in value:
        return "/home"
    return value[:512]


def _provider_redirect_uri(settings, provider: str) -> str:
    return {"google": settings.google_redirect_uri, "github": settings.github_redirect_uri}[provider]


@router.get("/providers")
def providers_route(request: Request):
    return {"providers": provider_configuration(request.app.state.settings)}


@router.get("/{provider}/start")
def provider_start(provider: str, request: Request, next: str | None = None, db: Session = Depends(get_db)):
    if provider not in {"google", "github"}:
        return RedirectResponse("/login?error=provider_unavailable", status_code=303)
    try:
        verifier = configured_verifier(request.app.state.settings, provider)
        redirect_uri = _provider_redirect_uri(request.app.state.settings, provider)
        state = begin_oauth(db, provider, redirect_uri, _safe_next(next))
        return RedirectResponse(verifier.authorization_url(state.state, state.nonce, _pkce_challenge(state.code_verifier)), status_code=303)
    except IdentityProviderUnavailable:
        return RedirectResponse("/login?error=provider_unavailable", status_code=303)


@router.post("/{provider}/link/start")
def provider_link_start(provider: str, request: Request, principal: ConsumerPrincipal = Depends(csrf_protected), db: Session = Depends(get_db)):
    if provider not in {"google", "github"}:
        raise HTTPException(status_code=404, detail={"code": "provider_unavailable"})
    try:
        verifier = configured_verifier(request.app.state.settings, provider)
        redirect_uri = _provider_redirect_uri(request.app.state.settings, provider)
        state = begin_oauth(db, provider, redirect_uri, "/settings", principal.user.id)
        return {"authorization_url": verifier.authorization_url(state.state, state.nonce, _pkce_challenge(state.code_verifier))}
    except IdentityProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "provider_unavailable"}) from exc


@router.get("/{provider}/callback")
def provider_callback(provider: str, request: Request, response: Response, code: str | None = None, state: str | None = None, error: str | None = None, db: Session = Depends(get_db)):
    if provider not in {"google", "github"}:
        return RedirectResponse("/login?error=provider_unavailable", status_code=303)
    if error or not code or not state:
        return RedirectResponse("/login?error=provider_cancelled", status_code=303)
    try:
        challenge = consume_oauth_state(db, provider, state)
        verifier = configured_verifier(request.app.state.settings, provider)
        verified = verifier.verify(code, redirect_uri=challenge.redirect_uri, nonce=challenge.nonce, code_verifier=challenge.code_verifier)
        issued = authenticate_external(
            db, request.app.state.settings, verified, request.headers.get("user-agent"),
            request.state.request_id, link_user_id=challenge.user_id,
        )
        _session_response(issued, response, request)
        redirect = RedirectResponse(challenge.next_path, status_code=303)
        _set_session_cookie(redirect, request, issued.raw_token, issued.expires_at)
        return redirect
    except (AuthFailure, IdentityProviderUnavailable, IdentityProviderFailure) as exc:
        code_value = exc.code if isinstance(exc, AuthFailure) else "provider_unavailable"
        return RedirectResponse(f"/login?error={code_value}", status_code=303)


def _pkce_challenge(verifier: str) -> str:
    import base64
    import hashlib
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


def _handle_failure(exc: AuthFailure) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})


def _set_session_cookie(response: Response, request: Request, token: str, expires_at: datetime) -> None:
    max_age = max(0, int((expires_at - datetime.now(timezone.utc)).total_seconds()))
    response.set_cookie(
        "cartel_session",
        token,
        httponly=True,
        secure=request.app.state.settings.secure_auth_cookie,
        samesite="lax",
        path="/",
        max_age=max_age,
        expires=expires_at,
    )


def _clear_session_cookie(response: Response, request: Request) -> None:
    response.delete_cookie(
        "cartel_session",
        path="/",
        secure=request.app.state.settings.secure_auth_cookie,
        httponly=True,
        samesite="lax",
    )


def _session_response(issued: IssuedSession, response: Response, request: Request) -> ConsumerSessionResponse:
    _set_session_cookie(response, request, issued.raw_token, issued.expires_at)
    email = next((identity.email for identity in issued.user.identities if identity.email), None)
    if email is None:
        raise HTTPException(status_code=500, detail={"code": "identity_email_unavailable"})
    return ConsumerSessionResponse(
        user_id=issued.user.id,
        email=email,
        expires_at=issued.expires_at,
        csrf_token=issued.raw_csrf,
    )


@router.post("/signup", response_model=AuthAcceptedResponse, status_code=202)
def signup_route(payload: SignupRequest, request: Request, db: Session = Depends(get_db)):
    require_same_origin(request)
    if not request.app.state.settings.email_delivery_configured:
        raise HTTPException(status_code=503, detail={"code": "email_delivery_unavailable"})
    try:
        signup(db, request.app.state.settings, str(payload.email), payload.password, request.state.request_id)
    except AuthFailure as exc:
        if exc.code == "account_exists":
            return AuthAcceptedResponse()
        raise _handle_failure(exc) from exc
    return AuthAcceptedResponse()


@router.post("/verification/resend", response_model=AuthAcceptedResponse, status_code=202)
def resend_route(payload: ResendVerificationRequest, request: Request, db: Session = Depends(get_db)):
    require_same_origin(request)
    if not request.app.state.settings.email_delivery_configured:
        raise HTTPException(status_code=503, detail={"code": "email_delivery_unavailable"})
    try:
        resend_verification(db, request.app.state.settings, str(payload.email), request.state.request_id)
    except AuthFailure:
        pass
    return AuthAcceptedResponse()


@router.post("/email/verify", response_model=ConsumerSessionResponse)
def verify_route(payload: VerifyEmailRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    require_same_origin(request)
    try:
        issued = verify_email(db, request.app.state.settings, payload.token, request.headers.get("user-agent"), request.state.request_id)
    except AuthFailure as exc:
        raise _handle_failure(exc) from exc
    return _session_response(issued, response, request)


@router.post("/login", response_model=ConsumerSessionResponse)
def login_route(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    require_same_origin(request)
    try:
        issued = login(db, request.app.state.settings, str(payload.email), payload.password, request.headers.get("user-agent"), request.state.request_id)
    except AuthFailure as exc:
        raise _handle_failure(exc) from exc
    return _session_response(issued, response, request)


@router.get("/csrf")
def csrf_route(request: Request, principal: ConsumerPrincipal = Depends(current_consumer)):
    raw_token = request.cookies.get("cartel_session", "")
    return {"csrf_token": csrf_token_for_session(raw_token)}


@router.get("/session", response_model=ConsumerSessionResponse)
def session_route(request: Request, principal: ConsumerPrincipal = Depends(current_consumer)):
    raw_token = request.cookies.get("cartel_session", "")
    email = next((identity.email for identity in principal.user.identities if identity.email), None)
    if email is None:
        raise HTTPException(status_code=500, detail={"code": "identity_email_unavailable"})
    return ConsumerSessionResponse(
        user_id=principal.user.id,
        email=email,
        expires_at=principal.session.expires_at,
        csrf_token=csrf_token_for_session(raw_token),
    )


@router.post("/rotate", response_model=ConsumerSessionResponse)
def rotate_route(request: Request, response: Response, principal: ConsumerPrincipal = Depends(csrf_protected), db: Session = Depends(get_db)):
    issued = rotate_session(db, request.app.state.settings, principal.session, principal.user, request.headers.get("user-agent"))
    return _session_response(issued, response, request)


@router.post("/logout", status_code=204)
def logout_route(request: Request, response: Response, principal: ConsumerPrincipal = Depends(csrf_protected), db: Session = Depends(get_db)):
    logout_current(db, principal.session, request.state.request_id)
    _clear_session_cookie(response, request)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/logout-all", status_code=204)
def logout_all_route(request: Request, response: Response, principal: ConsumerPrincipal = Depends(csrf_protected), db: Session = Depends(get_db)):
    logout_all(db, principal.user, request.state.request_id)
    _clear_session_cookie(response, request)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/password/recovery", response_model=AuthAcceptedResponse, status_code=202)
def recovery_route(payload: RecoveryRequest, request: Request, db: Session = Depends(get_db)):
    require_same_origin(request)
    if not request.app.state.settings.email_delivery_configured:
        raise HTTPException(status_code=503, detail={"code": "email_delivery_unavailable"})
    try:
        request_password_recovery(db, request.app.state.settings, str(payload.email), request.state.request_id)
    except AuthFailure:
        pass
    return AuthAcceptedResponse()


@router.post("/password/reset", response_model=AuthAcceptedResponse)
def reset_route(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    require_same_origin(request)
    try:
        reset_password(db, payload.token, payload.new_password, request.state.request_id)
    except AuthFailure as exc:
        raise _handle_failure(exc) from exc
    return AuthAcceptedResponse(status="completed")
