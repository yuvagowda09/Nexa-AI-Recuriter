# Nexa Recruit — AI-Powered Recruitment Management SaaS

Nexa Recruit is a premium, multi-tenant recruitment management platform designed for recruitment agencies, corporate HR departments, and internal talent acquisition teams. It streamlines the full hiring lifecycle from job creation and candidate sourcing to AI-assisted resume parsing, pipeline tracking, and team collaboration.

---

## 🏛 Architecture & Tech Stack

This repository is structured as a full-stack monorepo:

* **Backend:**
  * **Framework:** Python 3.11, FastAPI
  * **Database:** PostgreSQL, SQLAlchemy 2.0 (declarative models)
  * **Migrations:** Alembic
  * **Authentication:** PyJWT, OAuth2 Bearer, Argon2 password hashing (`pwdlib`)
  * **Validation:** Pydantic v2
  * **Testing:** Pytest (56 automated tests passing)

* **Frontend:**
  * **Framework:** React 19, Vite 8
  * **Styling:** Custom Vanilla CSS (Nexa Navy, Ivory & Champagne Gold aesthetic)
  * **Tooling:** Oxlint, Rolldown / Vite bundler

* **AI & Document Intelligence:**
  * Rule-based resume text extraction (`pdfplumber`) & structuring
  * AI Job Description generation (OpenAI integration)
  * Evidence-based match scoring & SkillProof assessments

---

## 📁 Repository Structure

```
Nexa-AI-Recruiter/
├── backend/                  # FastAPI Application
│   ├── migrations/           # Alembic database migrations
│   ├── routes/               # API route modules
│   │   ├── auth.py           # Registration, login, password reset
│   │   ├── organization.py   # Team management, member roles, invitations
│   │   ├── jobs.py           # Job creation & organization-scoped listings
│   │   ├── candidates.py     # Candidate management, resume uploads & parsing
│   │   ├── pipeline.py       # Recruitment workflow stage transitions
│   │   └── ai.py             # AI job description generation
│   ├── tests/                # Automated pytest suite (56 tests)
│   ├── models.py             # SQLAlchemy database models
│   ├── schemas.py            # Pydantic validation schemas
│   ├── security.py           # JWT authentication & role-based access control
│   ├── team_invitations.py   # Cryptographic team invitation tokens & emails
│   ├── password_reset.py     # Secure password reset tokens & emails
│   ├── resume_storage.py     # Secure PDF storage with magic-byte verification
│   ├── main.py               # FastAPI application entry point
│   └── requirements.txt      # Python dependencies
│
├── frontend/                 # React 19 + Vite SPA
│   ├── src/
│   │   ├── App.jsx           # Application shell & routing
│   │   ├── TeamPage.jsx      # Team member management & invitations UI
│   │   ├── CandidatesPage.jsx# Candidate profiles, resume upload & parsing UI
│   │   ├── PipelinePage.jsx  # Stage pipeline management UI
│   │   └── ...
│   ├── package.json          # Node dependencies
│   └── vite.config.js        # Vite configuration
│
├── docs/                     # Project documentation & progress logs
│   └── PROJECT_PROGRESS.md   # Milestone tracking
├── .gitignore                # Monorepo ignore rules (protects .env, venv, resumes)
└── README.md
```

---

## 🚀 Getting Started

### 1. Prerequisites
* Python 3.11+
* Node.js 18+ & npm
* PostgreSQL 14+

### 2. Backend Setup
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Configure your environment in backend/.env:
# DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/nexa_recruit
# JWT_SECRET_KEY=your_secure_secret_key

# Run database migrations
alembic upgrade head

# Start development server
python -m uvicorn main:app --reload
```
API Documentation will be accessible at: `http://127.0.0.1:8000/docs`

### 3. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```
Application will be accessible at: `http://localhost:5173`

### 4. Running Tests
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest
```

---

## 🛣 Development Roadmap

- [x] **Phase 1: Foundation & Security** (Authentication, PostgreSQL, multi-tenancy, jobs, pipeline, resume security)
- [x] **Phase 2.1: Team Management** (Team member listing, role promotion/downgrade, status toggle, email invitations)
- [ ] **Phase 2.2: Client Company Management** (Multi-client management for recruitment agencies)
- [ ] **Phase 2.3: Bulk Job Import** (Excel/CSV batch processing & column mapping)
- [ ] **Phase 3: Candidate Portal** (Self-service candidate applications & tracking)
- [ ] **Phase 4: Candidate Database & Resume Intelligence**
- [ ] **Phase 5: AI Recruitment Intelligence** (Live OpenAI integration)
- [ ] **Phase 6: Hiring Workflow, Nexa Connect & Analytics**
- [ ] **Phase 7: Monetization, Billing & Production Launch**

---

## 🔒 Security Principles
* **Multi-Tenancy:** Strict organizational boundary isolation. Organization context is derived strictly from backend JWT claims.
* **Secret Protection:** Environment configurations and API keys are strictly excluded from version control.
* **Document Security:** Resumes are validated by file size (≤ 5MB) and PDF magic-byte signatures (`%PDF-`), stored with randomized hashes, and protected against path traversal.
