from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, jobs_stats_endpoint
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

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(jobs_stats_endpoint.router, prefix="/jobs", tags=["jobs"])

@app.get("/")
def root():
    return {"message": "JobBoard API is running"}
