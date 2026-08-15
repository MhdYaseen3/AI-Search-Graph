# app/services/education_extraction.py

import logging
import httpx
import re

from app.core.config import settings

logger = logging.getLogger(__name__)


class EducationExtractionService:

    def __init__(self):
        self.ollama_base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def extract_education(self, resume_text: str):

        
        education = []

        lines = [line.strip() for line in resume_text.splitlines()]
        
        for line in lines:
        
            if "B.Tech" in line:
                education.append(line)
        
            elif "Bachelor" in line:
                education.append(line)
        
            elif "College" in line:
                education.append(line)
        
            elif "University" in line:
                education.append(line)
        
            elif "Institute" in line:
                education.append(line)
        
        return list(set(education))
        

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
            )

        result = response.json()["response"]

        return [
            item.strip()
            for item in result.split(",")
            if item.strip()
        ]