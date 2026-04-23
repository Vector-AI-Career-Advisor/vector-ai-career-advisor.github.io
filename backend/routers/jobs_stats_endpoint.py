

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from db.database import get_connection
from core.security import get_current_user
from models.schemas import JobOut

router = APIRouter()

LIMIT = 50


@router.get("/stats")
def get_stats(user_id: str = Depends(get_current_user)):
    """
    Returns aggregated statistics about the jobs in the database:
      - jobs_per_day       : count of jobs scraped per calendar day (last 60 days)
      - top_companies      : top 15 companies by number of listings
      - jobs_by_location   : top 15 locations by number of listings
      - top_skills         : top 20 must-have skills across all jobs
      - by_seniority       : job counts broken down by seniority level
      - skills_by_role     : top 8 must-have skills per distinct role
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:

            # ── 1. Jobs per day (last 60 days) ────────────────────────────
            cur.execute("""
                SELECT DATE(scraped_at) AS day, COUNT(*) AS count
                FROM jobs
                WHERE scraped_at >= NOW() - INTERVAL '60 days'
                GROUP BY day
                ORDER BY day ASC;
            """)
            jobs_per_day = [
                {"date": str(r[0]), "count": r[1]}
                for r in cur.fetchall()
            ]

            # ── 2. Top 15 hiring companies ─────────────────────────────────
            cur.execute("""
                SELECT company, COUNT(*) AS count
                FROM jobs
                WHERE company IS NOT NULL AND company <> ''
                GROUP BY company
                ORDER BY count DESC
                LIMIT 15;
            """)
            top_companies = [
                {"company": r[0], "count": r[1]}
                for r in cur.fetchall()
            ]

            # ── 3. Jobs by location (top 15) ───────────────────────────────
            cur.execute("""
                SELECT location, COUNT(*) AS count
                FROM jobs
                WHERE location IS NOT NULL AND location <> ''
                GROUP BY location
                ORDER BY count DESC
                LIMIT 15;
            """)
            jobs_by_location = [
                {"location": r[0], "count": r[1]}
                for r in cur.fetchall()
            ]

            # ── 4. Top 20 must-have skills (global) ────────────────────────
            cur.execute("""
                SELECT skill, COUNT(*) AS count
                FROM jobs, UNNEST(skills_must) AS skill
                WHERE skills_must IS NOT NULL
                  AND array_length(skills_must, 1) > 0
                GROUP BY skill
                ORDER BY count DESC
                LIMIT 20;
            """)
            top_skills = [
                {"skill": r[0], "count": r[1]}
                for r in cur.fetchall()
            ]

            # ── 5. Jobs by seniority ───────────────────────────────────────
            cur.execute("""
                SELECT seniority, COUNT(*) AS count
                FROM jobs
                WHERE seniority IS NOT NULL AND seniority <> ''
                GROUP BY seniority
                ORDER BY count DESC;
            """)
            by_seniority = [
                {"seniority": r[0], "count": r[1]}
                for r in cur.fetchall()
            ]

            # ── 6. Top skills per role (top 8 skills per role) ────────────
            cur.execute("""
                SELECT role, skill, COUNT(*) AS count
                FROM jobs, UNNEST(skills_must) AS skill
                WHERE role IS NOT NULL
                  AND role <> ''
                  AND skills_must IS NOT NULL
                  AND array_length(skills_must, 1) > 0
                GROUP BY role, skill
                ORDER BY role ASC, count DESC;
            """)
            raw_rows = cur.fetchall()

            skills_by_role: Dict[str, List[Dict]] = {}
            for role, skill, count in raw_rows:
                if role not in skills_by_role:
                    skills_by_role[role] = []
                if len(skills_by_role[role]) < 8:
                    skills_by_role[role].append({"skill": skill, "count": count})

            # ── 7. Summary counts ──────────────────────────────────────────
            cur.execute("SELECT COUNT(*) FROM jobs;")
            total_jobs = cur.fetchone()[0]

            cur.execute("SELECT COUNT(DISTINCT company) FROM jobs WHERE company IS NOT NULL;")
            total_companies = cur.fetchone()[0]

            cur.execute("SELECT COUNT(DISTINCT location) FROM jobs WHERE location IS NOT NULL;")
            total_locations = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(DISTINCT skill)
                FROM jobs, UNNEST(skills_must) AS skill
                WHERE skills_must IS NOT NULL;
            """)
            total_skills = cur.fetchone()[0]

            return {
                "summary": {
                    "total_jobs": total_jobs,
                    "total_companies": total_companies,
                    "total_locations": total_locations,
                    "total_skills": total_skills,
                },
                "jobs_per_day": jobs_per_day,
                "top_companies": top_companies,
                "jobs_by_location": jobs_by_location,
                "top_skills": top_skills,
                "by_seniority": by_seniority,
                "skills_by_role": skills_by_role,
            }
    finally:
        conn.close()




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
                       past_experience, keyword, source, posted_at, scraped_at,logo_url
                FROM jobs
                {where}
                ORDER BY scraped_at DESC
                LIMIT %s OFFSET %s;
            """, params)

            rows = cur.fetchall()
            if not rows:
                return {"items": [], "total": 0}

            cols = [d[0] for d in cur.description]
            total = rows[0][0]
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
                       past_experience, keyword, source, posted_at, scraped_at,logo_url
                FROM jobs WHERE id = %s
            """, (job_id,))
            row = cur.fetchone()
            if not row:
                return None

            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))
    finally:
        conn.close()
