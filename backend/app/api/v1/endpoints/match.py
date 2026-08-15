from fastapi import APIRouter, Depends, status

from app.api.deps import get_match_service
from app.schemas.match import JobMatchResponse
from app.services.match import MatchService

router = APIRouter(prefix="/jobs", tags=["Job Matching"])


@router.post(
    "/{job_id}/match",
    response_model=JobMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate candidate matches for a job",
)
async def match_candidates(
    job_id: str,
    service: MatchService = Depends(get_match_service),
) -> JobMatchResponse:
    """
    Generate and return ranked candidate matches for the specified job.
    """
    return await service.match_candidates(job_id)


@router.get(
    "/{job_id}/matches",
    response_model=JobMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Get matched candidates for a job",
)
async def get_job_matches(
    job_id: str,
    service: MatchService = Depends(get_match_service),
) -> JobMatchResponse:
    """
    Retrieve previously generated candidate matches for the specified job.
    """
    return await service.get_matches(job_id)