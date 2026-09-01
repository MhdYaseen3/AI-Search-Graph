import logging
from typing import Any

from app.core.config import settings
from app.db.neo4j import Neo4jConnection
from app.schemas.search import SearchQuery
from app.utils.experience_calc import calculate_experience_years

logger = logging.getLogger(__name__)


class SearchService:
    """Graph-based search over candidates, skills, and technologies."""

    def __init__(self, neo4j: Neo4jConnection) -> None:
        self.neo4j = neo4j

    async def search(
        self,
        query: SearchQuery,
    ) -> list[dict[str, Any]]:
        """Search candidates using graph relationships and filters."""
        limit = min(
            query.limit,
            settings.max_search_limit,
        )

        cypher = """
        MATCH (c:Candidate)

        OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill)
        OPTIONAL MATCH (c)-[:USES_TECHNOLOGY]->(t:Technology)
        OPTIONAL MATCH (c)-[:WORKED_ON]->(p:Project)
        OPTIONAL MATCH (c)-[:STUDIED_AT]->(e:Education)
        OPTIONAL MATCH (c)-[:WORKED_AT]->(x:Experience)

        WITH
            c,
            collect(DISTINCT s.name) AS skills,
            collect(DISTINCT t.name) AS technologies,
            collect(DISTINCT p.name) AS projects,
            collect(DISTINCT e.institution) AS education,
            collect(DISTINCT x.role) AS roles,
            collect(DISTINCT {
                company: x.company,
                role: x.role,
                start_date: x.start_date,
                end_date: x.end_date
            }) AS experiences

        WITH
            c,
            skills,
            technologies,
            projects,
            education,
            roles,
            experiences,

            [requested IN $skills
             WHERE any(
                 candidate_skill IN skills
                 WHERE toLower(candidate_skill) = toLower(requested)
             )
            ] AS matched_skills,

            [requested IN $technologies
             WHERE any(
                 candidate_tech IN technologies
                 WHERE toLower(candidate_tech) = toLower(requested)
             )
            ] AS matched_technologies,

            [requested IN $projects
             WHERE any(
                 candidate_project IN projects
                 WHERE toLower(candidate_project) CONTAINS toLower(requested)
             )
            ] AS matched_projects,

            [candidate_role IN roles
             WHERE candidate_role IS NOT NULL
                AND toLower(candidate_role) CONTAINS toLower($role)
            ] AS matched_roles

        WHERE
            (
                size($skills) = 0
                OR size(matched_skills) > 0
            )
            AND
            (
                size($technologies) = 0
                OR size(matched_technologies) > 0
            )
            AND
            (
                size($projects) = 0
                OR size(matched_projects) > 0
            )
            AND
            (
                $role IS NULL
                OR size(matched_roles) > 0
            )

        RETURN
            c.id AS candidate_id,
            c.full_name AS full_name,
            c.summary AS summary,

            skills,
            technologies,
            projects,
            education,
            roles,
            experiences,

            matched_skills,
            matched_technologies,
            matched_projects,
            matched_roles

        LIMIT $limit
        """

        parameters = {
            "role": query.role,
            "skills": query.skills,
            "technologies": query.technologies,
            "projects": query.projects,
            "limit": limit,
        }

        logger.info(
            "Executing graph search. "
            "query=%s role=%s skills=%s technologies=%s projects=%s "
            "min_experience_years=%s",
            query.query,
            query.role,
            query.skills,
            query.technologies,
            query.projects,
            query.min_experience_years,
        )

        records = await self.neo4j.execute_read(
            cypher,
            parameters,
        )

        results: list[dict[str, Any]] = []

        for record in records:
            experiences = [
                exp
                for exp in record.get("experiences", [])
                if exp and exp.get("company")
            ]
            record["experiences"] = experiences
            record["experience_years"] = calculate_experience_years(
                experiences,
            )

            if query.min_experience_years is not None:
                if record["experience_years"] < query.min_experience_years:
                    continue

            results.append(record)

        return results

    async def search_by_skills(
        self,
        skills: list[str],
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Find candidates possessing the requested skills."""
        limit = min(
            limit or settings.default_search_limit,
            settings.max_search_limit,
        )

        if not skills:
            return []

        cypher = """
        MATCH (c:Candidate)-[:HAS_SKILL]->(s:Skill)
        WHERE any(
            requested_skill IN $skills
            WHERE toLower(s.name) = toLower(requested_skill)
        )
        WITH c,
             collect(DISTINCT s.name) AS matched_skills,
             size(collect(DISTINCT s.name)) AS match_count

        RETURN
            c.id AS candidate_id,
            c.full_name AS full_name,
            c.email AS email,
            matched_skills,
            match_count

        ORDER BY match_count DESC
        LIMIT $limit
        """

        parameters = {
            "skills": skills,
            "limit": limit,
        }

        logger.info(
            "Searching candidates by skills: %s",
            skills,
        )

        records = await self.neo4j.execute_read(
            cypher,
            parameters,
        )

        return records
