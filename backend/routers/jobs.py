from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from db.database import get_connection
from core.security import get_current_user
from models.schemas import JobOut

router = APIRouter()

LIMIT = 50


@router.get("/")
def list_jobs(
    user_id: str = Depends(get_current_user),
    keyword: Optional[str] = Query(None),
    seniority: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    limit: int = Query(LIMIT),
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
                SELECT COUNT(*) OVER() AS total_count,
                       id, title, role, seniority, company, location, url,
                       description, skills_must, skills_nice, yearsexperience,
                       past_experience, keyword, source, posted_at, scraped_at
                FROM jobs
                {where}
                ORDER BY scraped_at DESC
                LIMIT %s OFFSET %s;
            """, params)

            rows = cur.fetchall()
            if not rows:
                return {"items": [], "total": 0}

            cols = [d[0] for d in cur.description]
            total = rows[0][0]  # total_count from window function
            items = []

            for row in rows:
                row_dict = dict(zip(cols, row))
                row_dict.pop("total_count")
                items.append(row_dict)

            return {"items": items, "total": total}
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
                return None

            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))
    finally:
        conn.close()