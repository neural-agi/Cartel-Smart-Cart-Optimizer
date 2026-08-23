from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    version: str


class ReadinessResponse(BaseModel):
    status: str
    service: str
    environment: str
    version: str
    checks: dict[str, str]
