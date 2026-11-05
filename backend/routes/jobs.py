
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from dependencies import get_db
from models import Job, User
from schemas import JobCreate, JobResponse
from security import get_current_user, require_roles

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)


@router.post("/", response_model=JobResponse)
def create_job(
    job: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "team_lead", "recruiter")
    ),
):
    new_job = Job(
        organization_id=current_user.organization_id,
        title=job.title,
        description=job.description,
        location=job.location,
        status=job.status,
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    return new_job


@router.get("/", response_model=list[JobResponse])
def get_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    jobs = (
        db.query(Job)
        .filter(Job.organization_id == current_user.organization_id)
        .all()
    )

    return jobs
