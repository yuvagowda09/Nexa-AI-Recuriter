
from fastapi import APIRouter, Depends
from models import User
from schemas import JobDescriptionRequest
from security import get_current_user
from ai_service import generate_job_description

router = APIRouter(
    prefix="/ai",
    tags=["AI"],
)


@router.post("/generate-job-description")
def generate_description(
    request: JobDescriptionRequest,
    current_user: User = Depends(get_current_user),
):
    description = generate_job_description(
        title=request.title,
        skills=request.skills,
        experience=request.experience,
    )

    return {
        "title": request.title,
        "description": description,
        "mode": "mock",
        "message": "Mock response only. No external AI API was called.",
    }
