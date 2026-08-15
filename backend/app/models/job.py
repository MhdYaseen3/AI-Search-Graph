from app.models.base import BaseEntity


class Job(BaseEntity):
    """Job domain model."""

    title: str
    description: str
    required_skills: list[str]
    experience: int
    location: str
    employment_type: str
    status: str
    salary: str | None = None
    created_by: str | None = None
