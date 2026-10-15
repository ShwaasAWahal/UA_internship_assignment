import React, { useCallback, useEffect, useState } from "react";
import { api, getStoredDemoUserId, setStoredDemoUserId } from "./api";
import { Announcement, LiveAnnouncer } from "./components/LiveAnnouncer";
import { Header } from "./components/Header";
import { IssueDetail } from "./components/IssueDetail";
import { IssueForm } from "./components/IssueForm";
import { IssueList } from "./components/IssueList";
import { SkipLink } from "./components/SkipLink";
import {
  Issue,
  IssueCreatePayload,
  IssueStatusUpdatePayload,
  IssueUpdatePayload,
  Severity,
  Status,
  User,
} from "./types";

type View = "list" | "create" | "detail" | "edit";

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [currentView, setCurrentView] = useState<View>("list");
  const [selectedIssueId, setSelectedIssueId] = useState<number | null>(null);
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);

  // Issues list state
  const [issues, setIssues] = useState<Issue[]>([]);
  const [totalIssues, setTotalIssues] = useState<number>(0);
  const [isListLoading, setIsListLoading] = useState<boolean>(true);
  const [listError, setListError] = useState<string | null>(null);

  // Filter state
  const [filterStatus, setFilterStatus] = useState<Status | "">("");
  const [filterSeverity, setFilterSeverity] = useState<Severity | "">("");

  // Form / Action loading state
  const [isFormSubmitting, setIsFormSubmitting] = useState<boolean>(false);
  const [isDetailLoading, setIsDetailLoading] = useState<boolean>(false);

  // Live region announcement state
  const [announcement, setAnnouncement] = useState<Announcement | null>(null);

  const announce = useCallback((message: string, type: "success" | "error" | "info" = "info") => {
    setAnnouncement({
      id: Date.now(),
      message,
      type,
    });
  }, []);

  // Fetch current user
  const loadUser = useCallback(async () => {
    try {
      const user = await api.getCurrentUser();
      setCurrentUser(user);
    } catch (err: unknown) {
      console.error("Failed to load user:", err);
      announce("Failed to verify user profile with server.", "error");
    }
  }, [announce]);

  // Fetch issues list
  const loadIssues = useCallback(async () => {
    setIsListLoading(true);
    setListError(null);
    try {
      const data = await api.getIssues({
        status: filterStatus || undefined,
        severity: filterSeverity || undefined,
        limit: 100,
        offset: 0,
      });
      setIssues(data.items);
      setTotalIssues(data.total);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load issues.";
      setListError(message);
    } finally {
      setIsListLoading(false);
    }
  }, [filterStatus, filterSeverity]);

  // Fetch single issue details
  const loadIssueDetail = useCallback(async (id: number) => {
    setIsDetailLoading(true);
    try {
      const issue = await api.getIssue(id);
      setSelectedIssue(issue);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : `Failed to load issue #${id}.`;
      announce(message, "error");
      setCurrentView("list");
    } finally {
      setIsDetailLoading(false);
    }
  }, [announce]);

  // Initial load
  useEffect(() => {
    loadUser();
  }, [loadUser]);

  useEffect(() => {
    loadIssues();
  }, [loadIssues]);

  // Load detail when selectedIssueId changes
  useEffect(() => {
    if (selectedIssueId !== null && (currentView === "detail" || currentView === "edit")) {
      loadIssueDetail(selectedIssueId);
    }
  }, [selectedIssueId, currentView, loadIssueDetail]);

  // Update dynamic document title
  useEffect(() => {
    let title = "Accessibility Issue Tracker";
    if (currentView === "create") {
      title = "Log New Issue — Accessibility Issue Tracker";
    } else if (currentView === "edit" && selectedIssue) {
      title = `Edit Issue #${selectedIssue.id}: ${selectedIssue.title} — Accessibility Issue Tracker`;
    } else if (currentView === "detail" && selectedIssue) {
      title = `Issue #${selectedIssue.id}: ${selectedIssue.title} — Accessibility Issue Tracker`;
    } else {
      title = "Issues List — Accessibility Issue Tracker";
    }
    document.title = title;
  }, [currentView, selectedIssue]);

  // Handle switching demo user
  const handleSelectUser = async (userId: string) => {
    setStoredDemoUserId(userId);
    setSelectedIssueId(null);
    setSelectedIssue(null);
    setCurrentView("list");

    try {
      const user = await api.getCurrentUser();
      setCurrentUser(user);
      announce(`Switched to demo user: ${user.display_name}`, "success");
      loadIssues();
    } catch (err: unknown) {
      announce("Failed to switch demo account.", "error");
    }
  };

  // Navigate helpers
  const handleNavigateHome = () => {
    setSelectedIssueId(null);
    setSelectedIssue(null);
    setCurrentView("list");
  };

  const handleSelectIssue = (id: number) => {
    setSelectedIssueId(id);
    setCurrentView("detail");
  };

  const handleCreateIssue = async (payload: IssueCreatePayload | IssueUpdatePayload) => {
    setIsFormSubmitting(true);
    try {
      const created = await api.createIssue(payload as IssueCreatePayload);
      announce(`Issue #${created.id} logged successfully!`, "success");
      setSelectedIssueId(created.id);
      setSelectedIssue(created);
      setCurrentView("detail");
      loadIssues();
    } finally {
      setIsFormSubmitting(false);
    }
  };

  const handleUpdateIssue = async (payload: IssueCreatePayload | IssueUpdatePayload) => {
    if (!selectedIssue) return;
    setIsFormSubmitting(true);
    try {
      const updated = await api.updateIssue(selectedIssue.id, payload as IssueUpdatePayload);
      setSelectedIssue(updated);
      announce(`Issue #${updated.id} updated successfully!`, "success");
      setCurrentView("detail");
      loadIssues();
    } finally {
      setIsFormSubmitting(false);
    }
  };

  const handleStatusUpdate = async (payload: IssueStatusUpdatePayload) => {
    if (!selectedIssue) return;
    const updated = await api.updateIssueStatus(selectedIssue.id, payload);
    setSelectedIssue(updated);
    announce(`Status changed to ${updated.status} successfully!`, "success");
    loadIssues();
  };

  return (
    <div className="site-container">
      <SkipLink />
      <LiveAnnouncer announcement={announcement} />

      <Header
        currentUser={currentUser}
        onSelectUser={handleSelectUser}
        onNavigateHome={handleNavigateHome}
        onCreateIssueClick={() => {
          setSelectedIssue(null);
          setSelectedIssueId(null);
          setCurrentView("create");
        }}
      />

      <main id="main-content" className="main-content" tabIndex={-1}>
        {/* Local Demo Notice Banner */}
        <div className="demo-banner" role="region" aria-label="Local demonstration mode notice">
          <div>
            <strong>Local Demo Environment:</strong> You are signed in as{" "}
            <strong>{currentUser ? currentUser.display_name : getStoredDemoUserId()}</strong>.
            All findings and status changes are isolated to your auditor account. Switch accounts in the
            navigation bar to simulate team handoffs.
          </div>
        </div>

        {/* View Router */}
        {currentView === "list" && (
          <IssueList
            issues={issues}
            total={totalIssues}
            isLoading={isListLoading}
            error={listError}
            selectedStatus={filterStatus}
            selectedSeverity={filterSeverity}
            onStatusChange={setFilterStatus}
            onSeverityChange={setFilterSeverity}
            onSelectIssue={handleSelectIssue}
            onCreateClick={() => {
              setSelectedIssue(null);
              setSelectedIssueId(null);
              setCurrentView("create");
            }}
            onRetry={loadIssues}
          />
        )}

        {currentView === "create" && (
          <IssueForm
            initialIssue={null}
            onSubmit={handleCreateIssue}
            onCancel={handleNavigateHome}
            isLoading={isFormSubmitting}
          />
        )}

        {currentView === "edit" && selectedIssue && (
          <IssueForm
            initialIssue={selectedIssue}
            onSubmit={handleUpdateIssue}
            onCancel={() => setCurrentView("detail")}
            isLoading={isFormSubmitting}
          />
        )}

        {currentView === "detail" && selectedIssue && (
          <IssueDetail
            issue={selectedIssue}
            isLoading={isDetailLoading}
            onEditClick={() => setCurrentView("edit")}
            onBackClick={handleNavigateHome}
            onStatusUpdate={handleStatusUpdate}
            onRefresh={() => loadIssueDetail(selectedIssue.id)}
          />
        )}
      </main>

      <footer className="site-footer" role="contentinfo">
        <p style={{ margin: 0 }}>
          <strong>Unified Accessibility Issue Tracker</strong> &bull; Accessible audit logging system (WCAG 2.2 AA compliant).
        </p>
        <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
          Built for the Unified Accessibility Full-Stack Take-Home Assignment. Designed with semantic HTML, native keyboard focus controls, and high-contrast color schemes.
        </p>
      </footer>
    </div>
  );
};

export default App;
