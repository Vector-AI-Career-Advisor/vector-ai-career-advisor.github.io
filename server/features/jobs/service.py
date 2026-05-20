from typing import Optional
from features.jobs import repository


def list_jobs(
    keyword: Optional[str] = None,
    seniority: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = repository.LIMIT,
    offset: int = 0,
) -> dict:
    return repository.list_jobs(keyword, seniority, location, limit, offset)


def get_job(job_id: str) -> Optional[dict]:
    return repository.get_job(job_id)
