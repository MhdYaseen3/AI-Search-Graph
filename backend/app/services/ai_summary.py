import logging
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalServiceError, NotFoundError
from app.db.neo4j import Neo4jConnection
from app.schemas.search import SearchQuery
from app.utils.experience_calc import calculate_experience_years

logger = logging.getLogger(__name__)


class AISummaryService:
    """Generates AI-powered candidate summaries using Ollama."""

    def __init__(
        self,
        neo4j: Neo4jConnection,
        ollama_base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.neo4j = neo4j
        self.ollama_base_url = ollama_base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model

    async def generate_summary(
        self,
        candidate_id: str,
        context: str | None = None,
    ) -> tuple[str, str]:
        """Generate a concise summary for a candidate."""
        candidate_data = await self._fetch_candidate_context(candidate_id)

        try:
            summary = await self._call_ollama(
                self._build_prompt(candidate_data, context),
            )
            logger.info("Generated AI summary for candidate %s", candidate_id)
            return summary.strip(), "ai"
        except Exception as exc:
            logger.warning(
                "AI summary unavailable for %s, using fallback: %s",
                candidate_id,
                exc,
            )
            return self._build_fallback_summary(candidate_data), "fallback"

    async def generate_match_explanation(
        self,
        candidate_id: str,
        query: SearchQuery,
        candidate: dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        """Explain why a candidate matches a search query."""
        candidate_data = candidate or await self._fetch_candidate_context(
            candidate_id,
        )

        prompt = self._build_match_prompt(candidate_data, query)

        try:
            explanation = await self._call_ollama(prompt)
            return explanation.strip(), "ai"
        except Exception as exc:
            logger.warning(
                "AI match explanation unavailable for %s: %s",
                candidate_id,
                exc,
            )
            return (
                self._build_fallback_match_explanation(
                    candidate_data,
                    query,
                ),
                "fallback",
            )

    async def _fetch_candidate_context(
        self,
        candidate_id: str,
    ) -> dict[str, Any]:
        query = """
        MATCH (c:Candidate {id: $id})
        OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill)
        OPTIONAL MATCH (c)-[:WORKED_ON]->(p:Project)
        OPTIONAL MATCH (c)-[:USES_TECHNOLOGY]->(t:Technology)
        OPTIONAL MATCH (c)-[:STUDIED_AT]->(e:Education)
        OPTIONAL MATCH (c)-[:WORKED_AT]->(x:Experience)
        RETURN
            c.full_name AS full_name,
            c.email AS email,
            c.summary AS summary,
            collect(DISTINCT s.name) AS skills,
            collect(DISTINCT p.name) AS projects,
            collect(DISTINCT t.name) AS technologies,
            collect(DISTINCT e.institution) AS education,
            collect(DISTINCT {
                company: x.company,
                role: x.role,
                start_date: x.start_date,
                end_date: x.end_date
            }) AS experiences
        """
        data = await self.neo4j.execute_read(
            query,
            {"id": candidate_id},
        )
        if not data:
            raise NotFoundError(f"Candidate {candidate_id} not found")

        record = data[0]
        experiences = [
            exp
            for exp in record.get("experiences", [])
            if exp and exp.get("company")
        ]
        record["experiences"] = experiences
        record["experience_years"] = calculate_experience_years(
            experiences,
        )
        return record

    def _build_prompt(
        self,
        candidate_data: dict[str, Any],
        context: str | None,
    ) -> str:
        base = f"""
You are a recruiter.

Create a professional summary using ALL of the information provided.

Candidate Name:
{candidate_data.get("full_name")}

Education:
{candidate_data.get("education")}

Skills:
{candidate_data.get("skills")}

Technologies:
{candidate_data.get("technologies")}

Projects:
{candidate_data.get("projects")}

Requirements:
- Mention education.
- Mention major projects.
- Mention key technologies.
- Keep it under 120 words.
- Do not invent experience.
- Do not claim years of experience.
"""
        if context:
            base += f"\nAdditional Context: {context}\n"
        return base

    def _build_match_prompt(
        self,
        candidate_data: dict[str, Any],
        query: SearchQuery,
    ) -> str:
        return f"""
You are a recruitment explanation system.

Search query:
{query.query}

Candidate:
{candidate_data.get("full_name")}

Experience years:
{candidate_data.get("experience_years")}

Skills:
{", ".join(candidate_data.get("skills") or [])}

Technologies:
{", ".join(candidate_data.get("technologies") or [])}

Projects:
{", ".join(candidate_data.get("projects") or [])}

Matched skills requested:
{", ".join(query.skills)}

Matched technologies requested:
{", ".join(query.technologies)}

Minimum experience requested:
{query.min_experience_years}

Write 3-4 plain sentences explaining why this candidate matches the query.
Use only the information provided.
"""

    def _build_fallback_summary(
        self,
        candidate_data: dict[str, Any],
    ) -> str:
        name = candidate_data.get("full_name") or "Candidate"
        skills = candidate_data.get("skills") or []
        technologies = candidate_data.get("technologies") or []
        projects = candidate_data.get("projects") or []
        education = candidate_data.get("education") or []
        experience_years = candidate_data.get("experience_years")

        parts = [f"{name} is a candidate in the talent graph."]

        if experience_years:
            parts.append(
                f"They have approximately {experience_years} years of professional experience.",
            )

        if skills:
            parts.append(
                f"Key skills include {', '.join(skills[:6])}.",
            )

        if technologies:
            parts.append(
                f"Technologies used include {', '.join(technologies[:6])}.",
            )

        if projects:
            parts.append(
                f"Notable projects include {', '.join(projects[:3])}.",
            )

        if education:
            parts.append(
                f"Education background includes {', '.join(education[:2])}.",
            )

        if candidate_data.get("summary"):
            parts.append(candidate_data["summary"])

        return " ".join(parts)

    def _build_fallback_match_explanation(
        self,
        candidate_data: dict[str, Any],
        query: SearchQuery,
    ) -> str:
        name = candidate_data.get("full_name") or "This candidate"
        parts: list[str] = []

        experience_years = candidate_data.get("experience_years")
        if query.min_experience_years and experience_years is not None:
            parts.append(
                f"{name} has {experience_years} years of experience, "
                f"meeting the requested minimum of "
                f"{query.min_experience_years} years.",
            )

        skills = set(
            skill.lower()
            for skill in candidate_data.get("skills") or []
        )
        matched_skills = [
            skill
            for skill in query.skills
            if skill.lower() in skills
        ]
        if matched_skills:
            parts.append(
                f"They match requested skills: {', '.join(matched_skills)}.",
            )

        technologies = set(
            tech.lower()
            for tech in candidate_data.get("technologies") or []
        )
        matched_technologies = [
            tech
            for tech in query.technologies
            if tech.lower() in technologies
        ]
        if matched_technologies:
            parts.append(
                "They also match requested technologies: "
                f"{', '.join(matched_technologies)}.",
            )

        projects = candidate_data.get("projects") or []
        matched_projects = [
            project
            for project in query.projects
            if any(
                project.lower() in existing.lower()
                for existing in projects
            )
        ]
        if matched_projects:
            parts.append(
                f"Relevant projects include {', '.join(matched_projects)}.",
            )

        experiences = candidate_data.get("experiences") or []
        if experiences:
            latest = experiences[0]
            role = latest.get("role")
            company = latest.get("company")
            if role and company:
                parts.append(
                    f"Recent work history includes {role} at {company}.",
                )

        if not parts:
            parts.append(
                f"{name} matches the search based on graph profile overlap.",
            )

        return " ".join(parts)

    async def _call_ollama(self, prompt: str) -> str:
        url = f"{self.ollama_base_url}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": False}

        try:
            async with httpx.AsyncClient(
                timeout=settings.ollama_timeout,
            ) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except httpx.HTTPError as exc:
            raise ExternalServiceError(
                "Failed to generate AI summary",
                service="ollama",
            ) from exc
