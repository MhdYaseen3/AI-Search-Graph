from app.models.base import BaseEntity


class Skill(BaseEntity):
    """Skill domain model."""

    name: str
    category: str | None = None
    proficiency: str | None = None
