import logging
from typing import Any

from app.core.exceptions import NotFoundError
from app.db.neo4j import Neo4jConnection
from app.schemas.graph import (
    CandidateDetailResponse,
    CandidateGraphResponse,
    EducationDetailResponse,
    ExperienceResponse,
    GraphLinkResponse,
    GraphNodeResponse,
)
from app.utils.experience_calc import calculate_experience_years

logger = logging.getLogger(__name__)

_NODE_TYPE_MAP = {
    "Skill": "skill",
    "Technology": "skill",
    "Project": "project",
    "Education": "institution",
    "Experience": "company",
}


class CandidateGraphService:
    """Retrieve candidate graph data for API responses."""

    def __init__(self, neo4j: Neo4jConnection) -> None:
        self.neo4j = neo4j

    async def get_candidate_detail(
        self,
        candidate_id: str,
    ) -> CandidateDetailResponse:
        query = """
        MATCH (c:Candidate {id: $candidate_id})
        OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill)
        OPTIONAL MATCH (c)-[:USES_TECHNOLOGY]->(t:Technology)
        OPTIONAL MATCH (c)-[:WORKED_ON]->(p:Project)
        OPTIONAL MATCH (c)-[:STUDIED_AT]->(e:Education)
        OPTIONAL MATCH (c)-[:WORKED_AT]->(x:Experience)
        RETURN
            c.id AS id,
            c.full_name AS full_name,
            c.email AS email,
            c.phone AS phone,
            c.location AS location,
            c.summary AS summary,
            collect(DISTINCT s.name) AS skills,
            collect(DISTINCT t.name) AS technologies,
            collect(DISTINCT p.name) AS projects,
            collect(DISTINCT {
                institution: e.institution,
                degree: e.degree
            }) AS education,
            collect(DISTINCT {
                id: x.id,
                company: x.company,
                role: x.role,
                description: x.description,
                start_date: x.start_date,
                end_date: x.end_date
            }) AS experiences
        """

        records = await self.neo4j.execute_read(
            query,
            {"candidate_id": candidate_id},
        )

        if not records:
            raise NotFoundError(f"Candidate {candidate_id} not found")

        record = records[0]
        experiences = [
            exp
            for exp in record.get("experiences", [])
            if exp and exp.get("company")
        ]
        education = [
            EducationDetailResponse(
                institution=item.get("institution"),
                degree=item.get("degree"),
            )
            for item in record.get("education", [])
            if item and item.get("institution")
        ]

        return CandidateDetailResponse(
            id=record["id"],
            full_name=record["full_name"],
            email=record.get("email"),
            phone=record.get("phone"),
            location=record.get("location"),
            summary=record.get("summary"),
            skills=[s for s in record.get("skills", []) if s],
            technologies=[t for t in record.get("technologies", []) if t],
            projects=[p for p in record.get("projects", []) if p],
            education=education,
            experiences=[
                ExperienceResponse(**exp)
                for exp in experiences
            ],
            experience_years=calculate_experience_years(experiences),
        )

    async def get_candidate_graph(
        self,
        candidate_id: str,
    ) -> CandidateGraphResponse:
        query = """
        MATCH (c:Candidate {id: $candidate_id})
        OPTIONAL MATCH (c)-[r]->(n)
        RETURN
            c.id AS candidate_id,
            c.full_name AS candidate_name,
            collect(DISTINCT {
                relationship: type(r),
                labels: labels(n),
                properties: properties(n)
            }) AS related
        """

        records = await self.neo4j.execute_read(
            query,
            {"candidate_id": candidate_id},
        )

        if not records:
            raise NotFoundError(f"Candidate {candidate_id} not found")

        record = records[0]
        nodes: dict[str, GraphNodeResponse] = {}
        links: list[GraphLinkResponse] = []

        candidate_node_id = record["candidate_id"]
        nodes[candidate_node_id] = GraphNodeResponse(
            id=candidate_node_id,
            label=record["candidate_name"],
            type="candidate",
        )

        for item in record.get("related", []):
            if not item or not item.get("properties"):
                continue

            props = item["properties"]
            labels = item.get("labels") or []
            label_name = labels[0] if labels else "Node"
            node_type = _NODE_TYPE_MAP.get(label_name, "project")

            node_id = self._node_id(label_name, props)
            node_label = self._node_label(label_name, props)

            if node_id not in nodes:
                nodes[node_id] = GraphNodeResponse(
                    id=node_id,
                    label=node_label,
                    type=node_type,
                )

            links.append(
                GraphLinkResponse(
                    source=candidate_node_id,
                    target=node_id,
                    type=item.get("relationship") or "RELATED",
                )
            )

        return CandidateGraphResponse(
            candidate_id=candidate_node_id,
            nodes=list(nodes.values()),
            links=links,
        )

    def _node_id(self, label: str, props: dict[str, Any]) -> str:
        if label == "Skill":
            return f"skill-{props.get('name', '').lower()}"
        if label == "Technology":
            return f"tech-{props.get('name', '').lower()}"
        if label == "Project":
            return f"project-{props.get('id') or props.get('name', '')}"
        if label == "Education":
            return f"education-{props.get('institution', '')}"
        if label == "Experience":
            return f"experience-{props.get('id') or props.get('company', '')}"
        return f"{label.lower()}-{props.get('id', 'unknown')}"

    def _node_label(self, label: str, props: dict[str, Any]) -> str:
        if label in {"Skill", "Technology", "Project"}:
            return props.get("name") or label
        if label == "Education":
            return props.get("institution") or label
        if label == "Experience":
            company = props.get("company") or "Company"
            role = props.get("role")
            return f"{role} @ {company}" if role else company
        return props.get("name") or label
