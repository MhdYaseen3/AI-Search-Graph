from fastapi import APIRouter, Depends, Query, status
from app.api.deps import get_job_service
from app.schemas.common import MessageResponse
from app.schemas.job import JobCreate, JobListResponse, JobResponse, JobUpdate
from app.services.job import JobManagementService

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)

@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    service: JobManagementService = Depends(get_job_service),
) -> JobResponse:
    """Create a new job posting."""
    job = await service.create(payload)
    return JobResponse.model_validate(job)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None, description="Filter by status: Active or Closed"),
    service: JobManagementService = Depends(get_job_service),
) -> JobListResponse:
    """List all jobs with optional status filtering."""
    if status and status in ["Active", "Closed"]:
        jobs, total = await service.list_jobs_by_status(status, skip=skip, limit=limit)
    else:
        jobs, total = await service.list_jobs(skip=skip, limit=limit)

    return JobListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[JobResponse.model_validate(j) for j in jobs],
    )


@router.get("/search", response_model=JobListResponse)
async def search_jobs(
    q: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: JobManagementService = Depends(get_job_service),
) -> JobListResponse:
    """Search jobs by title, description, skills, or location."""
    jobs, total = await service.search_jobs(q, skip=skip, limit=limit)

    return JobListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[JobResponse.model_validate(j) for j in jobs],
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    service: JobManagementService = Depends(get_job_service),
) -> JobResponse:
    """Retrieve a job by ID."""
    job = await service.get_by_id(job_id)
    return JobResponse.model_validate(job)


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    payload: JobUpdate,
    service: JobManagementService = Depends(get_job_service),
) -> JobResponse:
    """Update an existing job."""
    job = await service.update(job_id, payload)
    return JobResponse.model_validate(job)


@router.delete("/{job_id}", response_model=MessageResponse)
async def delete_job(
    job_id: str,
    service: JobManagementService = Depends(get_job_service),
) -> MessageResponse:
    """Delete a job posting."""
    await service.delete(job_id)
    return MessageResponse(message=f"Job {job_id} deleted successfully")
