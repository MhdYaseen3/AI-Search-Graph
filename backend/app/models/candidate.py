from app.models.base import BaseEntity


class Candidate(BaseEntity):
    """Candidate domain model."""

    full_name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    resume_file_path: str | None = None
    raw_text: str | None = None
    source: str | None = None
    skills: list[str] = []
