from uuid import uuid4

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from app.models import Technology, Experience

from app.api.deps import (
    get_ai_summary_service,
    get_candidate_service,
    get_education_extraction_service,
    get_neo4j_graph_service,
    get_pdf_extraction_service,
    get_project_extraction_service,
    get_resume_ingest_service,
    get_resume_upload_service,
    get_skill_extraction_service,
    get_technology_extraction_service,
)
from app.schemas.resume import (
    ExtractedResumeData,
    PDFUploadResponse,
    ResumeIngestResponse,
)
from app.schemas.search import AISummaryRequest, AISummaryResponse
from app.schemas.candidate import CandidateUpdate
from app.services.ai_summary import AISummaryService
from app.services.neo4j_graph import Neo4jGraphService
from app.services.pdf_extraction import PDFExtractionService
from app.services.project_extraction import ProjectExtractionService
from app.services.resume_ingest import ResumeIngestService
from app.services.resume_upload import ResumeUploadService
from app.services.skill_extraction import SkillExtractionService
from app.services.education_extraction import EducationExtractionService
from app.services.technology_extraction import TechnologyExtractionService
from app.models.education import Education
from app.services.resume_parser_service import ResumeParserService
from app.services.candidate_management import CandidateManagementService

router = APIRouter(
    prefix="/resumes",
    tags=["Resumes"],
)


@router.post("/upload", response_model=PDFUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(..., description="Resume PDF file"),
    candidate_id: str | None = Query(default=None),
    upload_service: ResumeUploadService = Depends(get_resume_upload_service),
) -> PDFUploadResponse:
    return await upload_service.upload_and_extract(
        file=file,
        candidate_id=candidate_id or str(uuid4()),
    )


@router.post("/ingest", response_model=ResumeIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_resume(
    file: UploadFile = File(..., description="Resume PDF file"),
    candidate_id: str | None = Query(default=None),
    ingest_service: ResumeIngestService = Depends(get_resume_ingest_service),
) -> ResumeIngestResponse:
    """Upload, parse, create candidate, and persist graph relationships."""
    return await ingest_service.ingest(
        file=file,
        candidate_id=candidate_id,
    )


@router.post("/{candidate_id}/process", response_model=ExtractedResumeData)
async def process_resume(
    candidate_id: str,
    file_path: str,
    pdf_service: PDFExtractionService = Depends(get_pdf_extraction_service),
    skill_service: SkillExtractionService = Depends(get_skill_extraction_service),
    project_service: ProjectExtractionService = Depends(get_project_extraction_service),
    education_service: EducationExtractionService = Depends(get_education_extraction_service),
    technology_service: TechnologyExtractionService = Depends(get_technology_extraction_service),
    candidate_service: CandidateManagementService = Depends(get_candidate_service),
    graph_service: Neo4jGraphService = Depends(get_neo4j_graph_service),
) -> ExtractedResumeData:
    """Extract resume content and persist knowledge graph relationships."""
    raw_text = await pdf_service.extract_text(file_path)

    parser = ResumeParserService()
    parsed = parser.parse(raw_text)

    skills = await skill_service.extract_skills(raw_text)
    projects = await project_service.extract_projects(raw_text)
    education = parsed.education
    technologies = await technology_service.extract_technologies(raw_text)

    await candidate_service.update(
        candidate_id,
        CandidateUpdate(summary=parsed.summary, raw_text=raw_text),
    )

    for skill in skills:
        await graph_service.link_skill(candidate_id, skill)

    for project in projects:
        await graph_service.link_project(candidate_id, project)

    for edu in education:
        education_obj = Education(
            institution=edu.institution or "Unknown",
            degree=edu.degree,
            field_of_study=edu.field_of_study,
            expected_graduation=edu.expected_graduation,
            cgpa=edu.cgpa,
        )
        await graph_service.link_education(candidate_id, education_obj)

    for exp in parsed.experiences:
        experience_obj = Experience(
            company=exp.company or "Unknown",
            role=exp.role,
            description=exp.description,
            duration=exp.duration,
            start_date=exp.start_date,
            end_date=exp.end_date,
        )
        await graph_service.link_experience(candidate_id, experience_obj)

    for tech in technologies:
        await graph_service.link_technology(
            candidate_id,
            Technology(name=tech),
        )

    return ExtractedResumeData(
        candidate_id=candidate_id,
        raw_text=raw_text,
        skills=[s.name for s in skills],
        projects=[p.name for p in projects],
        education=[edu.institution for edu in education if edu.institution],
        experiences=[experience.model_dump() for experience in parsed.experiences],
        technologies=technologies,
    )


@router.post("/{candidate_id}/summary", response_model=AISummaryResponse)
async def generate_candidate_summary(
    candidate_id: str,
    payload: AISummaryRequest | None = None,
    summary_service: AISummaryService = Depends(get_ai_summary_service),
) -> AISummaryResponse:
    context = payload.context if payload else None
    summary, source = await summary_service.generate_summary(
        candidate_id,
        context,
    )
    return AISummaryResponse(
        candidate_id=candidate_id,
        summary=summary,
        source=source,
    )
