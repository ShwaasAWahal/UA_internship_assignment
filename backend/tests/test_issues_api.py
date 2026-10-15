import pytest
from app.models import Issue, SeverityEnum, StatusEnum


def test_create_issue_success(client):
    """Test successful issue creation with default Open status, version 1, and owner assignment."""
    payload = {
        "title": "Low contrast on submit button",
        "description": "Button text contrast is 2.8:1, failing WCAG 1.4.3.",
        "page_url": "https://example.com/checkout",
        "wcag_criterion": "1.4.3 Contrast (Minimum)",
        "severity": "Serious",
    }
    response = client.post("/api/issues", json=payload, headers={"X-Demo-User-Id": "demo-user-alice"})
    assert response.status_code == 201
    data = response.json()

    assert data["id"] is not None
    assert data["owner_id"] == "demo-user-alice"
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["page_url"] == payload["page_url"]
    assert data["wcag_criterion"] == payload["wcag_criterion"]
    assert data["severity"] == "Serious"
    assert data["status"] == "Open"
    assert data["version"] == 1
    assert data["created_at"] is not None
    assert data["updated_at"] is not None


def test_create_issue_validation_failures(client):
    """Test server-side validation for missing/blank title, invalid URLs, and unknown severity."""
    # Blank title
    res_blank_title = client.post(
        "/api/issues",
        json={"title": "   ", "page_url": "https://example.com", "severity": "Minor"},
    )
    assert res_blank_title.status_code == 422
    err = res_blank_title.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert "title" in err["fields"]

    # Missing title
    res_no_title = client.post(
        "/api/issues",
        json={"page_url": "https://example.com", "severity": "Minor"},
    )
    assert res_no_title.status_code == 422
    assert "title" in res_no_title.json()["error"]["fields"]

    # Invalid URL schemes
    for invalid_url in ["ftp://example.com", "javascript:alert(1)", "not-a-url", "http://"]:
        res_url = client.post(
            "/api/issues",
            json={"title": "Invalid URL test", "page_url": invalid_url, "severity": "Minor"},
        )
        assert res_url.status_code == 422
        assert "page_url" in res_url.json()["error"]["fields"]

    # Invalid severity
    res_sev = client.post(
        "/api/issues",
        json={"title": "Invalid Severity", "page_url": "https://example.com", "severity": "Extreme"},
    )
    assert res_sev.status_code == 422
    assert "severity" in res_sev.json()["error"]["fields"]

    # Disallow injecting protected fields (e.g. owner_id, version, status) in body
    res_inject = client.post(
        "/api/issues",
        json={
            "title": "Injection attempt",
            "page_url": "https://example.com",
            "severity": "Minor",
            "owner_id": "malicious-user",
            "status": "Resolved",
        },
    )
    assert res_inject.status_code == 422
    err_inject = res_inject.json()["error"]
    assert err_inject["code"] == "VALIDATION_ERROR"


def test_list_issues_and_filtering(client):
    """Test listing issues scoped to current user, with status/severity filters and deterministic sorting."""
    # Seed issues for Alice (all start in Open)
    alice_headers = {"X-Demo-User-Id": "demo-user-alice"}
    created_ids = []
    for i, severity in enumerate(["Minor", "Critical", "Critical", "Serious"]):
        res = client.post(
            "/api/issues",
            json={
                "title": f"Alice Issue {i + 1}",
                "page_url": f"https://example.com/page{i + 1}",
                "severity": severity,
            },
            headers=alice_headers,
        )
        created_ids.append(res.json()["id"])

    # Transition issue 3 to In Progress
    client.patch(
        f"/api/issues/{created_ids[2]}/status",
        json={"status": "In Progress", "version": 1},
        headers=alice_headers,
    )

    # Transition issue 4 to In Progress then Resolved
    client.patch(
        f"/api/issues/{created_ids[3]}/status",
        json={"status": "In Progress", "version": 1},
        headers=alice_headers,
    )
    client.patch(
        f"/api/issues/{created_ids[3]}/status",
        json={"status": "Resolved", "version": 2},
        headers=alice_headers,
    )

    # Seed 1 issue for Bob
    client.post(
        "/api/issues",
        json={"title": "Bob Issue", "page_url": "https://example.com/bob", "severity": "Critical"},
        headers={"X-Demo-User-Id": "demo-user-bob"},
    )

    # List all for Alice: should have exactly 4 items, none of Bob's
    res_all = client.get("/api/issues", headers=alice_headers)
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["total"] == 4
    assert len(data_all["items"]) == 4
    assert all(item["owner_id"] == "demo-user-alice" for item in data_all["items"])

    # Filter by severity: Critical
    res_crit = client.get("/api/issues?severity=Critical", headers=alice_headers)
    assert res_crit.status_code == 200
    data_crit = res_crit.json()
    assert data_crit["total"] == 2
    assert all(item["severity"] == "Critical" for item in data_crit["items"])

    # Filter by status: Open
    res_open = client.get("/api/issues?status=Open", headers=alice_headers)
    assert res_open.status_code == 200
    data_open = res_open.json()
    assert data_open["total"] == 2
    assert all(item["status"] == "Open" for item in data_open["items"])

    # Bounded pagination
    res_page = client.get("/api/issues?limit=2&offset=0", headers=alice_headers)
    assert res_page.status_code == 200
    assert len(res_page.json()["items"]) == 2
    assert res_page.json()["total"] == 4


def test_cross_user_access_denial(client):
    """Test that a user cannot see, edit, or change status of another user's issue, receiving 404."""
    # Alice creates an issue
    res_alice_create = client.post(
        "/api/issues",
        json={"title": "Alice's Secret Issue", "page_url": "https://example.com/secret", "severity": "Serious"},
        headers={"X-Demo-User-Id": "demo-user-alice"},
    )
    issue_id = res_alice_create.json()["id"]

    bob_headers = {"X-Demo-User-Id": "demo-user-bob"}

    # Bob attempts to GET Alice's issue -> 404
    res_get = client.get(f"/api/issues/{issue_id}", headers=bob_headers)
    assert res_get.status_code == 404
    assert res_get.json()["error"]["code"] == "ISSUE_NOT_FOUND"

    # Bob attempts to PATCH Alice's issue fields -> 404
    res_patch = client.patch(
        f"/api/issues/{issue_id}",
        json={"title": "Hacked Title", "version": 1},
        headers=bob_headers,
    )
    assert res_patch.status_code == 404
    assert res_patch.json()["error"]["code"] == "ISSUE_NOT_FOUND"

    # Bob attempts to PATCH Alice's issue status -> 404
    res_status = client.patch(
        f"/api/issues/{issue_id}/status",
        json={"status": "In Progress", "version": 1},
        headers=bob_headers,
    )
    assert res_status.status_code == 404
    assert res_status.json()["error"]["code"] == "ISSUE_NOT_FOUND"


def test_issue_edit_and_optimistic_concurrency(client):
    """Test editing permitted fields, version bumping, and rejecting stale version with 409 Conflict."""
    alice_headers = {"X-Demo-User-Id": "demo-user-alice"}
    res = client.post(
        "/api/issues",
        json={"title": "Original Title", "page_url": "https://example.com/orig", "severity": "Minor"},
        headers=alice_headers,
    )
    issue_id = res.json()["id"]
    assert res.json()["version"] == 1

    # Successful update
    res_update = client.patch(
        f"/api/issues/{issue_id}",
        json={"title": "Updated Title", "severity": "Moderate", "version": 1},
        headers=alice_headers,
    )
    assert res_update.status_code == 200
    updated = res_update.json()
    assert updated["title"] == "Updated Title"
    assert updated["severity"] == "Moderate"
    assert updated["version"] == 2

    # Stale version update must fail with 409 Conflict
    res_stale = client.patch(
        f"/api/issues/{issue_id}",
        json={"title": "Stale Update", "version": 1},
        headers=alice_headers,
    )
    assert res_stale.status_code == 409
    err = res_stale.json()["error"]
    assert err["code"] == "CONCURRENCY_CONFLICT"
    assert "version 1 does not match" in err["message"]


def test_status_workflow_transitions_and_history(client):
    """Test allowed transitions, audit history creation, forbidden transitions, and no-ops."""
    alice_headers = {"X-Demo-User-Id": "demo-user-alice"}
    res = client.post(
        "/api/issues",
        json={"title": "Workflow Test Issue", "page_url": "https://example.com/flow", "severity": "Critical"},
        headers=alice_headers,
    )
    issue_id = res.json()["id"]

    # 1. Allowed: Open -> In Progress
    res_step1 = client.patch(
        f"/api/issues/{issue_id}/status",
        json={"status": "In Progress", "version": 1, "comment": "Starting remediation review"},
        headers=alice_headers,
    )
    assert res_step1.status_code == 200
    assert res_step1.json()["status"] == "In Progress"
    assert res_step1.json()["version"] == 2

    # Check history on detail endpoint
    res_detail1 = client.get(f"/api/issues/{issue_id}", headers=alice_headers)
    history1 = res_detail1.json()["status_history"]
    assert len(history1) == 1
    assert history1[0]["previous_status"] == "Open"
    assert history1[0]["new_status"] == "In Progress"
    assert history1[0]["actor_id"] == "demo-user-alice"
    assert history1[0]["comment"] == "Starting remediation review"

    # 2. No-op transition: In Progress -> In Progress should be rejected with 409 and not log history
    res_noop = client.patch(
        f"/api/issues/{issue_id}/status",
        json={"status": "In Progress", "version": 2},
        headers=alice_headers,
    )
    assert res_noop.status_code == 409
    assert res_noop.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"

    # 3. Allowed: In Progress -> Resolved
    res_step2 = client.patch(
        f"/api/issues/{issue_id}/status",
        json={"status": "Resolved", "version": 2, "comment": "Fixed and tested in all viewports"},
        headers=alice_headers,
    )
    assert res_step2.status_code == 200
    assert res_step2.json()["status"] == "Resolved"
    assert res_step2.json()["version"] == 3

    # 4. FORBIDDEN TRANSITION: Resolved -> In Progress directly must return 409
    res_forbidden = client.patch(
        f"/api/issues/{issue_id}/status",
        json={"status": "In Progress", "version": 3},
        headers=alice_headers,
    )
    assert res_forbidden.status_code == 409
    err_forbidden = res_forbidden.json()["error"]
    assert err_forbidden["code"] == "INVALID_STATUS_TRANSITION"
    assert "An issue cannot move from Resolved directly to In Progress" in err_forbidden["message"]
    assert "status" in err_forbidden["fields"]

    # 5. Allowed: Resolved -> Open (reopen)
    res_reopen = client.patch(
        f"/api/issues/{issue_id}/status",
        json={"status": "Open", "version": 3, "comment": "Reopening due to regression"},
        headers=alice_headers,
    )
    assert res_reopen.status_code == 200
    assert res_reopen.json()["status"] == "Open"
    assert res_reopen.json()["version"] == 4

    # Verify complete history timeline on detail view
    res_final = client.get(f"/api/issues/{issue_id}", headers=alice_headers)
    history_final = res_final.json()["status_history"]
    # 3 successful transitions: Open->In Progress, In Progress->Resolved, Resolved->Open
    assert len(history_final) == 3


def test_direct_open_to_resolved_and_in_progress_to_open(client):
    """Test the other allowed transitions: Open -> Resolved and In Progress -> Open."""
    alice_headers = {"X-Demo-User-Id": "demo-user-alice"}

    # Issue 1: Open -> Resolved directly
    res1 = client.post(
        "/api/issues",
        json={"title": "Direct Resolved Test", "page_url": "https://example.com/res", "severity": "Minor"},
        headers=alice_headers,
    )
    id1 = res1.json()["id"]
    res_direct_res = client.patch(
        f"/api/issues/{id1}/status",
        json={"status": "Resolved", "version": 1},
        headers=alice_headers,
    )
    assert res_direct_res.status_code == 200
    assert res_direct_res.json()["status"] == "Resolved"

    # Issue 2: Open -> In Progress -> Open
    res2 = client.post(
        "/api/issues",
        json={"title": "In Progress to Open Test", "page_url": "https://example.com/reopen", "severity": "Minor"},
        headers=alice_headers,
    )
    id2 = res2.json()["id"]
    client.patch(
        f"/api/issues/{id2}/status",
        json={"status": "In Progress", "version": 1},
        headers=alice_headers,
    )
    res_back_to_open = client.patch(
        f"/api/issues/{id2}/status",
        json={"status": "Open", "version": 2},
        headers=alice_headers,
    )
    assert res_back_to_open.status_code == 200
    assert res_back_to_open.json()["status"] == "Open"
    assert res_back_to_open.json()["version"] == 3


def test_pagination_bounds_and_deterministic_sorting(client):
    """Test boundary validation on pagination query params and deterministic sort order."""
    alice_headers = {"X-Demo-User-Id": "demo-user-alice"}

    # Limit too large
    res_large = client.get("/api/issues?limit=101", headers=alice_headers)
    assert res_large.status_code == 422

    # Limit zero or negative
    res_zero = client.get("/api/issues?limit=0", headers=alice_headers)
    assert res_zero.status_code == 422

    # Offset negative
    res_neg = client.get("/api/issues?offset=-1", headers=alice_headers)
    assert res_neg.status_code == 422

    # Verify deterministic sort: newest first
    ids_in_order = []
    for i in range(3):
        r = client.post(
            "/api/issues",
            json={"title": f"Sort test {i}", "page_url": "https://example.com", "severity": "Minor"},
            headers=alice_headers,
        )
        ids_in_order.append(r.json()["id"])

    res_list = client.get("/api/issues?limit=10", headers=alice_headers)
    returned_ids = [item["id"] for item in res_list.json()["items"]]
    # The last created issue must appear before earlier issues
    assert returned_ids.index(ids_in_order[2]) < returned_ids.index(ids_in_order[1]) < returned_ids.index(ids_in_order[0])


def test_patch_rejects_status_and_protected_fields(client):
    """Verify that general PATCH /api/issues/{id} cannot alter status, owner_id, or history."""
    alice_headers = {"X-Demo-User-Id": "demo-user-alice"}
    res = client.post(
        "/api/issues",
        json={"title": "Protected fields test", "page_url": "https://example.com", "severity": "Minor"},
        headers=alice_headers,
    )
    issue_id = res.json()["id"]

    # Attempting to change status via main PATCH endpoint must fail with 422
    res_status = client.patch(
        f"/api/issues/{issue_id}",
        json={"status": "Resolved", "version": 1},
        headers=alice_headers,
    )
    assert res_status.status_code == 422

    # Attempting to modify owner_id must fail with 422
    res_owner = client.patch(
        f"/api/issues/{issue_id}",
        json={"owner_id": "demo-user-bob", "version": 1},
        headers=alice_headers,
    )
    assert res_owner.status_code == 422
