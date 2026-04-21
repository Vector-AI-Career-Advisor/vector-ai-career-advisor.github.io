from __future__ import annotations
import logging
from datetime import date
from typing import List, Optional
import psycopg2
from psycopg2.extras import execute_values
from config import DB_CONFIG

log = logging.getLogger(__name__)


# ── Connection ────────────────────────────────────────────────────────────────

def get_connection():
    return psycopg2.connect(**DB_CONFIG)


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db(conn) -> None:
    """Create the jobs table and supporting indexes if they do not exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id                TEXT PRIMARY KEY,
                title             TEXT,
                role              TEXT,
                seniority         TEXT,
                company           TEXT,
                location          TEXT,
                url               TEXT,
                description       TEXT,
                skills_must       TEXT[],
                skills_nice       TEXT[],
                yearsexperience   INTEGER,
                past_experience   TEXT[],
                keyword           TEXT,
                source            TEXT DEFAULT 'linkedin',
                posted_at         DATE,
                scraped_at        TIMESTAMP DEFAULT NOW()
            );
        """)

        # Indexes — created with IF NOT EXISTS so repeated calls are safe
        cur.execute("""
            CREATE INDEX IF NOT EXISTS jobs_scraped_date_idx
                ON jobs ((scraped_at::date));
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS jobs_keyword_idx
                ON jobs (keyword);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS jobs_role_idx
                ON jobs (role);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS jobs_seniority_idx
                ON jobs (seniority);
        """)

    conn.commit()
    log.info("DB schema and indexes ready.")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_date(val) -> Optional[date]:
    """
    Coerce a posted_at value to a Python date object (or None).
    Accepts: date, datetime, ISO string 'YYYY-MM-DD', or None.
    Passing a native date object avoids psycopg2's implicit string cast
    which can silently produce wrong values on locale-sensitive servers.
    """
    if val is None:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return date.fromisoformat(val[:10])
        except ValueError:
            log.warning("Could not parse posted_at value '%s' — storing NULL.", val)
            return None
    return None


# ── Writes ────────────────────────────────────────────────────────────────────

def insert_jobs(conn, jobs: List[dict]) -> int:
    """Insert jobs, silently skip duplicates. Returns number of rows sent."""
    if not jobs:
        return 0

    rows = [
        (
            j["id"], j["title"], j.get("role"), j.get("seniority"),
            j["company"], j["location"], j["url"],
            j.get("description"),
            j.get("skills_must", []), j.get("skills_nice", []),
            j.get("yearsexperience"),
            j.get("past_experience", []),
            j["keyword"], j.get("source", "linkedin"),
            _to_date(j.get("posted_at")),   # always a date object or None
        )
        for j in jobs
    ]

    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO jobs (
                id, title, role, seniority, company, location, url,
                description, skills_must, skills_nice, yearsexperience,
                past_experience, keyword, source, posted_at
            )
            VALUES %s
            ON CONFLICT (id) DO NOTHING;
        """, rows)
    conn.commit()
    log.info("Inserted %d jobs into PostgreSQL.", len(rows))
    return len(rows)


# ── Reads ─────────────────────────────────────────────────────────────────────

def count_jobs(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM jobs")
        return cur.fetchone()[0]


def count_jobs_today(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM jobs WHERE scraped_at::date = %s",
            (date.today(),),
        )
        return cur.fetchone()[0]


def fetch_all_ids(conn) -> set:
    """Return all known job IDs — used to skip duplicates during scraping."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM jobs;")
        return {row[0] for row in cur.fetchall()}


def fetch_jobs_by_ids(conn, ids: List[str]) -> List[dict]:
    """Fetch full job rows for a given list of IDs."""
    if not ids:
        return []
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, title, role, seniority, company, location, url,
                   description, skills_must, skills_nice, yearsexperience,
                   past_experience, keyword, source, posted_at
            FROM jobs
            WHERE id = ANY(%s);
        """, (ids,))
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def fetch_jobs_missing_from_chroma(conn, chroma_job_ids: set) -> List[dict]:
    """
    Return jobs that exist in Postgres but are missing from ChromaDB.
    Fetches only IDs first to avoid a full table scan with data transfer.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM jobs;")
        all_ids = [row[0] for row in cur.fetchall()]

    missing_ids = [jid for jid in all_ids if jid not in chroma_job_ids]
    log.info("%d jobs missing from ChromaDB — backfilling.", len(missing_ids))
    return fetch_jobs_by_ids(conn, missing_ids)

    