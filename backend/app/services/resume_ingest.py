import logging
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.models import Technology
from app.models.education import Education
from app.models.experience import Experience
from app.schemas.candidate import CandidateCreate
from app.schemas.resume import ResumeIngestResponse
from app.schemas.resume import PDFUploadResponse
from app.services.candidate_management import CandidateManagementService
from app.services.education_extraction import EducationExtractionService
from app.services.neo4j_graph import Neo4jGraphService
from app.services.pdf_extraction import PDFExtractionService
from app.services.project_extraction import ProjectExtractionService
from app.services.resume_parser_service import ResumeParserService
from app.services.resume_upload import ResumeUploadService
from app.services.skill_extraction import SkillExtractionService
from app.services.technology_extraction import TechnologyExtractionService

logger = logging.getLogger(__name__)


class ResumeIngestService:
    """End-to-end resume upload, parse, and graph persistence."""

    def __init__(
        self,
        upload_service: ResumeUploadService,
        pdf_service: PDFExtractionService,
        candidate_service: CandidateManagementService,
        graph_service: Neo4jGraphService,
        skill_service: SkillExtractionService,
        project_service: ProjectExtractionService,
        education_service: EducationExtractionService,
        technology_service: TechnologyExtractionService,
    ) -> None:
        self.upload_service = upload_service
        self.pdf_service = pdf_service
        self.candidate_service = candidate_service
        self.graph_service = graph_service
        self.skill_service = skill_service
        self.project_service = project_service
        self.education_service = education_service
        self.technology_service = technology_service
        self.parser = ResumeParserService()

    async def ingest(
        self,
        file: UploadFile,
        candidate_id: str | None = None,
    ) -> ResumeIngestResponse:
        candidate_id = candidate_id or str(uuid4())

        upload_result = await self.upload_service.upload_and_extract(
            file=file,
            candidate_id=candidate_id,
        )

        return await self._ingest_extracted(
            upload_result,
            fallback_name=(file.filename or "Unknown Candidate").replace(
                ".pdf", ""
            ),
        )

    async def ingest_gmail_attachment(
        self,
        file: UploadFile,
        content: bytes,
        *,
        message_id: str,
        attachment_id: str,
        sha256: str,
    ) -> ResumeIngestResponse:
        """Ingest a validated Gmail PDF/DOCX through the shared resume pipeline."""
        upload_result = await self.upload_service.upload_and_extract_gmail(
            file=file,
            content=content,
            candidate_id=str(uuid4()),
        )

        fallback_name = file.filename or "Unknown Candidate"
        for extension in (".pdf", ".docx"):
            if fallback_name.lower().endswith(extension):
                fallback_name = fallback_name[: -len(extension)]
                break

        return await self._ingest_extracted(
            upload_result,
            fallback_name=fallback_name,
            gmail_identity=(message_id, attachment_id),
            sha256=sha256,
        )

    async def _ingest_extracted(
        self,
        upload_result: PDFUploadResponse,
        fallback_name: str,
        gmail_identity: tuple[str, str] | None = None,
        sha256: str | None = None,
    ) -> ResumeIngestResponse:
        raw_text = upload_result.text
        parsed = self.parser.parse(raw_text)

        skills = await self.skill_service.extract_skills(raw_text)
        projects = await self.project_service.extract_projects(raw_text)
        education = parsed.education
        technologies = await self.technology_service.extract_technologies(
            raw_text,
        )

        full_name = parsed.candidate_name or fallback_name

        experiences = [
            Experience(
                company=exp.company or "Unknown",
                role=exp.role,
                description=exp.description,
                duration=exp.duration,
                start_date=exp.start_date,
                end_date=exp.end_date,
            )
            for exp in parsed.experiences
        ]
        candidate_payload = CandidateCreate(
            full_name=full_name,
            email=parsed.email,
            phone=parsed.phone,
            summary=parsed.summary,
            resume_file_path=upload_result.file_path,
            raw_text=raw_text,
            source="gmail" if gmail_identity else None,
            skills=[skill.name for skill in skills],
        )

        if gmail_identity:
            if not sha256:
                raise ValueError("Gmail attachment SHA-256 is required.")
            try:
                candidate = await self.candidate_service.create_gmail_candidate(
                    candidate_payload,
                    skills,
                    projects,
                    [
                        Education(
                            institution=edu.institution or "Unknown",
                            degree=edu.degree,
                            field_of_study=edu.field_of_study,
                            expected_graduation=edu.expected_graduation,
                            cgpa=edu.cgpa,
                        )
                        for edu in education
                    ],
                    experiences,
                    [Technology(name=tech) for tech in technologies],
                    message_id=gmail_identity[0],
                    attachment_id=gmail_identity[1],
                    filename=upload_result.file_name,
                    sha256=sha256,
                )
            except Exception:
                try:
                    Path(upload_result.file_path).unlink(missing_ok=True)
                except OSError as cleanup_error:
                    logger.error(
                        "Could not remove Gmail upload after graph persistence "
                        "failed (error_type=%s)",
                        type(cleanup_error).__name__,
                    )
                raise
        else:
            candidate = await self.candidate_service.create(candidate_payload)
            for skill in skills:
                await self.graph_service.link_skill(candidate.id, skill)

            for project in projects:
                await self.graph_service.link_project(candidate.id, project)

            for edu in education:
                await self.graph_service.link_education(
                    candidate.id,
                    Education(
                        institution=edu.institution or "Unknown",
                        degree=edu.degree,
                        field_of_study=edu.field_of_study,
                        expected_graduation=edu.expected_graduation,
                        cgpa=edu.cgpa,
                    ),
                )

            for experience in experiences:
                await self.graph_service.link_experience(
                    candidate.id,
                    experience,
                )

            for tech in technologies:
                await self.graph_service.link_technology(
                    candidate.id,
                    Technology(name=tech),
                )

        candidate_id = candidate.id

        relationship_count = (
            len(skills)
            + len(projects)
            + len(education)
            + len(parsed.experiences)
            + len(technologies)
        )

        logger.info(
            "Ingested resume for candidate %s with %s graph links",
            candidate_id,
            relationship_count,
        )

        return ResumeIngestResponse(
            candidate_id=candidate_id,
            full_name=full_name,
            email=parsed.email,
            phone=parsed.phone,
            skills=[skill.name for skill in skills],
            technologies=technologies,
            projects=[project.name for project in projects],
            education=[edu.institution for edu in education if edu.institution],
            experiences=len(parsed.experiences),
            relationship_count=relationship_count,
            file_path=upload_result.file_path,
            message="Resume parsed and knowledge graph constructed successfully.",
        )
