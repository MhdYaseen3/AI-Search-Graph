import asyncio
import logging
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from neo4j import AsyncTransaction

from app.core.exceptions import NotFoundError
from app.db.neo4j import Neo4jConnection
from app.db.nodes import JobNode
from app.models import Job
from app.schemas.job import (
    ApplicationStatus,
    JobApplicationResponse,
    JobCreate,
    JobUpdate,
)
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
        count_records, records = await asyncio.gather(
            self.neo4j.execute_read(count_query),
            self.neo4j.execute_read(list_query, {"skip": skip, "limit": limit}),
        )
        total = count_records[0]["total"] if count_records else 0
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
        count_records, records = await asyncio.gather(
            self.neo4j.execute_read(count_query, {"status": status}),
            self.neo4j.execute_read(list_query, params),
        )
        total = count_records[0]["total"] if count_records else 0
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
        count_records, records = await asyncio.gather(
            self.neo4j.execute_read(count_query, {"search": query}),
            self.neo4j.execute_read(list_query, params),
        )
        total = count_records[0]["total"] if count_records else 0
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

    async def list_applicants(
        self,
        job_id: str,
    ) -> list[JobApplicationResponse]:
        await self.get_by_id(job_id)
        records = await self.neo4j.execute_read(
            """
            MATCH (j:Job {id: $job_id})-[:HAS_APPLICATION]->(a:JobApplication)
                  -[:FOR_CANDIDATE]->(c:Candidate)
            RETURN a.id AS id,
                   a.job_id AS job_id,
                   a.candidate_id AS candidate_id,
                   c.full_name AS full_name,
                   c.email AS email,
                   c.summary AS summary,
                   a.status AS status,
                   a.created_at AS created_at,
                   a.updated_at AS updated_at
            ORDER BY a.created_at DESC
            """,
            {"job_id": job_id},
        )
        return [JobApplicationResponse.model_validate(record) for record in records]

    async def add_applicant(
        self,
        job_id: str,
        candidate_id: str,
    ) -> JobApplicationResponse:
        now = datetime.utcnow().isoformat()
        application_id = str(uuid5(NAMESPACE_URL, f"graphcv-job:{job_id}:{candidate_id}"))

        async def create(tx: AsyncTransaction) -> dict | None:
            result = await tx.run(
                """
                MATCH (j:Job {id: $job_id})
                MATCH (c:Candidate {id: $candidate_id})
                MERGE (a:JobApplication {id: $application_id})
                ON CREATE SET
                    a.job_id = $job_id,
                    a.candidate_id = $candidate_id,
                    a.status = 'Applied',
                    a.created_at = $now,
                    a.updated_at = $now
                MERGE (j)-[:HAS_APPLICATION]->(a)
                MERGE (a)-[:FOR_CANDIDATE]->(c)
                RETURN a.id AS id,
                       a.job_id AS job_id,
                       a.candidate_id AS candidate_id,
                       c.full_name AS full_name,
                       c.email AS email,
                       c.summary AS summary,
                       a.status AS status,
                       a.created_at AS created_at,
                       a.updated_at AS updated_at
                """,
                {
                    "job_id": job_id,
                    "candidate_id": candidate_id,
                    "application_id": application_id,
                    "now": now,
                },
            )
            records = await result.data()
            return records[0] if records else None

        record = await self.neo4j.execute_write_transaction(create)
        if record:
            return JobApplicationResponse.model_validate(record)
        await self.get_by_id(job_id)
        raise NotFoundError(f"Candidate {candidate_id} not found")

    async def update_applicant_status(
        self,
        job_id: str,
        candidate_id: str,
        status: ApplicationStatus,
    ) -> JobApplicationResponse:
        now = datetime.utcnow().isoformat()
        records = await self.neo4j.execute_write(
            """
            MATCH (j:Job {id: $job_id})-[:HAS_APPLICATION]->(a:JobApplication {
                job_id: $job_id,
                candidate_id: $candidate_id
            })-[:FOR_CANDIDATE]->(c:Candidate {id: $candidate_id})
            SET a.status = $status,
                a.updated_at = $now
            RETURN a.id AS id,
                   a.job_id AS job_id,
                   a.candidate_id AS candidate_id,
                   c.full_name AS full_name,
                   c.email AS email,
                   c.summary AS summary,
                   a.status AS status,
                   a.created_at AS created_at,
                   a.updated_at AS updated_at
            """,
            {
                "job_id": job_id,
                "candidate_id": candidate_id,
                "status": status,
                "now": now,
            },
        )
        if not records:
            await self.get_by_id(job_id)
            raise NotFoundError(
                f"Application for candidate {candidate_id} not found"
            )
        return JobApplicationResponse.model_validate(records[0])
