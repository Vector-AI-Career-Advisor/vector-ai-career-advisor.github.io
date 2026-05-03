import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, resumes, agent_chat
from routers import jobs_stats_endpoint as jobs
from db.database import init_db

app = FastAPI(title="JobBoard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Init DB tables on startup
@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(auth.router,       prefix="/auth",    tags=["auth"])
app.include_router(jobs.router,       prefix="/jobs",    tags=["jobs"])
app.include_router(resumes.router,    prefix="/resumes", tags=["resumes"])
app.include_router(agent_chat.router, prefix="/agents",   tags=["agents"])

@app.get("/")
def root():
    return {"message": "JobBoard API is running"}
