from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from db.database import get_connection
from core.security import get_current_user
from models.schemas import JobOut

router = APIRouter()


@router.get("/", response_model=List[JobOut])
def list_jobs(
    user_id: str = Depends(get_current_user),
    keyword: Optional[str] = Query(None),
    seniority: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    conn = get_connection()
    try:
        filters = []
        params: list = []

        if keyword:
            filters.append("(title ILIKE %s OR keyword ILIKE %s)")
            params += [f"%{keyword}%", f"%{keyword}%"]
        if seniority:
            filters.append("seniority ILIKE %s")
            params.append(f"%{seniority}%")
        if location:
            filters.append("location ILIKE %s")
            params.append(f"%{location}%")

        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        params += [limit, offset]

        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT id, title, role, seniority, company, location, url,
                       description, skills_must, skills_nice, yearsexperience,
                       past_experience, keyword, source, posted_at, scraped_at
                FROM jobs
                {where}
                ORDER BY scraped_at DESC
                LIMIT %s OFFSET %s;
            """, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, user_id: str = Depends(get_current_user)):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, role, seniority, company, location, url,
                       description, skills_must, skills_nice, yearsexperience,
                       past_experience, keyword, source, posted_at, scraped_at
                FROM jobs WHERE id = %s
            """, (job_id,))
            row = cur.fetchone()
            if not row:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Job not found")
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))
    finally:
        conn.close()
