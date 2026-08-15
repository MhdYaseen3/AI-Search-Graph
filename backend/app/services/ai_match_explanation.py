import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIMatchExplanationService:
    """Generate AI explanations for candidate-job matches."""

    def __init__(self) -> None:
        self.ollama_base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def generate_explanation(
        self,
        job_title: str,
        matched_skills: list[str],
        missing_skills: list[str],
        match_score: float,
        recommendation: str,
    ) -> str:

        prompt = f"""
You are a recruitment explanation system.

Job:
{job_title}

Match score:
{match_score}%

Matched skills:
{", ".join(matched_skills) if matched_skills else "None"}

Missing skills:
{", ".join(missing_skills) if missing_skills else "None"}

System recommendation:
{recommendation}

Write exactly 3 plain-text sentences.

Sentence 1: State the matched skills.
Sentence 2: State the missing skills.
Sentence 3: State the system recommendation.

Rules:
- Use only the information provided.
- Never invent experience, qualifications, personality, or technologies.
- Never say a missing skill is present.
- Do not change the system recommendation.
- Do not use headings.
- Do not use Markdown.
- Do not use bullet points.
- Do not write labels such as "Sentence 1".
- Exactly 3 sentences.
"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1
                        }
                    }
                )

                response.raise_for_status()

            return response.json()["response"].strip()

        except Exception as exc:
         logger.exception("Failed to generate AI match explanation")
         print("AI EXPLANATION ERROR:", repr(exc))
         raise