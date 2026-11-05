
import { useEffect, useState } from "react";
import "./CandidatesPage.css";

const API_BASE_URL = "http://127.0.0.1:8000";

export default function CandidatesPage({ accessToken }) {
  const [candidates, setCandidates] = useState([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [location, setLocation] = useState("");
  const [selectedFiles, setSelectedFiles] = useState({});
  const [resumesByCandidate, setResumesByCandidate] = useState({});
  const [parsedResumes, setParsedResumes] = useState({});
  const [parsingResume, setParsingResume] = useState(null);
  const [profileByResume, setProfileByResume] = useState({});
  const [loadingProfile, setLoadingProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [busyCandidate, setBusyCandidate] = useState(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadCandidates() {
      setLoading(true);
      setError("");

      try {
        const response = await fetch(`${API_BASE_URL}/candidates/`, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Unable to load candidates.");
        }

        if (!cancelled) {
          setCandidates(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Unable to connect to the backend.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadCandidates();

    return () => {
      cancelled = true;
    };
  }, [accessToken]);



  useEffect(() => {
    if (!accessToken || candidates.length === 0) {
      setResumesByCandidate({});
      return;
    }

    let cancelled = false;

    async function loadCandidateResumes() {
      const results = await Promise.all(
        candidates.map(async (candidate) => {
          try {
            const response = await fetch(
              `${API_BASE_URL}/candidates/${candidate.id}/resumes`,
              {
                headers: {
                  Authorization: `Bearer ${accessToken}`,
                },
              }
            );

            if (!response.ok) {
              return [candidate.id, []];
            }

            const data = await response.json();
            return [candidate.id, Array.isArray(data) ? data : []];
          } catch {
            return [candidate.id, []];
          }
        })
      );


      if (!cancelled) {
        const resumeMap = Object.fromEntries(results);

        setResumesByCandidate(resumeMap);

        const savedParsedResumes = {};

        Object.values(resumeMap).flat().forEach((resume) => {
          if (
            resume.status === "parsed" &&
            resume.preview
          ) {
            savedParsedResumes[resume.id] = {
              status: resume.status,
              character_count: resume.character_count,
              preview: resume.preview,
            };
          }
        });

        setParsedResumes(savedParsedResumes);
      }
    } // closes loadCandidateResumes()

    loadCandidateResumes();
  }, [candidates, accessToken]);

  async function handleCreateCandidate(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");

    try {
      const response = await fetch(`${API_BASE_URL}/candidates/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim() || null,
          phone: phone.trim() || null,
          location: location.trim() || null,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to create candidate.");
      }

      setCandidates((current) => [data, ...current]);
      setName("");
      setEmail("");
      setPhone("");
      setLocation("");
      setNotice("Candidate added successfully.");
    } catch (err) {
      setError(err.message || "Unable to connect to the backend.");
    } finally {
      setSaving(false);
    }
  }

  async function handleUpload(candidateId) {
    const file = selectedFiles[candidateId];

    if (!file) {
      setError("Choose a PDF resume before uploading.");
      return;
    }

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please select a PDF file.");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setError("The resume must be 5 MB or smaller.");
      return;
    }

    setBusyCandidate(candidateId);
    setError("");
    setNotice("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `${API_BASE_URL}/candidates/${candidateId}/resumes`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Resume upload failed.");
      }

      setResumesByCandidate((current) => ({
        ...current,
        [candidateId]: [
          data,
          ...(current[candidateId] || []).filter(
            (resume) => resume.id !== data.id
          ),
        ],
      }));

      setSelectedFiles((current) => ({
        ...current,
        [candidateId]: null,
      }));

      setNotice(`Resume uploaded for ${candidates.find((item) => item.id === candidateId)?.name || "candidate"}.`);
    } catch (err) {
      setError(err.message || "Unable to connect to the backend.");
    } finally {
      setBusyCandidate(null);
    }
  }

  async function handleDownload(candidateId, resumeId) {
    setBusyCandidate(candidateId);
    setError("");
    setNotice("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/candidates/${candidateId}/resumes/${resumeId}/download`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );

      if (!response.ok) {
        let message = "Unable to download the resume.";

        try {
          const data = await response.json();
          message = data.detail || message;
        } catch {
          // Keep the generic download error.
        }

        throw new Error(message);
      }

      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = objectUrl;
      link.download = `resume-${resumeId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(objectUrl);

      setNotice("Resume download started.");
    } catch (err) {
      setError(err.message || "Unable to download the resume.");
    } finally {
      setBusyCandidate(null);
    }
  }



  async function handleParseResume(candidateId, resumeId) {
    const parseKey = `${candidateId}:${resumeId}`;

    setParsingResume(parseKey);
    setError("");
    setNotice("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/candidates/${candidateId}/resumes/${resumeId}/parse`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to parse resume.");
      }

      setParsedResumes((current) => ({
        ...current,
        [resumeId]: data,
      }));

      setResumesByCandidate((current) => ({
        ...current,
        [candidateId]: (current[candidateId] || []).map((resume) =>
          resume.id === resumeId
            ? { ...resume, status: data.status }
            : resume
        ),
      }));

      setNotice(`Resume #${resumeId} parsed successfully.`);
    } catch (err) {
      setError(err.message || "Unable to parse resume.");
    } finally {
      setParsingResume(null);
    }
  }

  async function handleViewProfile(candidateId, resumeId) {
    setLoadingProfile(resumeId);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/candidates/${candidateId}/resumes/${resumeId}/profile`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to load resume profile.");
      }

      setProfileByResume((current) => ({
        ...current,
        [resumeId]: data.profile,
      }));
    } catch (err) {
      setError(err.message || "Unable to load resume profile.");
    } finally {
      setLoadingProfile(null);
    }
  }


  return (
    <section className="candidate-page">
      <div className="candidate-heading">
        <div>
          <div className="eyebrow">
            <span className="gold-line" /> TALENT WORKSPACE
          </div>
          <h1>Candidates</h1>
          <p className="page-subtitle">
            Manage candidate profiles and their private resumes.
          </p>
        </div>

        <div className="candidate-total">
          <span>YOUR CANDIDATES</span>
          <strong>{candidates.length}</strong>
        </div>
      </div>

      {notice && (
        <div className="candidate-message success" role="status">
          {notice}
        </div>
      )}

      {error && (
        <div className="candidate-message error" role="alert">
          {error}
        </div>
      )}

      <div className="candidate-layout">
        <form
          className="panel candidate-form"
          onSubmit={handleCreateCandidate}
        >
          <div className="panel-heading">
            <div>
              <h3>Add a candidate</h3>
              <p>Create a private candidate record.</p>
            </div>
          </div>

          <label htmlFor="candidate-name">Full name *</label>
          <input
            id="candidate-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Enter candidate name"
            minLength={2}
            maxLength={255}
            required
          />

          <label htmlFor="candidate-email">Email address</label>
          <input
            id="candidate-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="candidate@example.com"
          />

          <label htmlFor="candidate-phone">Phone number</label>
          <input
            id="candidate-phone"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            placeholder="Enter phone number"
            maxLength={50}
          />

          <label htmlFor="candidate-location">Location</label>
          <input
            id="candidate-location"
            value={location}
            onChange={(event) => setLocation(event.target.value)}
            placeholder="e.g. Bengaluru"
            maxLength={255}
          />

          <button
            className="primary-button candidate-submit"
            type="submit"
            disabled={saving}
          >
            {saving ? "Adding candidate..." : "+ Add candidate"}
          </button>
        </form>

        <div className="panel candidate-list-panel">
          <div className="panel-heading">
            <div>
              <h3>Candidate directory</h3>
              <p>Records belonging to your organization.</p>
            </div>
          </div>

          {loading ? (
            <p className="candidate-empty">Loading candidates...</p>
          ) : candidates.length === 0 ? (
            <div className="candidate-empty">
              <span className="candidate-empty-icon">N</span>
              <h3>Your talent directory starts here</h3>
              <p>Add your first candidate using the form.</p>
            </div>
          ) : (
            <div className="candidate-list">
              {candidates.map((candidate) => {
                const resumes = resumesByCandidate[candidate.id] || [];

                return (
                  <article
                    className="candidate-card"
                    key={candidate.id}
                  >
                    <div className="candidate-card-top">
                      <div className="candidate-avatar">
                        {candidate.name.charAt(0).toUpperCase()}
                      </div>

                      <div className="candidate-details">
                        <h4>{candidate.name}</h4>
                        <p>{candidate.email || "No email provided"}</p>
                        <span>
                          {candidate.location || "Location not specified"}
                        </span>
                      </div>

                      <span className="candidate-id">
                        #{candidate.id}
                      </span>
                    </div>

                    {candidate.phone && (
                      <p className="candidate-phone">
                        Phone: {candidate.phone}
                      </p>
                    )}

                    <div className="candidate-resume">
                      <label htmlFor={`resume-${candidate.id}`}>
                        PDF resume · Maximum 5 MB
                      </label>

                      <input
                        id={`resume-${candidate.id}`}
                        type="file"
                        accept=".pdf,application/pdf"
                        onChange={(event) => {
                          const file = event.target.files?.[0] || null;

                          setSelectedFiles((current) => ({
                            ...current,
                            [candidate.id]: file,
                          }));
                        }}
                      />

                      <div className="candidate-actions">
                        <button
                          type="button"
                          className="secondary-button"
                          disabled={
                            busyCandidate === candidate.id ||
                            !selectedFiles[candidate.id]
                          }
                          onClick={() => handleUpload(candidate.id)}
                        >
                          {busyCandidate === candidate.id
                            ? "Please wait..."
                            : "Upload resume"}
                        </button>



                        {resumes.map((resume) => {
                          const parseKey = `${candidate.id}:${resume.id}`;
                          const parsed = parsedResumes[resume.id];

                          return (
                            <div key={resume.id} className="resume-actions">
                              <button
                                type="button"
                                className="secondary-button"
                                disabled={
                                  busyCandidate === candidate.id ||
                                  parsingResume !== null
                                }
                                onClick={() =>
                                  handleParseResume(candidate.id, resume.id)
                                }
                              >
                                {parsingResume === parseKey
                                  ? "Parsing resume..."
                                  : parsed || resume.status === "parsed"
                                    ? "Parse again"
                                    : "Parse Resume"}
                              </button>

                              <button
                                type="button"
                                className="primary-button"
                                disabled={busyCandidate === candidate.id}
                                onClick={() =>
                                  handleDownload(candidate.id, resume.id)
                                }
                              >
                                Download resume · #{resume.id}
                              </button>

                              {parsed && (
                                <div className="resume-parsed-preview">
                                  <p>
                                    <strong>Parsing complete</strong>
                                  </p>
                                  <p>
                                    Extracted {parsed.character_count} characters.
                                  </p>
                                  <details>
                                    <summary>View extracted text preview</summary>
                                    <pre>
                                      {parsed.preview
                                        .replace(/\r\n?/g, "\n")
                                        .replace(/[ \t]+$/gm, "")
                                        .replace(/\n{3,}/g, "\n\n")
                                        .trim()}
                                    </pre>
                                  </details>
                                </div>
                              )}

                              {resume.status === "parsed" && (
                                <button
                                  type="button"
                                  className="secondary-button"
                                  disabled={loadingProfile === resume.id}
                                  onClick={() =>
                                    handleViewProfile(candidate.id, resume.id)
                                  }
                                >
                                  {loadingProfile === resume.id
                                    ? "Loading profile..."
                                    : "View structured profile"}
                                </button>
                              )}

                              {profileByResume[resume.id] && (
                                <div className="resume-profile">
                                  <div className="resume-profile-header">
                                    <span className="eyebrow">NEXA RECRUIT · PROFILE</span>
                                    <h3>
                                      {profileByResume[resume.id].contact?.name ||
                                        candidate.name ||
                                        "Candidate profile"}
                                    </h3>

                                    <div className="resume-profile-contact">
                                      {profileByResume[resume.id].contact?.email && (
                                        <p>{profileByResume[resume.id].contact.email}</p>
                                      )}

                                      {profileByResume[resume.id].contact?.phone && (
                                        <p>{profileByResume[resume.id].contact.phone}</p>
                                      )}

                                      {(profileByResume[resume.id].contact?.links || []).map(
                                        (link) => (
                                          <p key={link}>{link}</p>
                                        )
                                      )}
                                    </div>
                                  </div>

                                  {(profileByResume[resume.id].sections || []).map(
                                    (section, index) => (
                                      <section
                                        className="resume-profile-section"
                                        key={`${section.title}-${index}`}
                                      >
                                        <h4>{section.title}</h4>

                                        {section.items.length > 0 ? (
                                          <ul>
                                            {section.items.map((item, itemIndex) => (
                                              <li key={`${item}-${itemIndex}`}>{item}</li>
                                            ))}
                                          </ul>
                                        ) : (
                                          <p>No details extracted for this section.</p>
                                        )}
                                      </section>
                                    )
                                  )}

                                  {(profileByResume[resume.id].unclassified || []).length > 0 && (
                                    <section className="resume-profile-section">
                                      <h4>Additional information</h4>
                                      <ul>
                                        {profileByResume[resume.id].unclassified.map(
                                          (item, index) => (
                                            <li key={`${item}-${index}`}>{item}</li>
                                          )
                                        )}
                                      </ul>
                                    </section>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}


                      </div>


                      {resumes.map((resume) => (
                        <p className="resume-success" key={resume.id}>
                          Resume available · ID {resume.id}
                        </p>
                      ))}

                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
