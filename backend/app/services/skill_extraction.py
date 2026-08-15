import logging
import re
import httpx

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.models import Skill

logger = logging.getLogger(__name__)


class SkillExtractionService:
    """Extracts skills from resume text using Ollama."""

    def __init__(self, ollama_base_url: str | None = None, model: str | None = None) -> None:
        self.ollama_base_url = ollama_base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model

    async def extract_skills(self, resume_text: str) -> list[Skill]:
        """Identify skills from resume text via LLM."""
        if not resume_text.strip():
            return []

        prompt = self._build_prompt(resume_text)

        try:
            response = await self._call_ollama(prompt)
            skills = self._parse_response(response)
            logger.info("Extracted %d skills", len(skills))
            return skills
        except ExternalServiceError:
            raise
        except Exception as exc:
         logger.exception("Skill extraction failed")
         raise

    def _build_prompt(self, resume_text: str) -> str:
          return f"""
      You are a resume parser.
      
      Extract ONLY technical skills.
      
      Return ONLY a comma separated list.
      
      Example:
      Python, FastAPI, React, MongoDB
      
      Do not explain.
      Do not use bullet points.
      Do not use sentences.
      Do not say "Sure".
      
      Resume:
      {resume_text}
      """
    async def _call_ollama(self, prompt: str) -> str:
     print("BASE URL =", self.ollama_base_url)
     print("MODEL =", self.model)
     url = f"{self.ollama_base_url}/api/generate"
     payload = {
         "model": self.model,
         "prompt": prompt,
         "stream": False,
     }

     print("OLLAMA URL:", url)
     print("OLLAMA MODEL:", self.model)
 
     async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
         response = await client.post(url, json=payload)
 
         print("STATUS:", response.status_code)
         print("RESPONSE:", response.text[:1000])
 
         response.raise_for_status()
 
         data = response.json()
         return data.get("response", "")

    def _parse_response(self, response: str) -> list[Skill]:
        # TODO: Implement structured parsing (JSON mode / schema validation)
      response = response.replace("-", ",")
      response = response.replace("\n", ",")
      
      raw_skills = [
          s.strip()
          for s in re.split(r",|\n", response)
          if s.strip() and len(s.strip()) < 50
      ]     
      return [Skill(name=name) for name in raw_skills]
