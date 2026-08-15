import logging
from datetime import datetime

from app.core.exceptions import NotFoundError
from app.db.neo4j import Neo4jConnection
from app.db.nodes import JobNode
from app.models import Job
from app.schemas.job import JobCreate, JobUpdate
from app.services.neo4j_graph import Neo4jGraphService

logger = logging.getLogger(__name__)


class JobManagementService:
    """CRUD operations for job entities."""

    def __init__(self, neo4j: Neo4jConnection) -> None:
        self.neo4j = neo4j
        self.graph = Neo4jGraphService(neo4j)

    async def create(self, payload: JobCreate) -> Job:
        """Create a new job posting."""
        job = Job(**payload.model_dump())
        return await self.graph.upsert_job(job)

    async def get_by_id(self, job_id: str) -> Job:
        """Retrieve a job by ID."""
        return await self.graph.get_job(job_id)

    async def list_jobs(self, skip: int = 0, limit: int = 20) -> tuple[list[Job], int]:
        """List jobs with pagination."""
        count_query = "MATCH (j:Job) RETURN count(j) AS total"
        list_query = """
        MATCH (j:Job)
        RETURN j
        ORDER BY j.created_at DESC
        SKIP $skip
        LIMIT $limit
        """
        count_records = await self.neo4j.execute_read(count_query)
        total = count_records[0]["total"] if count_records else 0

        records = await self.neo4j.execute_read(list_query, {"skip": skip, "limit": limit})
        jobs = [JobNode.from_neo4j(record["j"]).to_domain() for record in records]
        return jobs, total

    async def list_jobs_by_status(self, status: str, skip: int = 0, limit: int = 20) -> tuple[list[Job], int]:
        """List jobs filtered by status."""
        count_query = "MATCH (j:Job {status: $status}) RETURN count(j) AS total"
        list_query = """
        MATCH (j:Job {status: $status})
        RETURN j
        ORDER BY j.created_at DESC
        SKIP $skip
        LIMIT $limit
        """
        params = {"status": status, "skip": skip, "limit": limit}
        count_records = await self.neo4j.execute_read(count_query, {"status": status})
        total = count_records[0]["total"] if count_records else 0

        records = await self.neo4j.execute_read(list_query, params)
        jobs = [JobNode.from_neo4j(record["j"]).to_domain() for record in records]
        return jobs, total

    async def search_jobs(self, query: str, skip: int = 0, limit: int = 20) -> tuple[list[Job], int]:
        """Search jobs by title, description, or skills."""
        search_pattern = f"%{query}%".lower()
        count_query = """
        MATCH (j:Job)
        WHERE toLower(j.title) CONTAINS toLower($search) 
           OR toLower(j.description) CONTAINS toLower($search)
           OR any(skill in j.required_skills WHERE toLower(skill) CONTAINS toLower($search))
           OR toLower(j.location) CONTAINS toLower($search)
        RETURN count(j) AS total
        """
        list_query = """
        MATCH (j:Job)
        WHERE toLower(j.title) CONTAINS toLower($search)
           OR toLower(j.description) CONTAINS toLower($search)
           OR any(skill in j.required_skills WHERE toLower(skill) CONTAINS toLower($search))
           OR toLower(j.location) CONTAINS toLower($search)
        RETURN j
        ORDER BY j.created_at DESC
        SKIP $skip
        LIMIT $limit
        """
        params = {"search": query, "skip": skip, "limit": limit}
        count_records = await self.neo4j.execute_read(count_query, {"search": query})
        total = count_records[0]["total"] if count_records else 0

        records = await self.neo4j.execute_read(list_query, params)
        jobs = [JobNode.from_neo4j(record["j"]).to_domain() for record in records]
        return jobs, total

    async def update(self, job_id: str, payload: JobUpdate) -> Job:
        """Update an existing job."""
        job = await self.get_by_id(job_id)
        update_data = payload.model_dump(exclude_unset=True)
        updated = job.model_copy(
            update={**update_data, "updated_at": datetime.utcnow()}
        )
        return await self.graph.upsert_job(updated)

    async def delete(self, job_id: str) -> None:
        """Delete a job and related graph nodes."""
        await self.graph.delete_job(job_id)
        logger.info("Deleted job %s", job_id)
