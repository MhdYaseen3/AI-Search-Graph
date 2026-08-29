from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_candidate_graph_service, get_candidate_service
from app.schemas.candidate import (
    CandidateCreate,
    CandidateListResponse,
    CandidateResponse,
    CandidateUpdate,
)
from app.schemas.common import MessageResponse
from app.schemas.graph import CandidateDetailResponse, CandidateGraphResponse
from app.services.candidate_graph import CandidateGraphService
from app.services.candidate_management import CandidateManagementService

router = APIRouter(
    prefix="/candidates",
    tags=["Candidates"],
)

@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    payload: CandidateCreate,
    service: CandidateManagementService = Depends(get_candidate_service),
) -> CandidateResponse:
    candidate = await service.create(payload)
    return CandidateResponse.model_validate(candidate)


@router.get("", response_model=CandidateListResponse)
async def list_candidates(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: CandidateManagementService = Depends(get_candidate_service),
) -> CandidateListResponse:
    candidates, total = await service.list_candidates(skip=skip, limit=limit)
    return CandidateListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[CandidateResponse.model_validate(c) for c in candidates],
    )


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    service: CandidateManagementService = Depends(get_candidate_service),
) -> CandidateResponse:
    candidate = await service.get_by_id(candidate_id)
    return CandidateResponse.model_validate(candidate)


@router.get("/{candidate_id}/detail", response_model=CandidateDetailResponse)
async def get_candidate_detail(
    candidate_id: str,
    graph_service: CandidateGraphService = Depends(get_candidate_graph_service),
) -> CandidateDetailResponse:
    return await graph_service.get_candidate_detail(candidate_id)


@router.get("/{candidate_id}/graph", response_model=CandidateGraphResponse)
async def get_candidate_graph(
    candidate_id: str,
    graph_service: CandidateGraphService = Depends(get_candidate_graph_service),
) -> CandidateGraphResponse:
    return await graph_service.get_candidate_graph(candidate_id)


@router.patch("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: str,
    payload: CandidateUpdate,
    service: CandidateManagementService = Depends(get_candidate_service),
) -> CandidateResponse:
    candidate = await service.update(candidate_id, payload)
    return CandidateResponse.model_validate(candidate)


@router.delete("/{candidate_id}", response_model=MessageResponse)
async def delete_candidate(
    candidate_id: str,
    service: CandidateManagementService = Depends(get_candidate_service),
) -> MessageResponse:
    await service.delete(candidate_id)
    return MessageResponse(message=f"Candidate {candidate_id} deleted")
