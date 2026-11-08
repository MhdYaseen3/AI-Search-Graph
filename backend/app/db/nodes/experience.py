from datetime import datetime
from typing import Any, ClassVar, Self

from pydantic import Field

from app.db.nodes.base import (
    GraphNode,
    _parse_neo4j_datetime,
    _serialize_datetime,
    node_properties,
)
from app.models.experience import Experience


class ExperienceNode(GraphNode):
    """Neo4j Experience node."""

    label: ClassVar[str] = "Experience"
    unique_property: ClassVar[str] = "id"

    id: str
    company: str
    role: str | None = None
    description: str | None = None
    duration: str | None = None
    start_date: str | None = None
    end_date: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_domain(cls, experience: Experience) -> Self:
        return cls.model_validate(experience.model_dump())

    def to_domain(self) -> Experience:
        return Experience.model_validate(self.model_dump())

    @classmethod
    def from_neo4j(cls, node: Any) -> Self:
        props = node_properties(node)

        return cls(
            id=props["id"],
            company=props["company"],
            role=props.get("role"),
            description=props.get("description"),
            duration=props.get("duration"),
            start_date=props.get("start_date"),
            end_date=props.get("end_date"),
            created_at=_parse_neo4j_datetime(
                props.get("created_at")
            ),
            updated_at=_parse_neo4j_datetime(
                props.get("updated_at")
            ),
        )

    def to_neo4j_properties(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "company": self.company,
            "role": self.role,
            "description": self.description,
            "duration": self.duration,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "created_at": _serialize_datetime(
                self.created_at
            ),
            "updated_at": _serialize_datetime(
                self.updated_at
            ),
        }