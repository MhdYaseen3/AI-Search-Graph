import logging
from datetime import datetime, timezone
from typing  import Any, TypeVar

from neo4j import AsyncTransaction

from app.core.exceptions import DatabaseError, NotFoundError
from app.db.neo4j import Neo4jConnection
from app.db.nodes import (
    CandidateNode,
    GraphNode,
    JobNode,
    ProjectNode,
    SkillNode,
    TechnologyNode,
    EducationNode,
    ExperienceNode,
)

from app.db.relationships import (
    HAS_SKILL,
    PROJECT_USES,
    USES_TECHNOLOGY,
    WORKED_ON,
    WORKED_AT,
    STUDIED_AT,
)

from app.models import (
    Candidate,
    Education,
    Experience,
    Job,
    Project,
    Skill,
    Technology,
)
from app.db.nodes.education import EducationNode
# from backend.app.models import experience
# from backend.app.db.nodes import experience

logger = logging.getLogger(__name__)

NodeT = TypeVar("NodeT", bound=GraphNode)


class Neo4jGraphService:
    """Manages knowledge graph nodes and relationships in Neo4j."""

    def __init__(self, neo4j: Neo4jConnection) -> None:
        self.neo4j = neo4j

    async def upsert_candidate(self, candidate: Candidate) -> Candidate:
        """Create or update a Candidate node."""
        node = CandidateNode.from_domain(candidate)
        records = await self._merge_node(node)
        return CandidateNode.from_neo4j(records[0]["n"]).to_domain()

    async def persist_resume_graph(
        self,
        candidate: Candidate,
        skills: list[Skill],
        projects: list[Project],
        education: list[Education],
        experiences: list[Experience],
        technologies: list[Technology],
        *,
        gmail_message_id: str,
        gmail_attachment_id: str,
        filename: str,
        sha256: str,
    ) -> None:
        """Persist a Gmail resume and its graph relationships atomically."""
        async def persist(tx: AsyncTransaction) -> None:
            await self._merge_node_in_transaction(
                tx,
                CandidateNode.from_domain(candidate),
            )

            for skill in skills:
                await self._merge_node_in_transaction(
                    tx,
                    SkillNode.from_domain(skill),
                )
                await self._run_transaction_write(
                    tx,
                    f"""
                    MATCH (c:Candidate {{id: $candidate_id}})
                    MATCH (s:Skill {{name: $name}})
                    MERGE (c)-[:{HAS_SKILL}]->(s)
                    """,
                    {
                        "candidate_id": candidate.id,
                        "name": skill.name.strip(),
                    },
                )

            for project in projects:
                await self._merge_node_in_transaction(
                    tx,
                    ProjectNode.from_domain(project),
                )
                await self._run_transaction_write(
                    tx,
                    f"""
                    MATCH (c:Candidate {{id: $candidate_id}})
                    MATCH (p:Project {{id: $project_id}})
                    MERGE (c)-[:{WORKED_ON}]->(p)
                    """,
                    {
                        "candidate_id": candidate.id,
                        "project_id": project.id,
                    },
                )

            for institution in education:
                await self._merge_node_in_transaction(
                    tx,
                    EducationNode.from_domain(institution),
                )
                await self._run_transaction_write(
                    tx,
                    f"""
                    MATCH (c:Candidate {{id: $candidate_id}})
                    MATCH (e:Education {{institution: $institution}})
                    MERGE (c)-[:{STUDIED_AT}]->(e)
                    """,
                    {
                        "candidate_id": candidate.id,
                        "institution": institution.institution,
                    },
                )

            for experience in experiences:
                await self._merge_node_in_transaction(
                    tx,
                    ExperienceNode.from_domain(experience),
                )
                await self._run_transaction_write(
                    tx,
                    f"""
                    MATCH (c:Candidate {{id: $candidate_id}})
                    MATCH (e:Experience {{id: $experience_id}})
                    MERGE (c)-[:{WORKED_AT}]->(e)
                    """,
                    {
                        "candidate_id": candidate.id,
                        "experience_id": experience.id,
                    },
                )

            for technology in technologies:
                await self._merge_node_in_transaction(
                    tx,
                    TechnologyNode.from_domain(technology),
                )
                await self._run_transaction_write(
                    tx,
                    f"""
                    MATCH (c:Candidate {{id: $candidate_id}})
                    MATCH (t:Technology {{name: $name}})
                    MERGE (c)-[:{USES_TECHNOLOGY}]->(t)
                    """,
                    {
                        "candidate_id": candidate.id,
                        "name": technology.name.strip(),
                    },
                )

            await self._run_transaction_write(
                tx,
                """
                MERGE (a:GmailAttachment {
                    message_id: $message_id,
                    attachment_id: $attachment_id
                })
                SET a.source = 'gmail',
                    a.status = 'SUCCESS',
                    a.sha256 = $sha256,
                    a.imported_at = coalesce(a.imported_at, $processed_at),
                    a.updated_at = $processed_at,
                    a.candidate_id = $candidate_id,
                    a.filename = $filename,
                    a.failure_reason = null
                """,
                {
                    "message_id": gmail_message_id,
                    "attachment_id": gmail_attachment_id,
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "sha256": sha256,
                    "candidate_id": candidate.id,
                    "filename": filename,
                },
            )
            await self._run_transaction_write(
                tx,
                """
                MATCH (h:GmailAttachmentHash {sha256: $sha256})
                WHERE h.message_id = $message_id
                  AND h.attachment_id = $attachment_id
                SET h.status = 'SUCCESS',
                    h.candidate_id = $candidate_id,
                    h.failure_reason = null,
                    h.updated_at = $now
                """,
                {
                    "sha256": sha256,
                    "message_id": gmail_message_id,
                    "attachment_id": gmail_attachment_id,
                    "candidate_id": candidate.id,
                    "now": datetime.now(timezone.utc).isoformat(),
                },
            )

        await self.neo4j.execute_write_transaction(persist)

    @staticmethod
    async def _merge_node_in_transaction(
        tx: AsyncTransaction,
        node: GraphNode,
    ) -> None:
        result = await tx.run(node.merge_query(), node.merge_parameters())
        await result.consume()

    @staticmethod
    async def _run_transaction_write(
        tx: AsyncTransaction,
        query: str,
        parameters: dict[str, Any],
    ) -> None:
        result = await tx.run(query, parameters)
        await result.consume()

    async def get_candidate(self, candidate_id: str) -> Candidate:
        """Fetch a Candidate node by ID."""
        query = """
        MATCH (c:Candidate {id: $id})
        RETURN c AS n
        """
        records = await self.neo4j.execute_read(query, {"id": candidate_id})
        if not records:
            raise NotFoundError(f"Candidate {candidate_id} not found")
        return CandidateNode.from_neo4j(records[0]["n"]).to_domain()

    async def upsert_skill(self, skill: Skill) -> Skill:
        """Create or update a Skill node."""
        node = SkillNode.from_domain(skill)
        records = await self._merge_node(node)
        return SkillNode.from_neo4j(records[0]["n"]).to_domain()

    async def upsert_project(self, project: Project) -> Project:
        """Create or update a Project node."""
        node = ProjectNode.from_domain(project)
        records = await self._merge_node(node)
        return ProjectNode.from_neo4j(records[0]["n"]).to_domain()

    async def get_project(self, project_id: str) -> Project:
        """Fetch a Project node by ID."""
        query = """
        MATCH (p:Project {id: $id})
        RETURN p AS n
        """
        records = await self.neo4j.execute_read(query, {"id": project_id})
        if not records:
            raise NotFoundError(f"Project {project_id} not found")
        return ProjectNode.from_neo4j(records[0]["n"]).to_domain()

    async def upsert_job(self, job: Job) -> Job:
        """Create or update a Job node."""
        node = JobNode.from_domain(job)
        records = await self._merge_node(node)
        return JobNode.from_neo4j(records[0]["n"]).to_domain()

    async def get_job(self, job_id: str) -> Job:
        """Fetch a Job node by ID."""
        query = """
        MATCH (j:Job {id: $id})
        RETURN j AS n
        """
        records = await self.neo4j.execute_read(query, {"id": job_id})
        if not records:
            raise NotFoundError(f"Job {job_id} not found")
        return JobNode.from_neo4j(records[0]["n"]).to_domain()

    async def delete_job(self, job_id: str) -> None:
        """Delete job node and detach all relationships."""
        query = """
        MATCH (j:Job {id: $job_id})
        DETACH DELETE j
        RETURN count(j) AS deleted
        """
        records = await self.neo4j.execute_write(query, {"job_id": job_id})
        if not records or records[0].get("deleted", 0) == 0:
            raise NotFoundError(f"Job {job_id} not found")
    
    async def upsert_education(self, education: Education) -> Education:
         """Create or update an Education node."""
         node = EducationNode.from_domain(education)
         records = await self._merge_node(node)
         return EducationNode.from_neo4j(records[0]["n"]).to_domain()

    async def upsert_experience(self, experience: Experience) -> Experience:
         """Create or update an Experience node."""
         node = ExperienceNode.from_domain(experience)
         records = await self._merge_node(node)  
         return ExperienceNode.from_neo4j(records[0]["n"]).to_domain()
  
    async def upsert_technology(self, technology: Technology) -> Technology:
        """Create or update a Technology node."""
        node = TechnologyNode.from_domain(technology)
        records = await self._merge_node(node)
        return TechnologyNode.from_neo4j(records[0]["n"]).to_domain()

    async def link_skill(self, candidate_id: str, skill: Skill) -> None:
        """Create Skill node and HAS_SKILL relationship."""
        await self.upsert_skill(skill)
        query = f"""
        MATCH (c:Candidate {{id: $candidate_id}})
        MATCH (s:Skill {{name: $name}})
        MERGE (c)-[:{HAS_SKILL}]->(s)
        """
        await self.neo4j.execute_write(
            query,
            {"candidate_id": candidate_id, "name": skill.name.strip()},
        )
        logger.info("Linked skill %s to candidate %s", skill.name, candidate_id)

    async def link_project(self, candidate_id: str, project: Project) -> None:
        """Create Project node and WORKED_ON relationship."""
        await self.upsert_project(project)
        query = f"""
        MATCH (c:Candidate {{id: $candidate_id}})
        MATCH (p:Project {{id: $project_id}})
        MERGE (c)-[:{WORKED_ON}]->(p)
        """
        await self.neo4j.execute_write(
            query,
            {"candidate_id": candidate_id, "project_id": project.id},
        )
        logger.info("Linked project %s to candidate %s", project.name, candidate_id)


    async def link_education(self, candidate_id: str, education: Education) -> None:
        """Create Education node and STUDIED_AT relationship."""
        logger.debug("Upserting education node %s", education.institution)
        await self.upsert_education(education)

        query = """
        MATCH (c:Candidate {id: $candidate_id})
        MATCH (e:Education {institution: $institution})
        MERGE (c)-[:STUDIED_AT]->(e)
        """
        params = {
            "candidate_id": candidate_id,
            "institution": education.institution,
        }
        logger.debug("Linking education with params=%s", params)
        records = await self.neo4j.execute_write(query, params)
        logger.info("Linked education %s to candidate %s", education.institution, candidate_id)
        logger.debug("Education link query returned %s records", records)

    async def link_experience(
     self,
     candidate_id: str,
     experience: Experience,
 ) -> None:
     """Create Experience node and WORKED_AT relationship."""
 
     await self.upsert_experience(experience)
 
     query = f"""
     MATCH (c:Candidate {{id: $candidate_id}})
     MATCH (e:Experience {{id: $experience_id}})
     MERGE (c)-[:{WORKED_AT}]->(e)
     """
 
     await self.neo4j.execute_write(
         query,
         {
             "candidate_id": candidate_id,
             "experience_id": experience.id,
         },
     )
 
     logger.info(
         "Linked experience %s at %s to candidate %s",
         experience.role,
         experience.company,
         candidate_id,
     )

    async def link_technology(self, candidate_id: str, technology: Technology) -> None:
        """Create Technology node and USES_TECHNOLOGY relationship."""
        await self.upsert_technology(technology)
        query = f"""
        MATCH (c:Candidate {{id: $candidate_id}})
        MATCH (t:Technology {{name: $name}})
        MERGE (c)-[:{USES_TECHNOLOGY}]->(t)
        """
        await self.neo4j.execute_write(
            query,
            {"candidate_id": candidate_id, "name": technology.name.strip()},
        )
        logger.info("Linked technology %s to candidate %s", technology.name, candidate_id)

    async def link_project_technology(self, project_id: str, technology: Technology) -> None:
        """Link a project to a technology via PROJECT_USES."""
        await self.upsert_technology(technology)
        query = f"""
        MATCH (p:Project {{id: $project_id}})
        MATCH (t:Technology {{name: $name}})
        MERGE (p)-[:{PROJECT_USES}]->(t)
        """
        await self.neo4j.execute_write(
            query,
            {"project_id": project_id, "name": technology.name.strip()},
        )

    async def get_candidate_subgraph(self, candidate_id: str) -> dict[str, Any]:
        """Retrieve candidate and all related nodes."""
        query = """
        MATCH (c:Candidate {id: $candidate_id})
        OPTIONAL MATCH (c)-[r]->(n)
        RETURN c,
               collect({
                   relationship: type(r),
                   node_labels: labels(n),
                   properties: properties(n)
               }) AS relationships
        """
        records = await self.neo4j.execute_read(query, {"candidate_id": candidate_id})
        if not records:
            raise NotFoundError(f"Candidate {candidate_id} not found")

        candidate = CandidateNode.from_neo4j(records[0]["c"]).to_domain()
        return {
            "candidate": candidate.model_dump(),    
            "relationships": records[0]["relationships"],
        }

    async def delete_candidate(self, candidate_id: str) -> None:
        """Delete candidate node and detach all relationships."""
        query = """
        MATCH (c:Candidate {id: $candidate_id})
        DETACH DELETE c
        RETURN count(c) AS deleted
        """
        records = await self.neo4j.execute_write(query, {"candidate_id": candidate_id})
        if not records or records[0].get("deleted", 0) == 0:
            raise NotFoundError(f"Candidate {candidate_id} not found")

    async def _merge_node(self, node: NodeT) -> list[dict[str, Any]]:
        records = await self.neo4j.execute_write(
            node.merge_query(),
            node.merge_parameters(),
        )
        if not records:
            raise DatabaseError(f"Failed to upsert {node.label} node")
        return records
