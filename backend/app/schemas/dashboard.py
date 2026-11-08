from pydantic import BaseModel, Field


class DashboardCandidate(BaseModel):
    id: str
    full_name: str
    location: str | None = None
    relationship_count: int = 0


class DashboardSkill(BaseModel):
    name: str
    count: int


class ProcessingQueueMetrics(BaseModel):
    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    duplicates: int = 0
    idle: bool = True


class DashboardStatsResponse(BaseModel):
    total_resumes: int = 0
    graph_relationships: int = 0
    average_match_score: float | None = None
    processing_queue: ProcessingQueueMetrics = Field(
        default_factory=ProcessingQueueMetrics
    )
    recent_candidates: list[DashboardCandidate] = Field(default_factory=list)
    top_skills: list[DashboardSkill] = Field(default_factory=list)
