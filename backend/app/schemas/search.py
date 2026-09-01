from pydantic import BaseModel, Field


class MatchBreakdown(BaseModel):
    """Structured breakdown of why a candidate matches a query."""
    role_match: bool = False
    experience_match: bool = False
    skill_match: bool = False
    technology_match: bool = False
    project_match: bool = False


class SearchQuery(BaseModel):
    query: str = ""
    role: str | None = None
    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    min_experience_years: float | None = None
    limit: int = 20


class RankedCandidate(BaseModel):
    candidate_id: str
    full_name: str
    score: float
    experience_years: float | None = None
    matched_roles: list[str] = Field(default_factory=list)
    matched_skills: list[str] = Field(default_factory=list)
    matched_technologies: list[str] = Field(default_factory=list)
    matched_projects: list[str] = Field(default_factory=list)
    match_breakdown: MatchBreakdown = Field(default_factory=MatchBreakdown)
    explanation: str | None = None
    summary: str | None = None


class SearchResponse(BaseModel):
    query: str
    total: int
    parsed_role: str | None = None
    parsed_skills: list[str] = Field(default_factory=list)
    parsed_technologies: list[str] = Field(default_factory=list)
    parsed_projects: list[str] = Field(default_factory=list)
    min_experience_years: float | None = None
    results: list[RankedCandidate] = Field(default_factory=list)


class AISummaryRequest(BaseModel):
    context: str | None = None


class AISummaryResponse(BaseModel):
    candidate_id: str
    summary: str
    source: str = "ai"


class MatchExplanationRequest(BaseModel):
    query: str
    candidate_id: str


class MatchExplanationResponse(BaseModel):
    candidate_id: str
    query: str
    explanation: str
    source: str = "deterministic"


class StructuredMatchExplanationRequest(BaseModel):
    """Request for AI explanation using structured match evidence from ranking."""
    candidate_id: str
    candidate_name: str
    query: str
    role: str | None = None
    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    min_experience_years: float | None = None
    matched_roles: list[str] = Field(default_factory=list)
    matched_skills: list[str] = Field(default_factory=list)
    matched_technologies: list[str] = Field(default_factory=list)
    matched_projects: list[str] = Field(default_factory=list)
    match_breakdown: MatchBreakdown = Field(default_factory=MatchBreakdown)
    experience_years: float | None = None


class StructuredMatchExplanationResponse(BaseModel):
    candidate_id: str
    query: str
    explanation: str
    source: str = "ai"
