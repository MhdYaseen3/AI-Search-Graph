from datetime import datetime
from typing import Any, ClassVar, Self

from pydantic import Field

from app.db.nodes.base import GraphNode, _parse_neo4j_datetime, _serialize_datetime, node_properties
from app.models.project import Project


class ProjectNode(GraphNode):
    """Neo4j Project node."""

    label: ClassVar[str] = "Project"
    unique_property: ClassVar[str] = "id"

    id: str
    name: str
    description: str | None = None
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_domain(cls, project: Project) -> Self:
        return cls.model_validate(project.model_dump())

    def to_domain(self) -> Project:
        return Project.model_validate(self.model_dump())

    @classmethod
    def from_neo4j(cls, node: Any) -> Self:
        props = node_properties(node)
        return cls(
            id=props["id"],
            name=props["name"],
            description=props.get("description"),
            role=props.get("role"),
            start_date=props.get("start_date"),
            end_date=props.get("end_date"),
            created_at=_parse_neo4j_datetime(props.get("created_at")),
            updated_at=_parse_neo4j_datetime(props.get("updated_at")),
        )

    def to_neo4j_properties(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "role": self.role,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "created_at": _serialize_datetime(self.created_at),
            "updated_at": _serialize_datetime(self.updated_at),
        }
