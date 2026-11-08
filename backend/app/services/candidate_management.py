import asyncio
import logging
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from app.core.exceptions import NotFoundError
from app.db.neo4j import Neo4jConnection
from app.db.nodes import CandidateNode
from app.models import Candidate, Education, Experience, Project, Skill, Technology
from app.schemas.candidate import CandidateCreate, CandidateUpdate
from app.services.neo4j_graph import Neo4jGraphService

logger = logging.getLogger(__name__)


class CandidateManagementService:
    """CRUD operations for candidate entities."""

    def __init__(self, neo4j: Neo4jConnection) -> None:
        self.neo4j = neo4j
        self.graph = Neo4jGraphService(neo4j)

    async def create(self, payload: CandidateCreate) -> Candidate:
        """Create a new candidate record."""
        candidate = Candidate(**payload.model_dump())
        return await self.graph.upsert_candidate(candidate)

    async def create_gmail_candidate(
        self,
        payload: CandidateCreate,
        skills: list[Skill],
        projects: list[Project],
        education: list[Education],
        experiences: list[Experience],
        technologies: list[Technology],
        *,
        message_id: str,
        attachment_id: str,
        filename: str,
        sha256: str,
    ) -> Candidate:
        """Create or match a Gmail candidate and atomically persist its graph."""
        normalized_email = (payload.email or "").strip().casefold()
        normalized_name = " ".join(payload.full_name.casefold().split())
        existing = None
        if normalized_email:
            records = await self.neo4j.execute_read(
                """
                MATCH (c:Candidate)
                WHERE c.email IS NOT NULL
                  AND toLower(trim(c.email)) = $email
                  AND toLower(trim(c.full_name)) = $full_name
                RETURN c
                ORDER BY c.created_at ASC
                LIMIT 1
                """,
                {
                    "email": normalized_email,
                    "full_name": normalized_name,
                },
            )
            if records:
                existing = CandidateNode.from_neo4j(records[0]["c"]).to_domain()
        identity = (
            f"gmail-email:{normalized_email}:{normalized_name}"
            if normalized_email
            else f"gmail-attachment:{message_id}:{attachment_id}"
        )
        candidate_id = existing.id if existing else str(
            uuid5(NAMESPACE_URL, identity)
        )
        candidate = Candidate(
            id=candidate_id,
            **payload.model_dump(),
        )

        stable_projects = [
            project.model_copy(
                update={
                    "id": self._gmail_entity_id(
                        candidate_id,
                        "project",
                        project.name,
                        project.description,
                        project.role,
                        project.start_date,
                        project.end_date,
                    )
                }
            )
            for project in projects
        ]
        stable_experiences = [
            experience.model_copy(
                update={
                    "id": self._gmail_entity_id(
                        candidate_id,
                        "experience",
                        experience.company,
                        experience.role,
                        experience.description,
                        experience.duration,
                        experience.start_date,
                        experience.end_date,
                    )
                }
            )
            for experience in experiences
        ]

        await self.graph.persist_resume_graph(
            candidate,
            skills,
            stable_projects,
            education,
            stable_experiences,
            technologies,
            gmail_message_id=message_id,
            gmail_attachment_id=attachment_id,
            filename=filename,
            sha256=sha256,
        )
        return candidate

    @staticmethod
    def _gmail_entity_id(candidate_id: str, kind: str, *parts: str | None) -> str:
        identity = "\x1f".join(
            [kind, candidate_id, *(part or "" for part in parts)]
        )
        return str(uuid5(NAMESPACE_URL, identity))

    async def get_by_id(self, candidate_id: str) -> Candidate:
        """Retrieve a candidate by ID."""
        return await self.graph.get_candidate(candidate_id)

    async def list_candidates(self, skip: int = 0, limit: int = 20) -> tuple[list[Candidate], int]:
        """List candidates with pagination."""
        count_query = "MATCH (c:Candidate) RETURN count(c) AS total"
        list_query = """
        MATCH (c:Candidate)
        RETURN c
        ORDER BY c.created_at DESC
        SKIP $skip
        LIMIT $limit
        """
        count_records, records = await asyncio.gather(
            self.neo4j.execute_read(count_query),
            self.neo4j.execute_read(list_query, {"skip": skip, "limit": limit}),
        )
        total = count_records[0]["total"] if count_records else 0
        candidates = [CandidateNode.from_neo4j(record["c"]).to_domain() for record in records]
        return candidates, total

    async def update(self, candidate_id: str, payload: CandidateUpdate) -> Candidate:
        """Update an existing candidate."""
        candidate = await self.get_by_id(candidate_id)
        update_data = payload.model_dump(exclude_unset=True)
        updated = candidate.model_copy(
            update={**update_data, "updated_at": datetime.utcnow()}
        )
        return await self.graph.upsert_candidate(updated)

    async def delete(self, candidate_id: str) -> None:
        """Delete a candidate and related graph nodes."""
        await self.graph.delete_candidate(candidate_id)
        logger.info("Deleted candidate %s", candidate_id)

    async def get_by_email(self, email: str) -> Candidate | None:
        """Find a candidate by email address."""
        query = """
        MATCH (c:Candidate)
        WHERE c.email IS NOT NULL AND toLower(trim(c.email)) = $email
        RETURN c
        ORDER BY c.created_at ASC
        LIMIT 1
        """
    
        records = await self.neo4j.execute_read(
            query,
            {"email": email},
        )
    
        if not records:
            return None
    
        return CandidateNode.from_neo4j(records[0]["c"]).to_domain()