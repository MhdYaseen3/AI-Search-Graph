import logging
from datetime import datetime

from app.core.exceptions import NotFoundError
from app.db.neo4j import Neo4jConnection
from app.db.nodes import CandidateNode
from app.models import Candidate
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
        count_records = await self.neo4j.execute_read(count_query)
        total = count_records[0]["total"] if count_records else 0

        records = await self.neo4j.execute_read(list_query, {"skip": skip, "limit": limit})
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
        MATCH (c:Candidate {email: $email})
        RETURN c
        LIMIT 1
        """
    
        records = await self.neo4j.execute_read(
            query,
            {"email": email},
        )
    
        if not records:
            return None
    
        return CandidateNode.from_neo4j(records[0]["c"]).to_domain()