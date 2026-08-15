import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

class TechnologyExtractionService:
    def __init__(self):
        self.ollama_base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def extract_technologies(self, resume_text: str):
        prompt =f"""
Extract technologies, frameworks, databases, tools and platforms from this resume.

Rules:
- Return only technology names.
- No explanations.
- No headings.
- No bullet points.
- No extra text.
- Output must be a single comma-separated list.

Resume:

{resume_text}
"""

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
            )

        response.raise_for_status()

        result = response.json()["response"]

        print("TECH RESPONSE:")
        print(result)

        return self._parse_response(result)

    def _parse_response(self, response: str):
        cleaned = response.replace("\n", ",")
    
        items = []
    
        for item in cleaned.split(","):
    
            item = item.replace("-", "").strip()
    
            if not item:
                continue
    
            if len(item) > 40:
                continue
    
            bad_phrases = [
             "sure",
             "here are",
             "here's",
             "technologies",
             "frameworks",
             "databases",
             "tools",
             "platforms",
             "mentioned in the resume"
        ]         
             
            if any(bad in item.lower() for bad in bad_phrases):
                continue
            item = item.replace("-", "").strip()
    
            items.append(item)
    
        return list(set(items))