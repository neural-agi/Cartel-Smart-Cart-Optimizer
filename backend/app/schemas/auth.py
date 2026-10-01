from pydantic import BaseModel


class AuthSessionResponse(BaseModel):
    authenticated: bool
    user_id: str | None
