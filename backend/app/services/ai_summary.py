import logging

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalServiceError, NotFoundError
from app.db.neo4j import Neo4jConnection

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
    ) -> str:
        """Generate a concise AI summary for a candidate."""
        candidate_data = await self._fetch_candidate_context(candidate_id)
        prompt = self._build_prompt(candidate_data, context)

        try:
            summary = await self._call_ollama(prompt)
            logger.info("Generated summary for candidate %s", candidate_id)
            return summary.strip()
        except ExternalServiceError:
            raise
        except Exception as exc:
            logger.exception("Summary generation failed for %s", candidate_id)
            raise ExternalServiceError(
                "Failed to generate AI summary",
                service="ollama",
            ) from exc

    async def _fetch_candidate_context(self, candidate_id: str) -> dict:
        # TODO: Fetch candidate subgraph from Neo4j
        query = """
MATCH (c:Candidate {id: $id})

OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill)
OPTIONAL MATCH (c)-[:WORKED_ON]->(p:Project)
OPTIONAL MATCH (c)-[:USES_TECHNOLOGY]->(t:Technology)
OPTIONAL MATCH (c)-[:STUDIED_AT]->(e:Education)

RETURN
c.full_name AS full_name,
c.email AS email,

collect(DISTINCT s.name) AS skills,
collect(DISTINCT p.name) AS projects,
collect(DISTINCT t.name) AS technologies,
collect(DISTINCT e.institution) AS education
"""
        data = await self.neo4j.execute_read(
            query,
            {"id": candidate_id},
        )
        if not data:
            raise NotFoundError(f"Candidate {candidate_id} not found")
        return data[0]

    def _build_prompt(self, candidate_data: dict, context: str | None) -> str:
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

    async def _call_ollama(self, prompt: str) -> str:
        url = f"{self.ollama_base_url}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": False}

        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
