from __future__ import annotations
import os
import re
import textwrap
import psycopg2
import psycopg2.extras
from typing import Optional
from langchain.tools import tool
import anthropic

from db import get_connection
from db.chroma import init_chroma, search_jobs as chroma_search

# ── User context ───────────────────────────────────────────────────────────
# Set once at agent startup via set_current_user(); read by tools that need it.
_context: dict = {"user_id": None}

def set_current_user(user_id: int) -> None:
    _context["user_id"] = user_id


# ── helpers ───────────────────────────────────────────────────────────────

def _conn():
    return get_connection()

def _collection():
    return init_chroma()

def _run_query(sql: str, params: tuple = (), description: str = ""):
    """Safely runs SQL queries using tuple parameters to prevent SQL injection."""
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description] if cur.description else []
    finally:
        conn.close()
    return {"description": description, "columns": cols, "rows": [dict(r) for r in rows]}


# ── tools ─────────────────────────────────────────────────────────────────

@tool
def semantic_search_jobs(query: str, n_results: int = 5):
    """Search jobs using semantic similarity (vector search).
    Use for: finding jobs by natural-language description, skill match, or profile.
    Examples: 'find Python backend jobs', 'jobs at fintech startups'
    """
    collection = _collection()
    hits = chroma_search(collection, query, n_results=n_results)
    job_ids = [h["metadata"]["job_id"] for h in hits]

    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, title, company, role, location, url, description FROM jobs WHERE id = ANY(%s)",
                (job_ids,),
            )
            rows = {r["id"]: dict(r) for r in cur.fetchall()}
    finally:
        conn.close()

    return {"jobs": [rows[jid] for jid in job_ids if jid in rows]}


@tool
def get_job_details(job_ids: list[str]):
    """Get full job details for given job IDs.
    Use after search results return IDs the user wants to know more about.
    """
    return _run_query(
        "SELECT * FROM jobs WHERE id = ANY(%s)",
        (job_ids,),
        "Fetch full job details",
    )


@tool
def get_job_aggregate(operation: str, column: str, role_filter: Optional[str] = None):
    """Calculate COUNT, AVG, MIN, or MAX statistics on job data.
    - operation: one of ['COUNT', 'AVG', 'MIN', 'MAX']
    - column: one of ['yearsexperience', 'posted_at']
    - role_filter: optional role name to filter by (e.g. 'data scientist')
    Examples: average experience for Data Scientists, count of all jobs
    """
    ALLOWED_OPS = {"COUNT", "AVG", "MIN", "MAX"}
    ALLOWED_COLUMNS = {"yearsexperience", "posted_at", "scraped_at", "id"}

    op_upper = operation.upper()
    col_lower = column.lower()

    if op_upper not in ALLOWED_OPS:
        return {"error": f"Operation '{operation}' not allowed. Use COUNT, AVG, MIN, or MAX."}
    if col_lower not in ALLOWED_COLUMNS:
        return {"error": f"Column '{column}' not allowed for calculations."}

    sql = f"SELECT {op_upper}({col_lower}) AS result FROM jobs WHERE 1=1"
    params = []

    if role_filter:
        words = role_filter.split()
        or_conditions = [f"LOWER(role) LIKE LOWER(%s)" for _ in words]
        params.extend(f"%{w}%" for w in words)
        sql += f" AND ({' OR '.join(or_conditions)})"

    return _run_query(sql, tuple(params), f"{op_upper} of {col_lower}")


@tool
def get_column_distribution(column: str, limit: int = 15):
    """Get top items and their counts for a given column — useful for breakdowns.
    - column: one of ['role', 'seniority', 'location', 'company', 'yearsexperience']
    Examples: top companies, seniority breakdown, most common roles
    """
    ALLOWED_COLUMNS = {"role", "seniority", "location", "company", "yearsexperience"}
    col_lower = column.lower()

    if col_lower not in ALLOWED_COLUMNS:
        return {"error": f"Cannot group by column '{column}'."}

    return _run_query(
        f"""
        SELECT {col_lower} AS item, COUNT(*) AS count
        FROM jobs WHERE {col_lower} IS NOT NULL
        GROUP BY {col_lower} ORDER BY count DESC LIMIT %s
        """,
        (limit,),
        f"Distribution of {col_lower}",
    )


@tool
def search_jobs_by_criteria(
    role: Optional[str] = None,
    location: Optional[str] = None,
    company: Optional[str] = None,
    max_experience: Optional[int] = None,
):
    """Filter jobs by specific fields.
    - role: e.g. 'backend', 'react developer'
    - location: e.g. 'Tel Aviv', 'remote'
    - company: e.g. 'Google', 'startup'
    - max_experience: maximum years of experience required
    """
    sql = "SELECT id, title, company, role, location, url FROM jobs"
    conditions, params = [], []

    if role:
        conditions.append("LOWER(role) LIKE LOWER(%s)")
        params.append(f"%{role}%")
    if location:
        conditions.append("LOWER(location) LIKE LOWER(%s)")
        params.append(f"%{location}%")
    if company:
        conditions.append("LOWER(company) LIKE LOWER(%s)")
        params.append(f"%{company}%")
    if max_experience is not None:
        conditions.append("yearsexperience <= %s")
        params.append(max_experience)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY scraped_at DESC LIMIT %s"
    params.append(10)

    return _run_query(sql, tuple(params), "Filtered job search")


@tool
def top_skills(role: str, limit: int = 10):
    """Get the most required skills for a specific role.
    Examples: top skills for DevOps, most needed skills for Data Scientists
    """
    return _run_query(
        """
        SELECT unnest(skills_must) AS skill, COUNT(*) AS cnt
        FROM jobs WHERE LOWER(role) = LOWER(%s)
        GROUP BY skill ORDER BY cnt DESC LIMIT %s
        """,
        (role, limit),
        f"Top skills for {role}",
    )


@tool
def top_skills_all(limit: int = 15):
    """Get the most required skills across all jobs in the database.
    Use when the user asks about the overall market or doesn't specify a role.
    """
    return _run_query(
        """
        SELECT unnest(skills_must) AS skill, COUNT(*) AS cnt
        FROM jobs GROUP BY skill ORDER BY cnt DESC LIMIT %s
        """,
        (limit,),
        "Top skills overall",
    )


@tool
def tailor_resume_to_job(job_id: str) -> dict:
    """Tailor the current user's resume to a specific job posting.
    Rewords existing content to better match the job description using its keywords
    and priorities. Never adds new skills, experiences, or credentials that are not
    already in the resume. Saves the result as a PDF and returns the file path.
    Use when the user asks to tailor or customise their resume for a job.
    """
    user_id = _context.get("user_id")
    if not user_id:
        return {"error": "No user session active. Cannot access resume."}

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Fetch resume
            cur.execute(
                "SELECT content FROM resumes WHERE user_id = %s",
                (user_id,),
            )
            resume_row = cur.fetchone()
            if not resume_row:
                return {"error": "No resume on file. Please upload a PDF resume first."}

            # Fetch job
            cur.execute(
                "SELECT title, company, description, skills_must, skills_nice FROM jobs WHERE id = %s",
                (job_id,),
            )
            job_row = cur.fetchone()
            if not job_row:
                return {"error": f"Job '{job_id}' not found in the database."}
    finally:
        conn.close()

    resume_text = resume_row["content"]
    job_title   = job_row["title"] or ""
    job_company = job_row["company"] or ""
    job_desc    = job_row["description"] or ""
    skills_must = ", ".join(job_row["skills_must"] or [])
    skills_nice = ", ".join(job_row["skills_nice"] or [])

    prompt = textwrap.dedent(f"""
        You are a professional resume editor. Your task is to lightly tailor the
        candidate's resume for a specific job posting.

        STRICT RULES — you must follow all of them:
        1. Do NOT add any new skills, tools, technologies, experiences, projects,
           certifications, or credentials that are not already present in the resume.
        2. Only rephrase, reorder, or reword existing content to better reflect the
           language and priorities of the job description.
        3. Keep every section present in the original. Do not remove sections.
        4. Preserve all dates, company names, job titles, and education details exactly.
        5. Output only the final tailored resume text — no commentary, no preamble.

        ── JOB POSTING ──────────────────────────────────────────────────────
        Title:    {job_title}
        Company:  {job_company}
        Required skills: {skills_must}
        Nice-to-have:    {skills_nice}

        Description:
        {job_desc}

        ── ORIGINAL RESUME ──────────────────────────────────────────────────
        {resume_text}
    """).strip()

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    tailored_text = message.content[0].text.strip()

    # ── Save as PDF ───────────────────────────────────────────────────────
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "tailored_resumes",
    )
    os.makedirs(output_dir, exist_ok=True)

    safe_job = re.sub(r"[^a-zA-Z0-9_-]", "_", job_id)[:40]
    filename  = f"resume_user{user_id}_{safe_job}.pdf"
    filepath  = os.path.join(output_dir, filename)

    _save_pdf(tailored_text, filepath)

    return {
        "message":  "Tailored resume saved successfully.",
        "file":     filepath,
        "job_title": job_title,
        "company":   job_company,
    }


def _save_pdf(text: str, filepath: str) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_LEFT

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    body   = ParagraphStyle("body",   parent=styles["Normal"], fontSize=10, leading=14, alignment=TA_LEFT)
    header = ParagraphStyle("header", parent=styles["Normal"], fontSize=12, leading=16, spaceAfter=2 * mm, fontName="Helvetica-Bold")

    story = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 4 * mm))
            continue
        # Heuristic: all-caps short lines or lines ending with ":" are headings
        is_heading = (stripped.isupper() and len(stripped) < 60) or (stripped.endswith(":") and len(stripped) < 50)
        style = header if is_heading else body
        story.append(Paragraph(stripped, style))
        story.append(Spacer(1, 1 * mm))

    doc.build(story)


# ── exported list ─────────────────────────────────────────────────────────
# This is the only thing agent.py needs to import

TOOLS = [
    semantic_search_jobs,
    get_job_details,
    get_job_aggregate,
    get_column_distribution,
    search_jobs_by_criteria,
    top_skills,
    top_skills_all,
    tailor_resume_to_job,
]