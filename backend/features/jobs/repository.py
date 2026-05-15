from typing import Optional
from db.postgres import get_connection

LIMIT = 50


def list_jobs(
    keyword: Optional[str] = None,
    seniority: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = LIMIT,
    offset: int = 0,
) -> dict:
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


def get_job(job_id: str) -> Optional[dict]:
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
