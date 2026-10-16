import os
import signal
import subprocess
import sys
import time
import httpx

BACKEND_PORT = 8009
BASE_URL = f"http://127.0.0.1:{BACKEND_PORT}"
DB_FILE = os.path.abspath("backend/test_e2e_integration.db")

print("=====================================================================")
print("  END-TO-END INTEGRATION TEST FOR UNIFIED ACCESSIBILITY ISSUE TRACKER")
print("=====================================================================\n")

def start_backend():
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{DB_FILE}"
    python_exe = os.path.abspath("backend/.venv/Scripts/python.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable

    cmd = [
        python_exe,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(BACKEND_PORT),
        "--log-level",
        "warning",
    ]
    proc = subprocess.Popen(cmd, cwd=os.path.abspath("backend"), env=env)
    return proc

def wait_for_server(timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(f"{BASE_URL}/health", timeout=1.0)
            if r.status_code == 200 and r.json().get("status") == "ok":
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def stop_backend(proc):
    if proc:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

# Clean old test db if present
if os.path.exists(DB_FILE):
    try:
        os.remove(DB_FILE)
    except Exception:
        pass

server_proc = None
results = []

def record(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}")
    if detail:
        print(f"       {detail}")
    results.append((name, passed, detail))
    if not passed:
        raise AssertionError(f"Step failed: {name} - {detail}")

try:
    # -------------------------------------------------------------
    # 1. Start the backend locally
    # -------------------------------------------------------------
    print("\n--- Step 1: Start backend server locally ---")
    server_proc = start_backend()
    healthy = wait_for_server()
    record("Start backend server and verify health endpoint", healthy, f"Server responding at {BASE_URL}/health")

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # -------------------------------------------------------------
        # 2. Sign in as demo user A
        # -------------------------------------------------------------
        print("\n--- Step 2: Authenticate as demo user A (Alice) ---")
        res_me_a = client.get("/api/me", headers={"X-Demo-User-Id": "demo-user-alice"})
        record("User A profile lookup", res_me_a.status_code == 200, f"Status {res_me_a.status_code}")
        user_a = res_me_a.json()
        record("User A identity verified", user_a["id"] == "demo-user-alice" and "Alice Chen" in user_a["display_name"],
               f"Name: {user_a.get('display_name')}, Role: {user_a.get('role')}")

        # -------------------------------------------------------------
        # 3. Create an issue with valid fields
        # -------------------------------------------------------------
        print("\n--- Step 3: Create an issue with valid fields ---")
        issue_payload = {
            "title": "Color contrast insufficient on submit button",
            "description": "Button foreground text #888888 on #ffffff has ratio 2.8:1, failing WCAG 1.4.3.",
            "page_url": "https://example.com/checkout",
            "wcag_criterion": "1.4.3 Contrast (Minimum)",
            "severity": "Serious",
        }
        res_create = client.post("/api/issues", json=issue_payload, headers={"X-Demo-User-Id": "demo-user-alice"})
        record("Issue created with 201 Created", res_create.status_code == 201, f"Status {res_create.status_code}")
        issue = res_create.json()
        issue_id = issue["id"]
        created_at_initial = issue["created_at"]
        updated_at_initial = issue["updated_at"]
        record("Issue fields verified",
               issue["owner_id"] == "demo-user-alice" and
               issue["status"] == "Open" and
               issue["version"] == 1 and
               issue["severity"] == "Serious" and
               issue["title"] == issue_payload["title"],
               f"Issue #{issue_id}, Status={issue['status']}, Version={issue['version']}")

        # -------------------------------------------------------------
        # 4. Verify issue persists after backend restart
        # -------------------------------------------------------------
        print("\n--- Step 4: Verify persistence across backend restart ---")
        print("Stopping backend server process...")
        stop_backend(server_proc)
        time.sleep(1)

        print("Restarting backend server process against same SQLite database...")
        server_proc = start_backend()
        healthy_after_restart = wait_for_server()
        record("Backend successfully restarted", healthy_after_restart)

        res_persisted = client.get(f"/api/issues/{issue_id}", headers={"X-Demo-User-Id": "demo-user-alice"})
        record("Issue retrievable after restart", res_persisted.status_code == 200, f"Status {res_persisted.status_code}")
        persisted_issue = res_persisted.json()
        record("Persisted issue data integrity",
               persisted_issue["title"] == issue_payload["title"] and
               persisted_issue["page_url"] == issue_payload["page_url"] and
               persisted_issue["version"] == 1,
               f"Issue #{persisted_issue['id']} retrieved with identical fields")

        # -------------------------------------------------------------
        # 5. Edit the issue and confirm updated timestamp changes
        # -------------------------------------------------------------
        print("\n--- Step 5: Edit the issue & verify updated_at timestamp changes ---")
        time.sleep(0.5) # ensure clock advances
        edit_payload = {
            "title": "Color contrast insufficient on primary checkout submit button",
            "description": "Updated reproduction notes: also affects dark mode toggle.",
            "page_url": "https://example.com/checkout/step2",
            "wcag_criterion": "1.4.3 Contrast (Minimum)",
            "severity": "Critical",
            "version": 1,
        }
        res_edit = client.patch(f"/api/issues/{issue_id}", json=edit_payload, headers={"X-Demo-User-Id": "demo-user-alice"})
        record("Edit issue returned 200 OK", res_edit.status_code == 200, f"Status {res_edit.status_code}")
        edited = res_edit.json()
        record("Version incremented to 2", edited["version"] == 2, f"Version = {edited['version']}")
        record("Updated_at timestamp changed", edited["updated_at"] > updated_at_initial,
               f"Initial: {updated_at_initial} -> New: {edited['updated_at']}")
        record("Fields updated accurately", edited["severity"] == "Critical" and edited["page_url"] == edit_payload["page_url"])

        # -------------------------------------------------------------
        # 6. Filter issues by status and severity
        # -------------------------------------------------------------
        print("\n--- Step 6: Filter issues by status and severity ---")
        # Match filter: status=Open, severity=Critical
        res_filter_match = client.get("/api/issues?status=Open&severity=Critical", headers={"X-Demo-User-Id": "demo-user-alice"})
        match_data = res_filter_match.json()
        record("Filter matching status=Open&severity=Critical",
               res_filter_match.status_code == 200 and match_data["total"] >= 1 and any(i["id"] == issue_id for i in match_data["items"]),
               f"Total items: {match_data['total']}")

        # Non-matching filter: status=Resolved
        res_filter_nomatch = client.get("/api/issues?status=Resolved", headers={"X-Demo-User-Id": "demo-user-alice"})
        nomatch_data = res_filter_nomatch.json()
        record("Filter non-matching status=Resolved excludes open issue",
               res_filter_nomatch.status_code == 200 and not any(i["id"] == issue_id for i in nomatch_data["items"]),
               f"Open issue #{issue_id} correctly omitted from Resolved filter")

        # -------------------------------------------------------------
        # 7. Change Open -> In Progress -> Resolved
        # -------------------------------------------------------------
        print("\n--- Step 7: Transition Open -> In Progress -> Resolved ---")
        # Step 7a: Open -> In Progress
        status_payload_1 = {
            "status": "In Progress",
            "version": 2,
            "comment": "Auditor assigned and remediation branch opened",
        }
        res_stat_1 = client.patch(f"/api/issues/{issue_id}/status", json=status_payload_1, headers={"X-Demo-User-Id": "demo-user-alice"})
        record("Transition Open -> In Progress succeeded", res_stat_1.status_code == 200, f"Status: {res_stat_1.status_code}")
        stat_issue_1 = res_stat_1.json()
        record("Issue state is In Progress with version 3",
               stat_issue_1["status"] == "In Progress" and stat_issue_1["version"] == 3)

        # Step 7b: In Progress -> Resolved
        status_payload_2 = {
            "status": "Resolved",
            "version": 3,
            "comment": "Color tokens updated to 7:1 contrast; verified with axe-core",
        }
        res_stat_2 = client.patch(f"/api/issues/{issue_id}/status", json=status_payload_2, headers={"X-Demo-User-Id": "demo-user-alice"})
        record("Transition In Progress -> Resolved succeeded", res_stat_2.status_code == 200, f"Status: {res_stat_2.status_code}")
        stat_issue_2 = res_stat_2.json()
        record("Issue state is Resolved with version 4",
               stat_issue_2["status"] == "Resolved" and stat_issue_2["version"] == 4)

        # -------------------------------------------------------------
        # 8. Verify status change history
        # -------------------------------------------------------------
        print("\n--- Step 8: Verify status history audit trail ---")
        res_detail = client.get(f"/api/issues/{issue_id}", headers={"X-Demo-User-Id": "demo-user-alice"})
        detail_data = res_detail.json()
        history = detail_data.get("status_history", [])
        record("Status history has 2 entries", len(history) == 2, f"History count: {len(history)}")

        # Status history is ordered by desc(changed_at), so index 0 is most recent
        h_recent = history[0]
        record("Recent history entry (index 0): In Progress -> Resolved",
               h_recent["previous_status"] == "In Progress" and
               h_recent["new_status"] == "Resolved" and
               h_recent["actor_id"] == "demo-user-alice" and
               h_recent["comment"] == status_payload_2["comment"] and
               h_recent["changed_at"] is not None)

        h_earlier = history[1]
        record("Earlier history entry (index 1): Open -> In Progress",
               h_earlier["previous_status"] == "Open" and
               h_earlier["new_status"] == "In Progress" and
               h_earlier["actor_id"] == "demo-user-alice" and
               h_earlier["comment"] == status_payload_1["comment"] and
               h_earlier["changed_at"] is not None)

        # -------------------------------------------------------------
        # 9. Attempt Resolved -> In Progress and verify backend rejects it
        # -------------------------------------------------------------
        print("\n--- Step 9: Attempt disallowed Resolved -> In Progress transition ---")
        invalid_trans_payload = {
            "status": "In Progress",
            "version": 4,
            "comment": "Attempting invalid direct transition",
        }
        res_invalid_trans = client.patch(f"/api/issues/{issue_id}/status", json=invalid_trans_payload, headers={"X-Demo-User-Id": "demo-user-alice"})
        record("Resolved -> In Progress rejected with 409 Conflict", res_invalid_trans.status_code == 409, f"Status {res_invalid_trans.status_code}")
        trans_err = res_invalid_trans.json()["error"]
        record("Error code is INVALID_STATUS_TRANSITION", trans_err["code"] == "INVALID_STATUS_TRANSITION", trans_err["message"])

        # -------------------------------------------------------------
        # 10. User B isolation: cannot read, edit, or change User A's issue
        # -------------------------------------------------------------
        print("\n--- Step 10: Verify multi-user isolation for demo user B (Bob) ---")
        # 10a: Verify Bob's identity
        res_me_b = client.get("/api/me", headers={"X-Demo-User-Id": "demo-user-bob"})
        record("User B profile lookup", res_me_b.status_code == 200 and res_me_b.json()["id"] == "demo-user-bob")

        # 10b: Bob attempts to read Alice's issue -> 404
        res_bob_get = client.get(f"/api/issues/{issue_id}", headers={"X-Demo-User-Id": "demo-user-bob"})
        record("User B reading User A's issue returns 404 Not Found", res_bob_get.status_code == 404, f"Status {res_bob_get.status_code}")

        # 10c: Bob attempts to edit Alice's issue -> 404
        res_bob_patch = client.patch(f"/api/issues/{issue_id}", json={"title": "Hacked by Bob", "version": 4}, headers={"X-Demo-User-Id": "demo-user-bob"})
        record("User B editing User A's issue returns 404 Not Found", res_bob_patch.status_code == 404, f"Status {res_bob_patch.status_code}")

        # 10d: Bob attempts to change status of Alice's issue -> 404
        res_bob_status = client.patch(f"/api/issues/{issue_id}/status", json={"status": "Open", "version": 4}, headers={"X-Demo-User-Id": "demo-user-bob"})
        record("User B changing status of User A's issue returns 404 Not Found", res_bob_status.status_code == 404, f"Status {res_bob_status.status_code}")

        # 10e: Bob lists issues -> Alice's issue is not in Bob's list
        res_bob_list = client.get("/api/issues", headers={"X-Demo-User-Id": "demo-user-bob"})
        bob_issues = res_bob_list.json()["items"]
        record("User A's issue omitted from User B's issue list", not any(i["id"] == issue_id for i in bob_issues))

        # -------------------------------------------------------------
        # 11. Submit invalid titles, URLs, and enum values
        # -------------------------------------------------------------
        print("\n--- Step 11: Validation error tests ---")
        # Blank title
        r1 = client.post("/api/issues", json={"title": "   ", "page_url": "https://example.com", "severity": "Minor"}, headers={"X-Demo-User-Id": "demo-user-alice"})
        record("Blank title rejected with 422", r1.status_code == 422 and "title" in r1.json()["error"]["fields"], str(r1.json()["error"]))

        # Non-HTTP URL
        r2 = client.post("/api/issues", json={"title": "Bad URL test", "page_url": "ftp://files.example.com", "severity": "Minor"}, headers={"X-Demo-User-Id": "demo-user-alice"})
        record("FTP URL rejected with 422", r2.status_code == 422 and "page_url" in r2.json()["error"]["fields"], str(r2.json()["error"]))

        # Invalid Severity Enum
        r3 = client.post("/api/issues", json={"title": "Bad Severity test", "page_url": "https://example.com", "severity": "Catastrophic"}, headers={"X-Demo-User-Id": "demo-user-alice"})
        record("Invalid severity enum rejected with 422", r3.status_code == 422 and "severity" in r3.json()["error"]["fields"], str(r3.json()["error"]))

        # Invalid Status Enum
        r4 = client.patch(f"/api/issues/{issue_id}/status", json={"status": "Archived", "version": 4}, headers={"X-Demo-User-Id": "demo-user-alice"})
        record("Invalid status enum rejected with 422", r4.status_code == 422 and "status" in r4.json()["error"]["fields"], str(r4.json()["error"]))

        # -------------------------------------------------------------
        # 12. Simulate/reproduce stale-version concurrency conflict
        # -------------------------------------------------------------
        print("\n--- Step 12: Stale-version concurrency conflict test ---")
        # Current version is 4. Submit with version 2.
        stale_edit_payload = {
            "title": "Stale update attempting overwrite",
            "version": 2,
        }
        res_stale = client.patch(f"/api/issues/{issue_id}", json=stale_edit_payload, headers={"X-Demo-User-Id": "demo-user-alice"})
        record("Stale version update rejected with 409 Conflict", res_stale.status_code == 409, f"Status {res_stale.status_code}")
        stale_err = res_stale.json()["error"]
        record("Error code is CONCURRENCY_CONFLICT",
               stale_err["code"] == "CONCURRENCY_CONFLICT",
               stale_err["message"])

        # Stale version on status update
        stale_status_payload = {
            "status": "Open",
            "version": 1,
        }
        res_stale_status = client.patch(f"/api/issues/{issue_id}/status", json=stale_status_payload, headers={"X-Demo-User-Id": "demo-user-alice"})
        record("Stale version status change rejected with 409 Conflict", res_stale_status.status_code == 409, f"Status {res_stale_status.status_code}")
        stale_status_err = res_stale_status.json()["error"]
        record("Status conflict error code is CONCURRENCY_CONFLICT",
               stale_status_err["code"] == "CONCURRENCY_CONFLICT",
               stale_status_err["message"])

    print("\n=====================================================================")
    print(f"  ALL {len(results)} WORKFLOW CHECKS PASSED SUCCESSFULLY!")
    print("=====================================================================\n")

finally:
    stop_backend(server_proc)
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
        except Exception:
            pass
