# Unified Accessibility Issue Tracker

An accessible, responsive web application for audit team members to record, edit, track, and remediate web accessibility issues according to WCAG 2.2 Level AA guidelines.

Built for the **Unified Accessibility Full-Stack Intern Take-Home Assignment**.

---

## Table of Contents

- [Overview & Key Features](#overview--key-features)
- [Technology Stack](#technology-stack)
- [Architecture & Design Principles](#architecture--design-principles)
- [Demo Sign-In Mechanism](#demo-sign-in-mechanism)
- [Project Structure](#project-structure)
- [Quick Start & Setup Instructions](#quick-start--setup-instructions)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [Running Automated Tests](#running-automated-tests)
- [API Reference](#api-reference)
- [Status Workflow & Concurrency](#status-workflow--concurrency)
- [Accessibility Compliance](#accessibility-compliance)
- [AI Tooling Disclosure](#ai-tooling-disclosure)

---

## Overview & Key Features

1. **Accessibility Finding Management**: Audit team members can create, view, edit, and filter web accessibility findings with required title, HTTP/HTTPS page URL, WCAG success criteria, severity, and remediation notes.
2. **Predictable Demo Accounts**: Includes two seeded auditor profiles (`Alice Chen` and `Bob Martinez`) with a demonstration switch mechanism to test multi-user isolation and ownership checks.
3. **Audit Status Lifecycle & History**: Strict status workflow (`Open`, `In Progress`, `Resolved`) with an append-only timeline tracking the actor, timestamp, previous status, new status, and remediation comments.
4. **Server-Side Security & Invariants**: Enforces server-side input validation, ownership scoping (users only see and edit their own findings), SQLite CHECK constraints, and atomic transactional database writes.
5. **Optimistic Concurrency Control**: Prevents silent overwrite conflicts during collaborative edits via an integer `version` field (rejecting stale updates with HTTP `409 Conflict`).
6. **WCAG 2.2 AA First Design**: Semantic HTML5 landmarks, visible focus outlines (>= 3:1 contrast), skip link, high-contrast text (>= 4.5:1), screen reader live announcements (`aria-live="polite"`), GDS-style error summaries, and full responsiveness down to 320px width and 200% text zoom.

---

## Technology Stack

| Tier | Technologies |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, Plain Semantic CSS (Zero heavy UI libraries) |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0 (ORM), SQLite |
| **Testing** | pytest, FastAPI TestClient (httpx), isolated in-memory test databases |
| **Tooling** | npm, Python venv, Uvicorn |

---

## Architecture & Design Principles

The project strictly follows the architecture documented in [`ARCHITECTURE.md`](ARCHITECTURE.md):
- **Local vs Production**: While the local application uses SQLite and a header-based demo identity for local evaluation, the architecture design accounts for PostgreSQL, OIDC/SSO authentication, team-based multitenancy, and scalable worker queues.
- **Defense in Depth**: Invariants are enforced at three layers:
  1. Frontend: Helpful early validation and accessible error summaries.
  2. API Layer: Pydantic schemas, URL protocol checks, workflow validation, and ownership verification.
  3. Database: Foreign keys (`PRAGMA foreign_keys = ON`), `NOT NULL` constraints, and SQLite `CheckConstraint` definitions.
- **Safe Database Migrations**: Includes a non-destructive SQLite table rebuild engine (`backend/app/migration.py`) that introspects database schema constraints and upgrades tables while preserving all existing data and foreign key relationships.

---

## Demo Sign-In Mechanism

> **Important Demonstration Notice**: The sign-in mechanism is provided strictly for local evaluation and testing of user isolation. It is **not** a production authentication system.

- Two demo users are seeded predictably on startup:
  - **Alice Chen** (`demo-user-alice`) — `alice@example.com` (Accessibility Auditor)
  - **Bob Martinez** (`demo-user-bob`) — `bob@example.com` (Accessibility Auditor)
- The frontend stores the selected user ID in `localStorage` under `ua_demo_user_id` (defaulting to `demo-user-alice`).
- Every API request transmits the identity via the custom request header:
  ```http
  X-Demo-User-Id: demo-user-alice
  ```
- The backend verifies this identity against an explicit whitelist of known demo users. Requests without this header or with an unrecognized user ID return `401 Unauthorized`.
- Clients are forbidden from supplying arbitrary owner IDs in request bodies; ownership is always resolved server-side from the verified demo identity.

---

## Project Structure

```text
UA_internship_assignment/
├── ARCHITECTURE.md                  # Comprehensive system architecture & production roadmap
├── ACCESSIBILITY.md                 # Detailed WCAG 2.2 AA accessibility audit & design notes
├── README.md                        # Project documentation (this file)
├── docs/                            # Architecture and ER diagrams
│   ├── architecture.png
│   ├── er-diagram.png
│   └── status-workflow.png
├── backend/
│   ├── requirements.txt             # Python dependencies
│   ├── pytest.ini                  # Pytest configuration
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app factory & lifespan initialization
│   │   ├── config.py                # Environment-configurable database URL & settings
│   │   ├── database.py              # SQLAlchemy engine, session maker, demo user seeding
│   │   ├── models.py                # User, Issue, IssueStatusHistory models with CheckConstraints
│   │   ├── schemas.py               # Pydantic validation schemas and error envelopes
│   │   ├── auth.py                  # Demo identity resolver dependency
│   │   ├── crud.py                  # Data access queries and pagination logic
│   │   ├── workflow.py              # Issue status transition rules & validation
│   │   ├── migration.py             # Non-destructive SQLite schema migration & rebuild
│   │   └── routers/
│   │       ├── health.py            # Sanitized health check endpoint
│   │       ├── users.py             # /api/me and /api/users/demo
│   │       └── issues.py            # Issue CRUD & status management endpoints
│   └── tests/
│       ├── conftest.py              # Isolated test fixtures and engine setup
│       ├── test_foundation.py       # Persistence, FKs, and seeding tests
│       ├── test_issues_api.py       # API CRUD, validation, permissions, and workflow tests
│       └── test_codex_findings.py   # Regression tests for health masking, CHECK constraints, migrations
└── frontend/
    ├── package.json                 # Frontend dependencies and scripts
    ├── vite.config.ts               # Vite bundler configuration with backend proxy
    ├── tsconfig.json                # TypeScript strict configuration
    ├── index.html                   # HTML entry point with skip link anchor
    └── src/
        ├── main.tsx                 # React DOM root render
        ├── App.tsx                  # View routing, demo identity state, live announcements
        ├── types.ts                 # Domain models, API payload types, ApiClientError
        ├── api.ts                   # Typed HTTP client sending X-Demo-User-Id
        ├── styles.css               # WCAG 2.2 AA compliant design system & responsive styling
        └── components/
            ├── SkipLink.tsx         # Keyboard bypass block link
            ├── LiveAnnouncer.tsx    # Persistent aria-live polite region & toast feedback
            ├── Header.tsx           # Semantic header, user badge, modal triggers
            ├── DemoSwitcherModal.tsx # Accessible dialog to switch demo auditor accounts
            ├── ErrorSummary.tsx     # GDS-style error summary with keyboard anchor jumps
            ├── IssueList.tsx        # Filterable semantic table with badges & actions
            ├── IssueForm.tsx        # Accessible create/edit form with field validation
            └── IssueDetail.tsx      # Detail inspection, status controls, and history timeline
```

---

## Quick Start & Setup Instructions

### Prerequisites
- **Python**: Version 3.10+ (tested with Python 3.12)
- **Node.js**: Version 18+ (tested with Node.js 22 LTS)

### Backend Setup

1. Open a terminal and navigate to the `backend/` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
     .\.venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the backend development server:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   The backend will initialize the SQLite database (`issues.db`), seed the two demo users, and serve the API at `http://127.0.0.1:8000`.
   - Health check: `http://127.0.0.1:8000/health`
   - Interactive OpenAPI docs: `http://127.0.0.1:8000/docs`

### Frontend Setup

1. Open a second terminal and navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```

2. Install frontend dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   Vite will serve the frontend at `http://localhost:5173`. API requests to `/api` and `/health` are automatically proxied to the backend on `http://127.0.0.1:8000`.

4. Open `http://localhost:5173` in your browser.

---

## Running Automated Tests

### Backend Test Suite
The backend includes a comprehensive automated test suite covering model persistence, foreign keys, demo identity validation, API validation, status workflow transitions, optimistic concurrency conflicts, SQLite table migrations, and error sanitization.

To execute the complete test suite:
```bash
# From the repository root (or backend directory)
backend\.venv\Scripts\pytest -v backend/tests
```
Expected output:
```text
============================= 28 passed in 1.57s ==============================
```

> **Test Database Isolation**: Tests run against a dedicated in-memory or temporary SQLite database (`sqlite:///:memory:`) using isolated test fixtures. Running tests will never overwrite or mutate the application's runtime `issues.db`.

### Frontend Build Verification
To verify TypeScript compilation and asset bundling:
```bash
cd frontend
npm run build
```
Output:
```text
✓ 37 modules transformed.
✓ built in 1.36s
```

---

## API Reference

All requests must include the header `X-Demo-User-Id: demo-user-alice` (or `demo-user-bob`).

### 1. User Endpoints
- `GET /api/me`: Returns the current authenticated demo user profile.
- `GET /api/users/demo`: Returns the list of predictable demo auditor accounts.

### 2. Issue Endpoints
- `GET /api/issues`: List issues owned by the current user.
  - Query parameters:
    - `status`: Optional filter (`Open`, `In Progress`, `Resolved`).
    - `severity`: Optional filter (`Minor`, `Moderate`, `Serious`, `Critical`).
    - `limit`: Bounded page size (1 to 100, default 20).
    - `offset`: Pagination offset (default 0).
- `POST /api/issues`: Create an issue. Status defaults to `Open`.
  - Body: `{ "title": "...", "page_url": "https://...", "severity": "Serious", "wcag_criterion": "...", "description": "..." }`
- `GET /api/issues/{id}`: Retrieve issue details and complete status history timeline.
- `PATCH /api/issues/{id}`: Edit permitted fields (`title`, `description`, `page_url`, `wcag_criterion`, `severity`). Requires `version`. (Directly modifying `status` or `owner_id` is forbidden).
- `PATCH /api/issues/{id}/status`: Transition status.
  - Body: `{ "status": "In Progress", "version": 1, "comment": "Optional note" }`

### Standard Error Envelope
All error responses return a standardized JSON structure:
```json
{
  "error": {
    "code": "INVALID_STATUS_TRANSITION",
    "message": "Direct transition from 'Resolved' to 'In Progress' is disallowed. Reopen to 'Open' first.",
    "fields": {
      "status": "Target status 'In Progress' is not permitted from current status 'Resolved'."
    }
  }
}
```

---

## Status Workflow & Concurrency

### Workflow Matrix
The application enforces an explicit audit remediation workflow:
```text
  [ Open ] <-------------------+
     │   ^                     │
     │   │                     │
     v   │                     │
[ In Progress ] --------> [ Resolved ]
```
- `Open` ➔ `In Progress` or `Resolved`
- `In Progress` ➔ `Open` or `Resolved`
- `Resolved` ➔ `Open` (Reopen)
- `Resolved` ➔ `In Progress` is **blocked**; issues must be reopened to `Open` first.

### Optimistic Concurrency Control
Every `Issue` entity includes an integer `version` property initialized to `1`.
When updating an issue or changing its status, the client must submit the current `version`. The update is committed in an atomic database transaction only if the database version matches the submitted version:
- On match: Changes are saved, `version` is incremented by 1, and `updated_at` is refreshed.
- On mismatch: The server aborts the transaction and returns HTTP `409 Conflict` with code `CONCURRENCY_CONFLICT`. The frontend notifies the user and provides a one-click reload button to inspect the latest state.

---

## Accessibility Compliance

The frontend was constructed with an accessibility-first methodology, meeting **WCAG 2.2 Level AA**:
- **Contrast**: Text elements maintain >= 4.5:1 contrast against backgrounds (body text is #0f172a on white, 15.6:1). All UI controls and borders exceed 3:1.
- **Focus Indicators**: Unambiguous 3px solid high-contrast focus outlines with offset on all interactive elements.
- **Bypass Blocks**: Top-level skip link jumping directly to `<main id="main-content">`.
- **Screen Reader Announcements**: Success and status notifications post to a persistent `aria-live="polite"` region without stealing keyboard focus.
- **Error Handling**: UK GDS-style `<ErrorSummary>` with programmatic focus management and anchor links jumping directly to offending form inputs.
- **Responsive & Zoom**: Fully responsive down to 320px viewport width and supports 200% browser text scaling without horizontal clipping.

For in-depth analysis, keyboard navigation flows, and audit matrices, refer to [`ACCESSIBILITY.md`](ACCESSIBILITY.md).

---

## AI Tooling Disclosure

In accordance with the Unified Accessibility take-home assignment instructions regarding transparency in tooling:
- **Tooling Used**: Google Antigravity (AI pair programming assistant powered by Gemini).
- **Scope of AI Assistance**:
  - Accelerated initial boilerplate scaffolding of FastAPI routes, Pydantic schemas, and SQLAlchemy models.
  - Formulated comprehensive test cases covering edge cases, SQLite table migration, and concurrency conflicts.
  - Assisted with WCAG 2.2 AA accessibility token design, semantic HTML review, and GDS error-summary patterns.
- **Engineering Review**: All architecture decisions, database constraints, concurrency strategies, migration code, and security invariants were verified, refined, and tested by the engineer.
