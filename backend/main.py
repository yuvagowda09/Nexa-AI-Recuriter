from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from routes.candidates import router as candidates_router
from routes.pipeline import router as pipeline_router
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from routes.jobs import router as jobs_router
from routes.auth import router as auth_router
from routes.ai import router as ai_router
from routes.organization import router as organization_router


app = FastAPI(title="AI Recruiter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(organization_router)
app.include_router(candidates_router)
app.include_router(pipeline_router)


@app.get("/")
def home():
    return {
        "message": "AI Recruiter Backend is running!"
    }


@app.get("/health")
def health():

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as e:

        return {
            "status": "error",
            "database": "not connected",
            "message": str(e)
        }
