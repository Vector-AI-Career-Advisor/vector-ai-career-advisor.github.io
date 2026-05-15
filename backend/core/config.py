import os
from dotenv import load_dotenv

load_dotenv()

# Resolve paths relative to the backend/ directory so relative values in .env
# (e.g. "./chroma_db") always point inside backend/ regardless of CWD.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _resolve(path: str) -> str:
    """Return path unchanged if absolute, otherwise anchor it to backend/."""
    return path if os.path.isabs(path) else os.path.normpath(os.path.join(_BACKEND_DIR, path))

# ── Database ──────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME", "jobboard"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# ── JWT ───────────────────────────────────────────────────
SECRET_KEY            = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM             = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# ── ChromaDB ──────────────────────────────────────────────
CHROMA_PERSIST_DIR = _resolve(os.getenv("CHROMA_DIR", "chroma_db"))
CHROMA_COLLECTION  = os.getenv("CHROMA_COLLECTION")

# ── Pipeline ──────────────────────────────────────────────
ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL     = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
CHROME_VERSION      = int(os.getenv("CHROME_VERSION", 147))
DATE_FILTER         = os.getenv("DATE_FILTER", "r604800")
DAILY_TARGET        = int(os.getenv("DAILY_TARGET", 50))
