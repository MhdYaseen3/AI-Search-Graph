from pydantic import BaseModel, Field


class ProjectItem(BaseModel):
    title: str
    description: str | None = None
    raw_text: str


class EducationItem(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    expected_graduation: str | None = None
    cgpa: str | None = None
    raw_text: str

class ExperienceItem(BaseModel):
    company: str | None = None
    role: str | None = None
    description: str | None = None
    duration: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    raw_text: str


class ParsedResume(BaseModel):
    candidate_name: str | None = None
    email: str | None = None
    phone: str | None = None
    summary: str | None = None

    skills: list[str] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    experiences: list[ExperienceItem] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)