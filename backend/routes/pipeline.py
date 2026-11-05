
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from dependencies import get_db
from models import Candidate, Job, Review, User
from security import get_current_user, require_roles

router = APIRouter(prefix="/pipeline", tags=["Recruitment Pipeline"])

ALLOWED_STATUSES = {
    "screening",
    "shortlisted",
    "interview_scheduled",
    "interview_completed",
    "offer",
    "hired",
    "rejected",
    "withdrawn",
}


class PipelineCreate(BaseModel):
    candidate_id: int
    job_id: int
    status: str = "screening"
    notes: str | None = Field(default=None, max_length=5000)


class PipelineUpdate(BaseModel):
    status: str
    notes: str | None = Field(default=None, max_length=5000)


def validate_status(status: str):
    if status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}",
        )


def get_review_for_org(db, review_id, organization_id):
    return (
        db.query(Review)
        .join(Job, Review.job_id == Job.id)
        .join(Candidate, Review.candidate_id == Candidate.id)
        .filter(
            Review.id == review_id,
            Job.organization_id == organization_id,
            Candidate.organization_id == organization_id,
        )
        .first()
    )


@router.get("/")
def list_pipeline(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reviews = (
        db.query(Review, Candidate, Job)
        .join(Job, Review.job_id == Job.id)
        .join(Candidate, Review.candidate_id == Candidate.id)
        .filter(
            Job.organization_id == current_user.organization_id,
            Candidate.organization_id == current_user.organization_id,
        )
        .order_by(Review.created_at.desc())
        .all()
    )

    return [
        {
            "id": review.id,
            "candidate_id": review.candidate_id,
            "candidate_name": candidate.name,
            "job_id": review.job_id,
            "job_title": job.title,
            "status": review.status,
            "notes": review.notes,
            "created_at": review.created_at,
        }
        for review, candidate, job in reviews
    ]


@router.post("/", status_code=201)
def create_pipeline_entry(
    payload: PipelineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "team_lead", "recruiter")
    ),
):
    validate_status(payload.status)

    candidate = db.query(Candidate).filter(
        Candidate.id == payload.candidate_id,
        Candidate.organization_id == current_user.organization_id,
    ).first()

    job = db.query(Job).filter(
        Job.id == payload.job_id,
        Job.organization_id == current_user.organization_id,
    ).first()

    if candidate is None or job is None:
        raise HTTPException(
            status_code=404,
            detail="Candidate or job not found in your organization.",
        )

    existing = db.query(Review).filter(
        Review.candidate_id == candidate.id,
        Review.job_id == job.id,
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="This candidate already has a pipeline entry for this job.",
        )

    review = Review(
        candidate_id=candidate.id,
        job_id=job.id,
        status=payload.status,
        notes=payload.notes,
    )

    try:
        db.add(review)
        db.commit()
        db.refresh(review)
    except Exception:
        db.rollback()
        raise

    return {
        "id": review.id,
        "candidate_id": candidate.id,
        "candidate_name": candidate.name,
        "job_id": job.id,
        "job_title": job.title,
        "status": review.status,
        "notes": review.notes,
        "created_at": review.created_at,
    }


@router.patch("/{review_id}")
def update_pipeline_entry(
    review_id: int,
    payload: PipelineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "team_lead", "recruiter")
    ),
):
    validate_status(payload.status)

    review = get_review_for_org(
        db, review_id, current_user.organization_id
    )

    if review is None:
        raise HTTPException(
            status_code=404, detail="Pipeline entry not found.")

    review.status = payload.status
    review.notes = payload.notes

    try:
        db.commit()
        db.refresh(review)
    except Exception:
        db.rollback()
        raise

    return {
        "id": review.id,
        "candidate_id": review.candidate_id,
        "job_id": review.job_id,
        "status": review.status,
        "notes": review.notes,
        "created_at": review.created_at,
    }


@router.delete("/{review_id}", status_code=204)
def delete_pipeline_entry(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    ),
):
    review = get_review_for_org(
        db, review_id, current_user.organization_id
    )

    if review is None:
        raise HTTPException(
            status_code=404, detail="Pipeline entry not found.")

    db.delete(review)
    db.commit()
    return None
