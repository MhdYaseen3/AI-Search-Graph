from app.models.base import BaseEntity


class Technology(BaseEntity):
    """Technology domain model."""

    name: str
    category: str | None = None
