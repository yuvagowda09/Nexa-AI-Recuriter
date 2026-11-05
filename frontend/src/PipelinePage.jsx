
import { useCallback, useEffect, useState } from "react";
import "./PipelinePage.css";

const API = "http://127.0.0.1:8000";

const STAGES = [
    { id: "screening", label: "Screening" },
    { id: "shortlisted", label: "Shortlisted" },
    { id: "interview_scheduled", label: "Interview" },
    { id: "interview_completed", label: "Interview Completed" },
    { id: "offer", label: "Offer" },
    { id: "hired", label: "Hired" },
    { id: "rejected", label: "Rejected" },
    { id: "withdrawn", label: "Withdrawn" },
];

export default function PipelinePage({ accessToken }) {
    const [entries, setEntries] = useState([]);
    const [jobs, setJobs] = useState([]);
    const [candidates, setCandidates] = useState([]);
    const [candidateId, setCandidateId] = useState("");
    const [jobId, setJobId] = useState("");
    const [status, setStatus] = useState("screening");
    const [notes, setNotes] = useState("");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [busyId, setBusyId] = useState(null);
    const [error, setError] = useState("");
    const [notice, setNotice] = useState("");

    const headers = {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
    };

    const loadData = useCallback(async () => {
        if (!accessToken) return;

        setLoading(true);
        setError("");

        try {
            const [pipelineResponse, jobsResponse, candidatesResponse] =
                await Promise.all([
                    fetch(`${API}/pipeline/`, { headers }),
                    fetch(`${API}/jobs/`, { headers }),
                    fetch(`${API}/candidates/`, { headers }),
                ]);

            const responses = [
                pipelineResponse,
                jobsResponse,
                candidatesResponse,
            ];

            const data = await Promise.all(
                responses.map(async (response) => {
                    const result = await response.json().catch(() => ({}));
                    if (!response.ok) {
                        throw new Error(
                            result.detail || "Unable to load recruitment data."
                        );
                    }
                    return result;
                })
            );

            setEntries(Array.isArray(data[0]) ? data[0] : []);
            setJobs(Array.isArray(data[1]) ? data[1] : []);
            setCandidates(Array.isArray(data[2]) ? data[2] : []);
        } catch (err) {
            setError(err.message || "Unable to connect to the backend.");
        } finally {
            setLoading(false);
        }
    }, [accessToken]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    async function handleCreate(event) {
        event.preventDefault();
        if (!candidateId || !jobId) {
            setError("Select both a candidate and a job.");
            return;
        }

        setSaving(true);
        setError("");
        setNotice("");

        try {
            const response = await fetch(`${API}/pipeline/`, {
                method: "POST",
                headers,
                body: JSON.stringify({
                    candidate_id: Number(candidateId),
                    job_id: Number(jobId),
                    status,
                    notes: notes.trim() || null,
                }),
            });

            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.detail || "Unable to add candidate to pipeline.");
            }

            setEntries((current) => [data, ...current]);
            setCandidateId("");
            setJobId("");
            setStatus("screening");
            setNotes("");
            setNotice("Candidate added to the recruitment pipeline.");
        } catch (err) {
            setError(err.message || "Unable to create pipeline entry.");
        } finally {
            setSaving(false);
        }
    }

    async function handleUpdate(entry, nextStatus) {
        const updatedNotes = window.prompt(
            "Add or update recruiter notes (optional):",
            entry.notes || ""
        );
        if (updatedNotes === null) return;

        setBusyId(entry.id);
        setError("");
        setNotice("");

        try {
            const response = await fetch(`${API}/pipeline/${entry.id}`, {
                method: "PATCH",
                headers,
                body: JSON.stringify({
                    status: nextStatus,
                    notes: updatedNotes.trim() || null,
                }),
            });

            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.detail || "Unable to update candidate status.");
            }

            setEntries((current) =>
                current.map((item) =>
                    item.id === entry.id
                        ? {
                            ...item, ...data, candidate_name: entry.candidate_name,
                            job_title: entry.job_title
                        }
                        : item
                )
            );
            setNotice("Candidate pipeline status updated.");
        } catch (err) {
            setError(err.message || "Unable to update status.");
        } finally {
            setBusyId(null);
        }
    }

    const activeCount = entries.filter(
        (entry) => !["hired", "rejected", "withdrawn"].includes(entry.status)
    ).length;

    return (
        <main className="pipeline-page">
            <header className="pipeline-heading">
                <div>
                    <p className="pipeline-eyebrow">NEXA RECRUIT · TALENT OPERATIONS</p>
                    <h1>Recruitment Pipeline</h1>
                    <p>Track every candidate's journey, from screening to decision.</p>
                </div>
                <div className="pipeline-stat">
                    <span>ACTIVE CANDIDATES</span>
                    <strong>{activeCount}</strong>
                </div>
            </header>

            {error && <div className="pipeline-alert error">{error}</div>}
            {notice && <div className="pipeline-alert success">{notice}</div>}

            <form className="pipeline-form" onSubmit={handleCreate}>
                <div>
                    <h2>Add to pipeline</h2>
                    <p>Connect an existing candidate to a specific job.</p>
                </div>

                <label>
                    Candidate
                    <select
                        value={candidateId}
                        onChange={(event) => setCandidateId(event.target.value)}
                        required
                    >
                        <option value="">Select candidate</option>
                        {candidates.map((candidate) => (
                            <option key={candidate.id} value={candidate.id}>
                                {candidate.name}
                            </option>
                        ))}
                    </select>
                </label>

                <label>
                    Job
                    <select
                        value={jobId}
                        onChange={(event) => setJobId(event.target.value)}
                        required
                    >
                        <option value="">Select job</option>
                        {jobs.map((job) => (
                            <option key={job.id} value={job.id}>
                                {job.title}
                            </option>
                        ))}
                    </select>
                </label>

                <label>
                    Initial stage
                    <select
                        value={status}
                        onChange={(event) => setStatus(event.target.value)}
                    >
                        {STAGES.map((stage) => (
                            <option key={stage.id} value={stage.id}>
                                {stage.label}
                            </option>
                        ))}
                    </select>
                </label>

                <label>
                    Recruiter notes
                    <input
                        value={notes}
                        onChange={(event) => setNotes(event.target.value)}
                        maxLength={5000}
                        placeholder="Optional notes"
                    />
                </label>

                <button type="submit" disabled={saving}>
                    {saving ? "Adding..." : "+ Add candidate"}
                </button>
            </form>

            {loading ? (
                <p className="pipeline-empty">Loading recruitment pipeline...</p>
            ) : entries.length === 0 ? (
                <div className="pipeline-empty">
                    <h2>Your pipeline starts here</h2>
                    <p>Add a candidate to a job using the form above.</p>
                </div>
            ) : (
                <div className="pipeline-board">
                    {STAGES.map((stage) => {
                        const stageEntries = entries.filter(
                            (entry) => entry.status === stage.id
                        );

                        return (
                            <section className="pipeline-column" key={stage.id}>
                                <header className="pipeline-column-heading">
                                    <h2>{stage.label}</h2>
                                    <span>{stageEntries.length}</span>
                                </header>

                                {stageEntries.length === 0 ? (
                                    <p className="pipeline-column-empty">No candidates</p>
                                ) : (
                                    stageEntries.map((entry) => (
                                        <article className="pipeline-card" key={entry.id}>
                                            <span className="pipeline-card-id">
                                                APPLICATION #{entry.id}
                                            </span>
                                            <h3>{entry.candidate_name || `Candidate #${entry.candidate_id}`}</h3>
                                            <p className="pipeline-job">
                                                {entry.job_title || `Job #${entry.job_id}`}
                                            </p>

                                            {entry.notes && (
                                                <p className="pipeline-notes">{entry.notes}</p>
                                            )}

                                            <label>
                                                Move to stage
                                                <select
                                                    value={entry.status}
                                                    disabled={busyId === entry.id}
                                                    onChange={(event) =>
                                                        handleUpdate(entry, event.target.value)
                                                    }
                                                >
                                                    {STAGES.map((option) => (
                                                        <option key={option.id} value={option.id}>
                                                            {option.label}
                                                        </option>
                                                    ))}
                                                </select>
                                            </label>
                                        </article>
                                    ))
                                )}
                            </section>
                        );
                    })}
                </div>
            )}
        </main>
    );
}
