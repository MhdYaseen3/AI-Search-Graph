from app.models.base import BaseEntity


class Project(BaseEntity):
    """Project domain model."""

    name: str
    description: str | None = None
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
