from datetime import datetime
from typing import Any, ClassVar, Self

from pydantic import Field

from app.db.nodes.base import (
    GraphNode,
    _parse_neo4j_datetime,
    _serialize_datetime,
    node_properties,
)
from app.models.education import Education


class EducationNode(GraphNode):
    """Neo4j Education node."""

    label: ClassVar[str] = "Education"
    unique_property: ClassVar[str] = "institution"

    id: str
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_domain(cls, education: Education) -> Self:
        return cls.model_validate(education.model_dump())

    def to_domain(self) -> Education:
        return Education.model_validate(self.model_dump())

    @classmethod
    def from_neo4j(cls, node: Any) -> Self:
        props = node_properties(node)

        return cls(
            id=props.get("id"),
            institution=props["institution"],
            degree=props.get("degree"),
            field_of_study=props.get("field_of_study"),
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
            "institution": self.institution,
            "degree": self.degree,
            "field_of_study": self.field_of_study,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "created_at": _serialize_datetime(
                self.created_at
            ),
            "updated_at": _serialize_datetime(
                self.updated_at
            ),
        }