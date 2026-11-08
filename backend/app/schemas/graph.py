from pydantic import BaseModel, Field


class ExperienceResponse(BaseModel):
    id: str | None = None
    company: str
    role: str | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class EducationDetailResponse(BaseModel):
    institution: str | None = None
    degree: str | None = None


class CandidateDetailResponse(BaseModel):
    id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    education: list[EducationDetailResponse] = Field(default_factory=list)
    experiences: list[ExperienceResponse] = Field(default_factory=list)
    experience_years: float | None = None


class GraphNodeResponse(BaseModel):
    id: str
    label: str
    type: str


class GraphLinkResponse(BaseModel):
    id: str | None = None
    source: str
    target: str
    type: str


class CandidateGraphResponse(BaseModel):
    candidate_id: str
    total: int | None = None
    skip: int = 0
    limit: int | None = None
    nodes: list[GraphNodeResponse] = Field(default_factory=list)
    links: list[GraphLinkResponse] = Field(default_factory=list)
