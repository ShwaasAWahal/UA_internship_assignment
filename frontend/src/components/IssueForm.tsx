import React, { useState } from "react";
import { ApiClientError, Issue, IssueCreatePayload, IssueUpdatePayload, Severity } from "../types";
import { ErrorItem, ErrorSummary } from "./ErrorSummary";

interface IssueFormProps {
  initialIssue?: Issue | null;
  onSubmit: (payload: IssueCreatePayload | IssueUpdatePayload) => Promise<void>;
  onCancel: () => void;
  isLoading: boolean;
}

const COMMON_WCAG_CRITERIA = [
  "1.1.1 Non-text Content (Level A)",
  "1.3.1 Info and Relationships (Level A)",
  "1.4.1 Use of Color (Level A)",
  "1.4.3 Contrast (Minimum) (Level AA)",
  "1.4.11 Non-text Contrast (Level AA)",
  "2.1.1 Keyboard (Level A)",
  "2.1.2 No Keyboard Trap (Level A)",
  "2.4.1 Bypass Blocks (Level A)",
  "2.4.3 Focus Order (Level A)",
  "2.4.7 Focus Visible (Level AA)",
  "3.3.1 Error Identification (Level A)",
  "3.3.2 Labels or Instructions (Level A)",
  "4.1.2 Name, Role, Value (Level A)",
];

export const IssueForm: React.FC<IssueFormProps> = ({
  initialIssue,
  onSubmit,
  onCancel,
  isLoading,
}) => {
  const isEditing = Boolean(initialIssue);

  const [title, setTitle] = useState(initialIssue?.title || "");
  const [description, setDescription] = useState(initialIssue?.description || "");
  const [pageUrl, setPageUrl] = useState(initialIssue?.page_url || "");
  const [wcagCriterion, setWcagCriterion] = useState(initialIssue?.wcag_criterion || "");
  const [severity, setSeverity] = useState<Severity>(initialIssue?.severity || "Moderate");

  const [errors, setErrors] = useState<ErrorItem[]>([]);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [conflictError, setConflictError] = useState<string | null>(null);

  const validate = (): boolean => {
    const newFieldErrors: Record<string, string> = {};
    const newErrors: ErrorItem[] = [];

    if (!title.trim()) {
      const msg = "Title is required and cannot be blank.";
      newFieldErrors.title = msg;
      newErrors.push({ field: "title", message: msg });
    }

    if (!pageUrl.trim()) {
      const msg = "Page URL is required.";
      newFieldErrors.page_url = msg;
      newErrors.push({ field: "page_url", message: msg });
    } else {
      try {
        const parsed = new URL(pageUrl.trim());
        if (!["http:", "https:"].includes(parsed.protocol)) {
          const msg = "Page URL must use HTTP or HTTPS protocol (e.g. https://example.com).";
          newFieldErrors.page_url = msg;
          newErrors.push({ field: "page_url", message: msg });
        }
      } catch {
        const msg = "Please enter a valid page URL (e.g. https://example.com/page).";
        newFieldErrors.page_url = msg;
        newErrors.push({ field: "page_url", message: msg });
      }
    }

    if (!["Minor", "Moderate", "Serious", "Critical"].includes(severity)) {
      const msg = "Severity must be Minor, Moderate, Serious, or Critical.";
      newFieldErrors.severity = msg;
      newErrors.push({ field: "severity", message: msg });
    }

    setFieldErrors(newFieldErrors);
    setErrors(newErrors);
    return newErrors.length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setConflictError(null);

    if (!validate()) {
      return;
    }

    try {
      if (isEditing && initialIssue) {
        const updatePayload: IssueUpdatePayload = {
          title: title.trim(),
          description: description.trim() || null,
          page_url: pageUrl.trim(),
          wcag_criterion: wcagCriterion.trim() || null,
          severity,
          version: initialIssue.version,
        };
        await onSubmit(updatePayload);
      } else {
        const createPayload: IssueCreatePayload = {
          title: title.trim(),
          description: description.trim() || null,
          page_url: pageUrl.trim(),
          wcag_criterion: wcagCriterion.trim() || null,
          severity,
        };
        await onSubmit(createPayload);
      }
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        if (err.statusCode === 409) {
          setConflictError(
            "This issue was modified by another request or session. Please reload the latest issue details to avoid overwriting changes."
          );
          setErrors([
            {
              message:
                "Concurrency Conflict: The issue version is outdated. Please refresh to load the latest record.",
            },
          ]);
        } else if (err.fields) {
          const apiFieldErrors: Record<string, string> = {};
          const apiErrors: ErrorItem[] = [];
          Object.entries(err.fields).forEach(([field, msg]) => {
            apiFieldErrors[field] = msg;
            apiErrors.push({ field, message: msg });
          });
          setFieldErrors(apiFieldErrors);
          setErrors(apiErrors);
        } else {
          setErrors([{ message: err.message }]);
        }
      } else if (err instanceof Error) {
        setErrors([{ message: err.message }]);
      } else {
        setErrors([{ message: "An unexpected error occurred while saving the issue." }]);
      }
    }
  };

  return (
    <div className="card" style={{ maxWidth: "750px", margin: "0 auto" }}>
      <div className="card-header">
        <h1 id="form-heading" style={{ margin: 0, fontSize: "1.5rem" }}>
          {isEditing ? `Edit Issue #${initialIssue?.id}` : "Log New Accessibility Issue"}
        </h1>
        {isEditing && initialIssue && (
          <span className="badge badge-status-open">
            Version {initialIssue.version}
          </span>
        )}
      </div>

      <ErrorSummary errors={errors} heading="Please correct the following errors:" />

      {conflictError && (
        <div className="demo-banner" style={{ borderColor: "var(--color-danger-border)", backgroundColor: "var(--color-danger-bg)" }}>
          <strong style={{ color: "#7f1d1d" }}>Concurrency Conflict:</strong>
          <span style={{ color: "#7f1d1d", marginLeft: "0.5rem" }}>{conflictError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate aria-labelledby="form-heading">
        {/* Title */}
        <div className="form-group">
          <label htmlFor="title" className="form-label">
            Issue Title <span className="required-indicator">(required)</span>
          </label>
          <input
            id="title"
            name="title"
            type="text"
            className="form-control"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            aria-required="true"
            aria-invalid={Boolean(fieldErrors.title)}
            aria-describedby={fieldErrors.title ? "title-error title-hint" : "title-hint"}
            placeholder="e.g. Main navigation toggle lacks accessible name"
          />
          <div id="title-hint" className="form-hint">
            Provide a concise, descriptive summary of the accessibility failure.
          </div>
          {fieldErrors.title && (
            <div id="title-error" className="form-error" role="alert">
              <span aria-hidden="true">⚠️</span> {fieldErrors.title}
            </div>
          )}
        </div>

        {/* Page URL */}
        <div className="form-group">
          <label htmlFor="page_url" className="form-label">
            Page URL <span className="required-indicator">(required)</span>
          </label>
          <input
            id="page_url"
            name="page_url"
            type="url"
            className="form-control"
            value={pageUrl}
            onChange={(e) => setPageUrl(e.target.value)}
            aria-required="true"
            aria-invalid={Boolean(fieldErrors.page_url)}
            aria-describedby={
              fieldErrors.page_url
                ? "page_url-error page_url-hint"
                : "page_url-hint"
            }
            placeholder="https://example.com/checkout"
          />
          <div id="page_url-hint" className="form-hint">
            Must be a valid HTTP or HTTPS web address where the issue was observed.
          </div>
          {fieldErrors.page_url && (
            <div id="page_url-error" className="form-error" role="alert">
              <span aria-hidden="true">⚠️</span> {fieldErrors.page_url}
            </div>
          )}
        </div>

        {/* WCAG Criterion */}
        <div className="form-group">
          <label htmlFor="wcag_criterion" className="form-label">
            WCAG Criterion <span style={{ fontWeight: 400, color: "var(--color-text-muted)" }}>(Optional)</span>
          </label>
          <input
            id="wcag_criterion"
            name="wcag_criterion"
            type="text"
            list="wcag-suggestions"
            className="form-control"
            value={wcagCriterion}
            onChange={(e) => setWcagCriterion(e.target.value)}
            aria-describedby="wcag_criterion-hint"
            placeholder="e.g. 1.4.3 Contrast (Minimum)"
          />
          <datalist id="wcag-suggestions">
            {COMMON_WCAG_CRITERIA.map((criterion) => (
              <option key={criterion} value={criterion} />
            ))}
          </datalist>
          <div id="wcag_criterion-hint" className="form-hint">
            Select or type the relevant WCAG 2.1 / 2.2 Success Criterion.
          </div>
        </div>

        {/* Severity */}
        <div className="form-group">
          <fieldset
            id="severity"
            tabIndex={-1}
            style={{ border: "none", padding: 0, margin: 0 }}
            aria-describedby={fieldErrors.severity ? "severity-error severity-hint" : "severity-hint"}
          >
            <legend className="form-label">
              Severity Level <span className="required-indicator">(required)</span>
            </legend>
            <div id="severity-hint" className="form-hint" style={{ marginBottom: "0.5rem" }}>
              Categorize the impact on assistive technology users.
            </div>
            {fieldErrors.severity && (
              <div id="severity-error" className="form-error" role="alert" style={{ marginBottom: "0.5rem" }}>
                <span aria-hidden="true">⚠️</span> {fieldErrors.severity}
              </div>
            )}
            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
              {(["Minor", "Moderate", "Serious", "Critical"] as Severity[]).map((level) => (
                <label
                  key={level}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.375rem",
                    cursor: "pointer",
                    padding: "0.375rem 0.625rem",
                    border: severity === level ? "2px solid var(--color-primary)" : "1px solid var(--color-border)",
                    borderRadius: "var(--border-radius)",
                    backgroundColor: severity === level ? "#f0f7ff" : "var(--color-surface)",
                    fontWeight: severity === level ? 700 : 500,
                  }}
                >
                  <input
                    type="radio"
                    name="severity"
                    id={`severity-${level.toLowerCase()}`}
                    value={level}
                    checked={severity === level}
                    onChange={() => setSeverity(level)}
                    aria-describedby="severity-hint"
                  />
                  <span>{level}</span>
                </label>
              ))}
            </div>
          </fieldset>
        </div>

        {/* Description */}
        <div className="form-group">
          <label htmlFor="description" className="form-label">
            Description and Remediation Notes <span style={{ fontWeight: 400, color: "var(--color-text-muted)" }}>(Optional)</span>
          </label>
          <textarea
            id="description"
            name="description"
            rows={5}
            className="form-control"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            aria-describedby="description-hint"
            placeholder="Detailed description of the issue, how to reproduce it, screen reader behavior, and suggested remediation..."
          />
          <div id="description-hint" className="form-hint">
            Include reproduction steps, impacted user groups, and recommended code fixes.
          </div>
        </div>

        {/* Form Actions */}
        <div className="form-actions" style={{ display: "flex", gap: "1rem", marginTop: "1.5rem", flexWrap: "wrap" }}>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={isLoading}
          >
            {isLoading ? "Saving Issue..." : isEditing ? "Save Changes" : "Create Issue"}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onCancel}
            disabled={isLoading}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};
