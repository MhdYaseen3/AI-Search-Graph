from app.models.base import BaseEntity


class Education(BaseEntity):
    """Education domain model."""

    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    expected_graduation: str | None = None
    cgpa: str | None = None
    start_date: str | None = None
    end_date: str | None = None
