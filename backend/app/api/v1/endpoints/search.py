from fastapi import APIRouter, Depends

from app.api.deps import (
    get_query_parser,
    get_ranking_service,
    get_search_service,
)
from app.schemas.search import SearchResponse
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
        results=ranked_results,
    )