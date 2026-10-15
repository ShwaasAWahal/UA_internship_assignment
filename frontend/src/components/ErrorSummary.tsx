import React, { useEffect, useRef } from "react";

export interface ErrorItem {
  field?: string;
  message: string;
}

interface ErrorSummaryProps {
  heading?: string;
  errors: ErrorItem[];
}

export const ErrorSummary: React.FC<ErrorSummaryProps> = ({
  heading = "There is a problem",
  errors,
}) => {
  const summaryRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (errors.length > 0 && summaryRef.current) {
      summaryRef.current.focus();
    }
  }, [errors]);

  if (errors.length === 0) {
    return null;
  }

  const handleLinkClick = (e: React.MouseEvent<HTMLAnchorElement>, fieldId?: string) => {
    if (!fieldId) return;
    e.preventDefault();
    const el = document.getElementById(fieldId);
    if (el) {
      el.focus();
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  return (
    <div
      ref={summaryRef}
      tabIndex={-1}
      role="alert"
      aria-labelledby="error-summary-title"
      className="error-summary"
    >
      <h2 id="error-summary-title">{heading}</h2>
      <ul>
        {errors.map((err, idx) => (
          <li key={idx}>
            {err.field ? (
              <a
                href={`#${err.field}`}
                onClick={(e) => handleLinkClick(e, err.field)}
              >
                {err.message}
              </a>
            ) : (
              <span>{err.message}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
};
