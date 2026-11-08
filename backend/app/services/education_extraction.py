# app/services/education_extraction.py

from app.services.resume_parser_service import ResumeParserService


class EducationExtractionService:

    async def extract_education(self, resume_text: str):
        """Return institutions from the shared section-aware parser."""
        parsed = ResumeParserService().parse(resume_text)
        return [item.institution for item in parsed.education if item.institution]
