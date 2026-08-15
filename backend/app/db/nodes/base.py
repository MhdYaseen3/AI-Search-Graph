from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict


def _parse_neo4j_datetime(value: Any) -> datetime:
    if value is None:
        return datetime.utcnow()
    if isinstance(value, datetime):
        return value
    if hasattr(value, "to_native"):
        return value.to_native()
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.utcnow()


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def node_properties(raw: Any) -> dict[str, Any]:
    """Normalize a Neo4j Node or mapping into a plain property dict."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if hasattr(raw, "_properties"):
        return dict(raw._properties)
    if hasattr(raw, "items"):
        return dict(raw.items())
    raise TypeError(f"Unsupported Neo4j node type: {type(raw)!r}")


class GraphNode(BaseModel, ABC):
    """Base Neo4j node model with serialization helpers."""

    model_config = ConfigDict(from_attributes=True)

    label: ClassVar[str]
    unique_property: ClassVar[str]

    @classmethod
    @abstractmethod
    def from_neo4j(cls, node: Any) -> Self:
        """Build a node model from a Neo4j node or property mapping."""

    @abstractmethod
    def to_neo4j_properties(self) -> dict[str, Any]:
        """Serialize model fields to Neo4j-storable properties."""

    @classmethod
    def merge_query(cls) -> str:
        """Cypher MERGE statement for upserting this node type."""
        unique = cls.unique_property
        return f"""
        MERGE (n:{cls.label} {{{unique}: ${unique}}})
        ON CREATE SET n.created_at = $created_at
        SET n += $properties
        SET n.updated_at = $updated_at
        RETURN n
        """

    def merge_parameters(self) -> dict[str, Any]:
        """Parameters for the MERGE query."""
        properties = self.to_neo4j_properties()
        unique_value = properties.pop(self.unique_property)
        created_at = properties.pop("created_at", None)
        updated_at = properties.pop("updated_at", None)

        return {
            self.unique_property: unique_value,
            "created_at": created_at or _serialize_datetime(datetime.utcnow()),
            "updated_at": updated_at or _serialize_datetime(datetime.utcnow()),
            "properties": properties,
        }
