from typing import List, Optional
from db.postgres import get_connection, fetch_applications_by_user


def get_applications(user_id: int, status: Optional[str] = None) -> List[dict]:
    conn = get_connection()
    try:
        return fetch_applications_by_user(conn, user_id, status)
    finally:
        conn.close()
