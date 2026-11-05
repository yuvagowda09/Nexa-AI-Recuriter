import { useCallback, useEffect, useState } from "react";
import "./TeamPage.css";

const API_BASE_URL = "http://127.0.0.1:8000";

export default function TeamPage({ accessToken }) {
  const [activeTab, setActiveTab] = useState("members"); // 'members' | 'invitations'
  const [members, setMembers] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [actionLoading, setActionLoading] = useState(null); // id of item being modified
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  // Confirmation modal state
  const [confirmModal, setConfirmModal] = useState(null);
  // shape: { title, message, onConfirm, confirmText, danger }

  // Add Member Form State
  const [addName, setAddName] = useState("");
  const [addEmail, setAddEmail] = useState("");
  const [addPassword, setAddPassword] = useState("");
  const [addRole, setAddRole] = useState("recruiter");

  // Invite Member Form State
  const [invName, setInvName] = useState("");
  const [invEmail, setInvEmail] = useState("");
  const [invRole, setInvRole] = useState("recruiter");

  // Load team members and invitations
  const loadData = useCallback(async () => {
    if (!accessToken) return;
    setLoading(true);
    setError("");

    try {
      const [membersRes, invRes] = await Promise.all([
        fetch(`${API_BASE_URL}/organization/team-members`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        }),
        fetch(`${API_BASE_URL}/organization/team-invitations`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        }),
      ]);

      if (!membersRes.ok) {
        const err = await membersRes.json();
        throw new Error(err.detail || "Unable to load team members.");
      }

      const membersData = await membersRes.json();
      setMembers(Array.isArray(membersData) ? membersData : []);

      if (invRes.ok) {
        const invData = await invRes.json();
        setInvitations(Array.isArray(invData) ? invData : []);
      }
    } catch (err) {
      setError(err.message || "Failed to connect to backend.");
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handle direct creation of team member
  async function handleAddMember(e) {
    e.preventDefault();
    setNotice("");
    setError("");

    if (!addName.trim() || !addEmail.trim() || !addPassword.trim()) {
      setError("Please fill in all required fields.");
      return;
    }

    if (addPassword.length < 12) {
      setError("Password must be at least 12 characters long.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE_URL}/organization/team-members`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          name: addName.trim(),
          email: addEmail.trim(),
          password: addPassword,
          role: addRole,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to create team member.");
      }

      setNotice(`Team member ${data.name} created successfully.`);
      setAddName("");
      setAddEmail("");
      setAddPassword("");
      setAddRole("recruiter");
      await loadData();
    } catch (err) {
      setError(err.message || "Unable to create member.");
    } finally {
      setSubmitting(false);
    }
  }

  // Handle sending email invitation
  async function handleInviteMember(e) {
    e.preventDefault();
    setNotice("");
    setError("");

    if (!invName.trim() || !invEmail.trim()) {
      setError("Please enter the invitee's name and email.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE_URL}/organization/team-invitations`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          name: invName.trim(),
          email: invEmail.trim(),
          role: invRole,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to send invitation.");
      }

      setNotice(`Invitation sent to ${data.email}.`);
      setInvName("");
      setInvEmail("");
      setInvRole("recruiter");
      await loadData();
    } catch (err) {
      setError(err.message || "Unable to send invitation.");
    } finally {
      setSubmitting(false);
    }
  }

  // Handle Role Change
  function requestRoleChange(member, newRole) {
    if (member.role === newRole) return;

    setConfirmModal({
      title: "Confirm Role Change",
      message: `Are you sure you want to change ${member.name}'s role from ${member.role} to ${newRole}?`,
      confirmText: "Change Role",
      danger: false,
      onConfirm: async () => {
        setConfirmModal(null);
        setActionLoading(member.id);
        setNotice("");
        setError("");

        try {
          const res = await fetch(
            `${API_BASE_URL}/organization/team-members/${member.id}/role`,
            {
              method: "PATCH",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${accessToken}`,
              },
              body: JSON.stringify({ role: newRole }),
            }
          );

          const data = await res.json();
          if (!res.ok) {
            throw new Error(data.detail || "Unable to update role.");
          }

          setNotice(`Updated ${member.name}'s role to ${data.role}.`);
          await loadData();
        } catch (err) {
          setError(err.message || "Failed to update role.");
        } finally {
          setActionLoading(null);
        }
      },
    });
  }

  // Handle Status Toggle (Activate / Deactivate)
  function requestStatusToggle(member) {
    const nextStatus = !member.is_active;
    const actionWord = nextStatus ? "reactivate" : "deactivate";

    setConfirmModal({
      title: `${nextStatus ? "Reactivate" : "Deactivate"} Team Member`,
      message: `Are you sure you want to ${actionWord} ${member.name}? ${
        !nextStatus ? "They will be blocked from logging in until reactivated." : ""
      }`,
      confirmText: nextStatus ? "Reactivate" : "Deactivate",
      danger: !nextStatus,
      onConfirm: async () => {
        setConfirmModal(null);
        setActionLoading(member.id);
        setNotice("");
        setError("");

        try {
          const res = await fetch(
            `${API_BASE_URL}/organization/team-members/${member.id}/status?is_active=${nextStatus}`,
            {
              method: "PATCH",
              headers: {
                Authorization: `Bearer ${accessToken}`,
              },
            }
          );

          const data = await res.json();
          if (!res.ok) {
            throw new Error(data.detail || "Unable to update status.");
          }

          setNotice(
            `Account for ${member.name} ${
              data.is_active ? "reactivated" : "deactivated"
            } successfully.`
          );
          await loadData();
        } catch (err) {
          setError(err.message || "Failed to update status.");
        } finally {
          setActionLoading(null);
        }
      },
    });
  }

  // Handle Cancel Invitation
  function requestCancelInvitation(inv) {
    setConfirmModal({
      title: "Cancel Invitation",
      message: `Cancel the invitation sent to ${inv.email}? The invite link will become invalid.`,
      confirmText: "Cancel Invitation",
      danger: true,
      onConfirm: async () => {
        setConfirmModal(null);
        setActionLoading(inv.id);
        setNotice("");
        setError("");

        try {
          const res = await fetch(
            `${API_BASE_URL}/organization/team-invitations/${inv.id}`,
            {
              method: "DELETE",
              headers: { Authorization: `Bearer ${accessToken}` },
            }
          );

          const data = await res.json();
          if (!res.ok) {
            throw new Error(data.detail || "Unable to cancel invitation.");
          }

          setNotice("Invitation cancelled successfully.");
          await loadData();
        } catch (err) {
          setError(err.message || "Failed to cancel invitation.");
        } finally {
          setActionLoading(null);
        }
      },
    });
  }

  // Handle Resend Invitation
  async function handleResendInvitation(inv) {
    setActionLoading(inv.id);
    setNotice("");
    setError("");

    try {
      const res = await fetch(
        `${API_BASE_URL}/organization/team-invitations/${inv.id}/resend`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${accessToken}` },
        }
      );

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Unable to resend invitation.");
      }

      setNotice(`Invitation resent successfully to ${inv.email}.`);
      await loadData();
    } catch (err) {
      setError(err.message || "Failed to resend invitation.");
    } finally {
      setActionLoading(null);
    }
  }

  const activeMembersCount = members.filter((m) => m.is_active).length;
  const pendingInvitesCount = invitations.filter((i) => i.status === "pending").length;

  return (
    <div className="team-page">
      {/* Confirmation Modal */}
      {confirmModal && (
        <div className="team-confirm-overlay">
          <div className="team-confirm-modal">
            <h4>{confirmModal.title}</h4>
            <p>{confirmModal.message}</p>
            <div className="team-confirm-actions">
              <button
                className="team-btn-secondary"
                onClick={() => setConfirmModal(null)}
              >
                Cancel
              </button>
              <button
                className={confirmModal.danger ? "team-btn-danger" : "team-btn-primary"}
                onClick={confirmModal.onConfirm}
              >
                {confirmModal.confirmText}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header & Metrics */}
      <div className="team-heading">
        <div className="team-heading-text">
          <h1>Team Management</h1>
          <p>Manage your recruitment team members, roles, and pending invitations.</p>
        </div>

        <div className="team-metrics">
          <div className="team-metric-card">
            <span>TOTAL MEMBERS</span>
            <strong>{members.length}</strong>
          </div>
          <div className="team-metric-card">
            <span>ACTIVE ACCOUNTS</span>
            <strong>{activeMembersCount}</strong>
          </div>
          <div className="team-metric-card">
            <span>PENDING INVITES</span>
            <strong>{pendingInvitesCount}</strong>
          </div>
        </div>
      </div>

      {/* Alert Notices */}
      {notice && (
        <div className="team-message success">
          ✓ {notice}
        </div>
      )}
      {error && (
        <div className="team-message error">
          ⚠ {error}
        </div>
      )}

      {/* Tabs */}
      <div className="team-tabs">
        <button
          className={`team-tab-btn ${activeTab === "members" ? "active" : ""}`}
          onClick={() => setActiveTab("members")}
        >
          Team Members
          <span className="team-badge-count">{members.length}</span>
        </button>
        <button
          className={`team-tab-btn ${activeTab === "invitations" ? "active" : ""}`}
          onClick={() => setActiveTab("invitations")}
        >
          Invitations
          <span className="team-badge-count">{invitations.length}</span>
        </button>
      </div>

      {/* TAB 1: MEMBERS */}
      {activeTab === "members" && (
        <div className="team-layout">
          {/* Add Team Member Form */}
          <div className="team-panel">
            <h3>Add Team Member</h3>
            <p className="team-panel-desc">
              Create a team member account directly with credentials.
            </p>

            <form className="team-form" onSubmit={handleAddMember}>
              <label>FULL NAME</label>
              <input
                type="text"
                placeholder="e.g. Sarah Jenkins"
                value={addName}
                onChange={(e) => setAddName(e.target.value)}
                disabled={submitting}
                required
              />

              <label>WORK EMAIL</label>
              <input
                type="email"
                placeholder="sarah@agency.com"
                value={addEmail}
                onChange={(e) => setAddEmail(e.target.value)}
                disabled={submitting}
                required
              />

              <label>TEMPORARY PASSWORD</label>
              <input
                type="password"
                placeholder="At least 12 characters"
                value={addPassword}
                onChange={(e) => setAddPassword(e.target.value)}
                disabled={submitting}
                required
              />

              <label>ROLE ASSIGNMENT</label>
              <select
                value={addRole}
                onChange={(e) => setAddRole(e.target.value)}
                disabled={submitting}
              >
                <option value="recruiter">Recruiter (manage jobs & candidates)</option>
                <option value="team_lead">Team Lead (supervise recruitment)</option>
              </select>

              <button
                type="submit"
                className="team-btn-primary"
                disabled={submitting}
              >
                {submitting ? "Creating Member..." : "Create Team Member"}
              </button>
            </form>
          </div>

          {/* Members Table */}
          <div className="team-panel">
            <h3>Organization Roster</h3>
            <p className="team-panel-desc">
              All registered recruiters and leaders in your organization.
            </p>

            {loading ? (
              <div className="team-empty-state">
                <p>Loading team members...</p>
              </div>
            ) : members.length === 0 ? (
              <div className="team-empty-state">
                <p>No team members found.</p>
              </div>
            ) : (
              <div className="team-table-wrapper">
                <table className="team-table">
                  <thead>
                    <tr>
                      <th>MEMBER</th>
                      <th>ROLE</th>
                      <th>STATUS</th>
                      <th>ACTIONS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {members.map((member) => {
                      const isAdmin = member.role === "admin";
                      const isBusy = actionLoading === member.id;

                      return (
                        <tr key={member.id}>
                          <td>
                            <div className="team-user-cell">
                              <div className="team-avatar">
                                {member.name ? member.name[0].toUpperCase() : "U"}
                              </div>
                              <div className="team-user-info">
                                <strong>{member.name}</strong>
                                <small>{member.email}</small>
                              </div>
                            </div>
                          </td>
                          <td>
                            {isAdmin ? (
                              <span className="team-role-badge admin">Admin</span>
                            ) : (
                              <select
                                className="team-role-select"
                                value={member.role}
                                onChange={(e) =>
                                  requestRoleChange(member, e.target.value)
                                }
                                disabled={isBusy}
                              >
                                <option value="recruiter">Recruiter</option>
                                <option value="team_lead">Team Lead</option>
                              </select>
                            )}
                          </td>
                          <td>
                            <span
                              className={`team-status-badge ${
                                member.is_active ? "active" : "inactive"
                              }`}
                            >
                              {member.is_active ? "Active" : "Inactive"}
                            </span>
                          </td>
                          <td>
                            <div className="team-actions-cell">
                              {!isAdmin && (
                                <button
                                  className={`team-action-btn ${
                                    member.is_active ? "danger" : "success"
                                  }`}
                                  onClick={() => requestStatusToggle(member)}
                                  disabled={isBusy}
                                >
                                  {isBusy
                                    ? "Updating..."
                                    : member.is_active
                                    ? "Deactivate"
                                    : "Reactivate"}
                                </button>
                              )}
                              {isAdmin && (
                                <small style={{ color: "#94a3b8" }}>Primary Admin</small>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: INVITATIONS */}
      {activeTab === "invitations" && (
        <div className="team-layout">
          {/* Send Invitation Form */}
          <div className="team-panel">
            <h3>Send Team Invitation</h3>
            <p className="team-panel-desc">
              Send an email with a secure 48-hour onboarding link.
            </p>

            <form className="team-form" onSubmit={handleInviteMember}>
              <label>RECIPIENT NAME</label>
              <input
                type="text"
                placeholder="e.g. Alex Morgan"
                value={invName}
                onChange={(e) => setInvName(e.target.value)}
                disabled={submitting}
                required
              />

              <label>RECIPIENT EMAIL</label>
              <input
                type="email"
                placeholder="alex@example.com"
                value={invEmail}
                onChange={(e) => setInvEmail(e.target.value)}
                disabled={submitting}
                required
              />

              <label>ASSIGNED ROLE</label>
              <select
                value={invRole}
                onChange={(e) => setInvRole(e.target.value)}
                disabled={submitting}
              >
                <option value="recruiter">Recruiter</option>
                <option value="team_lead">Team Lead</option>
              </select>

              <p className="team-form-note">
                An invitation email will be sent with a cryptographically signed token.
                The recipient can set their own password upon accepting.
              </p>

              <button
                type="submit"
                className="team-btn-primary"
                disabled={submitting}
              >
                {submitting ? "Sending Invitation..." : "Send Invitation"}
              </button>
            </form>
          </div>

          {/* Invitations Table */}
          <div className="team-panel">
            <h3>Sent Invitations</h3>
            <p className="team-panel-desc">
              Track pending, accepted, and expired invitations.
            </p>

            {loading ? (
              <div className="team-empty-state">
                <p>Loading invitations...</p>
              </div>
            ) : invitations.length === 0 ? (
              <div className="team-empty-state">
                <p>No invitations sent yet.</p>
              </div>
            ) : (
              <div className="team-table-wrapper">
                <table className="team-table">
                  <thead>
                    <tr>
                      <th>RECIPIENT</th>
                      <th>ROLE</th>
                      <th>STATUS</th>
                      <th>ACTIONS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invitations.map((inv) => {
                      const isBusy = actionLoading === inv.id;
                      const isPending = inv.status === "pending";
                      const isAccepted = inv.status === "accepted";

                      return (
                        <tr key={inv.id}>
                          <td>
                            <div className="team-user-cell">
                              <div className="team-avatar">
                                {inv.name ? inv.name[0].toUpperCase() : "I"}
                              </div>
                              <div className="team-user-info">
                                <strong>{inv.name}</strong>
                                <small>{inv.email}</small>
                              </div>
                            </div>
                          </td>
                          <td>
                            <span className={`team-role-badge ${inv.role}`}>
                              {inv.role === "team_lead" ? "Team Lead" : "Recruiter"}
                            </span>
                          </td>
                          <td>
                            <span className={`team-status-badge ${inv.status}`}>
                              {inv.status.charAt(0).toUpperCase() + inv.status.slice(1)}
                            </span>
                          </td>
                          <td>
                            <div className="team-actions-cell">
                              {isPending && (
                                <>
                                  <button
                                    className="team-action-btn"
                                    onClick={() => handleResendInvitation(inv)}
                                    disabled={isBusy}
                                  >
                                    {isBusy ? "Sending..." : "Resend"}
                                  </button>
                                  <button
                                    className="team-action-btn danger"
                                    onClick={() => requestCancelInvitation(inv)}
                                    disabled={isBusy}
                                  >
                                    Cancel
                                  </button>
                                </>
                              )}
                              {inv.status === "expired" && (
                                <button
                                  className="team-action-btn"
                                  onClick={() => handleResendInvitation(inv)}
                                  disabled={isBusy}
                                >
                                  {isBusy ? "Resending..." : "Resend Link"}
                                </button>
                              )}
                              {isAccepted && (
                                <small style={{ color: "#166534", fontWeight: "600" }}>
                                  ✓ Accepted
                                </small>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
