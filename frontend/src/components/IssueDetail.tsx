import React, { useState } from "react";
import { ApiClientError, Issue, IssueStatusUpdatePayload, Status } from "../types";
import { ErrorItem, ErrorSummary } from "./ErrorSummary";

interface IssueDetailProps {
  issue: Issue;
  isLoading: boolean;
  onEditClick: () => void;
  onBackClick: () => void;
  onStatusUpdate: (payload: IssueStatusUpdatePayload) => Promise<void>;
  onRefresh: () => Promise<void>;
}

export const IssueDetail: React.FC<IssueDetailProps> = ({
  issue,
  isLoading,
  onEditClick,
  onBackClick,
  onStatusUpdate,
  onRefresh,
}) => {
  const [selectedNewStatus, setSelectedNewStatus] = useState<Status | "">("");
  const [statusComment, setStatusComment] = useState("");
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [statusErrors, setStatusErrors] = useState<ErrorItem[]>([]);
  const [statusFieldErrors, setStatusFieldErrors] = useState<Record<string, string>>({});
  const [conflictWarning, setConflictWarning] = useState<string | null>(null);

  // Compute allowed transitions based on workflow rules
  const getAllowedTransitions = (current: Status): Status[] => {
    switch (current) {
      case "Open":
        return ["In Progress", "Resolved"];
      case "In Progress":
        return ["Open", "Resolved"];
      case "Resolved":
        return ["Open"]; // Note: Resolved -> In Progress is blocked by backend
      default:
        return [];
    }
  };

  const allowedStatuses = getAllowedTransitions(issue.status);

  const handleStatusSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setConflictWarning(null);
    setStatusErrors([]);
    setStatusFieldErrors({});

    if (!selectedNewStatus) {
      setStatusFieldErrors({ "new-status": "Please select a target status." });
      setStatusErrors([{ field: "new-status", message: "Please select a target status." }]);
      return;
    }

    if (selectedNewStatus === issue.status) {
      setStatusFieldErrors({ "new-status": "New status must be different from current status." });
      setStatusErrors([{ field: "new-status", message: "New status must be different from current status." }]);
      return;
    }

    setIsUpdatingStatus(true);
    try {
      await onStatusUpdate({
        status: selectedNewStatus as Status,
        version: issue.version,
        comment: statusComment.trim() || null,
      });
      setSelectedNewStatus("");
      setStatusComment("");
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        if (err.statusCode === 409) {
          setConflictWarning(
            err.message ||
              "Workflow or Concurrency Conflict: The issue status could not be changed. Please reload the latest issue state."
          );
          setStatusErrors([
            {
              message:
                err.message ||
                "Conflict: The status change was rejected due to an invalid transition or outdated record version.",
            },
          ]);
        } else {
          setStatusErrors([{ message: err.message }]);
        }
      } else if (err instanceof Error) {
        setStatusErrors([{ message: err.message }]);
      } else {
        setStatusErrors([{ message: "An unexpected error occurred while updating status." }]);
      }
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "Open":
        return "badge-status-open";
      case "In Progress":
        return "badge-status-in-progress";
      case "Resolved":
        return "badge-status-resolved";
      default:
        return "";
    }
  };

  const getSeverityBadgeClass = (severity: string) => {
    switch (severity) {
      case "Critical":
        return "badge-severity-critical";
      case "Serious":
        return "badge-severity-serious";
      case "Moderate":
        return "badge-severity-moderate";
      case "Minor":
        return "badge-severity-minor";
      default:
        return "";
    }
  };

  return (
    <article aria-labelledby="issue-detail-heading">
      {/* Navigation Breadcrumb */}
      <nav aria-label="Breadcrumb" style={{ marginBottom: "1rem" }}>
        <button
          type="button"
          className="btn btn-secondary btn-small"
          onClick={onBackClick}
          aria-label="Back to issues list"
        >
          &larr; Back to Issues List
        </button>
      </nav>

      {/* Main Issue Card */}
      <div className="card">
        <div className="card-header">
          <div>
            <div style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: "0.25rem" }}>
              Issue #{issue.id} &bull; Version {issue.version}
            </div>
            <h1 id="issue-detail-heading" style={{ margin: 0, fontSize: "1.75rem" }}>
              {issue.title}
            </h1>
          </div>

          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onEditClick}
            >
              ✎ Edit Issue
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-small"
              onClick={onRefresh}
              disabled={isLoading}
              title="Reload latest details from server"
              aria-label="Refresh issue details"
            >
              {isLoading ? "Loading..." : "🔄 Refresh"}
            </button>
          </div>
        </div>

        {/* Metadata Details Grid */}
        <dl
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "1.25rem",
            margin: "0 0 1.5rem 0",
            backgroundColor: "#f8fafc",
            padding: "1rem",
            borderRadius: "var(--border-radius)",
            border: "1px solid var(--color-border-subtle)",
          }}
        >
          <div>
            <dt style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", fontWeight: 600 }}>
              Status
            </dt>
            <dd style={{ margin: "0.25rem 0 0 0" }}>
              <span className={`badge ${getStatusBadgeClass(issue.status)}`}>
                {issue.status}
              </span>
            </dd>
          </div>

          <div>
            <dt style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", fontWeight: 600 }}>
              Severity
            </dt>
            <dd style={{ margin: "0.25rem 0 0 0" }}>
              <span className={`badge ${getSeverityBadgeClass(issue.severity)}`}>
                {issue.severity}
              </span>
            </dd>
          </div>

          <div>
            <dt style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", fontWeight: 600 }}>
              WCAG Criterion
            </dt>
            <dd style={{ margin: "0.25rem 0 0 0", fontWeight: 600 }}>
              {issue.wcag_criterion || "Not specified"}
            </dd>
          </div>

          <div>
            <dt style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", fontWeight: 600 }}>
              Created At
            </dt>
            <dd style={{ margin: "0.25rem 0 0 0", fontSize: "0.875rem" }}>
              <time dateTime={issue.created_at}>
                {new Date(issue.created_at).toLocaleString()}
              </time>
            </dd>
          </div>

          <div>
            <dt style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", fontWeight: 600 }}>
              Last Updated
            </dt>
            <dd style={{ margin: "0.25rem 0 0 0", fontSize: "0.875rem" }}>
              <time dateTime={issue.updated_at}>
                {new Date(issue.updated_at).toLocaleString()}
              </time>
            </dd>
          </div>
        </dl>

        {/* Page URL */}
        <div style={{ marginBottom: "1.25rem" }}>
          <strong style={{ display: "block", marginBottom: "0.25rem", fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
            Affected Page URL:
          </strong>
          <a
            href={issue.page_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              color: "var(--color-primary)",
              fontWeight: 600,
              wordBreak: "break-all",
              textDecoration: "underline",
            }}
          >
            {issue.page_url}
            <span className="sr-only"> (opens in new tab)</span>
          </a>
        </div>

        {/* Description */}
        <div>
          <strong style={{ display: "block", marginBottom: "0.25rem", fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
            Description &amp; Remediation Notes:
          </strong>
          <div
            style={{
              whiteSpace: "pre-wrap",
              lineHeight: 1.6,
              backgroundColor: "#fdfdfd",
              padding: "1rem",
              borderRadius: "var(--border-radius)",
              border: "1px solid var(--color-border-subtle)",
            }}
          >
            {issue.description || <em style={{ color: "var(--color-text-muted)" }}>No description provided.</em>}
          </div>
        </div>
      </div>

      {/* Change Status Workflow Box */}
      <section className="card" aria-labelledby="status-transition-heading">
        <h2 id="status-transition-heading" style={{ margin: "0 0 0.75rem 0", fontSize: "1.25rem" }}>
          Update Issue Status
        </h2>

        <p style={{ color: "var(--color-text-muted)", fontSize: "0.9375rem", margin: "0 0 1rem 0" }}>
          Move this issue through the audit remediation lifecycle. Valid next statuses:{" "}
          {allowedStatuses.length > 0 ? (
            allowedStatuses.map((s) => (
              <strong key={s} style={{ margin: "0 0.25rem" }}>
                {s}
              </strong>
            ))
          ) : (
            <em>None available</em>
          )}
          .
        </p>

        <ErrorSummary errors={statusErrors} heading="Status update failed:" />

        {conflictWarning && (
          <div className="demo-banner" style={{ borderColor: "var(--color-danger-border)", backgroundColor: "var(--color-danger-bg)", marginBottom: "1rem" }}>
            <strong style={{ color: "#7f1d1d" }}>Workflow Notice:</strong>
            <span style={{ color: "#7f1d1d", marginLeft: "0.5rem" }}>{conflictWarning}</span>
          </div>
        )}

        <form onSubmit={handleStatusSubmit} noValidate>
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "flex-end" }}>
            <div style={{ flex: "1 1 200px" }}>
              <label htmlFor="new-status" className="form-label">
                Next Status <span className="required-indicator">(required)</span>
              </label>
              <select
                id="new-status"
                className="form-control"
                value={selectedNewStatus}
                onChange={(e) => {
                  setSelectedNewStatus(e.target.value as Status | "");
                  if (statusFieldErrors["new-status"]) {
                    setStatusFieldErrors({});
                  }
                }}
                aria-required="true"
                aria-invalid={Boolean(statusFieldErrors["new-status"])}
                aria-describedby={statusFieldErrors["new-status"] ? "new-status-error" : undefined}
              >
                <option value="">-- Choose target status --</option>
                {allowedStatuses.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              {statusFieldErrors["new-status"] && (
                <div id="new-status-error" className="form-error" role="alert">
                  <span aria-hidden="true">⚠️</span> {statusFieldErrors["new-status"]}
                </div>
              )}
            </div>

            <div style={{ flex: "2 1 300px" }}>
              <label htmlFor="status-comment" className="form-label">
                Remediation Comment <span style={{ fontWeight: 400, color: "var(--color-text-muted)" }}>(Optional)</span>
              </label>
              <input
                id="status-comment"
                type="text"
                className="form-control"
                value={statusComment}
                onChange={(e) => setStatusComment(e.target.value)}
                placeholder="Reason or notes regarding this status change"
              />
            </div>

            <div>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isUpdatingStatus || !selectedNewStatus}
              >
                {isUpdatingStatus ? "Updating..." : "Submit Status Change"}
              </button>
            </div>
          </div>
        </form>
      </section>

      {/* Persistent Status History Timeline */}
      <section className="card" aria-labelledby="status-history-heading">
        <h2 id="status-history-heading" style={{ margin: "0 0 1.25rem 0", fontSize: "1.25rem" }}>
          Status Change History
        </h2>

        {(!issue.status_history || issue.status_history.length === 0) ? (
          <p style={{ color: "var(--color-text-muted)" }}>
            No status changes have been recorded for this issue yet.
          </p>
        ) : (
          <ol className="status-timeline">
            {issue.status_history.map((entry) => (
              <li key={entry.id} className="status-timeline-item">
                <div className="timeline-dot" aria-hidden="true" />
                <div className="timeline-meta">
                  <time dateTime={entry.changed_at}>
                    {new Date(entry.changed_at).toLocaleString()}
                  </time>{" "}
                  &bull; Actor: <strong>{entry.actor_id}</strong>
                </div>

                <div style={{ margin: "0.25rem 0", fontSize: "0.9375rem" }}>
                  Status changed from{" "}
                  <span className={`badge ${getStatusBadgeClass(entry.previous_status)}`}>
                    {entry.previous_status}
                  </span>{" "}
                  to{" "}
                  <span className={`badge ${getStatusBadgeClass(entry.new_status)}`}>
                    {entry.new_status}
                  </span>
                </div>

                {entry.comment && (
                  <div
                    style={{
                      marginTop: "0.375rem",
                      fontSize: "0.875rem",
                      fontStyle: "italic",
                      backgroundColor: "#f8fafc",
                      padding: "0.5rem 0.75rem",
                      borderRadius: "var(--border-radius)",
                      border: "1px solid var(--color-border-subtle)",
                    }}
                  >
                    &ldquo;{entry.comment}&rdquo;
                  </div>
                )}
              </li>
            ))}
          </ol>
        )}
      </section>
    </article>
  );
};
