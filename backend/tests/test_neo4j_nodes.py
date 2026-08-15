from datetime import datetime

import pytest

from app.db.nodes import CandidateNode, ProjectNode, SkillNode, TechnologyNode
from app.models import Candidate, Project, Skill, Technology


def test_candidate_node_domain_round_trip() -> None:
    candidate = Candidate(
        id="cand-1",
        full_name="Jane Doe",
        email="jane@example.com",
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 2, 12, 0, 0),
    )

    node = CandidateNode.from_domain(candidate)
    restored = node.to_domain()

    assert restored.id == candidate.id
    assert restored.full_name == candidate.full_name
    assert restored.email == candidate.email


def test_candidate_node_from_neo4j_mapping() -> None:
    props = {
        "id": "cand-2",
        "full_name": "John Smith",
        "email": "john@example.com",
        "created_at": "2024-03-01T10:00:00",
        "updated_at": "2024-03-01T10:00:00",
    }

    node = CandidateNode.from_neo4j(props)

    assert node.id == "cand-2"
    assert node.full_name == "John Smith"
    assert node.merge_parameters()["id"] == "cand-2"
    assert "full_name" in node.merge_parameters()["properties"]


def test_skill_node_normalizes_name() -> None:
    skill = Skill(id="skill-1", name="  Python  ")
    node = SkillNode.from_domain(skill)

    assert node.name == "Python"
    assert node.label == "Skill"
    assert node.unique_property == "name"


def test_project_node_merge_query() -> None:
    project = Project(id="proj-1", name="Graph Search")
    node = ProjectNode.from_domain(project)

    assert "MERGE (n:Project {id: $id})" in node.merge_query()
    assert node.to_neo4j_properties()["name"] == "Graph Search"


def test_technology_node_from_neo4j_mapping() -> None:
    node = TechnologyNode.from_neo4j({"name": "Neo4j", "id": "tech-neo4j"})

    assert node.name == "Neo4j"
    assert node.to_domain().name == "Neo4j"


@pytest.mark.parametrize(
    "node_cls,unique_property",
    [
        (CandidateNode, "id"),
        (SkillNode, "name"),
        (ProjectNode, "id"),
        (TechnologyNode, "name"),
    ],
)
def test_node_unique_properties(node_cls, unique_property) -> None:
    assert node_cls.unique_property == unique_property
