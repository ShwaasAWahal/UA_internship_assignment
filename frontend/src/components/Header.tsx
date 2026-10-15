import React, { useState } from "react";
import { User } from "../types";
import { DemoSwitcherModal } from "./DemoSwitcherModal";

interface HeaderProps {
  currentUser: User | null;
  onSelectUser: (userId: string) => void;
  onNavigateHome: () => void;
  onCreateIssueClick: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentUser,
  onSelectUser,
  onNavigateHome,
  onCreateIssueClick,
}) => {
  const [isSwitcherOpen, setIsSwitcherOpen] = useState(false);

  return (
    <>
      <header className="site-header" role="banner">
        <div className="header-inner">
          <div className="header-brand">
            <button
              type="button"
              onClick={onNavigateHome}
              style={{
                background: "none",
                border: "none",
                padding: 0,
                font: "inherit",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                color: "inherit",
                textAlign: "left",
              }}
              aria-label="Unified Accessibility Issue Tracker Home"
            >
              <span aria-hidden="true" style={{ fontSize: "1.5rem" }}>
                ♿
              </span>
              <span className="header-title" style={{ fontSize: "1.25rem", fontWeight: 700 }}>
                Accessibility Issue Tracker
              </span>
            </button>
          </div>

          <nav className="header-nav" aria-label="User and actions navigation">
            <div className="user-badge" aria-label={`Current demo user: ${currentUser?.display_name || "Loading..."}`}>
              <span aria-hidden="true">👤</span>
              <span>
                <strong>{currentUser ? currentUser.display_name : "Loading profile..."}</strong>
                {currentUser && (
                  <span style={{ color: "var(--color-text-muted)", marginLeft: "0.25rem", fontSize: "0.8125rem" }}>
                    ({currentUser.role})
                  </span>
                )}
              </span>
            </div>

            <button
              id="switch-user-btn"
              type="button"
              className="btn btn-secondary btn-small"
              onClick={() => setIsSwitcherOpen(true)}
              aria-haspopup="dialog"
              aria-expanded={isSwitcherOpen}
            >
              Switch User
            </button>

            <button
              type="button"
              className="btn btn-primary btn-small"
              onClick={onCreateIssueClick}
            >
              + Log New Issue
            </button>
          </nav>
        </div>
      </header>

      <DemoSwitcherModal
        isOpen={isSwitcherOpen}
        currentUser={currentUser}
        onClose={() => setIsSwitcherOpen(false)}
        onSelectUser={onSelectUser}
      />
    </>
  );
};
