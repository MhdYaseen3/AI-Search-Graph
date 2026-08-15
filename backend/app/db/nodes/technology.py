from datetime import datetime
from typing import Any, ClassVar, Self

from pydantic import Field, field_validator

from app.db.nodes.base import GraphNode, _parse_neo4j_datetime, _serialize_datetime, node_properties
from app.models.technology import Technology


class TechnologyNode(GraphNode):
    """Neo4j Technology node."""

    label: ClassVar[str] = "Technology"
    unique_property: ClassVar[str] = "name"

    id: str
    name: str
    category: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @classmethod
    def from_domain(cls, technology: Technology) -> Self:
        return cls.model_validate(technology.model_dump())

    def to_domain(self) -> Technology:
        return Technology.model_validate(self.model_dump())

    @classmethod
    def from_neo4j(cls, node: Any) -> Self:
        props = node_properties(node)
        return cls(
            id=props.get("id", props["name"]),
            name=props["name"],
            category=props.get("category"),
            created_at=_parse_neo4j_datetime(props.get("created_at")),
            updated_at=_parse_neo4j_datetime(props.get("updated_at")),
        )

    def to_neo4j_properties(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "created_at": _serialize_datetime(self.created_at),
            "updated_at": _serialize_datetime(self.updated_at),
        }
