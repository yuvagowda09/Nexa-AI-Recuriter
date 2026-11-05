from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=1)
    location: Optional[str] = Field(default=None, max_length=255)
    status: str = Field(default="active", max_length=50)


class JobResponse(BaseModel):
    id: int
    organization_id: int
    title: str
    description: str
    location: Optional[str] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=255)
    organization_type: str = Field(pattern="^(agency|internal_hr)$")
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class JobDescriptionRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    skills: list[str] = Field(default_factory=list, max_length=20)
    experience: str = Field(default="Entry level", max_length=100)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=2048)
    new_password: str = Field(min_length=12, max_length=128)


class TeamMemberCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: str = Field(pattern="^(team_lead|recruiter)$")


class TeamMemberRoleUpdate(BaseModel):
    role: str = Field(pattern="^(team_lead|recruiter)$")


class TeamInvitationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    role: str = Field(pattern="^(team_lead|recruiter)$")


class TeamInvitationAccept(BaseModel):
    token: str = Field(min_length=1, max_length=2048)
    new_password: str = Field(min_length=12, max_length=128)


class CandidateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    location: Optional[str] = Field(default=None, max_length=255)


class CandidateResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ResumeUploadResponse(BaseModel):
    id: int
    candidate_id: int
    status: str

    model_config = ConfigDict(from_attributes=True)
