from datetime import datetime
from pydantic import BaseModel, Field


class ResumeUploadResponse(BaseModel):
    candidate_id: str
    file_name: str
    file_path: str
    file_size_bytes: int
    uploaded_at: datetime


class PDFUploadResponse(BaseModel):
    candidate_id: str
    file_name: str
    file_path: str
    file_size_bytes: int
    page_count: int
    character_count: int
    text: str
    uploaded_at: datetime


class ExtractedResumeData(BaseModel):
    candidate_id: str
    raw_text: str

    skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)

    experiences: list[dict] = Field(default_factory=list)

    technologies: list[str] = Field(default_factory=list)


class ResumeIngestResponse(BaseModel):
    candidate_id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    experiences: int = 0
    relationship_count: int = 0
    file_path: str
    message: str