from datetime import datetime
from typing import Any, ClassVar, Self

from pydantic import Field

from app.db.nodes.base import GraphNode, _parse_neo4j_datetime, _serialize_datetime, node_properties
from app.models.job import Job


class JobNode(GraphNode):
    """Neo4j Job node."""

    label: ClassVar[str] = "Job"
    unique_property: ClassVar[str] = "id"

    id: str
    title: str
    description: str
    required_skills: list[str]
    experience: int
    location: str
    employment_type: str
    status: str
    salary: str | None = None
    created_by: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_domain(cls, job: Job) -> Self:
        return cls.model_validate(job.model_dump())

    def to_domain(self) -> Job:
        return Job.model_validate(self.model_dump())

    @classmethod
    def from_neo4j(cls, node: Any) -> Self:
        props = node_properties(node)
        # Parse required_skills from Neo4j (might be stored as string or list)
        required_skills = props.get("required_skills", [])
        if isinstance(required_skills, str):
            required_skills = [s.strip() for s in required_skills.split(",") if s.strip()]
        elif not isinstance(required_skills, list):
            required_skills = list(required_skills) if required_skills else []

        return cls(
            id=props["id"],
            title=props["title"],
            description=props["description"],
            required_skills=required_skills,
            experience=int(props.get("experience", 0)),
            location=props["location"],
            employment_type=props["employment_type"],
            status=props["status"],
            salary=props.get("salary"),
            created_by=props.get("created_by"),
            created_at=_parse_neo4j_datetime(props.get("created_at")),
            updated_at=_parse_neo4j_datetime(props.get("updated_at")),
        )

    def to_neo4j_properties(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "required_skills": self.required_skills,
            "experience": self.experience,
            "location": self.location,
            "employment_type": self.employment_type,
            "status": self.status,
            "salary": self.salary,
            "created_by": self.created_by,
            "created_at": _serialize_datetime(self.created_at),
            "updated_at": _serialize_datetime(self.updated_at),
        }
