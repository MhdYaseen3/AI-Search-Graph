import logging
from uuid import uuid4

from fastapi import UploadFile

from app.models import Technology
from app.models.education import Education
from app.models.experience import Experience
from app.schemas.candidate import CandidateCreate
from app.schemas.resume import ResumeIngestResponse
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

        raw_text = upload_result.text
        parsed = self.parser.parse(raw_text)

        skills = await self.skill_service.extract_skills(raw_text)
        projects = await self.project_service.extract_projects(raw_text)
        education = await self.education_service.extract_education(raw_text)
        technologies = await self.technology_service.extract_technologies(
            raw_text,
        )

        full_name = (
            parsed.candidate_name
            or (file.filename or "Unknown Candidate").replace(".pdf", "")
        )

        candidate = await self.candidate_service.create(
            CandidateCreate(
                full_name=full_name,
                email=parsed.email,
                phone=parsed.phone,
                summary=None,
                resume_file_path=upload_result.file_path,
                raw_text=raw_text,
                skills=[skill.name for skill in skills],
            ),
        )
        candidate_id = candidate.id

        for skill in skills:
            await self.graph_service.link_skill(candidate_id, skill)

        for project in projects:
            await self.graph_service.link_project(candidate_id, project)

        for edu in education:
            await self.graph_service.link_education(
                candidate_id,
                Education(institution=edu),
            )

        for exp in parsed.experiences:
            experience_obj = Experience(
                company=exp.company or "Unknown",
                role=exp.role,
                description=exp.description,
                start_date=exp.start_date,
                end_date=exp.end_date,
            )
            await self.graph_service.link_experience(
                candidate_id,
                experience_obj,
            )

        for tech in technologies:
            await self.graph_service.link_technology(
                candidate_id,
                Technology(name=tech),
            )

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
            education=education,
            experiences=len(parsed.experiences),
            relationship_count=relationship_count,
            file_path=upload_result.file_path,
            message="Resume parsed and knowledge graph constructed successfully.",
        )
