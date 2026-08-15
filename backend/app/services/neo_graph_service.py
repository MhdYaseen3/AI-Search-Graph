"""
Neo4jGraphService — graph persistence layer for the resume processing
pipeline.

Per spec, nodes are kept minimal (a single `name` property each):

    (:Skill {name})
    (:Project {name})
    (:Education {name})
    (:Technology {name})

Relationships (all created with MERGE, so re-processing the same resume
never creates duplicates):

    (Candidate)-[:HAS_SKILL]->(Skill)
    (Candidate)-[:WORKED_ON]->(Project)
    (Candidate)-[:STUDIED_AT]->(Education)
    (Candidate)-[:USES_TECH]->(Technology)

ASSUMPTION (please verify against your actual Candidate nodes): this
service assumes Candidate nodes already exist and are matched by a
`candidate_id` property. If your Candidate CRUD layer keys nodes by a
different property (e.g. plain `id`), change CANDIDATE_ID_PROPERTY below
— every query in this file reads from that one constant.

NOTE ON Project/Education SHARING: because the spec defines Project and
Education nodes with only a `name` property (no candidate scoping), two
different candidates who both have a project literally titled "Portfolio
Website", or both studied "B.Tech - XYZ University", will MERGE onto the
*same* node and both link to it via WORKED_ON / STUDIED_AT. That's fine
(arguably useful — "everyone who studied at XYZ University" becomes a
single traversal) but flagging it in case you expected each candidate's
project to always be a distinct node.
"""

from __future__ import annotations

from typing import Dict, Optional

from neo4j import Driver, ManagedTransaction

from app.schemas.resume_parser import EducationItem, ParsedResume, ProjectItem
from app.db.nodes import education as EducationNode
from app.models import Education
from app.models.education import Education

CANDIDATE_ID_PROPERTY = "id"


def _education_name(edu: EducationItem) -> Optional[str]:
    """Collapse an EducationItem into the single display name the
    (:Education {name}) node stores."""
    if edu.degree and edu.institution:
        return f"{edu.degree} - {edu.institution}"
    if edu.institution:
        return edu.institution
    if edu.degree:
        return edu.degree
    if edu.raw_text:
        return edu.raw_text.strip()[:200]
    return None


def _project_name(project: ProjectItem) -> Optional[str]:
    if project.title:
        return project.title
    if project.raw_text:
        return project.raw_text.strip()[:200]
    return None


class Neo4jGraphService:
    """Persists extracted resume entities into the Neo4j graph."""

    def __init__(self, driver: Driver):
        self.driver = driver

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def ensure_constraints(self) -> None:
        """Create uniqueness constraints (idempotent — safe to call on
        every app startup). Keeps MERGE lookups fast as the graph grows.
        """
        statements = [
            "CREATE CONSTRAINT skill_name_unique IF NOT EXISTS "
            "FOR (s:Skill) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT project_name_unique IF NOT EXISTS "
            "FOR (p:Project) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT education_name_unique IF NOT EXISTS "
            "FOR (e:Education) REQUIRE e.name IS UNIQUE",
            "CREATE CONSTRAINT technology_name_unique IF NOT EXISTS "
            "FOR (t:Technology) REQUIRE t.name IS UNIQUE",
        ]
        with self.driver.session() as session:
            for statement in statements:
                session.execute_write(lambda tx, q=statement: tx.run(q))

    # ------------------------------------------------------------------
    # Per-entity link methods
    # ------------------------------------------------------------------

    def link_skill(self, candidate_id: str, skill_name: str) -> None:
        """MERGE a (:Skill {name}) node and a (Candidate)-[:HAS_SKILL]->(Skill) edge."""
        name = (skill_name or "").strip()
        if not candidate_id or not name:
            return
        with self.driver.session() as session:
            session.execute_write(self._link_skill_tx, candidate_id, name)

    async def link_project(self, candidate_id: str, project: ProjectItem) -> None:
        """MERGE a (:Project {name}) node and a (Candidate)-[:WORKED_ON]->(Project) edge."""
        name = _project_name(project)
        if not candidate_id or not name:
            return
        with self.driver.session() as session:
            await session.execute_write(self._link_project_tx, candidate_id, name)

    async def link_education(self, candidate_id: str, education: Education) -> None:
         """Create Education node and STUDIED_AT relationship."""
         
         await self.upsert_education(education)
     
         query = """
         MATCH (c:Candidate {id: $candidate_id})
         MATCH (e:Education {institution: $institution})
         MERGE (c)-[:STUDIED_AT]->(e)
         """
         print("LINK EDUCATION CALLED")
         print(candidate_id)
         print(education)
     
         await self.neo4j.execute_write(
             query,
             {
                 "candidate_id": candidate_id,
                 "institution": education.institution,
             },
         )
     
         logger.info(
             "Linked education %s to candidate %s",
             education.institution,
             candidate_id,
         )

    def link_technology(self, candidate_id: str, technology_name: str) -> None:
        """MERGE a (:Technology {name}) node and a (Candidate)-[:USES_TECH]->(Technology) edge."""
        name = (technology_name or "").strip()
        if not candidate_id or not name:
            return
        with self.driver.session() as session:
            session.execute_write(self._link_technology_tx, candidate_id, name)

    # ------------------------------------------------------------------
    # Orchestrator — used by process_resume()
    # ------------------------------------------------------------------

    def persist_resume_entities(
    self,
    candidate_id: str,
    parsed: ParsedResume,
) -> Dict[str, int]:

        skills_linked = 0
        for skill in parsed.skills:
            self.link_skill(candidate_id, skill)
            skills_linked += 1
    
        projects_linked = 0
        for project in parsed.projects:
            self.link_project(candidate_id, project)
            projects_linked += 1

        
        print("========== EDUCATION DEBUG ==========")
        print(parsed.education)
        print("====================================")
        print("EDUCATION LOOP STARTED")
        education_linked = 0
    for edu in parsed.education:
    
        print("EDU =", edu)
    
        name = str(edu).strip()
    
        print("NAME =", name)
    
        if not name:
            continue
    
        with self.driver.session() as session:
            print("WRITING TO NEO4J")
            session.execute_write(
                self._link_education_tx,
                candidate_id,
                name,
            )
     
        education_linked += 1
        
        technologies_linked = 0
        for tech in parsed.technologies:
            self.link_technology(candidate_id, tech)
            technologies_linked += 1
    
        return {
            "skills_linked": skills_linked,
            "projects_linked": projects_linked,
            "education_linked": education_linked,
            "technologies_linked": technologies_linked,
        }

    # ------------------------------------------------------------------
    # Write transactions
    # ------------------------------------------------------------------

    @staticmethod
    def _link_skill_tx(tx: ManagedTransaction, candidate_id: str, name: str) -> None:
        tx.run(
            f"""
            MATCH (c:Candidate {{{CANDIDATE_ID_PROPERTY}: $candidate_id}})
            MERGE (s:Skill {{name: $name}})
            MERGE (c)-[r:HAS_SKILL]->(s)
            ON CREATE SET r.created_at = datetime()
            """,
            candidate_id=candidate_id,
            name=name,
        )

    @staticmethod
    def _link_project_tx(tx: ManagedTransaction, candidate_id: str, name: str) -> None:
        tx.run(
            f"""
            MATCH (c:Candidate {{{CANDIDATE_ID_PROPERTY}: $candidate_id}})
            MERGE (p:Project {{name: $name}})
            MERGE (c)-[r:WORKED_ON]->(p)
            ON CREATE SET r.created_at = datetime()
            """,
            candidate_id=candidate_id,
            name=name,
        )

    @staticmethod
    def _link_education_tx(tx: ManagedTransaction, candidate_id: str, name: str) -> None:
        tx.run(
            f"""
            MATCH (c:Candidate {{{CANDIDATE_ID_PROPERTY}: $candidate_id}})
            MERGE (e:Education {{name: $name}})
            MERGE (c)-[r:STUDIED_AT]->(e)
            ON CREATE SET r.created_at = datetime()
            """,
            candidate_id=candidate_id,
            name=name,
        )

    @staticmethod
    def _link_technology_tx(tx: ManagedTransaction, candidate_id: str, name: str) -> None:
        tx.run(
            f"""
            MATCH (c:Candidate {{{CANDIDATE_ID_PROPERTY}: $candidate_id}})
            MERGE (t:Technology {{name: $name}})
            MERGE (c)-[r:USES_TECH]->(t)
            ON CREATE SET r.created_at = datetime()
            """,
            candidate_id=candidate_id,
            name=name,
        )


async def upsert_education(self, education: Education) -> Education:
    """Create or update an Education node."""
    node = EducationNode.from_domain(education)
    records = await self._merge_node(node)
    return EducationNode.from_neo4j(records[0]["n"]).to_domain()