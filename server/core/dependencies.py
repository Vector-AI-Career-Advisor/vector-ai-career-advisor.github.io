"""Shared FastAPI dependencies."""
from core.security import get_current_user
from db.postgres import get_connection

__all__ = ["get_current_user", "get_connection"]
