from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ApplicationStatus = Literal[
    "Applied",
    "Shortlisted",
    "Interview",
    "Selected",
    "Rejected",
]


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
    created_at: datetime | None = None
    updated_at: datetime | None = None


class JobListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[JobResponse] = Field(default_factory=list)


class JobApplicationCreate(BaseModel):
    candidate_id: str


class JobApplicationUpdate(BaseModel):
    status: ApplicationStatus


class JobApplicationResponse(BaseModel):
    id: str
    job_id: str
    candidate_id: str
    full_name: str
    email: str | None = None
    summary: str | None = None
    status: ApplicationStatus
    created_at: str
    updated_at: str