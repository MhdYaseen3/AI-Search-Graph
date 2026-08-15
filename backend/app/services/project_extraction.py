import logging

import httpx
import re

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.models import Project

logger = logging.getLogger(__name__)


class ProjectExtractionService:
    """Extracts projects and associated technologies from resume text."""

    def __init__(self, ollama_base_url: str | None = None, model: str | None = None) -> None:
        self.ollama_base_url = ollama_base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model

    async def extract_projects(self, resume_text: str) -> list[Project]:
        """Identify projects from resume text via LLM."""
        if not resume_text.strip():
            return []
    
        prompt = self._build_prompt(resume_text)

        try:
            response = await self._call_ollama(prompt)
            print("PROJECT RESPONSE:")
            print(response)
            projects = self._parse_response(response)
            logger.info("Extracted %d projects", len(projects))
            return projects
        except ExternalServiceError:
            raise
        except Exception as exc:
            logger.exception("Project extraction failed")
            raise ExternalServiceError(
                "Failed to extract projects",
                service="ollama",
            ) from exc

    def _build_prompt(self, resume_text: str) -> str:
        return f"""
    Extract only the project names from this resume.
    
    Return one project per line.

    Example:
    
    AI Resume Search Engine
    Smart Plant Watering System
    AI Voice Assistant
    
    Resume:
    
    {resume_text}
    """

    async def _call_ollama(self, prompt: str) -> str:
        url = f"{self.ollama_base_url}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": False}

        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

    def _parse_response(self, response: str):
     projects = []
 
     for line in response.splitlines():
         line = line.strip()
 
         # Remove numbering like 1. 2. 3.
         line = re.sub(r"^\d+\.\s*", "", line)
 
         if (
           line
           and "project" not in line.lower()
           and len(line) > 3
       ):
           projects.append(Project(name=line))
 
     return projects