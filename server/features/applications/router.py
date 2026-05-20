from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends
from core.security import get_current_user
from features.applications import service

router = APIRouter()


@router.get("/")
def list_my_applications(
    status: Optional[str] = None,
    user_id: str = Depends(get_current_user),
):
    return service.list_applications(int(user_id), status)
