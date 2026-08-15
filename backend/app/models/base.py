from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class BaseEntity(BaseModel):
    """Base domain entity with common identifiers and timestamps."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
