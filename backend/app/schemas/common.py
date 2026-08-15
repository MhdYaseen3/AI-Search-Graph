from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    environment: str


class PaginationParams(BaseModel):
    skip: int = 0
    limit: int = 20