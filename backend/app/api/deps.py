from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.db.neo4j import Neo4jConnection, get_neo4j_connection
from app.services.ai_summary import AISummaryService
from app.services.candidate_management import CandidateManagementService
from app.services.education_extraction import EducationExtractionService
from app.services.job import JobManagementService
from app.services.neo4j_graph import Neo4jGraphService
from app.services.pdf_extraction import PDFExtractionService
from app.services.project_extraction import ProjectExtractionService
from app.services.ranking import RankingService
from app.services.resume_upload import ResumeUploadService
from app.services.search import SearchService
from app.services.skill_extraction import SkillExtractionService
from app.services.technology_extraction import TechnologyExtractionService
from app.services.match import MatchService
from app.services.ai_match_explanation import AIMatchExplanationService
from app.services.gmail_ingestion import GmailIngestionService
from app.services.gmail_message_tracking import (
    GmailMessageTrackingService,
)
from app.services.query_parser import QueryParser

SettingsDep = Annotated[Settings, Depends(get_settings)]
Neo4jDep = Annotated[Neo4jConnection, Depends(get_neo4j_connection)]


def get_resume_upload_service() -> ResumeUploadService:
    return ResumeUploadService()


def get_pdf_extraction_service() -> PDFExtractionService:
    return PDFExtractionService()


def get_candidate_service(neo4j: Neo4jDep) -> CandidateManagementService:
    return CandidateManagementService(neo4j)


def get_job_service(neo4j: Neo4jDep) -> JobManagementService:
    return JobManagementService(neo4j)


def get_ai_match_explanation_service() -> AIMatchExplanationService:
    return AIMatchExplanationService()


def get_match_service(
    neo4j: Neo4jDep,
    ai_explanation_service: Annotated[
        AIMatchExplanationService,
        Depends(get_ai_match_explanation_service),
    ],
) -> MatchService:
    return MatchService(neo4j, ai_explanation_service)


def get_skill_extraction_service() -> SkillExtractionService:
    return SkillExtractionService()


def get_project_extraction_service() -> ProjectExtractionService:
    return ProjectExtractionService()


def get_neo4j_graph_service(neo4j: Neo4jDep) -> Neo4jGraphService:
    return Neo4jGraphService(neo4j)


def get_search_service(neo4j: Neo4jDep) -> SearchService:
    return SearchService(neo4j)


def get_ranking_service() -> RankingService:
    return RankingService()


def get_ai_summary_service(neo4j: Neo4jDep) -> AISummaryService:
    return AISummaryService(neo4j)


def get_education_extraction_service() -> EducationExtractionService:
    return EducationExtractionService()


def get_technology_extraction_service() -> TechnologyExtractionService:
    return TechnologyExtractionService()


def get_gmail_message_tracking_service(
    neo4j: Neo4jDep,
) -> GmailMessageTrackingService:
    return GmailMessageTrackingService(neo4j)


async def get_neo4j_session() -> AsyncGenerator[Neo4jConnection, None]:
    """Yield Neo4j connection for request-scoped dependency injection."""
    connection = get_neo4j_connection()
    yield connection


def get_gmail_ingestion_service(
    candidate_service: CandidateManagementService = Depends(
        get_candidate_service
    ),
    pdf_service: PDFExtractionService = Depends(
        get_pdf_extraction_service
    ),
    skill_service: SkillExtractionService = Depends(
        get_skill_extraction_service
    ),
    project_service: ProjectExtractionService = Depends(
        get_project_extraction_service
    ),
    education_service: EducationExtractionService = Depends(
        get_education_extraction_service
    ),
    technology_service: TechnologyExtractionService = Depends(
        get_technology_extraction_service
    ),
    graph_service: Neo4jGraphService = Depends(
        get_neo4j_graph_service
    ),
    message_tracking_service: GmailMessageTrackingService = Depends(
        get_gmail_message_tracking_service
    ),
) -> GmailIngestionService:
    return GmailIngestionService(
        candidate_service=candidate_service,
        pdf_service=pdf_service,
        skill_service=skill_service,
        project_service=project_service,
        education_service=education_service,
        technology_service=technology_service,
        graph_service=graph_service,
        message_tracking_service=message_tracking_service,
    )

def get_query_parser() -> QueryParser:
    return QueryParser()