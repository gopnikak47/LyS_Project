"""FR-04 lớp 4: tenant A không đọc/ghi được dữ liệu tenant B qua BẤT KỲ endpoint nào.

`CASES` liệt kê mọi endpoint có tham số định danh trong đường dẫn. Test
`test_every_parameterized_endpoint_is_covered` sẽ đỏ nếu thêm endpoint mới mà quên bổ sung
vào đây — bắt buộc người viết endpoint nghĩ tới cô lập tenant.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import jwt
import pytest
from fastapi.routing import APIRoute

from tests.api.conftest import Harness

pytestmark = pytest.mark.db


@dataclass
class TenantB:
    ids: dict[str, str]


Case = tuple[str, str, Callable[[TenantB], dict[str, Any] | None]]

# (method, path template, body builder). Placeholder {xxx} lấy từ dữ liệu của tenant B.
CASES: list[Case] = [
    ("GET", "/api/v1/workspaces/{workspace_id}", lambda b: None),
    ("PATCH", "/api/v1/workspaces/{workspace_id}", lambda b: {"name": "chiem quyen"}),
    ("POST", "/api/v1/workspaces/{workspace_id}/delete", lambda b: {"confirm_name": "WS B"}),
    ("PATCH", "/api/v1/members/{membership_id}", lambda b: {"role": "VIEWER"}),
    ("DELETE", "/api/v1/members/{membership_id}", lambda b: None),
    ("DELETE", "/api/v1/invitations/{invitation_id}", lambda b: None),
    ("GET", "/api/v1/workspaces/{workspace_id}/topics", lambda b: None),
    ("POST", "/api/v1/workspaces/{workspace_id}/topics", lambda b: {"name": "Chen ngang"}),
    ("PATCH", "/api/v1/topics/{topic_id}", lambda b: {"name": "Bi sua"}),
    ("DELETE", "/api/v1/topics/{topic_id}", lambda b: None),
    (
        "POST",
        "/api/v1/workspaces/{workspace_id}/topics/merge",
        lambda b: {"source_ids": [b.ids["topic_id"]], "target_id": b.ids["topic2_id"]},
    ),
    (
        "PUT",
        "/api/v1/workspaces/{workspace_id}/topics/order",
        lambda b: {"ids": [b.ids["topic_id"]]},
    ),
    (
        "POST",
        "/api/v1/workspaces/{workspace_id}/topics/apply-template",
        lambda b: {"template_code": "it", "replace": True},
    ),
    ("POST", "/api/v1/workspaces/{workspace_id}/topics/reanalyze", lambda b: None),
]

CASES += [
    ("GET", "/api/v1/surveys/{survey_id}", lambda b: None),
    ("PUT", "/api/v1/surveys/{survey_id}", lambda b: {"title": "B", "questions": []}),
    *[
        ("POST", "/api/v1/surveys/{survey_id}/" + action, lambda b: None)
        for action in ("publish", "close", "duplicate")
    ],
    ("DELETE", "/api/v1/surveys/{survey_id}?confirm_title=B", lambda b: None),
    ("GET", "/api/v1/surveys/{survey_id}/share", lambda b: None),
    ("GET", "/api/v1/surveys/{survey_id}/qr", lambda b: None),
    ("GET", "/api/v1/surveys/{survey_id}/email-invitations", lambda b: None),
    ("POST", "/api/v1/surveys/{survey_id}/email-invitations", lambda b: {"recipients": ["x@a.vn"]}),
    ("GET", "/api/v1/responses/{analysis_id}", lambda b: None),
    ("GET", "/api/v1/analyses/{analysis_id}/corrections", lambda b: None),
    ("POST", "/api/v1/analyses/{analysis_id}/corrections", lambda b: {"sentiment": "positive"}),
    ("POST", "/api/v1/corrections/{correction_id}/undo", lambda b: None),
    ("POST", "/api/v1/corrections/{correction_id}/review?approved=true", lambda b: None),
    ("GET", "/api/v1/imports/{job_id}", lambda b: None),
    ("GET", "/api/v1/imports/{job_id}/errors", lambda b: None),
    ("POST", "/api/v1/imports/{job_id}/start", lambda b: {"columns": {"comment": "comment"}}),
    ("GET", "/api/v1/exports/{job_id}", lambda b: None),
    ("GET", "/api/v1/exports/{job_id}/download", lambda b: None),
    ("GET", "/api/v1/tickets/{ticket_id}", lambda b: None),
    ("PATCH", "/api/v1/tickets/{ticket_id}", lambda b: {"note": "x"}),
    ("DELETE", "/api/v1/report-schedules/{schedule_id}", lambda b: None),
    (
        "DELETE",
        "/api/v1/privacy/responses/{response_id}",
        lambda b: {"confirm_response_id": b.ids["response_id"]},
    ),
    ("POST", "/api/v1/surveys/{survey_id}/assets", lambda b: None),
    ("POST", "/api/v1/surveys/{survey_id}/questions/import", lambda b: None),
]

# Endpoint có tham số nhưng không định danh dữ liệu tenant (token công khai một lần).
EXEMPT = {
    ("GET", "/api/v1/public/invitations/{token}"),
    ("POST", "/api/v1/public/invitations/{token}/accept"),
    # Public slug is intentionally shared. Session/submission tokens are tested separately.
    ("GET", "/api/v1/public/surveys/{slug}"),
    ("POST", "/api/v1/public/surveys/{slug}/session"),
    ("POST", "/api/v1/public/surveys/{slug}/responses"),
    ("POST", "/api/v1/public/surveys/{slug}/uploads"),
    ("GET", "/api/v1/public/assets/{token}"),
    ("GET", "/api/v1/public/email/{token}/open"),
    ("GET", "/api/v1/public/email/{token}/click"),
    ("GET", "/api/v1/public/reports/{token}"),
    ("POST", "/api/v1/templates/{code}/use"),
}


async def _setup(api: Harness) -> tuple[Any, TenantB, Any]:
    client_a, _ = await api.register("Tenant A", "a@a.vn")
    client_b, _ = await api.register("Tenant B", "b@b.vn")
    ws_b = (await client_b.post("/api/v1/workspaces", json={"name": "WS B"})).json()
    await api.invite_and_accept(client_b, "nv@b.vn", role="ANALYST")
    inv = (
        await client_b.post("/api/v1/invitations", json={"email": "cho@b.vn", "role": "VIEWER"})
    ).json()
    members_b = (await client_b.get("/api/v1/members")).json()
    analyst_b = next(m for m in members_b if m["email"] == "nv@b.vn")
    topics_b = (await client_b.get(f"/api/v1/workspaces/{ws_b['id']}/topics")).json()["topics"]
    if not topics_b:
        await client_b.post(
            f"/api/v1/workspaces/{ws_b['id']}/topics/apply-template",
            json={"template_code": "retail"},
        )
        topics_b = (await client_b.get(f"/api/v1/workspaces/{ws_b['id']}/topics")).json()["topics"]
    ids = {
        "workspace_id": ws_b["id"],
        "membership_id": analyst_b["id"],
        "invitation_id": inv["id"],
        "topic_id": topics_b[0]["id"],
        "topic2_id": topics_b[1]["id"],
    }

    survey_res = await client_b.post(
        "/api/v1/surveys",
        json={
            "workspace_id": ws_b["id"],
            "title": "B",
            "questions": [{"code": "comment", "type": "text", "title": {"vi": "Góp ý"}}],
        },
    )
    assert survey_res.status_code == 201, survey_res.text
    survey = survey_res.json()
    pub = await client_b.post(f"/api/v1/surveys/{survey['id']}/publish")
    assert pub.status_code == 200, pub.text
    guest = api.client()
    session = (await guest.post(f"/api/v1/public/surveys/{survey['slug']}/session")).json()
    secret = api.app.state.settings.secret_key.get_secret_value()
    claims = jwt.decode(session["token"], secret, algorithms=["HS256"], audience="survey-submit")
    claims["iat"] = int(time.time()) - 3
    token = jwt.encode(claims, secret, algorithm="HS256")
    submitted = await guest.post(
        f"/api/v1/public/surveys/{survey['slug']}/responses",
        json={"token": token, "answers": {"comment": "rất tệ"}},
    )
    assert submitted.status_code == 201, submitted.text
    feedback = (await client_b.get(f"/api/v1/responses?workspace_id={ws_b['id']}")).json()["items"][
        0
    ]
    corrected = await client_b.post(
        f"/api/v1/analyses/{feedback['id']}/corrections", json={"sentiment": "negative"}
    )
    assert corrected.status_code == 200, corrected.text
    correction = (await client_b.get(f"/api/v1/analyses/{feedback['id']}/corrections")).json()[0]
    ticket = (await client_b.get(f"/api/v1/tickets?workspace_id={ws_b['id']}")).json()["items"][0]
    imported = await client_b.post(
        f"/api/v1/imports?survey_id={survey['id']}",
        files={"file": ("input.csv", b"comment\nhello\n", "text/csv")},
    )
    assert imported.status_code == 201, imported.text
    exported = await client_b.post(
        "/api/v1/exports", json={"kind": "xlsx", "filters": {"workspace_id": ws_b["id"]}}
    )
    assert exported.status_code == 202, exported.text
    schedule = await client_b.post(
        "/api/v1/report-schedules",
        json={
            "workspace_id": ws_b["id"],
            "recipients": ["b@b.vn"],
            "cadence": "week",
            "next_run_at": "2027-01-01T00:00:00Z",
            "filters": {"workspace_id": ws_b["id"]},
        },
    )
    assert schedule.status_code == 201, schedule.text
    ids.update(
        submit_token=token,
        slug=survey["slug"],
        survey_id=survey["id"],
        analysis_id=feedback["id"],
        response_id=submitted.json()["response_id"],
        correction_id=correction["id"],
        ticket_id=ticket["id"],
        import_id=imported.json()["id"],
        export_id=exported.json()["id"],
        schedule_id=schedule.json()["id"],
    )
    return client_a, TenantB(ids), client_b


async def test_tenant_a_cannot_touch_tenant_b_resources(api: Harness) -> None:
    client_a, b, client_b = await _setup(api)
    for method, template, body in CASES:
        ids = {**b.ids, "job_id": b.ids["export_id" if "/exports/" in template else "import_id"]}
        path = template.format(**ids)
        if template.endswith(("/assets", "/questions/import")):
            res = await client_a.request(
                method, path, files={"file": ("image.png", b"invalid", "image/png")}
            )
        else:
            res = await client_a.request(method, path, json=body(b))
        assert res.status_code == 404, f"{method} {path} → {res.status_code}: {res.text}"
        assert "WS B" not in res.text and "nv@b.vn" not in res.text

    # Dữ liệu B còn nguyên vẹn sau mọi nỗ lực của A.
    ws = await client_b.get(f"/api/v1/workspaces/{b.ids['workspace_id']}")
    assert ws.status_code == 200
    assert ws.json()["name"] == "WS B"
    members = {m["email"]: m["role"] for m in (await client_b.get("/api/v1/members")).json()}
    assert members["nv@b.vn"] == "ANALYST"
    assert len((await client_b.get("/api/v1/invitations")).json()) == 1
    topics = (await client_b.get(f"/api/v1/workspaces/{b.ids['workspace_id']}/topics")).json()
    assert topics["topics"][0]["id"] == b.ids["topic_id"]
    assert topics["template_code"] == "retail"
    assert api.queue.of("worker.tasks.nlp.reanalyze_workspace") == []


async def test_list_endpoints_only_return_own_tenant(api: Harness) -> None:
    client_a, _, _ = await _setup(api)
    workspaces = [w["name"] for w in (await client_a.get("/api/v1/workspaces")).json()]
    members = [m["email"] for m in (await client_a.get("/api/v1/members")).json()]
    invitations = (await client_a.get("/api/v1/invitations")).json()
    tenant = (await client_a.get("/api/v1/tenants/me")).json()
    assert workspaces == ["Không gian chung"]
    assert members == ["a@a.vn"]
    assert invitations == []
    assert tenant["name"] == "Tenant A"


async def test_cannot_switch_into_foreign_tenant(api: Harness) -> None:
    client_a, _, client_b = await _setup(api)
    tenant_b = (await client_b.get("/api/v1/tenants/me")).json()
    res = await client_a.post("/api/v1/auth/switch-tenant", json={"tenant_id": tenant_b["id"]})
    assert res.status_code == 403


async def test_invite_cannot_reference_foreign_workspace(api: Harness) -> None:
    client_a, b, _ = await _setup(api)
    res = await client_a.post(
        "/api/v1/invitations",
        json={"email": "x@a.vn", "role": "ANALYST", "workspace_ids": [b.ids["workspace_id"]]},
    )
    assert res.status_code == 404


def test_every_parameterized_endpoint_is_covered(api_routes: list[tuple[str, str]]) -> None:
    covered = {(m, p.split("?")[0]) for m, p, _ in CASES} | EXEMPT
    missing = [r for r in api_routes if r not in covered]
    assert missing == [], f"Thêm các endpoint sau vào CASES/EXEMPT của test cô lập: {missing}"


@pytest.fixture
def api_routes() -> list[tuple[str, str]]:
    from app.main import create_app

    app = create_app()
    routes: list[tuple[str, str]] = []
    for route in app.routes:
        if isinstance(route, APIRoute) and "{" in route.path and route.path.startswith("/api/v1"):
            routes.extend((method, route.path) for method in sorted(route.methods or ()))
    return routes
