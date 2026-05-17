from typing import List, Optional
from features.applications import repository


def list_applications(user_id: int, status: Optional[str] = None) -> List[dict]:
    return repository.get_applications(user_id, status)
