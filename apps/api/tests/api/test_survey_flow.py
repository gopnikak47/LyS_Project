from __future__ import annotations

import pytest

from tests.api.conftest import Harness
from tests.api.test_tenant_isolation import _setup

pytestmark = pytest.mark.db


async def test_idempotent_submission_analytics_and_erasure(api: Harness) -> None:
    client_a, b, owner = await _setup(api)
    workspace = b.ids["workspace_id"]
    for endpoint in (
        "overview",
        "trends",
        "topics",
        "wordcloud",
        "per-question",
        "pivot",
        "events",
    ):
        foreign = await client_a.get(f"/api/v1/analytics/{endpoint}?workspace_id={workspace}")
        assert foreign.status_code == 404, foreign.text
    overview = await owner.get(f"/api/v1/analytics/overview?workspace_id={workspace}")
    assert overview.status_code == 200, overview.text
    assert overview.json()["total_responses"] == 1
    per_question = await owner.get(f"/api/v1/analytics/per-question?workspace_id={workspace}")
    assert per_question.status_code == 200, per_question.text
    assert per_question.json()[0]["answered"] == 1
    assert per_question.json()[0]["distribution"] == []
    erased = await owner.request(
        "DELETE",
        f"/api/v1/privacy/responses/{b.ids['response_id']}",
        json={"confirm_response_id": b.ids["response_id"]},
    )
    assert erased.status_code == 204, erased.text
    assert (await owner.get(f"/api/v1/responses/{b.ids['analysis_id']}")).status_code == 404
    assert (await owner.get(f"/api/v1/tickets/{b.ids['ticket_id']}")).status_code == 404
    assert (await owner.get(f"/api/v1/exports/{b.ids['export_id']}/download")).status_code == 410
    retry = await owner.post(
        f"/api/v1/imports/{b.ids['import_id']}/start", json={"columns": {"comment": "comment"}}
    )
    assert retry.status_code == 409
    assert (await owner.get(f"/api/v1/analytics/overview?workspace_id={workspace}")).json()[
        "total_responses"
    ] == 0


async def test_free_plan_limit_and_invalid_public_capabilities(api: Harness) -> None:
    admin, _ = await api.register("Quota", "quota@a.vn")
    downgraded = await admin.post("/api/v1/billing/mock-subscription", json={"plan_code": "free"})
    assert downgraded.status_code == 200, downgraded.text
    limited = await admin.post("/api/v1/workspaces", json={"name": "Extra"})
    assert limited.status_code == 409 and limited.json()["error"]["code"] == "PLAN_LIMIT"
    guest = api.client()
    for path in ("assets/invalid", "email/invalid/open", "email/invalid/click", "reports/invalid"):
        response = await guest.get(f"/api/v1/public/{path}")
        assert response.status_code == 404, response.text
