import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from features.auth.router import router as auth_router
from features.jobs.router import router as jobs_router
from features.resumes.router import router as resumes_router
from features.stats.router import router as stats_router
from features.applications.router import router as applications_router
from agents.router import router as agent_router
from db.postgres import init_db
from core.exceptions import AppError, app_error_handler
from core.logging import setup_logging

setup_logging()
log = logging.getLogger(__name__)

app = FastAPI(title="JobBoard API", version="1.0.0")

app.add_exception_handler(AppError, app_error_handler)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    log.info("%s %s → %d", request.method, request.url.path, response.status_code)
    return response

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.error(
        "%s %s → 500 | Internal server error\n%s",
        request.method,
        request.url.path,
        traceback.format_exc(),
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

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
    log.info("Starting JobBoard API")
    init_db()

app.include_router(auth_router,    prefix="/auth",    tags=["auth"])
app.include_router(stats_router,   prefix="/jobs",    tags=["jobs"])   # /jobs/stats — must be before jobs_router
app.include_router(jobs_router,    prefix="/jobs",    tags=["jobs"])
app.include_router(resumes_router,      prefix="/resumes",      tags=["resumes"])
app.include_router(applications_router, prefix="/applications", tags=["applications"])
app.include_router(agent_router,        prefix="/agents",       tags=["agents"])

@app.get("/")
def root():
    return {"message": "JobBoard API is running"}
