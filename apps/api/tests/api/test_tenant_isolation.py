"""FR-04 lớp 4: tenant A không đọc/ghi được dữ liệu tenant B qua BẤT KỲ endpoint nào.

`CASES` liệt kê mọi endpoint có tham số định danh trong đường dẫn. Test
`test_every_parameterized_endpoint_is_covered` sẽ đỏ nếu thêm endpoint mới mà quên bổ sung
vào đây — bắt buộc người viết endpoint nghĩ tới cô lập tenant.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

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
]

# Endpoint có tham số nhưng không định danh dữ liệu tenant (token công khai một lần).
EXEMPT = {
    ("GET", "/api/v1/public/invitations/{token}"),
    ("POST", "/api/v1/public/invitations/{token}/accept"),
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
    ids = {"workspace_id": ws_b["id"], "membership_id": analyst_b["id"], "invitation_id": inv["id"]}
    return client_a, TenantB(ids), client_b


async def test_tenant_a_cannot_touch_tenant_b_resources(api: Harness) -> None:
    client_a, b, client_b = await _setup(api)
    for method, template, body in CASES:
        path = template.format(**b.ids)
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
    covered = {(m, p) for m, p, _ in CASES} | EXEMPT
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
