from pydantic import BaseModel, Field


class MatchedCandidate(BaseModel):
    candidate_id: str
    full_name: str
    match_score: float = Field(..., ge=0.0, le=100.0)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    experience: int
    summary: str | None = None
    ai_explanation: str | None = None


class JobMatchResponse(BaseModel):
    job_id: str
    total_candidates: int
    matched_candidates: list[MatchedCandidate] = Field(
        default_factory=list
    )