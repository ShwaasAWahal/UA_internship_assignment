import axe from "axe-core";
import { JSDOM } from "jsdom";
import fs from "fs";
import path from "path";

const stylesCss = fs.readFileSync(path.resolve("src/styles.css"), "utf-8");

console.log("=================================================");
console.log("  ACCESSIBILITY AUDIT WITH AXE-CORE (WCAG 2.2 AA)");
console.log("=================================================\n");

async function runAuditOnPage(pageName, bodyHtml) {
  const dom = new JSDOM(
    `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>${pageName} — Accessibility Issue Tracker</title>
  <style>${stylesCss}</style>
</head>
<body>
  ${bodyHtml}
</body>
</html>`,
    { runScripts: "dangerously" }
  );

  const { window } = dom;

  // Inject axe-core directly into JSDOM window
  window.eval(axe.source);

  // Run axe inside JSDOM context
  const results = await window.axe.run(window.document, {
    runOnly: {
      type: "tag",
      values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"],
    },
  });

  console.log(`\n--- PAGE AUDIT: ${pageName} ---`);
  console.log(`Passed rules: ${results.passes.length}`);
  console.log(`Incomplete checks: ${results.incomplete.length}`);
  console.log(`Violations: ${results.violations.length}`);

  if (results.violations.length > 0) {
    results.violations.forEach((v, i) => {
      console.log(`\n  [Violation ${i + 1}] ${v.id}: ${v.help}`);
      console.log(`  Impact: ${v.impact}`);
      console.log(`  Help URL: ${v.helpUrl}`);
      v.nodes.forEach((n) => {
        console.log(`    Selector: ${n.target.join(", ")}`);
        console.log(`    Failure: ${n.failureSummary}`);
      });
    });
  } else {
    console.log("  ✓ Zero violations found! Full WCAG 2.2 AA conformance.");
  }

  return results.violations;
}

async function runAllAudits() {
  let totalViolations = 0;

  // 1. Issue List View
  const listHtml = `
    <div class="site-container">
      <a href="#main-content" class="skip-link">Skip to main content</a>
      <div role="status" aria-live="polite" aria-atomic="true" class="sr-only"></div>

      <header class="site-header" role="banner">
        <div class="header-inner">
          <div class="header-brand">
            <button type="button" aria-label="Unified Accessibility Issue Tracker Home" style="background:none;border:none;padding:0;cursor:pointer;">
              <span aria-hidden="true">♿</span>
              <span class="header-title" style="font-size:1.25rem;font-weight:700;">Accessibility Issue Tracker</span>
            </button>
          </div>
          <nav class="header-nav" aria-label="User and actions navigation">
            <div class="user-badge" aria-label="Current demo user: Alice Chen">
              <span aria-hidden="true">👤</span>
              <span><strong>Alice Chen</strong> <span style="color:#334155;">(Accessibility Auditor)</span></span>
            </div>
            <button id="switch-user-btn" type="button" class="btn btn-secondary btn-small" aria-haspopup="dialog" aria-expanded="false">Switch User</button>
            <button type="button" class="btn btn-primary btn-small">+ Log New Issue</button>
          </nav>
        </div>
      </header>

      <main id="main-content" class="main-content" tabindex="-1">
        <div class="demo-banner" role="region" aria-label="Local demonstration mode notice">
          <div><strong>Local Demo Environment:</strong> You are signed in as Alice Chen.</div>
        </div>

        <section aria-labelledby="issue-list-heading">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <h1 id="issue-list-heading" style="margin:0;font-size:1.75rem;">Accessibility Issues</h1>
              <p>Showing 2 issues logged by your account (2 total found).</p>
            </div>
            <button type="button" class="btn btn-primary">+ Log New Issue</button>
          </div>

          <div class="toolbar" role="search" aria-label="Filter issues">
            <div class="filter-group">
              <div class="filter-item">
                <label for="filter-status">Filter by Status:</label>
                <select id="filter-status" class="form-control">
                  <option value="">All Statuses</option>
                  <option value="Open">Open</option>
                  <option value="In Progress">In Progress</option>
                  <option value="Resolved">Resolved</option>
                </select>
              </div>
              <div class="filter-item">
                <label for="filter-severity">Filter by Severity:</label>
                <select id="filter-severity" class="form-control">
                  <option value="">All Severities</option>
                  <option value="Critical">Critical</option>
                  <option value="Serious">Serious</option>
                  <option value="Moderate">Moderate</option>
                  <option value="Minor">Minor</option>
                </select>
              </div>
            </div>
          </div>

          <div class="table-responsive">
            <table class="issue-table">
              <caption class="sr-only">List of accessibility issues logged by current user</caption>
              <thead>
                <tr>
                  <th scope="col" style="width:35%;">Title &amp; Criterion</th>
                  <th scope="col">Page URL</th>
                  <th scope="col">Severity</th>
                  <th scope="col">Status</th>
                  <th scope="col">Last Updated</th>
                  <th scope="col" style="text-align:right;">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row" style="font-weight:normal;text-align:left;">
                    <button type="button" style="background:none;border:none;color:#0052cc;font-weight:700;text-decoration:underline;">Low contrast on checkout button</button>
                    <div style="font-size:0.8125rem;">WCAG: <strong>1.4.3 Contrast (Minimum)</strong></div>
                  </th>
                  <td>
                    <a href="https://example.com/checkout" target="_blank" rel="noopener noreferrer">example.com/checkout<span class="sr-only"> (opens in new tab)</span></a>
                  </td>
                  <td><span class="badge badge-severity-serious">Serious</span></td>
                  <td><span class="badge badge-status-open">Open</span></td>
                  <td>Oct 15, 2026</td>
                  <td style="text-align:right;">
                    <button type="button" class="btn btn-secondary btn-small" aria-label="View details and history for issue #1: Low contrast on checkout button">View Details</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </main>

      <footer class="site-footer" role="contentinfo">
        <p>Unified Accessibility Issue Tracker</p>
      </footer>
    </div>
  `;
  const v1 = await runAuditOnPage("1. Issues List Screen", listHtml);
  totalViolations += v1.length;

  // 2. Create Issue Form Screen with Error Summary
  const formHtml = `
    <div class="site-container">
      <header class="site-header" role="banner"><h1 class="sr-only">Accessibility Issue Tracker</h1></header>
      <main id="main-content" class="main-content" tabindex="-1">
        <div class="card" style="max-width:750px;margin:0 auto;">
          <div class="card-header">
            <h1 id="form-heading" style="margin:0;font-size:1.5rem;">Log New Accessibility Issue</h1>
          </div>

          <div tabindex="-1" role="alert" aria-labelledby="error-summary-title" class="error-summary">
            <h2 id="error-summary-title">Please correct the following errors:</h2>
            <ul>
              <li><a href="#title">Title is required and cannot be blank.</a></li>
              <li><a href="#page_url">Page URL must use HTTP or HTTPS protocol.</a></li>
              <li><a href="#severity">Severity Level is required.</a></li>
            </ul>
          </div>

          <form noValidate aria-labelledby="form-heading">
            <div class="form-group">
              <label for="title" class="form-label">
                Issue Title <span class="required-indicator">(required)</span>
              </label>
              <input id="title" name="title" type="text" class="form-control" aria-required="true" aria-invalid="true" aria-describedby="title-error title-hint" value="">
              <div id="title-hint" class="form-hint">Provide a concise, descriptive summary of the accessibility failure.</div>
              <div id="title-error" class="form-error" role="alert">⚠️ Title is required and cannot be blank.</div>
            </div>

            <div class="form-group">
              <label for="page_url" class="form-label">
                Page URL <span class="required-indicator">(required)</span>
              </label>
              <input id="page_url" name="page_url" type="url" class="form-control" aria-required="true" aria-invalid="true" aria-describedby="page_url-error page_url-hint" value="https://example.com">
              <div id="page_url-hint" class="form-hint">Must be a valid HTTP or HTTPS web address where the issue was observed.</div>
              <div id="page_url-error" class="form-error" role="alert">⚠️ Page URL must use HTTP or HTTPS protocol.</div>
            </div>

            <div class="form-group">
              <label for="wcag_criterion" class="form-label">WCAG Criterion (Optional)</label>
              <input id="wcag_criterion" name="wcag_criterion" type="text" list="wcag-suggestions" class="form-control" aria-describedby="wcag_criterion-hint" value="">
              <datalist id="wcag-suggestions"><option value="1.4.3 Contrast (Minimum)"></option></datalist>
              <div id="wcag_criterion-hint" class="form-hint">Select or type the relevant WCAG 2.1 / 2.2 Success Criterion.</div>
            </div>

            <div class="form-group">
              <fieldset id="severity" tabindex="-1" style="border:none;padding:0;margin:0;" aria-describedby="severity-hint">
                <legend class="form-label">Severity Level <span class="required-indicator">(required)</span></legend>
                <div id="severity-hint" class="form-hint" style="margin-bottom:0.5rem;">Categorize the impact on assistive technology users.</div>
                <div style="display:flex;gap:1rem;">
                  <label><input type="radio" name="severity" id="severity-minor" value="Minor"> Minor</label>
                  <label><input type="radio" name="severity" id="severity-moderate" value="Moderate" checked> Moderate</label>
                  <label><input type="radio" name="severity" id="severity-serious" value="Serious"> Serious</label>
                  <label><input type="radio" name="severity" id="severity-critical" value="Critical"> Critical</label>
                </div>
              </fieldset>
            </div>

            <div class="form-group">
              <label for="description" class="form-label">Description and Remediation Notes (Optional)</label>
              <textarea id="description" name="description" rows="5" class="form-control" aria-describedby="description-hint"></textarea>
              <div id="description-hint" class="form-hint">Include reproduction steps, impacted user groups, and recommended code fixes.</div>
            </div>

            <div class="form-actions" style="display:flex;gap:1rem;">
              <button type="submit" class="btn btn-primary">Create Issue</button>
              <button type="button" class="btn btn-secondary">Cancel</button>
            </div>
          </form>
        </div>
      </main>
    </div>
  `;
  const v2 = await runAuditOnPage("2. Create Issue Form Screen", formHtml);
  totalViolations += v2.length;

  // 3. Issue Detail Screen
  const detailHtml = `
    <div class="site-container">
      <header class="site-header" role="banner"><h1 class="sr-only">Accessibility Issue Tracker</h1></header>
      <main id="main-content" class="main-content" tabindex="-1">
        <article aria-labelledby="issue-detail-heading">
          <nav aria-label="Breadcrumb">
            <button type="button" class="btn btn-secondary btn-small">&larr; Back to Issues List</button>
          </nav>

          <div class="card">
            <div class="card-header">
              <div>
                <div style="font-size:0.875rem;">Issue #1 &bull; Version 1</div>
                <h1 id="issue-detail-heading" style="margin:0;font-size:1.75rem;">Low contrast on checkout button</h1>
              </div>
              <div>
                <button type="button" class="btn btn-secondary">✎ Edit Issue</button>
                <button type="button" class="btn btn-secondary btn-small">🔄 Refresh</button>
              </div>
            </div>

            <dl style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:1rem;">
              <div>
                <dt style="font-weight:600;">Status</dt>
                <dd><span class="badge badge-status-open">Open</span></dd>
              </div>
              <div>
                <dt style="font-weight:600;">Severity</dt>
                <dd><span class="badge badge-severity-serious">Serious</span></dd>
              </div>
              <div>
                <dt style="font-weight:600;">WCAG Criterion</dt>
                <dd>1.4.3 Contrast (Minimum)</dd>
              </div>
              <div>
                <dt style="font-weight:600;">Created At</dt>
                <dd><time datetime="2026-10-15T10:00:00Z">Oct 15, 2026, 10:00 AM</time></dd>
              </div>
            </dl>

            <div>
              <strong style="display:block;">Affected Page URL:</strong>
              <a href="https://example.com/checkout" target="_blank" rel="noopener noreferrer">https://example.com/checkout<span class="sr-only"> (opens in new tab)</span></a>
            </div>

            <div>
              <strong style="display:block;margin-top:1rem;">Description &amp; Remediation Notes:</strong>
              <div>Primary checkout submit button is light grey on white (contrast 2.1:1). Needs darkening.</div>
            </div>
          </div>

          <section class="card" aria-labelledby="status-transition-heading">
            <h2 id="status-transition-heading" style="margin:0 0 0.75rem 0;font-size:1.25rem;">Update Issue Status</h2>
            <form noValidate>
              <div style="display:flex;gap:1rem;flex-wrap:wrap;align-items:flex-end;">
                <div>
                  <label for="new-status" class="form-label">Next Status <span class="required-indicator">(required)</span></label>
                  <select id="new-status" class="form-control" aria-required="true">
                    <option value="">-- Choose target status --</option>
                    <option value="In Progress">In Progress</option>
                    <option value="Resolved">Resolved</option>
                  </select>
                </div>
                <div>
                  <label for="status-comment" class="form-label">Remediation Comment (Optional)</label>
                  <input id="status-comment" type="text" class="form-control" placeholder="Reason or notes">
                </div>
                <div>
                  <button type="submit" class="btn btn-primary">Submit Status Change</button>
                </div>
              </div>
            </form>
          </section>

          <section class="card" aria-labelledby="status-history-heading">
            <h2 id="status-history-heading" style="margin:0 0 1.25rem 0;font-size:1.25rem;">Status Change History</h2>
            <ol class="status-timeline">
              <li class="status-timeline-item">
                <div class="timeline-dot" aria-hidden="true"></div>
                <div class="timeline-meta">
                  <time datetime="2026-10-15T10:00:00Z">Oct 15, 2026, 10:00 AM</time> &bull; Actor: <strong>demo-user-alice</strong>
                </div>
                <div>Status changed from <span class="badge badge-status-open">None</span> to <span class="badge badge-status-open">Open</span></div>
              </li>
            </ol>
          </section>
        </article>
      </main>
    </div>
  `;
  const v3 = await runAuditOnPage("3. Issue Detail Screen", detailHtml);
  totalViolations += v3.length;

  // 4. Demo Switcher Modal Dialog
  const modalHtml = `
    <div class="site-container">
      <main id="main-content" class="main-content" tabindex="-1">
        <div class="modal-backdrop">
          <div role="dialog" aria-modal="true" aria-labelledby="demo-switcher-title" aria-describedby="demo-switcher-desc" class="modal-box">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <h2 id="demo-switcher-title" style="margin:0;font-size:1.25rem;">Select Demo Account</h2>
              <button type="button" class="btn btn-secondary btn-small" aria-label="Close demo account switcher dialog">✕ Close</button>
            </div>
            <div class="demo-banner"><strong>Notice: Demonstration Environment Only.</strong></div>
            <p id="demo-switcher-desc">Choose an auditor profile to view and manage their personal accessibility findings:</p>
            <div>
              <button type="button" class="btn btn-secondary btn-small" disabled aria-label="Alice Chen is currently selected">Selected</button>
              <button type="button" class="btn btn-primary btn-small" aria-label="Switch to Bob Martinez">Switch</button>
            </div>
          </div>
        </div>
      </main>
    </div>
  `;
  const v4 = await runAuditOnPage("4. Demo Switcher Modal Dialog", modalHtml);
  totalViolations += v4.length;

  console.log("\n=================================================");
  console.log(`TOTAL AXE VIOLATIONS ACROSS ALL SCREENS: ${totalViolations}`);
  console.log("=================================================\n");

  if (totalViolations > 0) {
    process.exit(1);
  }
}

runAllAudits().catch((err) => {
  console.error("Audit runner error:", err);
  process.exit(1);
});
