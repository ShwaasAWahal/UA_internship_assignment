# Accessibility Evaluation & Conformance Notes (Targeting WCAG 2.2 Level AA)

## 1. Executive Summary

An accessibility evaluation of the **Unified Accessibility Issue Tracker** frontend was conducted targeting **WCAG 2.2 Level AA** standards.

The evaluation used a layered approach:
1. **Automated Auditing on Static Fixtures**: Deque **`axe-core`** (v4.14.0) executed rules for `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`, and `best-practice` against representative static HTML fixtures of the four primary application views in a JSDOM environment (`npm run test:a11y`).
2. **Formulaic Color Contrast Verification**: Mathematical evaluation of foreground and background color tokens using WCAG 2.1 relative luminance formulas ($L_1, L_2$) for all text and UI component borders.
3. **Source Code & Semantic Inspection**: Code-level verification of semantic HTML markup, heading hierarchy, bypass links, form control labeling, error associations (`aria-describedby`, `aria-invalid`), modal focus management, and status announcement live regions.
4. **Interactive Keyboard Traversal**: Manual verification of focus order, visible focus rings, tab navigation, and modal dismissal (`Escape`) in a desktop browser.

### Key Audit Findings & Scope
- **Automated Fixture Audit**: Automated `axe-core` testing of the static fixtures reported **0 violations**. However, this result applies to static DOM representations and does **not** establish full WCAG 2.2 AA conformance for the live dynamic application.
- **Incomplete Checks & JSDOM Limitations**: The automated check reported **13 incomplete checks** across the four screens (e.g., color contrast rules where computed CSS background colors cannot be fully evaluated in headless JSDOM without a full browser layout engine, accompanied by a JSDOM canvas context warning). These incomplete checks require manual evaluation.
- **Remediated Issues**: Eight confirmed accessibility defects identified during code inspection and testing were remediated directly in source code (detailed in Section 4).

---

## 2. Audit Scope & Workflows Evaluated

The evaluation covered every primary screen and interactive user workflow:

1. **Top Navigation & Demo Account Switcher**:
   - Skip to main content bypass link.
   - Demo account banner and auditor badge.
   - Demo account switcher modal dialog (`role="dialog"`, `aria-modal="true"`).
2. **Issue List Screen**:
   - Filter toolbar (Status and Severity dropdowns, filter reset).
   - Empty, loading, and populated states.
   - Semantic data table (`<caption>`, `<th scope="col">`, `<th scope="row">`).
3. **Issue Creation & Editing Screen**:
   - Form field labeling, hint text, and visible required indicators.
   - UK GDS-style `<ErrorSummary>` box with focus placement and anchor jumping.
   - Inline field error rendering (`aria-invalid="true"`, `aria-describedby`).
   - Radio button group for Severity levels within `<fieldset>` and `<legend>`.
4. **Issue Detail & Remediation Screen**:
   - Issue metadata definition list (`<dl>`, `<dt>`, `<dd>`).
   - Status workflow transition form with validation.
   - Append-only chronological status change history timeline.
5. **Dynamic Feedback & Live Announcements**:
   - Asynchronous action notifications via persistent `role="status"` / `aria-live="polite"` region.

---

## 3. Evaluation Methodology & Tools Used

- **Automated Engine**: `axe-core` 4.14.0 executed within a Node.js / JSDOM harness (`npm run test:a11y`) evaluating representative static HTML fixtures.
  > **JSDOM Limitations**: JSDOM does not implement a layout or rendering engine, nor does it support `HTMLCanvasElement.getContext()`. As a result, certain visual checks (such as color contrast on layered backgrounds) cannot be fully resolved by automated tooling in JSDOM and are flagged as "incomplete" (13 across the suite). Automated fixture checks provide a valuable automated regression safeguard for HTML/ARIA semantics, but cannot replace live browser audits.
- **Contrast Calculations**: Formulaic relative luminance verification for all design palette tokens:
  $$\text{Contrast Ratio} = \frac{\max(L_1, L_2) + 0.05}{\min(L_1, L_2) + 0.05}$$
- **Keyboard Navigation Verification**: Desktop browser inspection verifying that interactive elements receive visible focus outlines, follow logical tab order, and support keyboard operation (`Tab`, `Shift+Tab`, `Enter`, `Space`, `Escape`).
- **Layout & Zoom Inspection**: Responsive layout verification in a desktop browser at 320px viewport width and 200% text zoom.

> **Screen Reader Disclosure**: Full end-to-end audio testing with native physical screen reader software (e.g. JAWS, NVDA on Windows; VoiceOver on macOS/iOS; TalkBack on Android) was not conducted. ARIA attributes, live regions (`role="status"`, `aria-live="polite"`), and accessible names were implemented and verified according to the W3C WAI-ARIA Authoring Practices Guide (APG), but full multi-platform assistive technology testing remains a requirement for formal production acceptance.

---

## 4. Confirmed Issues & Remediation Details

During the dedicated audit, 8 confirmed accessibility issues were identified and resolved:

### Finding 1: Invalid Nested `<h1>` inside Interactive `<button>` & Heading Hierarchy
- **Location**: [`frontend/src/components/Header.tsx`](frontend/src/components/Header.tsx)
- **WCAG SC**: 1.3.1 (Info and Relationships), 4.1.2 (Name, Role, Value)
- **Problem**: The brand title in the header wrapped an `<h1>` inside a `<button>`. Heading content inside button phrasing content is invalid HTML and causes screen readers to announce confusing interactive roles. In addition, having `<h1>` in the site header deprived the main content views of a unique, primary `<h1>`.
- **Fix**: Replaced `<h1 className="header-title">` inside the button with `<span className="header-title">`. Promoted the main view headings in `IssueList`, `IssueForm`, and `IssueDetail` to be the unique primary `<h1>` on each respective screen, followed by logical `<h2>` subheadings.

### Finding 2: Modal Dialog Focus Leaking & Missing Focus Restoration
- **Location**: [`frontend/src/components/DemoSwitcherModal.tsx`](frontend/src/components/DemoSwitcherModal.tsx)
- **WCAG SC**: 2.1.2 (No Keyboard Trap), 2.4.3 (Focus Order)
- **Problem**: Opening the demo user switcher dialog did not trap focus inside the modal. Pressing `Tab` allowed keyboard focus to escape onto background page elements. Furthermore, closing the modal did not return focus to the "Switch User" button.
- **Fix**: Implemented a bidirectional keyboard focus trap (wrapping `Tab` and `Shift+Tab` within the dialog's focusable elements). Stored `document.activeElement` prior to opening and restored focus to the trigger button upon dialog dismissal. Added `aria-describedby="demo-switcher-desc"` to the `role="dialog"` container.

### Finding 3: Skip Link Programmatic Focus Placement
- **Location**: [`frontend/src/components/SkipLink.tsx`](frontend/src/components/SkipLink.tsx)
- **WCAG SC**: 2.4.1 (Bypass Blocks)
- **Problem**: While `<a href="#main-content">` targeted `<main id="main-content" tabIndex={-1}>`, certain browser engines do not reliably move keyboard focus on hash navigation without an explicit script event.
- **Fix**: Added an `onClick` handler that calls `document.getElementById("main-content")?.focus()` and scrolls smoothly to the content container.

### Finding 4: Duplicate Announcements in Live Region
- **Location**: [`frontend/src/components/LiveAnnouncer.tsx`](frontend/src/components/LiveAnnouncer.tsx)
- **WCAG SC**: 4.1.3 (Status Messages)
- **Problem**: Both the visually hidden text `<span className="sr-only">` and the visual toast banner `<div className="live-toast">` were nested inside the same `aria-live="polite"` element. Screen readers would read the exact same status message twice in succession.
- **Fix**: Kept the `role="status"` `aria-live="polite"` region dedicated strictly to assistive technology text, and isolated the visual transient toast with `aria-hidden="true"`, eliminating duplicate speech.

### Finding 5: Severity Error Link Target in ErrorSummary
- **Location**: [`frontend/src/components/IssueForm.tsx`](frontend/src/components/IssueForm.tsx)
- **WCAG SC**: 3.3.1 (Error Identification), 2.4.3 (Focus Order)
- **Problem**: When a severity error occurred, the `<ErrorSummary>` rendered an anchor `<a href="#severity">`. However, individual radios were named `severity-minor`, etc., with no element matching `id="severity"`. Clicking the error link failed to navigate or move focus.
- **Fix**: Added `id="severity"` and `tabIndex={-1}` to the severity `<fieldset>`, linked it to `aria-describedby="severity-error"`, and rendered an inline error message with `role="alert"`.

### Finding 6: Missing Table Row Headers
- **Location**: [`frontend/src/components/IssueList.tsx`](frontend/src/components/IssueList.tsx)
- **WCAG SC**: 1.3.1 (Info and Relationships)
- **Problem**: In the issues table, the first column was rendered as a plain `<td>`. Screen reader users navigating horizontally across cells did not receive the issue title as row context.
- **Fix**: Changed the first cell of each table row to `<th scope="row" style={{ fontWeight: "normal", textAlign: "left" }}>`.

### Finding 7: Unambiguous Visible Required Field Indicators
- **Location**: [`frontend/src/components/IssueForm.tsx`](frontend/src/components/IssueForm.tsx) & [`frontend/src/components/IssueDetail.tsx`](frontend/src/components/IssueDetail.tsx)
- **WCAG SC**: 3.3.2 (Labels or Instructions)
- **Problem**: Required fields only used an asterisk `*` visually, with `(required)` hidden in `.sr-only`. Users unfamiliar with asterisks or with cognitive impairments could be uncertain about field requirements.
- **Fix**: Replaced isolated visual asterisks with explicit, visible `<span className="required-indicator">(required)</span>` text on all required field labels.

### Finding 8: Status Transition Form Error Association
- **Location**: [`frontend/src/components/IssueDetail.tsx`](frontend/src/components/IssueDetail.tsx)
- **WCAG SC**: 3.3.1 (Error Identification), 4.1.2 (Name, Role, Value)
- **Problem**: When submitting the status update form without choosing a next status, the `<select id="new-status">` did not receive `aria-invalid="true"` or `aria-describedby="new-status-error"`, and only the top summary showed the error.
- **Fix**: Added `statusFieldErrors` state, wired `aria-invalid` and `aria-describedby`, and rendered an inline `role="alert"` error message below the select.

---

## 5. Automated axe-core Audit Results (Static Fixtures)

The automated accessibility test script (`npm run test:a11y`) runs `axe-core` 4.14.0 against representative static HTML fixtures representing the four primary UI states.

```text
=================================================
  ACCESSIBILITY AUDIT WITH AXE-CORE (WCAG 2.2 AA)
=================================================

Not implemented: HTMLCanvasElement's getContext() method: without installing the canvas npm package

--- PAGE AUDIT: 1. Issues List Screen ---
Passed rules: 40
Incomplete checks: 5
Violations: 0

--- PAGE AUDIT: 2. Create Issue Form Screen ---
Passed rules: 34
Incomplete checks: 3
Violations: 0

--- PAGE AUDIT: 3. Issue Detail Screen ---
Passed rules: 38
Incomplete checks: 3
Violations: 0

--- PAGE AUDIT: 4. Demo Switcher Modal Dialog ---
Passed rules: 28
Incomplete checks: 2
Violations: 0

=================================================
TOTAL AXE VIOLATIONS ACROSS ALL SCREENS: 0
=================================================
```

### Analysis of Incomplete Checks & Scope Limitations
1. **Zero Violations on Fixtures**: The 0 violations confirm that the static fixtures contain no automated rule violations regarding semantic tags, ARIA attributes, form labels, or landmark structure.
2. **13 Incomplete Checks**: The 13 incomplete checks (5 on List, 3 on Form, 3 on Detail, 2 on Modal) primarily involve `color-contrast` where JSDOM cannot compute layout positioning or blended backgrounds. These were manually verified via formulaic color token evaluation (Section 6).
3. **Canvas Limitation Warning**: JSDOM does not provide a canvas 2D context by default, producing the harmless notice `Not implemented: HTMLCanvasElement's getContext() method`.
4. **Scope Limitation**: Zero violations on static fixtures does **not** prove full WCAG 2.2 Level AA compliance for the live React application, which involves dynamic state changes, client-side routing, and real-time user input.

---

## 6. Color Contrast Verification Ratios

All color combinations were verified using the WCAG relative luminance formula. Every pair surpasses the 4.5:1 text standard and 3.0:1 non-text standard:

| Element Description | Foreground | Background | Computed Ratio | Standard | Status |
|---|---|---|---|---|---|
| Primary Body Text | `#0f172a` | `#ffffff` | **17.85:1** | 4.5:1 | **PASS** |
| Muted Body Text | `#334155` | `#ffffff` | **10.35:1** | 4.5:1 | **PASS** |
| Primary Action Button | `#ffffff` | `#0052cc` | **6.82:1** | 4.5:1 | **PASS** |
| Form Border (Non-text) | `#64748b` | `#ffffff` | **4.76:1** | 3.0:1 | **PASS** |
| Focus Ring Indicator | `#003e9c` | `#ffffff` | **9.68:1** | 3.0:1 | **PASS** |
| Critical Severity Badge | `#991b1b` | `#fef2f2` | **7.60:1** | 4.5:1 | **PASS** |
| Serious Severity Badge | `#9a3412` | `#fff7ed` | **6.88:1** | 4.5:1 | **PASS** |
| Moderate Severity Badge | `#713f12` | `#fefce8` | **8.38:1** | 4.5:1 | **PASS** |
| Minor Severity Badge | `#334155` | `#f8fafc` | **9.90:1** | 4.5:1 | **PASS** |
| Status Open Badge | `#1e40af` | `#eff6ff` | **8.01:1** | 4.5:1 | **PASS** |
| Status In Progress Badge | `#854d0e` | `#fefce8` | **6.62:1** | 4.5:1 | **PASS** |
| Status Resolved Badge | `#166534` | `#f0fdf4` | **6.81:1** | 4.5:1 | **PASS** |
| Danger Alert Text | `#b91c1c` | `#ffffff` | **6.47:1** | 4.5:1 | **PASS** |
| Warning Notice Text | `#92400e` | `#fffbeb` | **6.84:1** | 4.5:1 | **PASS** |

---

## 7. Responsive Reflow & Zoom Verification (320px & 200% Zoom)

- **320px Viewport Width (SC 1.4.10)**:
  - Header items wrap cleanly with compact padding (`0.75rem 0.5rem`).
  - Table utilizes a designated `.table-responsive` container with smooth horizontal scrolling to avoid breaking parent page boundaries.
  - Form actions and inputs scale to 100% available width without clipping.
- **200% Browser Zoom**:
  - Tested with browser text scaling set to 200%. Typography uses relative units (`rem`, `%`), allowing clean text expansion without overlapping or truncation.

---

## 8. Remaining Limitations & Production Recommendations

1. **Test Environment Scope (Static Fixtures vs. Live App)**: The automated `axe-core` test runs against static JSDOM fixtures rather than a live, rendered React application with real browser layout geometry. For continuous integration in production, automated accessibility checks should be integrated with Playwright or Cypress running axe-core in real Chromium, WebKit, and Firefox browsers.
2. **Manual Review of Incomplete Checks**: The 13 automated checks flagged as "incomplete" by axe-core in JSDOM (primarily background contrast on layered elements) require ongoing manual inspection or headless browser rendering with computed styles.
3. **Physical Screen Reader Diversity**: While semantic markup and ARIA live regions follow W3C APG guidelines, formal user acceptance testing must include native screen reader users using JAWS, NVDA, and VoiceOver across operating systems and browsers.
4. **Operating System High-Contrast Modes**: In Windows High Contrast Mode / Forced Colors Mode, custom borders and background colors may be overridden by system palettes. Production styles should incorporate `@media (forced-colors: active)` overrides for custom focus rings and status chips.
5. **Internationalization & Localization**: The interface currently supports English (`lang="en"`). Future iterations should include localized strings and bidirectional (`dir="rtl"`) text support.
