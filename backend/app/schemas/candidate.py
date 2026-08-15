from pydantic import BaseModel, ConfigDict, Field


class CandidateCreate(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    resume_file_path: str | None = None
    raw_text: str | None = None
    skills: list[str] = Field(default_factory=list)


class CandidateUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    resume_file_path: str | None = None
    raw_text: str | None = None
    skills: list[str] | None = None


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    resume_file_path: str | None = None
    raw_text: str | None = None
    skills: list[str] = Field(default_factory=list)

class CandidateListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[CandidateResponse] = Field(default_factory=list)