from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=1024)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class RecoveryRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=12, max_length=1024)


class AuthAcceptedResponse(BaseModel):
    status: str = "accepted"


class ConsumerSessionResponse(BaseModel):
    authenticated: bool = True
    user_id: UUID
    email: EmailStr
    expires_at: datetime
    csrf_token: str


class ConsumerMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: EmailStr
    created_at: datetime
