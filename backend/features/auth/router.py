from fastapi import APIRouter, Depends
from core.security import get_current_user
from features.auth.schemas import UserCreate, UserLogin, TokenResponse
from features.auth import service

router = APIRouter()


@router.post("/signup", status_code=201)
def signup(user: UserCreate):
    return service.signup(user)


@router.post("/login", response_model=TokenResponse)
def login(user: UserLogin):
    return service.login(user)


@router.get("/me")
def get_me(user_id: str = Depends(get_current_user)):
    return service.get_me(user_id)
