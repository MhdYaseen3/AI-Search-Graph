"""
Neo4j Relationship Builder.

Takes a candidate's parsed resume data (ParsedResume — see
app.schemas.resume_parser) and writes it into the Neo4j knowledge graph:

    (Candidate)-[:KNOWS]->(Skill)
    (Candidate)-[:BUILT]->(Project)
    (Candidate)-[:STUDIED]->(Education)

Every write uses MERGE, so re-running this for the same candidate (e.g.
after a resume re-upload, or a retried request) never creates duplicate
nodes or duplicate relationships.

Wiring:
    This service takes a `neo4j.Driver` via constructor injection rather
    than reaching for a global connection, so it can reuse whatever
    driver instance your app/db layer already creates ("Neo4j connected"
    in your completed features) and stays easy to unit test with a mock.

        from app.services.neo4j_relationship_builder import Neo4jRelationshipBuilder
        from app.db.neo4j_driver import driver  # however your db/ layer exposes it

        builder = Neo4jRelationshipBuilder(driver)
        builder.ensure_constraints()  # call once, e.g. on app startup
        summary = builder.build_candidate_graph(candidate_id, parsed_resume)
"""

from __future__ import annotations

import re
from typing import Dict, Optional

from neo4j import Driver, ManagedTransaction

from app.schemas.resume_parser import EducationItem, ParsedResume, ProjectItem


def _normalize(text: Optional[str]) -> str:
    """Lowercase + collapse whitespace.

    Used as the MERGE key for Skill/Education nodes so 'Python',
    ' python', and 'PYTHON' all resolve to the same node instead of
    creating near-duplicate entries.
    """
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip().lower())


class Neo4jRelationshipBuilder:
    """Writes a ParsedResume into the Neo4j graph for a given candidate."""

    def __init__(self, driver: Driver):
        self.driver = driver

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_candidate_graph(self, candidate_id: str, parsed: ParsedResume) -> Dict[str, int]:
        """Create/update the Candidate node and all KNOWS / BUILT / STUDIED
        relationships described by `parsed`.

        Safe to call multiple times for the same candidate_id — every
        write is a MERGE, so existing nodes/relationships are matched
        and updated rather than duplicated.

        Returns a summary dict (counts written) useful for logging or
        returning from an API endpoint.
        """
        if not candidate_id:
            raise ValueError("candidate_id is required to build the graph")

        with self.driver.session() as session:
            session.execute_write(
                self._merge_candidate,
                candidate_id,
                parsed.candidate_name,
                parsed.email,
                parsed.phone,
            )

            skills_written = 0
            for skill in parsed.skills:
                if skill and skill.strip():
                    session.execute_write(self._merge_skill, candidate_id, skill.strip())
                    skills_written += 1

            projects_written = 0
            for project in parsed.projects:
                if project.title or project.raw_text:
                    session.execute_write(self._merge_project, candidate_id, project)
                    projects_written += 1

            education_written = 0
            for edu in parsed.education:
                if edu.institution or edu.degree or edu.raw_text:
                    session.execute_write(self._merge_education, candidate_id, edu)
                    education_written += 1

        return {
            "candidate_id": candidate_id,
            "skills_written": skills_written,
            "projects_written": projects_written,
            "education_written": education_written,
        }

    def ensure_constraints(self) -> None:
        """Create uniqueness constraints (idempotent — safe to call on
        every app startup, e.g. in main.py's startup event).

        Without these, MERGE has to fall back to a label scan to check
        for an existing node, which gets slow as the graph grows. Each
        constraint also implicitly creates a backing index.
        """
        statements = [
            "CREATE CONSTRAINT candidate_id_unique IF NOT EXISTS "
            "FOR (c:Candidate) REQUIRE c.candidate_id IS UNIQUE",
            "CREATE CONSTRAINT skill_name_unique IF NOT EXISTS "
            "FOR (s:Skill) REQUIRE s.name_normalized IS UNIQUE",
            "CREATE CONSTRAINT project_key_unique IF NOT EXISTS "
            "FOR (p:Project) REQUIRE p.project_key IS UNIQUE",
            "CREATE CONSTRAINT education_key_unique IF NOT EXISTS "
            "FOR (e:Education) REQUIRE e.education_key IS UNIQUE",
        ]
        with self.driver.session() as session:
            for statement in statements:
                session.execute_write(lambda tx, q=statement: tx.run(q))

    # ------------------------------------------------------------------
    # Write transactions (one per node/relationship type)
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_candidate(
        tx: ManagedTransaction,
        candidate_id: str,
        name: Optional[str],
        email: Optional[str],
        phone: Optional[str],
    ) -> None:
        tx.run(
            """
            MERGE (c:Candidate {candidate_id: $candidate_id})
            ON CREATE SET
                c.name = $name,
                c.email = $email,
                c.phone = $phone,
                c.created_at = datetime()
            ON MATCH SET
                c.name = coalesce($name, c.name),
                c.email = coalesce($email, c.email),
                c.phone = coalesce($phone, c.phone),
                c.updated_at = datetime()
            """,
            candidate_id=candidate_id,
            name=name,
            email=email,
            phone=phone,
        )

    @staticmethod
    def _merge_skill(tx: ManagedTransaction, candidate_id: str, skill_name: str) -> None:
        # Skill nodes are shared across all candidates (MERGE key = normalized
        # name only) so "find every candidate who knows Python" is a single
        # graph traversal rather than a string match across Candidate nodes.
        tx.run(
            """
            MERGE (c:Candidate {candidate_id: $candidate_id})
            MERGE (s:Skill {name_normalized: $name_normalized})
            ON CREATE SET
                s.name = $name,
                s.created_at = datetime()
            MERGE (c)-[r:KNOWS]->(s)
            ON CREATE SET r.created_at = datetime()
            """,
            candidate_id=candidate_id,
            name=skill_name,
            name_normalized=_normalize(skill_name),
        )

    @staticmethod
    def _merge_project(tx: ManagedTransaction, candidate_id: str, project: ProjectItem) -> None:
        # Project nodes are scoped per-candidate (MERGE key includes
        # candidate_id) — two different candidates with a similarly titled
        # "Portfolio Website" project should remain distinct nodes, while
        # re-parsing the same candidate's resume must not duplicate theirs.
        title = project.title or (project.raw_text or "")[:120]
        title_normalized = _normalize(title)
        project_key = f"{candidate_id}::{title_normalized}"

        tx.run(
            """
            MERGE (c:Candidate {candidate_id: $candidate_id})
            MERGE (p:Project {project_key: $project_key})
            ON CREATE SET
                p.title = $title,
                p.description = $description,
                p.raw_text = $raw_text,
                p.created_at = datetime()
            ON MATCH SET
                p.title = coalesce($title, p.title),
                p.description = coalesce($description, p.description),
                p.raw_text = coalesce($raw_text, p.raw_text),
                p.updated_at = datetime()
            MERGE (c)-[r:BUILT]->(p)
            ON CREATE SET r.created_at = datetime()
            """,
            candidate_id=candidate_id,
            project_key=project_key,
            title=title,
            description=project.description,
            raw_text=project.raw_text,
        )

    @staticmethod
    def _merge_education(tx: ManagedTransaction, candidate_id: str, edu: EducationItem) -> None:
        # Education nodes are shared across candidates (MERGE key =
        # institution + degree, not candidate_id) so "find candidates who
        # studied B.Tech at XYZ University" is also a single traversal.
        institution_normalized = _normalize(edu.institution)
        degree_normalized = _normalize(edu.degree)

        if institution_normalized or degree_normalized:
            education_key = f"{institution_normalized}::{degree_normalized}"
        else:
            # Neither field was parsed out — fall back to the raw entry so
            # we still get a stable, idempotent MERGE key.
            education_key = _normalize(edu.raw_text)

        tx.run(
            """
            MERGE (c:Candidate {candidate_id: $candidate_id})
            MERGE (e:Education {education_key: $education_key})
            ON CREATE SET
                e.institution = $institution,
                e.degree = $degree,
                e.created_at = datetime()
            ON MATCH SET
                e.institution = coalesce($institution, e.institution),
                e.degree = coalesce($degree, e.degree),
                e.updated_at = datetime()
            MERGE (c)-[r:STUDIED]->(e)
            ON CREATE SET
                r.raw_text = $raw_text,
                r.created_at = datetime()
            """,
            candidate_id=candidate_id,
            education_key=education_key,
            institution=edu.institution,
            degree=edu.degree,
            raw_text=edu.raw_text,
        )
