from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    title: str
    description: str
    required_skills: list[str] = Field(default_factory=list)
    experience: int
    location: str
    employment_type: str
    status: str
    salary: str | None = None
    created_by: str | None = None


class JobUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    required_skills: list[str] | None = None
    experience: int | None = None
    location: str | None = None
    employment_type: str | None = None
    status: str | None = None
    salary: str | None = None
    created_by: str | None = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    required_skills: list[str] = Field(default_factory=list)
    experience: int
    location: str
    employment_type: str
    status: str
    salary: str | None = None
    created_by: str | None = None


class JobListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[JobResponse] = Field(default_factory=list)