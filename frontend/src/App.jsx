
import { useEffect, useState } from "react";

import "./App.css";
import CandidatesPage from "./CandidatesPage.jsx";
import PipelinePage from "./PipelinePage.jsx";
import TeamPage from "./TeamPage.jsx";

const API_BASE_URL = "http://127.0.0.1:8000";


const initialJobs = [
  {
    id: 1,
    title: "Junior Python Developer",
    department: "Engineering",
    location: "Bengaluru",
    type: "Full-time",
    status: "Open",
    applicants: 24,
  },
  {
    id: 2,
    title: "Digital Marketing Executive",
    department: "Marketing",
    location: "Remote",
    type: "Full-time",
    status: "Open",
    applicants: 18,
  },
  {
    id: 3,
    title: "UI/UX Designer",
    department: "Design",
    location: "Bengaluru",
    type: "Full-time",
    status: "Draft",
    applicants: 0,
  },
];

function App() {
  const [page, setPage] = useState(
    () => sessionStorage.getItem("nexa_current_page") || "Dashboard"
  );
  useEffect(() => {
    sessionStorage.setItem("nexa_current_page", page);
  }, [page]);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const [jobs, setJobs] = useState(initialJobs);

  useEffect(() => {
    async function loadJobs() {
      const token = sessionStorage.getItem("nexa_access_token");

      if (!token) return;

      try {
        const response = await fetch(`${API_BASE_URL}/jobs/`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          console.error("Failed to load jobs:", response.status);
          return;
        }


        const data = await response.json();

        if (!Array.isArray(data)) {
          console.error("Expected a list of jobs, received:", data);
          return;
        }

        const savedJobs = data.map((job) => ({
          ...job,
          department: job.department || "General",
          type: job.type || "Full-time",
          location: job.location || "Not specified",
          status: job.status || "active",
          applicants: 0,
        }));

        setJobs(savedJobs);

      } catch (error) {
        console.error("Error loading jobs:", error);
      }
    }

    loadJobs();
  }, []);

  const [method, setMethod] = useState("manual");
  const [title, setTitle] = useState("");
  const [location, setLocation] = useState("");
  const [department, setDepartment] = useState("Engineering");
  const [jobType, setJobType] = useState("Full-time");
  const [description, setDescription] = useState("");
  const [notice, setNotice] = useState("");
  const [accessToken, setAccessToken] = useState(
    () => sessionStorage.getItem("nexa_access_token") || ""
  );
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [keepSignedIn, setKeepSignedIn] = useState(true);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const [recoveryEmail, setRecoveryEmail] = useState("");
  const [isSendingReset, setIsSendingReset] = useState(false);
  const [resetToken, setResetToken] = useState(
    () => new URLSearchParams(window.location.search).get("reset_token") || ""
  );
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isResettingPassword, setIsResettingPassword] = useState(false);



  async function handleLogin(event) {
    event.preventDefault();
    setNotice("");
    setIsLoggingIn(true);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: loginEmail.trim(),
          password: loginPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Login failed.");
      }

      sessionStorage.setItem("nexa_access_token", data.access_token);
      setAccessToken(data.access_token);
      setLoginPassword("");
      setNotice("Login successful. Welcome to Nexa Recruit!");
    } catch (error) {
      setNotice(error.message || "Unable to connect to the backend.");
    } finally {
      setIsLoggingIn(false);
    }
  }


  async function handleForgotPassword(event) {
    event.preventDefault();
    setNotice("");
    setIsSendingReset(true);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: recoveryEmail.trim() }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to request a reset link.");
      }

      setNotice(data.message || "If an account exists for that email, a reset link will be sent.");
    } catch (error) {
      setNotice(error.message || "Unable to connect to the backend.");
    } finally {
      setIsSendingReset(false);
    }
  }



  async function handleResetPassword(event) {
    event.preventDefault();
    setNotice("");

    if (newPassword !== confirmPassword) {
      setNotice("Your passwords do not match.");
      return;
    }

    if (newPassword.length < 12) {
      setNotice("Your new password must be at least 12 characters.");
      return;
    }

    setIsResettingPassword(true);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: resetToken,
          new_password: newPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to reset your password.");
      }

      setNotice("Password reset successfully. You can now sign in.");
      setNewPassword("");
      setConfirmPassword("");
      setResetToken("");
      window.history.replaceState({}, document.title, window.location.pathname);
      setPage("Login");
    } catch (error) {
      setNotice(error.message || "Unable to connect to the backend.");
    } finally {
      setIsResettingPassword(false);
    }
  }


  function openCreateJob() {
    setNotice("");
    setPage("Create Job");
  }


  async function saveJob(event) {
    event.preventDefault();
    setNotice("");

    if (!title.trim() || !description.trim()) {
      setNotice("Please enter a job title and job description.");
      return;
    }

    if (!accessToken) {
      setNotice("Please log in before saving a job.");
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/jobs/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
          location: location.trim() || null,
          status: "active",
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || "Unable to save the job.");
      }

      const newJob = {
        ...data,
        department,
        type: jobType,
        applicants: 0,
      };

      setJobs((current) => [
        newJob,
        ...current.filter((job) => job.id !== newJob.id),
      ]);

      setNotice("Job saved successfully to Nexa Recruit!");
      setTitle("");
      setLocation("");
      setDescription("");
      setPage("Jobs");
    } catch (error) {
      setNotice(error.message || "Unable to connect to the backend.");
    }
  }




  async function generateDraft() {
    if (!title.trim()) {
      setNotice("Enter the job title first.");
      return;
    }

    setIsGenerating(true);
    setNotice("");

    try {
      // Temporary development token: replace this with the
      // real login session integration in the next step.
      const token = sessionStorage.getItem("nexa_access_token");

      if (!token) {
        setNotice("Please log in before generating a job description.");
        setIsGenerating(false);
        return;
      }

      const response = await fetch(
        "http://127.0.0.1:8000/ai/generate-job-description",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            title: title.trim(),
            skills: [],
            experience: "Entry level",
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to generate the draft.");
      }

      setDescription(data.description);
      setNotice(
        data.mode === "mock"
          ? "Mock draft received from the Nexa Recruit backend. Live AI is not enabled."
          : "Job description generated successfully."
      );
    } catch (error) {
      setNotice(error.message || "Unable to connect to the backend.");
    } finally {
      setIsGenerating(false);
    }
  }

  const navigation = [
    { name: "Dashboard", icon: "◫" },
    { name: "Jobs", icon: "▤" },
    { name: "Candidates", icon: "♙" },
    { name: "Pipeline", icon: "⇄" },
    { name: "Team", icon: "👥" },
    { name: "Interviews", icon: "▦" },
    { name: "Analytics", icon: "↗" },
  ];

  const totalApplicants = jobs.reduce(
    (total, job) => total + job.applicants,
    0
  );

  return (


    !accessToken && resetToken ? (
      <main className="login-screen">
        <section className="login-card">
          <div className="brand-emblem">N</div>
          <p className="brand-eyebrow">ACCOUNT RECOVERY</p>
          <h1>Choose a new password</h1>
          <p>Enter and confirm your new password below.</p>

          <form onSubmit={handleResetPassword}>
            <label htmlFor="new-password">New password</label>
            <input
              id="new-password"
              type="password"
              autoComplete="new-password"
              minLength={12}
              maxLength={128}
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              placeholder="At least 12 characters"
              required
            />

            <label htmlFor="confirm-password">Confirm new password</label>
            <input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              minLength={12}
              maxLength={128}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="Enter your new password again"
              required
            />

            <button
              type="submit"
              className="login-submit"
              disabled={isResettingPassword}
            >
              {isResettingPassword ? "Updating password..." : "Reset password"}
            </button>
          </form>

          {notice && <p role="status">{notice}</p>}

          <button
            type="button"
            className="forgot-password-link"
            onClick={() => {
              setResetToken("");
              window.history.replaceState({}, document.title, window.location.pathname);
              setNotice("");
              setPage("Login");
            }}
          >
            Back to sign in
          </button>
        </section>
      </main>
    ) : !accessToken && page !== "Forgot Password" ? (

      <main className="login-screen">
        <section className="login-brand">
          <div className="login-wordmark">
            <span className="login-wordmark-mark">N</span>
            <span className="login-wordmark-type"><strong>NEXA</strong><small>RECRUIT</small></span>
          </div>

          <div className="brand-content">
            <div className="brand-emblem">N</div>

            <p className="brand-eyebrow">THE FUTURE OF HIRING</p>

            <h1>
              Hire with clarity.
              <span>Build with confidence.</span>
            </h1>

            <div className="brand-divider" />

            <p className="brand-description">
              Your intelligent recruitment workspace.
              Find exceptional talent and build exceptional teams.
            </p>

            <div className="brand-benefits">
              <div>
                <span>01</span>
                <strong>SMARTER HIRING</strong>
              </div>
              <div>
                <span>02</span>
                <strong>BETTER TALENT</strong>
              </div>
              <div>
                <span>03</span>
                <strong>GREATER IMPACT</strong>
              </div>
            </div>
          </div>

          <p className="brand-footer">INTELLIGENCE. PEOPLE. POSSIBILITY.</p>
        </section>

        <section className="login-main">
          <form className="login-card" onSubmit={handleLogin}>
            <div className="login-card-topline">
              <div className="login-card-emblem">N</div>
              <p className="login-contact">Don’t have an account? <button type="button" onClick={() => setNotice("Please contact your Nexa Recruit workspace administrator to create an account.")}>Contact Admin</button></p>
            </div>

            <p className="login-eyebrow">WELCOME BACK</p>
            <h2>Sign in to Nexa Recruit</h2>
            <p className="login-subtitle">
              Access your recruitment workspace and continue building exceptional teams.
            </p>

            {notice && (
              <p className="login-notice" role="status">
                {notice}
              </p>
            )}

            <div className="login-field">
              <label htmlFor="login-email">WORK EMAIL</label>
              <input
                id="login-email"
                type="email"
                placeholder="you@company.com"
                autoComplete="username"
                value={loginEmail}
                onChange={(event) => setLoginEmail(event.target.value)}
                required
              />
            </div>

            <div className="login-field">
              <label htmlFor="login-password">PASSWORD</label>
              <input
                id="login-password"
                type={showLoginPassword ? "text" : "password"}
                placeholder="Enter your password"
                autoComplete="current-password"
                value={loginPassword}
                onChange={(event) => setLoginPassword(event.target.value)}
                required
              />
            </div>

            <div className="login-options-row">
              <label className="remember-option">
                <input type="checkbox" checked={keepSignedIn} onChange={(event) => setKeepSignedIn(event.target.checked)} />
                <span>Keep me signed in</span>
              </label>
              <div className="forgot-password-row">
                <button
                  type="button"
                  className="forgot-password-link"
                  onClick={() => {
                    setNotice("");
                    setPage("Forgot Password");
                  }}
                >
                  Forgot password?
                </button>
              </div>
            </div>

            <button
              className="login-submit"
              type="submit"
              disabled={isLoggingIn}
            >
              <span>
                {isLoggingIn ? "Signing in..." : "Sign in to Nexa"}
              </span>
              {!isLoggingIn && <span aria-hidden="true">→</span>}
            </button>

            <div className="login-security">
              <span className="security-shield" aria-hidden="true">✓</span>
              <div><strong>Secure access for your hiring team</strong><small>Your data is protected with enterprise-grade security.</small></div>
            </div>
          </form>

          <p className="login-bottom-brand">
            NEXA <strong>RECRUIT</strong>
          </p>
        </section>
      </main>
    ) : page === "Forgot Password" ? (
      <main className="login-screen">
        <section className="login-card">
          <div className="brand-emblem">N</div>
          <p className="brand-eyebrow">ACCOUNT RECOVERY</p>
          <h1>Forgot password?</h1>
          <p>Enter your work email to reset your password.</p>


          <form onSubmit={handleForgotPassword}>
            <label htmlFor="recovery-email">Work email</label>

            <input
              id="recovery-email"
              type="email"
              placeholder="you@company.com"
              value={recoveryEmail}
              onChange={(event) => setRecoveryEmail(event.target.value)}
              required
            />

            <button
              type="submit"
              className="login-submit"
              disabled={isSendingReset}
            >
              {isSendingReset ? "Sending..." : "Send reset link"}
            </button>

          </form>

          <button
            type="button"
            className="forgot-password-link"
            onClick={() => {
              setNotice("");
              setPage("Login");
            }}
          >
            Back to sign in
          </button>

          {notice && <p role="status">{notice}</p>}
        </section>
      </main>
    ) : (

      <div className="app-shell">
        <aside className="sidebar">
          <button className="brand" onClick={() => setPage("Dashboard")}>
            <span className="brand-mark">N</span>
            <span>
              <strong>NEXA</strong>
              <small>RECRUIT</small>
            </span>
          </button>

          <div className="workspace-label">WORKSPACE</div>
          <div className="workspace-card">
            <div className="workspace-avatar">N</div>
            <div>
              <strong>Nexa Workspace</strong>
              <small>Recruitment team</small>
            </div>
            <span className="workspace-dots">•••</span>
          </div>

          <div className="nav-label">RECRUITMENT</div>
          <nav className="navigation">
            {navigation.map((item) => (
              <button
                key={item.name}
                className={`nav-item ${page === item.name ? "active" : ""}`}
                onClick={() => {
                  setNotice("");
                  setPage(item.name);
                }}
              >
                <span className="nav-icon">{item.icon}</span>
                {item.name}
                {item.name === "Jobs" && (
                  <span className="nav-count">{jobs.length}</span>
                )}
              </button>
            ))}
          </nav>

          <div className="sidebar-bottom">
            <div className="credits-card">
              <span className="credits-spark">✧</span>
              <strong>AI workspace</strong>
              <p>AI-assisted hiring tools are coming next.</p>
              <div className="credits-progress">
                <span />
              </div>
              <small>Preview mode</small>
            </div>
            <button className="nav-item settings-item" onClick={() => setNotice("Workspace settings will be added in a later step.")}>
              <span className="nav-icon">⚙</span>
              Settings
            </button>
            <div className="profile">
              <div className="profile-avatar">R</div>
              <div>
                <strong>Recruiter</strong>
                <small>Workspace preview</small>
              </div>
              <span className="workspace-dots">•••</span>
            </div>
          </div>
        </aside>

        <main className="main-content">
          <header className="topbar">
            <div className="breadcrumb">
              Workspace <span>/</span> <strong>{page}</strong>
            </div>
            <div className="topbar-actions">
              <span className="preview-badge">
                <span /> Preview environment
              </span>
              <button
                className="notification-button"
                aria-label="Notifications"
                onClick={() => setNotice("You are all caught up.")}
              >
                ♧
              </button>

              <div className="profile-menu-container">
                <button
                  type="button"
                  className="topbar-avatar"
                  aria-label="Open profile menu"
                  aria-expanded={profileMenuOpen}
                  onClick={() => setProfileMenuOpen((open) => !open)}
                >
                  R
                </button>

                {profileMenuOpen && (
                  <div className="profile-dropdown">
                    <div className="profile-dropdown-heading">
                      <strong>Recruiter</strong>
                      <span>Nexa Recruit Workspace</span>
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        setProfileMenuOpen(false);
                        setPage("Settings");
                      }}
                    >
                      Account settings
                    </button>

                    <div className="profile-dropdown-divider" />

                    <button
                      type="button"
                      className="profile-logout"
                      onClick={() => {
                        sessionStorage.removeItem("nexa_access_token");
                        setProfileMenuOpen(false);
                        setAccessToken("");
                        setNotice("You have been signed out successfully.");
                      }}
                    >
                      Sign out
                    </button>
                  </div>
                )}
              </div>

            </div>
          </header>

          <div className="page-container">
            {notice && (
              <div className="notice" role="status">
                <span>{notice}</span>
                <button onClick={() => setNotice("")} aria-label="Dismiss notice">
                  ×
                </button>
              </div>
            )}

            {page === "Dashboard" && (
              <>
                <section className="welcome-row">
                  <div>
                    <div className="eyebrow">
                      <span className="gold-line" /> YOUR HIRING WORKSPACE
                    </div>
                    <h1>Good morning, Recruiter.</h1>
                    <p className="page-subtitle">
                      Great people build great companies. Let's find yours.
                    </p>
                  </div>
                  <button className="primary-button" onClick={openCreateJob}>
                    <span>＋</span> Create a job
                  </button>
                </section>

                <section className="hero-banner">
                  <div className="hero-copy">
                    <span className="hero-kicker">THE SMARTER WAY TO HIRE</span>
                    <h2>Every great hire<br />starts with a great role.</h2>
                    <p>
                      Create a clear job description, organize your openings,
                      and build a better hiring process.
                    </p>
                    <button className="hero-button" onClick={openCreateJob}>
                      Create your first role <span>→</span>
                    </button>
                  </div>
                  <div className="hero-art" aria-hidden="true">
                    <div className="orbit orbit-one" />
                    <div className="orbit orbit-two" />
                    <div className="art-center">
                      <span>✧</span>
                      <small>N</small>
                    </div>
                    <div className="art-card art-card-top">
                      <span className="art-dot" />
                      Role clarity
                      <strong>01</strong>
                    </div>
                    <div className="art-card art-card-bottom">
                      <span className="art-check">✓</span>
                      Better hiring
                      <strong>02</strong>
                    </div>
                  </div>
                  <div className="hero-watermark">N</div>
                </section>

                <section className="metrics-grid">
                  <div className="metric-card">
                    <div className="metric-top">
                      <span>OPEN POSITIONS</span>
                      <span className="metric-icon gold-icon">▤</span>
                    </div>
                    <strong className="metric-number">
                      {jobs.filter((job) => job.status === "Open").length}
                    </strong>
                    <p>Roles currently open</p>
                    <span className="metric-foot">Across your workspace</span>
                  </div>
                  <div className="metric-card">
                    <div className="metric-top">
                      <span>TOTAL APPLICANTS</span>
                      <span className="metric-icon blue-icon">♙</span>
                    </div>
                    <strong className="metric-number">{totalApplicants}</strong>
                    <p>Across sample job data</p>
                    <span className="metric-foot">Demo figures for preview</span>
                  </div>
                  <div className="metric-card">
                    <div className="metric-top">
                      <span>INTERVIEWS</span>
                      <span className="metric-icon violet-icon">▦</span>
                    </div>
                    <strong className="metric-number">—</strong>
                    <p>Interview tracking</p>
                    <span className="metric-foot">Not connected yet</span>
                  </div>
                  <div className="metric-card">
                    <div className="metric-top">
                      <span>DRAFT JOBS</span>
                      <span className="metric-icon green-icon">✎</span>
                    </div>
                    <strong className="metric-number">
                      {jobs.filter((job) => job.status === "Draft").length}
                    </strong>
                    <p>Ready for review</p>
                    <span className="metric-foot">Finish before publishing</span>
                  </div>
                </section>

                <section className="content-grid">
                  <div className="panel jobs-panel">
                    <div className="panel-heading">
                      <div>
                        <h3>Recent job openings</h3>
                        <p>Your latest roles at a glance</p>
                      </div>
                      <button className="text-button" onClick={() => setPage("Jobs")}>
                        View all jobs <span>→</span>
                      </button>
                    </div>

                    <div className="job-table">
                      <div className="table-head">
                        <span>JOB TITLE</span>
                        <span>LOCATION</span>
                        <span>APPLICANTS</span>
                        <span>STATUS</span>
                      </div>
                      {jobs.slice(0, 4).map((job) => (
                        <div className="table-row" key={job.id}>
                          <div className="job-title-cell">
                            <span className="job-avatar">
                              {job.title.charAt(0).toUpperCase()}
                            </span>
                            <div>
                              <strong>{job.title}</strong>
                              <small>{job.department} · {job.type}</small>
                            </div>
                          </div>
                          <span className="table-location">{job.location}</span>
                          <strong className="applicant-count">{job.applicants}</strong>
                          <span className={`status-pill ${job.status.toLowerCase()}`}>
                            <i /> {job.status}
                          </span>
                        </div>
                      ))}
                    </div>
                    <button className="mobile-view-all" onClick={() => setPage("Jobs")}>
                      View all jobs →
                    </button>
                  </div>

                  <div className="panel quick-panel">
                    <div className="panel-heading">
                      <div>
                        <h3>Quick actions</h3>
                        <p>Make your next move</p>
                      </div>
                    </div>
                    <button className="quick-action" onClick={openCreateJob}>
                      <span className="quick-icon gold-icon">＋</span>
                      <span>
                        <strong>Create a new job</strong>
                        <small>Start with a job title and details</small>
                      </span>
                      <b>→</b>
                    </button>
                    <button
                      className="quick-action"
                      onClick={() => {
                        setMethod("ai");
                        openCreateJob();
                      }}
                    >
                      <span className="quick-icon violet-icon">✧</span>
                      <span>
                        <strong>Build a job description</strong>
                        <small>Prepare a draft with guided assistance</small>
                      </span>
                      <b>→</b>
                    </button>
                    <button
                      className="quick-action"
                      onClick={() => setNotice("Candidate management will be connected in a later step.")}
                    >
                      <span className="quick-icon blue-icon">♙</span>
                      <span>
                        <strong>Explore candidates</strong>
                        <small>Candidate tools are coming next</small>
                      </span>
                      <b>→</b>
                    </button>
                    <div className="helper-note">
                      <span>✦</span>
                      <p><strong>A little guidance</strong><br />A clear JD helps candidates understand the role before applying.</p>
                    </div>
                  </div>
                </section>
              </>
            )}

            {page === "Jobs" && (
              <section>
                <div className="welcome-row">
                  <div>
                    <div className="eyebrow">
                      <span className="gold-line" /> RECRUITMENT
                    </div>
                    <h1>Jobs & openings</h1>
                    <p className="page-subtitle">
                      Organize your roles and keep every opening moving.
                    </p>
                  </div>
                  <button className="primary-button" onClick={openCreateJob}>
                    ＋ Create a job
                  </button>
                </div>

                <div className="panel jobs-list-panel">
                  <div className="panel-heading">
                    <div>
                      <h3>All jobs <span className="subtle-count">{jobs.length}</span></h3>
                      <p>Sample jobs for the frontend preview</p>
                    </div>
                  </div>
                  {jobs.map((job) => (
                    <div className="job-list-row" key={job.id}>
                      <span className="job-avatar">{job.title.charAt(0)}</span>
                      <div className="job-list-main">
                        <strong>{job.title}</strong>
                        <small>{job.department} · {job.location} · {job.type}</small>
                      </div>
                      <span className="job-list-applicants">
                        <strong>{job.applicants}</strong>
                        <small>Applicants</small>
                      </span>
                      <span className={`status-pill ${job.status.toLowerCase()}`}>
                        <i /> {job.status}
                      </span>
                    </div>
                  ))}
                  <p className="preview-disclaimer">
                    These are sample preview jobs. Your database has not been changed.
                  </p>
                </div>
              </section>
            )}

            {page === "Create Job" && (
              <section>
                <div className="welcome-row">
                  <div>
                    <div className="eyebrow">
                      <span className="gold-line" /> JOB WORKSPACE
                    </div>
                    <h1>Create a new job</h1>
                    <p className="page-subtitle">
                      Start with the basics. You can review everything before publishing.
                    </p>
                  </div>
                  <button className="secondary-button" onClick={() => setPage("Jobs")}>
                    ← Back to jobs
                  </button>
                </div>

                <div className="builder-layout">
                  <form className="panel builder-form" onSubmit={saveJob}>
                    <div className="form-section-heading">
                      <span className="step-number">01</span>
                      <div>
                        <h3>Role details</h3>
                        <p>Give your opening a clear name and location.</p>
                      </div>
                    </div>

                    <label htmlFor="job-title">Job title <span>*</span></label>
                    <input
                      id="job-title"
                      value={title}
                      onChange={(event) => setTitle(event.target.value)}
                      placeholder="e.g. Senior Software Engineer"
                      required
                    />

                    <div className="form-two-columns">
                      <div>
                        <label htmlFor="department">Department</label>
                        <select
                          id="department"
                          value={department}
                          onChange={(event) => setDepartment(event.target.value)}
                        >
                          <option>Engineering</option>
                          <option>Marketing</option>
                          <option>Sales</option>
                          <option>Design</option>
                          <option>Human Resources</option>
                          <option>Finance</option>
                          <option>Operations</option>
                        </select>
                      </div>
                      <div>
                        <label htmlFor="location">Location</label>
                        <input
                          id="location"
                          value={location}
                          onChange={(event) => setLocation(event.target.value)}
                          placeholder="e.g. Bengaluru or Remote"
                        />
                      </div>
                    </div>

                    <label htmlFor="job-type">Employment type</label>
                    <select
                      id="job-type"
                      value={jobType}
                      onChange={(event) => setJobType(event.target.value)}
                    >
                      <option>Full-time</option>
                      <option>Part-time</option>
                      <option>Contract</option>
                      <option>Internship</option>
                      <option>Temporary</option>
                    </select>

                    <div className="form-section-heading jd-heading">
                      <span className="step-number">02</span>
                      <div>
                        <h3>Job description</h3>
                        <p>Choose how you want to prepare your JD.</p>
                      </div>
                    </div>

                    <div className="method-tabs">
                      <button
                        type="button"
                        className={method === "manual" ? "method-tab selected" : "method-tab"}
                        onClick={() => {
                          setMethod("manual");
                          setNotice("");
                        }}
                      >
                        <span>✎</span> Write or paste
                      </button>
                      <button
                        type="button"
                        className={method === "ai" ? "method-tab selected" : "method-tab"}
                        onClick={() => {
                          setMethod("ai");
                          setNotice("");
                        }}
                      >
                        <span>✧</span> AI-assisted draft
                      </button>
                    </div>

                    {method === "ai" && (
                      <div className="ai-helper">
                        <span className="ai-helper-icon">✧</span>
                        <div>
                          <strong>JD drafting assistant</strong>
                          <p>
                            Prepare an editable starter template from your role details.
                            Live AI generation will be connected later.
                          </p>
                          <button
                            className="ai-generate-button"
                            type="button"
                            onClick={generateDraft}
                            disabled={isGenerating}
                          >
                            {isGenerating ? "Generating..." : "✧ Generate job description"}
                          </button>
                        </div>
                      </div>
                    )}

                    <label htmlFor="job-description">
                      {method === "manual" ? "Paste or write your JD" : "Review and edit your draft"}
                      <span> *</span>
                    </label>
                    <textarea
                      id="job-description"
                      value={description}
                      onChange={(event) => setDescription(event.target.value)}
                      placeholder={
                        method === "manual"
                          ? "Paste your existing job description here, or write responsibilities, skills and qualifications..."
                          : "Click 'Prepare a draft' to create an editable starter template, then customize it here..."
                      }
                      rows={11}
                      required
                    />
                    <div className="character-hint">
                      <span>Tip: include responsibilities, essential skills and experience.</span>
                      <span>{description.length} characters</span>
                    </div>

                    <div className="form-footer">
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => setPage("Jobs")}
                      >
                        Cancel
                      </button>
                      <button type="submit" className="primary-button">
                        Save as draft <span>→</span>
                      </button>
                    </div>
                  </form>

                  <aside className="builder-aside">
                    <div className="panel guidance-panel">
                      <span className="guidance-icon">✧</span>
                      <h3>Make your JD stand out</h3>
                      <p>A clear description helps candidates decide whether the role is right for them.</p>
                      <div className="guidance-item">
                        <span>✓</span>
                        <div><strong>Be specific</strong><small>Explain what the person will do.</small></div>
                      </div>
                      <div className="guidance-item">
                        <span>✓</span>
                        <div><strong>Separate must-haves</strong><small>Distinguish essential and preferred skills.</small></div>
                      </div>
                      <div className="guidance-item">
                        <span>✓</span>
                        <div><strong>Set expectations</strong><small>Include location and employment type.</small></div>
                      </div>
                    </div>

                    <div className="panel preview-panel">
                      <div className="preview-panel-heading">
                        <span>LIVE PREVIEW</span>
                        <span className="preview-dot" />
                      </div>
                      <h3>{title || "Your job title"}</h3>
                      <p>{department} · {location || "Location not set"}</p>
                      <span className="job-type-tag">{jobType}</span>
                      <div className="preview-divider" />
                      <strong>Job description</strong>
                      <p className="description-preview">
                        {description || "Your job description will appear here as you write."}
                      </p>
                    </div>
                  </aside>
                </div>
              </section>
            )}

            {page === "Candidates" && (
              <CandidatesPage accessToken={accessToken} />
            )}

            {page === "Pipeline" && (
              <PipelinePage accessToken={accessToken} />
            )}

            {page === "Team" && (
              <TeamPage accessToken={accessToken} />
            )}

            {page !== "Dashboard" &&
              page !== "Jobs" &&
              page !== "Create Job" &&
              page !== "Candidates" &&
              page !== "Pipeline" &&
              page !== "Team" && (
                <section>
                  <div className="eyebrow">
                    <span className="gold-line" /> YOUR WORKSPACE
                  </div>
                  <h1>{page}</h1>
                  <p className="page-subtitle">
                    This section is planned for a future development milestone.
                  </p>
                  <div className="panel placeholder-panel">
                    <span className="placeholder-icon">✧</span>
                    <h3>{page} tools are coming next</h3>
                    <p>
                      We're building the recruitment foundation one reliable feature at a time.
                    </p>
                    <button
                      className="primary-button"
                      onClick={() => setPage("Dashboard")}
                    >
                      Return to dashboard
                    </button>
                  </div>
                </section>
              )}
          </div>
        </main>
      </div>
    )
  );

}

export default App;
