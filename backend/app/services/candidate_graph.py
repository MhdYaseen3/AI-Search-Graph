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
    "Candidate": "candidate",
    "Job": "job",
    "JobApplication": "application",
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

    async def get_global_candidate_graph(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> CandidateGraphResponse:
        """Return a page of candidates and their persisted adjacent relationships."""
        count_records = await self.neo4j.execute_read(
            "MATCH (c:Candidate) RETURN count(c) AS total"
        )
        total = int(count_records[0].get("total") or 0) if count_records else 0
        records = await self.neo4j.execute_read(
            """
            MATCH (c:Candidate)
            OPTIONAL MATCH (c)-[r]-(n)
            WITH c,
                 collect(DISTINCT n) AS neighbors,
                 collect(DISTINCT CASE
                WHEN r IS NULL THEN null
                ELSE {
                    relationship_id: elementId(r),
                    relationship: type(r),
                    source_labels: labels(startNode(r)),
                    source_properties: properties(startNode(r)),
                    target_labels: labels(endNode(r)),
                    target_properties: properties(endNode(r))
                }
            END) AS direct_relationships
            UNWIND CASE
                WHEN size(neighbors) = 0 THEN [null]
                ELSE neighbors
            END AS neighbor
            OPTIONAL MATCH (neighbor)-[r2]-(other)
            WHERE other IS NULL OR other <> c
            WITH c,
                 direct_relationships,
                 collect(DISTINCT CASE
                     WHEN r2 IS NULL THEN null
                     ELSE {
                         relationship_id: elementId(r2),
                         relationship: type(r2),
                         source_labels: labels(startNode(r2)),
                         source_properties: properties(startNode(r2)),
                         target_labels: labels(endNode(r2)),
                         target_properties: properties(endNode(r2))
                     }
                 END) AS adjacent_relationships
            RETURN c.id AS candidate_id,
                   c.full_name AS candidate_name,
                   direct_relationships + adjacent_relationships AS related
            ORDER BY candidate_id
            SKIP $skip
            LIMIT $limit
            """,
            {"skip": skip, "limit": limit},
        )

        nodes: dict[str, GraphNodeResponse] = {}
        links: dict[str, GraphLinkResponse] = {}
        for record in records:
            candidate_id = record["candidate_id"]
            nodes[candidate_id] = GraphNodeResponse(
                id=candidate_id,
                label=record.get("candidate_name") or "Candidate",
                type="candidate",
            )
            for item in record.get("related", []):
                if not item:
                    continue
                endpoint_ids: dict[str, str] = {}
                for endpoint in ("source", "target"):
                    labels = item.get(f"{endpoint}_labels") or []
                    label_name = labels[0] if labels else "Node"
                    properties = item.get(f"{endpoint}_properties") or {}
                    endpoint_id = self._node_id(label_name, properties)
                    endpoint_ids[endpoint] = endpoint_id
                    nodes.setdefault(
                        endpoint_id,
                        GraphNodeResponse(
                            id=endpoint_id,
                            label=self._node_label(label_name, properties),
                            type=_NODE_TYPE_MAP.get(label_name, "project"),
                        ),
                    )
                source, target = endpoint_ids["source"], endpoint_ids["target"]
                relationship = item.get("relationship") or "RELATED"
                relationship_id = item.get("relationship_id")
                key = relationship_id or f"{source}|{target}|{relationship}"
                links[key] = GraphLinkResponse(
                    id=relationship_id,
                    source=source,
                    target=target,
                    type=relationship,
                )

        return CandidateGraphResponse(
            candidate_id="global",
            total=total,
            skip=skip,
            limit=limit,
            nodes=list(nodes.values()),
            links=list(links.values()),
        )

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
            if exp and (exp.get("company") or exp.get("role"))
        ]
        education = [
            EducationDetailResponse(
                institution=item.get("institution"),
                degree=item.get("degree"),
            )
            for item in record.get("education", [])
            if item and item.get("institution")
        ]

        # Generate deterministic profile if summary is missing
        summary = record.get("summary")
        if not summary:
            summary = self._generate_profile_summary(
                record["full_name"],
                experiences,
                record.get("skills", []),
                record.get("technologies", []),
                record.get("projects", []),
                education,
            )

        return CandidateDetailResponse(
            id=record["id"],
            full_name=record["full_name"],
            email=record.get("email"),
            phone=record.get("phone"),
            location=record.get("location"),
            summary=summary,
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
        if label == "Candidate":
            return str(props.get("id", "unknown"))
        if label in {"Job", "JobApplication"}:
            prefix = "job" if label == "Job" else "application"
            return f"{prefix}-{props.get('id', 'unknown')}"
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
        if label == "Job":
            return props.get("title") or label
        if label == "JobApplication":
            status = props.get("status")
            return f"Application · {status}" if status else label
        if label in {"Skill", "Technology", "Project"}:
            return props.get("name") or label
        if label == "Education":
            return props.get("institution") or label
        if label == "Experience":
            company = props.get("company") or "Company"
            role = props.get("role")
            return f"{role} @ {company}" if role else company
        return props.get("name") or label

    def _generate_profile_summary(
        self,
        full_name: str,
        experiences: list[dict[str, Any]],
        skills: list[str],
        technologies: list[str],
        projects: list[str],
        education: list[EducationDetailResponse],
    ) -> str:
        """Generate deterministic profile summary from real candidate data."""
        parts: list[str] = []

        # Count experience entries (includes internships)
        exp_count = len(experiences)
        if exp_count > 0:
            if exp_count == 1:
                parts.append(f"{full_name} has experience through 1 position.")
            else:
                parts.append(f"{full_name} has experience through {exp_count} positions.")
        else:
            parts.append(f"{full_name} is a candidate.")

        # Add skills/technologies if available
        all_tech = skills + technologies
        if all_tech:
            tech_sample = all_tech[:5]
            if len(all_tech) > 5:
                parts.append(f"Technical experience includes {', '.join(tech_sample)} and {len(all_tech) - 5} more.")
            else:
                parts.append(f"Technical experience includes {', '.join(tech_sample)}.")

        # Add projects if available
        if projects:
            if len(projects) == 1:
                parts.append(f"Has worked on projects including {projects[0]}.")
            else:
                parts.append(f"Has worked on projects including {', '.join(projects[:2])}.")

        # Add education if available
        if education:
            edu_sample = education[0]
            if edu_sample.institution:
                parts.append(f"Education includes {edu_sample.institution}.")

        return " ".join(parts)
