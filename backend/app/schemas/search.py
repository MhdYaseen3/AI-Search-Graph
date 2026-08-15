from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    query: str = ""
    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    limit: int = 20


class RankedCandidate(BaseModel):
    candidate_id: str
    full_name: str
    score: float
    matched_skills: list[str] = Field(default_factory=list)
    matched_technologies: list[str] = Field(default_factory=list)
    matched_projects: list[str] = Field(default_factory=list)
    summary: str | None = None


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[RankedCandidate] = Field(default_factory=list)


class AISummaryRequest(BaseModel):
    context: str | None = None


class AISummaryResponse(BaseModel):
    candidate_id: str
    summary: str