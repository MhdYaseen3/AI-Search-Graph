from fastapi import APIRouter

from app.api.v1.endpoints import (
    candidates,
    health,
    jobs,
    resumes,
    search,
    match,
    gmail,
)


api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(candidates.router)
api_router.include_router(jobs.router)
api_router.include_router(resumes.router)
api_router.include_router(search.router)
api_router.include_router(match.router)
api_router.include_router(gmail.router)