from app.models.base import BaseEntity


class Experience(BaseEntity):
    """Candidate work experience."""

    company: str
    role: str | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None