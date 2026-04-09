import logging
import psycopg2
from core.config import DB_CONFIG

log = logging.getLogger(__name__)


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def init_db() -> None:
    """Create all required tables on first run."""
    conn = get_connection()
    with conn.cursor() as cur:
        # Users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         SERIAL PRIMARY KEY,
                email      TEXT UNIQUE NOT NULL,
                password   TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        # Jobs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id               TEXT PRIMARY KEY,
                title            TEXT,
                role             TEXT,
                seniority        TEXT,
                company          TEXT,
                location         TEXT,
                url              TEXT,
                description      TEXT,
                skills_must      TEXT[],
                skills_nice      TEXT[],
                yearsexperience  INTEGER,
                past_experience  TEXT[],
                keyword          TEXT,
                source           TEXT DEFAULT 'linkedin',
                posted_at        DATE,
                scraped_at       TIMESTAMP DEFAULT NOW()
            );
        """)
    conn.commit()
    conn.close()
    log.info("DB schema ready.")
