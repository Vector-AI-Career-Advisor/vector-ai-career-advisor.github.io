from typing import Optional
from fastapi import APIRouter, Depends, Query
from core.security import get_current_user
from features.jobs.schemas import JobOut
from features.jobs import service, repository

router = APIRouter()


@router.get("/")
def list_jobs(
    user_id: str = Depends(get_current_user),
    keyword: Optional[str] = Query(None),
    seniority: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    limit: int = Query(repository.LIMIT),
    offset: int = Query(0),
):
    return service.list_jobs(keyword, seniority, location, limit, offset)


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, user_id: str = Depends(get_current_user)):
    return service.get_job(job_id)
