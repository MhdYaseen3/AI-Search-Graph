from datetime import datetime
from typing import Any, ClassVar, Self

from pydantic import Field

from app.db.nodes.base import GraphNode, _parse_neo4j_datetime, _serialize_datetime, node_properties
from app.models.candidate import Candidate


class CandidateNode(GraphNode):
    """Neo4j Candidate node."""

    label: ClassVar[str] = "Candidate"
    unique_property: ClassVar[str] = "id"

    id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    resume_file_path: str | None = None
    raw_text: str | None = None
    source: str | None = None
    skills: list[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_domain(cls, candidate: Candidate) -> Self:
        return cls.model_validate(candidate.model_dump())

    def to_domain(self) -> Candidate:
        return Candidate.model_validate(self.model_dump())

    @classmethod
    def from_neo4j(cls, node: Any) -> Self:
        props = node_properties(node)
        # Parse skills from Neo4j (might be stored as string or list)
        skills = props.get("skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        elif not isinstance(skills, list):
            skills = list(skills) if skills else []
        
        return cls(
            id=props["id"],
            full_name=props["full_name"],
            email=props.get("email"),
            phone=props.get("phone"),
            location=props.get("location"),
            summary=props.get("summary"),
            resume_file_path=props.get("resume_file_path"),
            raw_text=props.get("raw_text"),
            source=props.get("source"),
            skills=skills,
            created_at=_parse_neo4j_datetime(props.get("created_at")),
            updated_at=_parse_neo4j_datetime(props.get("updated_at")),
        )

    def to_neo4j_properties(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "summary": self.summary,
            "resume_file_path": self.resume_file_path,
            "raw_text": self.raw_text,
            "source": self.source,
            "skills": self.skills,
            "created_at": _serialize_datetime(self.created_at),
            "updated_at": _serialize_datetime(self.updated_at),
        }
