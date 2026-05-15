import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from features.auth.router import router as auth_router
from features.jobs.router import router as jobs_router
from features.resumes.router import router as resumes_router
from features.stats.router import router as stats_router
from agents.router import router as agent_router
from db.postgres import init_db

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

app.include_router(auth_router,    prefix="/auth",    tags=["auth"])
app.include_router(stats_router,   prefix="/jobs",    tags=["jobs"])   # /jobs/stats — must be before jobs_router
app.include_router(jobs_router,    prefix="/jobs",    tags=["jobs"])
app.include_router(resumes_router, prefix="/resumes", tags=["resumes"])
app.include_router(agent_router,   prefix="/agents",  tags=["agents"])

@app.get("/")
def root():
    return {"message": "JobBoard API is running"}
