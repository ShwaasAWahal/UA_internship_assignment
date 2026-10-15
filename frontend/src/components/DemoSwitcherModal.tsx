import React, { useEffect, useRef } from "react";
import { User } from "../types";

interface DemoSwitcherModalProps {
  isOpen: boolean;
  currentUser: User | null;
  onClose: () => void;
  onSelectUser: (userId: string) => void;
}

export const DEMO_ACCOUNTS = [
  {
    id: "demo-user-alice",
    name: "Alice Chen",
    role: "Accessibility Auditor",
    email: "alice@example.com",
    description: "Primary auditor account with seeded accessibility issues.",
  },
  {
    id: "demo-user-bob",
    name: "Bob Martinez",
    role: "Accessibility Auditor",
    email: "bob@example.com",
    description: "Colleague auditor account for testing multi-user isolation.",
  },
];

export const DemoSwitcherModal: React.FC<DemoSwitcherModalProps> = ({
  isOpen,
  currentUser,
  onClose,
  onSelectUser,
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const previousActiveElementRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      previousActiveElementRef.current = document.activeElement as HTMLElement | null;

      // Small delay to ensure modal DOM is mounted before focusing
      const focusTimer = setTimeout(() => {
        closeButtonRef.current?.focus();
      }, 20);

      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          e.preventDefault();
          onClose();
          return;
        }

        if (e.key === "Tab" && modalRef.current) {
          const focusable = modalRef.current.querySelectorAll<HTMLElement>(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
          );
          if (focusable.length === 0) return;

          const firstEl = focusable[0];
          const lastEl = focusable[focusable.length - 1];

          if (e.shiftKey && document.activeElement === firstEl) {
            e.preventDefault();
            lastEl.focus();
          } else if (!e.shiftKey && document.activeElement === lastEl) {
            e.preventDefault();
            firstEl.focus();
          }
        }
      };

      document.addEventListener("keydown", handleKeyDown);
      return () => {
        clearTimeout(focusTimer);
        document.removeEventListener("keydown", handleKeyDown);
        // Restore focus to element that triggered the modal
        if (previousActiveElementRef.current && typeof previousActiveElementRef.current.focus === "function") {
          previousActiveElementRef.current.focus();
        } else {
          document.getElementById("switch-user-btn")?.focus();
        }
      };
    }
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="demo-switcher-title"
        aria-describedby="demo-switcher-desc"
        className="modal-box"
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h2 id="demo-switcher-title" style={{ margin: 0, fontSize: "1.25rem" }}>
            Select Demo Account
          </h2>
          <button
            ref={closeButtonRef}
            type="button"
            className="btn btn-secondary btn-small"
            onClick={onClose}
            aria-label="Close demo account switcher dialog"
          >
            ✕ Close
          </button>
        </div>

        <div className="demo-banner" style={{ marginBottom: "1rem" }}>
          <div>
            <strong>Notice: Demonstration Environment Only.</strong>
            <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.875rem" }}>
              This application is configured with local demo identities for testing.
              The backend verifies requests using an identity header. This is not
              a production security mechanism.
            </p>
          </div>
        </div>

        <p id="demo-switcher-desc" style={{ fontSize: "0.9375rem", marginBottom: "1rem" }}>
          Choose an auditor profile to view and manage their personal accessibility findings:
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {DEMO_ACCOUNTS.map((acc) => {
            const isCurrent = currentUser?.id === acc.id;
            return (
              <div
                key={acc.id}
                style={{
                  border: isCurrent ? "2px solid var(--color-primary)" : "1px solid var(--color-border-subtle)",
                  borderRadius: "var(--border-radius)",
                  padding: "0.75rem 1rem",
                  backgroundColor: isCurrent ? "#f0f7ff" : "var(--color-surface)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, fontSize: "1rem" }}>
                    {acc.name}{" "}
                    {isCurrent && (
                      <span className="badge badge-status-resolved" style={{ marginLeft: "0.5rem" }}>
                        Active Profile
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                    {acc.role} &bull; {acc.email}
                  </div>
                  <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", marginTop: "0.25rem" }}>
                    {acc.description}
                  </div>
                </div>

                <button
                  type="button"
                  className={isCurrent ? "btn btn-secondary btn-small" : "btn btn-primary btn-small"}
                  onClick={() => {
                    onSelectUser(acc.id);
                    onClose();
                  }}
                  disabled={isCurrent}
                  aria-label={isCurrent ? `${acc.name} is currently selected` : `Switch to ${acc.name}`}
                >
                  {isCurrent ? "Selected" : "Switch"}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
