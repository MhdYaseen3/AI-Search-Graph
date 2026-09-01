from fastapi import APIRouter, Depends

from app.api.deps import (
    get_ai_summary_service,
    get_query_parser,
    get_ranking_service,
    get_search_service,
)
from app.schemas.search import (
    MatchExplanationRequest,
    MatchExplanationResponse,
    SearchResponse,
)
from app.services.ai_summary import AISummaryService
from app.services.query_parser import QueryParser
from app.services.ranking import RankingService
from app.services.search import SearchService

router = APIRouter(
    prefix="/search",
    tags=["Search"],
)


@router.post("", response_model=SearchResponse)
async def search_candidates(
    query: str,
    query_parser: QueryParser = Depends(get_query_parser),
    search_service: SearchService = Depends(get_search_service),
    ranking_service: RankingService = Depends(get_ranking_service),
) -> SearchResponse:
    parsed_query = query_parser.parse(query)

    raw_results = await search_service.search(parsed_query)

    ranked_results = ranking_service.rank(
        raw_results,
        parsed_query,
    )

    return SearchResponse(
        query=query,
        total=len(ranked_results),
        parsed_role=parsed_query.role,
        parsed_skills=parsed_query.skills,
        parsed_technologies=parsed_query.technologies,
        parsed_projects=parsed_query.projects,
        min_experience_years=parsed_query.min_experience_years,
        results=ranked_results,
    )


@router.post("/explain", response_model=MatchExplanationResponse)
async def explain_match(
    payload: MatchExplanationRequest,
    query_parser: QueryParser = Depends(get_query_parser),
    summary_service: AISummaryService = Depends(get_ai_summary_service),
) -> MatchExplanationResponse:
    parsed_query = query_parser.parse(payload.query)
    explanation, source = await summary_service.generate_match_explanation(
        payload.candidate_id,
        parsed_query,
    )

    return MatchExplanationResponse(
        candidate_id=payload.candidate_id,
        query=payload.query,
        explanation=explanation,
        source=source,
    )
