from __future__ import annotations
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr


# ── Auth ──────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Jobs ──────────────────────────────────────────────────

class JobOut(BaseModel):
    id: str
    title: Optional[str]
    role: Optional[str]
    seniority: Optional[str]
    company: Optional[str]
    location: Optional[str]
    url: Optional[str]
    description: Optional[str]
    skills_must: Optional[List[str]]
    skills_nice: Optional[List[str]]
    yearsexperience: Optional[int]
    past_experience: Optional[List[str]]
    keyword: Optional[str]
    source: Optional[str]
    posted_at: Optional[date]
    scraped_at: Optional[datetime]

    class Config:
        from_attributes = True
