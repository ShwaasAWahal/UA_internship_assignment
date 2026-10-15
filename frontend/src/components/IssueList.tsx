import React from "react";
import { Issue, Severity, Status } from "../types";

interface IssueListProps {
  issues: Issue[];
  total: number;
  isLoading: boolean;
  error: string | null;
  selectedStatus: Status | "";
  selectedSeverity: Severity | "";
  onStatusChange: (status: Status | "") => void;
  onSeverityChange: (severity: Severity | "") => void;
  onSelectIssue: (issueId: number) => void;
  onCreateClick: () => void;
  onRetry: () => void;
}

export const IssueList: React.FC<IssueListProps> = ({
  issues,
  total,
  isLoading,
  error,
  selectedStatus,
  selectedSeverity,
  onStatusChange,
  onSeverityChange,
  onSelectIssue,
  onCreateClick,
  onRetry,
}) => {
  const getStatusBadgeClass = (status: Status) => {
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

  const getSeverityBadgeClass = (severity: Severity) => {
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
    <section aria-labelledby="issue-list-heading">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 id="issue-list-heading" style={{ margin: 0, fontSize: "1.75rem" }}>
            Accessibility Issues
          </h1>
          <p style={{ margin: "0.25rem 0 0 0", color: "var(--color-text-muted)", fontSize: "0.9375rem" }}>
            Showing {issues.length} {issues.length === 1 ? "issue" : "issues"} logged by your account ({total} total found).
          </p>
        </div>

        <button
          type="button"
          className="btn btn-primary"
          onClick={onCreateClick}
        >
          + Log New Issue
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="toolbar" role="search" aria-label="Filter issues">
        <div className="filter-group">
          <div className="filter-item">
            <label htmlFor="filter-status">Filter by Status:</label>
            <select
              id="filter-status"
              className="form-control"
              style={{ width: "auto" }}
              value={selectedStatus}
              onChange={(e) => onStatusChange(e.target.value as Status | "")}
            >
              <option value="">All Statuses</option>
              <option value="Open">Open</option>
              <option value="In Progress">In Progress</option>
              <option value="Resolved">Resolved</option>
            </select>
          </div>

          <div className="filter-item">
            <label htmlFor="filter-severity">Filter by Severity:</label>
            <select
              id="filter-severity"
              className="form-control"
              style={{ width: "auto" }}
              value={selectedSeverity}
              onChange={(e) => onSeverityChange(e.target.value as Severity | "")}
            >
              <option value="">All Severities</option>
              <option value="Critical">Critical</option>
              <option value="Serious">Serious</option>
              <option value="Moderate">Moderate</option>
              <option value="Minor">Minor</option>
            </select>
          </div>
        </div>

        {(selectedStatus || selectedSeverity) && (
          <button
            type="button"
            className="btn btn-secondary btn-small"
            onClick={() => {
              onStatusChange("");
              onSeverityChange("");
            }}
          >
            Reset Filters
          </button>
        )}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="card" style={{ textAlign: "center", padding: "3rem 1rem" }} role="status">
          <p style={{ fontSize: "1.125rem", fontWeight: 600, margin: 0 }}>
            Loading accessibility issues...
          </p>
        </div>
      )}

      {/* Error State */}
      {!isLoading && error && (
        <div className="card" style={{ border: "2px solid var(--color-danger-border)", backgroundColor: "var(--color-danger-bg)" }}>
          <h3 style={{ color: "#7f1d1d", margin: "0 0 0.5rem 0" }}>Failed to load issues</h3>
          <p style={{ color: "#7f1d1d", margin: "0 0 1rem 0" }}>{error}</p>
          <button type="button" className="btn btn-secondary" onClick={onRetry}>
            Try Again
          </button>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && issues.length === 0 && (
        <div className="card" style={{ textAlign: "center", padding: "3rem 1.5rem" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }} aria-hidden="true">
            📋
          </div>
          <h3 style={{ margin: "0 0 0.5rem 0", fontSize: "1.25rem" }}>No issues found</h3>
          <p style={{ color: "var(--color-text-muted)", maxWidth: "450px", margin: "0 auto 1.5rem auto" }}>
            {selectedStatus || selectedSeverity
              ? "No accessibility issues match your active filter criteria. Try resetting your filters."
              : "You have not recorded any accessibility issues under this account yet. Click below to record your first finding."}
          </p>
          {selectedStatus || selectedSeverity ? (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                onStatusChange("");
                onSeverityChange("");
              }}
            >
              Clear Active Filters
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-primary"
              onClick={onCreateClick}
            >
              + Log New Issue
            </button>
          )}
        </div>
      )}

      {/* Issue Table */}
      {!isLoading && !error && issues.length > 0 && (
        <div className="table-responsive">
          <table className="issue-table">
            <caption className="sr-only">
              List of accessibility issues logged by current user
            </caption>
            <thead>
              <tr>
                <th scope="col" style={{ width: "35%" }}>Title &amp; Criterion</th>
                <th scope="col">Page URL</th>
                <th scope="col">Severity</th>
                <th scope="col">Status</th>
                <th scope="col">Last Updated</th>
                <th scope="col" style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {issues.map((issue) => (
                <tr key={issue.id}>
                  <th scope="row" style={{ fontWeight: "normal", textAlign: "left" }}>
                    <button
                      type="button"
                      onClick={() => onSelectIssue(issue.id)}
                      style={{
                        background: "none",
                        border: "none",
                        padding: 0,
                        color: "var(--color-primary)",
                        fontWeight: 700,
                        fontSize: "1rem",
                        textAlign: "left",
                        cursor: "pointer",
                        textDecoration: "underline",
                      }}
                    >
                      {issue.title}
                    </button>
                    {issue.wcag_criterion && (
                      <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", marginTop: "0.25rem" }}>
                        WCAG: <strong>{issue.wcag_criterion}</strong>
                      </div>
                    )}
                  </th>
                  <td>
                    <a
                      href={issue.page_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        color: "var(--color-primary)",
                        fontSize: "0.875rem",
                        wordBreak: "break-all",
                        textDecoration: "underline",
                      }}
                      title={`Open ${issue.page_url} in a new tab`}
                    >
                      {issue.page_url.replace(/^https?:\/\//i, "")}
                      <span className="sr-only"> (opens in new tab)</span>
                    </a>
                  </td>
                  <td>
                    <span className={`badge ${getSeverityBadgeClass(issue.severity)}`}>
                      {issue.severity}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${getStatusBadgeClass(issue.status)}`}>
                      {issue.status}
                    </span>
                  </td>
                  <td style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", whiteSpace: "nowrap" }}>
                    {new Date(issue.updated_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </td>
                  <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-small"
                      onClick={() => onSelectIssue(issue.id)}
                      aria-label={`View details and history for issue #${issue.id}: ${issue.title}`}
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};
