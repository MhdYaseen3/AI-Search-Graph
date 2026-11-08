from fastapi import APIRouter, Depends

from app.api.deps import Neo4jDep, get_match_service
from app.schemas.dashboard import DashboardStatsResponse
from app.services.dashboard_metrics import DashboardMetricsService
from app.services.match import MatchService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    neo4j: Neo4jDep,
    match_service: MatchService = Depends(get_match_service),
) -> DashboardStatsResponse:
    return await DashboardMetricsService(neo4j, match_service).get_stats()
