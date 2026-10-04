from fastapi import APIRouter, Depends, HTTPException

from app.api.v2.dependencies import ConsumerPrincipal
from app.api.v2.dependencies import current_consumer
from app.schemas.consumer_auth import ConsumerMeResponse


router = APIRouter(tags=["consumer-account"])


@router.get("/me", response_model=ConsumerMeResponse)
def get_me(principal: ConsumerPrincipal = Depends(current_consumer)) -> ConsumerMeResponse:
    email_identity = next((identity for identity in principal.user.identities if identity.email), None)
    if email_identity is None:
        raise HTTPException(status_code=500, detail={"code": "identity_email_unavailable"})
    return ConsumerMeResponse(user_id=principal.user.id, email=email_identity.email, created_at=principal.user.created_at)
