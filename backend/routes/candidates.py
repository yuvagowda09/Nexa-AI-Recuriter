
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from ai_service import extract_resume_text, structure_resume_text
from pathlib import Path
from fastapi.responses import FileResponse

from sqlalchemy.orm import Session
from resume_storage import STORAGE_DIR, save_pdf_resume

from dependencies import get_db
from models import Candidate, Resume, User
from schemas import CandidateCreate, CandidateResponse, ResumeUploadResponse
from security import get_current_user, require_roles

router = APIRouter(
    prefix="/candidates",
    tags=["Candidates"],
)


@router.post("/", response_model=CandidateResponse)
def create_candidate(
    candidate: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "team_lead", "recruiter")
    ),
):
    new_candidate = Candidate(
        organization_id=current_user.organization_id,
        name=candidate.name,
        email=candidate.email,
        phone=candidate.phone,
        location=candidate.location,
    )

    db.add(new_candidate)
    db.commit()
    db.refresh(new_candidate)

    return new_candidate


@router.get("/", response_model=list[CandidateResponse])
def get_candidates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidates = (
        db.query(Candidate)
        .filter(
            Candidate.organization_id == current_user.organization_id
        )
        .all()
    )

    return candidates


@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = (
        db.query(Candidate)
        .filter(
            Candidate.id == candidate_id,
            Candidate.organization_id == current_user.organization_id,
        )
        .first()
    )

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found.",
        )

    return candidate


@router.post(
    "/{candidate_id}/resumes",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_candidate_resume(
    candidate_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "team_lead", "recruiter")
    ),
):
    # Verify company ownership before saving any file.
    candidate = (
        db.query(Candidate)
        .filter(
            Candidate.id == candidate_id,
            Candidate.organization_id == current_user.organization_id,
        )
        .first()
    )

    if candidate is None:
        await file.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found.",
        )

    stored_name, destination = await save_pdf_resume(file)

    try:
        resume = Resume(
            candidate_id=candidate.id,
            file_path=stored_name,
            status="uploaded",
        )

        db.add(resume)
        db.commit()
        db.refresh(resume)

        return resume

    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save the resume right now.",
        ) from None


@router.get("/{candidate_id}/resumes/{resume_id}/download")
def download_candidate_resume(
    candidate_id: int,
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "team_lead", "recruiter")
    ),
):
    # Verify the resume, candidate, and company all match.
    resume = (
        db.query(Resume)
        .join(Candidate, Resume.candidate_id == Candidate.id)
        .filter(
            Resume.id == resume_id,
            Resume.candidate_id == candidate_id,
            Candidate.organization_id == current_user.organization_id,
        )
        .first()
    )

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    storage_root = STORAGE_DIR.resolve()
    file_path = (storage_root / resume.file_path).resolve()

    # Prevent a stored path from escaping the private storage directory.
    if file_path.parent != storage_root or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume file not found.",
        )

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=f"resume-{resume.id}.pdf",
        content_disposition_type="attachment",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.get("/{candidate_id}/resumes")
def list_candidate_resumes(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "team_lead", "recruiter")
    ),
):
    candidate = (
        db.query(Candidate)
        .filter(
            Candidate.id == candidate_id,
            Candidate.organization_id == current_user.organization_id,
        )
        .first()
    )

    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail="Candidate not found.",
        )

    resumes = (
        db.query(Resume)
        .filter(Resume.candidate_id == candidate.id)
        .order_by(Resume.created_at.desc())
        .all()
    )

    return [
        {
            "id": resume.id,
            "candidate_id": candidate.id,
            "status": resume.status,
            "created_at": resume.created_at,
            "character_count": (
                len(resume.extracted_text)
                if resume.extracted_text
                else 0
            ),
            "preview": (
                resume.extracted_text[:500]
                if resume.extracted_text
                else None
            ),
            "download_url": (
                f"/candidates/{candidate.id}/resumes/"
                f"{resume.id}/download"
            ),
        }
        for resume in resumes
    ]


@router.post("/{candidate_id}/resumes/{resume_id}/parse")
def parse_candidate_resume(
    candidate_id: int,
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "team_lead", "recruiter")
    ),
):
    # Find the resume only if it belongs to this organization's candidate.
    resume = (
        db.query(Resume)
        .join(Candidate, Resume.candidate_id == Candidate.id)
        .filter(
            Resume.id == resume_id,
            Resume.candidate_id == candidate_id,
            Candidate.organization_id == current_user.organization_id,
        )
        .first()
    )

    if resume is None:
        raise HTTPException(
            status_code=404,
            detail="Resume not found.",
        )

    # Resolve the path and prevent access outside private resume storage.
    storage_root = STORAGE_DIR.resolve()
    file_path = (storage_root / resume.file_path).resolve()

    if file_path.parent != storage_root or not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Resume file not found.",
        )

    # Extract text from the PDF.
    try:
        extracted_text = extract_resume_text(file_path)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="No readable text found. The PDF may be scanned or encrypted.",
        )
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Unable to extract text from this PDF.",
        )

    # Save extracted text to the existing database record.
    try:
        resume.extracted_text = extracted_text
        resume.status = "parsed"
        db.commit()
        db.refresh(resume)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to save extracted resume text.",
        )

    return {
        "message": "Resume parsed successfully.",
        "candidate_id": candidate_id,
        "resume_id": resume.id,
        "status": resume.status,
        "character_count": len(extracted_text),
        "preview": extracted_text,
    }


@router.get("/{candidate_id}/resumes/{resume_id}/profile")
def get_structured_resume_profile(
    candidate_id: int,
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "team_lead", "recruiter")
    ),
):
    resume = (
        db.query(Resume)
        .join(Candidate, Resume.candidate_id == Candidate.id)
        .filter(
            Resume.id == resume_id,
            Resume.candidate_id == candidate_id,
            Candidate.organization_id == current_user.organization_id,
        )
        .first()
    )

    if resume is None:
        raise HTTPException(
            status_code=404,
            detail="Resume not found.",
        )

    if not resume.extracted_text:
        raise HTTPException(
            status_code=409,
            detail="Parse this resume before requesting its profile.",
        )

    profile = structure_resume_text(resume.extracted_text)

    return {
        "candidate_id": candidate_id,
        "resume_id": resume.id,
        "status": resume.status,
        "profile": profile,
    }
