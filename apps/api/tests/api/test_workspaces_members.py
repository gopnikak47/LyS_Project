"""FR-02 (workspace) & FR-03 (thành viên, lời mời, ma trận quyền, phạm vi workspace)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db.tenant import system_session
from app.models import Topic
from tests.api.conftest import PASSWORD, Harness

pytestmark = pytest.mark.db


async def test_workspace_crud_with_soft_delete_confirmation(api: Harness) -> None:
    client, _ = await api.register("Chuỗi Cà Phê", "admin@caphe.vn")
    res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Chi nhánh Thủ Đức", "industry": "restaurant", "color": "#22c55e"},
    )
    assert res.status_code == 201
    ws = res.json()
    assert ws["color"] == "#22c55e"

    # Workspace theo ngành được tạo sẵn bộ chủ đề mẫu.
    async with system_session(api.app.state.resources.session_factory) as db:
        topics = (
            (await db.execute(select(Topic.name).where(Topic.workspace_id == ws["id"])))
            .scalars()
            .all()
        )
    assert {"Món ăn", "Phục vụ", "Giá cả", "Không gian", "Vệ sinh"} <= set(topics)

    res = await client.patch(
        f"/api/v1/workspaces/{ws['id']}",
        json={"name": "CN Thủ Đức", "settings": {"urgent_keywords": ["hư hỏng"]}},
    )
    assert res.status_code == 200
    assert res.json()["settings"]["urgent_keywords"] == ["hư hỏng"]

    res = await client.post(f"/api/v1/workspaces/{ws['id']}/delete", json={"confirm_name": "sai"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "CONFIRMATION_MISMATCH"
    res = await client.post(
        f"/api/v1/workspaces/{ws['id']}/delete", json={"confirm_name": "CN Thủ Đức"}
    )
    assert res.status_code == 200
    assert (await client.get(f"/api/v1/workspaces/{ws['id']}")).status_code == 404
    names = [w["name"] for w in (await client.get("/api/v1/workspaces")).json()]
    assert names == ["Không gian chung"]


async def test_invite_new_user_with_workspace_scope(api: Harness) -> None:
    admin, _ = await api.register("Chuỗi Cà Phê", "admin@caphe.vn")
    ws_a = (await admin.post("/api/v1/workspaces", json={"name": "CN A"})).json()
    await admin.post("/api/v1/workspaces", json={"name": "CN B"})

    analyst, session = await api.invite_and_accept(
        admin, "nv@caphe.vn", role="ANALYST", workspace_ids=[ws_a["id"]]
    )
    assert session["role"] == "ANALYST"
    assert session["all_workspaces"] is False
    assert session["workspace_ids"] == [ws_a["id"]]

    # Email mời đã được đẩy vào hàng đợi với link nhận lời mời.
    invite_mail = api.queue.of("worker.tasks.email.send_email")[0]
    assert invite_mail["to"] == "nv@caphe.vn"
    assert "/invite/" in invite_mail["text"]

    # Analyst chỉ thấy workspace được giao; truy cập workspace khác → 404.
    visible = [w["name"] for w in (await analyst.get("/api/v1/workspaces")).json()]
    assert visible == ["CN A"]
    others = (await admin.get("/api/v1/workspaces")).json()
    ws_b = next(w for w in others if w["name"] == "CN B")
    assert (await analyst.get(f"/api/v1/workspaces/{ws_b['id']}")).status_code == 404

    members = (await admin.get("/api/v1/members")).json()
    assert {m["email"]: m["role"] for m in members} == {
        "admin@caphe.vn": "ADMIN",
        "nv@caphe.vn": "ANALYST",
    }


async def test_public_invitation_lookup_and_invalid_tokens(api: Harness) -> None:
    admin, _ = await api.register("Chuỗi Cà Phê", "admin@caphe.vn")
    res = await admin.post("/api/v1/invitations", json={"email": "xem@caphe.vn", "role": "VIEWER"})
    token = res.json()["invite_url"].rsplit("/", 1)[-1]
    info = (await api.client().get(f"/api/v1/public/invitations/{token}")).json()
    assert info["tenant_name"] == "Chuỗi Cà Phê"
    assert info["user_exists"] is False

    bad = await api.client().get("/api/v1/public/invitations/token-khong-hop-le-123")
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "TOKEN_INVALID"

    # Thu hồi lời mời → không dùng được nữa.
    pending = (await admin.get("/api/v1/invitations")).json()
    assert (await admin.delete(f"/api/v1/invitations/{pending[0]['id']}")).status_code == 200
    gone = await api.client().get(f"/api/v1/public/invitations/{token}")
    assert gone.status_code == 400


async def test_existing_user_joins_second_tenant_and_switches(api: Harness) -> None:
    admin_a, _ = await api.register("Công ty A", "a@a.vn")
    _, body_b = await api.register("Công ty B", "b@b.vn")
    # Admin A mời chủ công ty B (đã có tài khoản) → xác nhận bằng mật khẩu hiện tại.
    res = await admin_a.post("/api/v1/invitations", json={"email": "b@b.vn", "role": "VIEWER"})
    token = res.json()["invite_url"].rsplit("/", 1)[-1]
    joined = api.client()
    wrong = await joined.post(
        f"/api/v1/public/invitations/{token}/accept", json={"password": "SaiMatKhau1"}
    )
    assert wrong.status_code == 401
    res = await joined.post(
        f"/api/v1/public/invitations/{token}/accept", json={"password": PASSWORD}
    )
    assert res.status_code == 200
    joined.headers["X-CSRF-Token"] = res.json()["csrf_token"]
    assert res.json()["tenant"]["name"] == "Công ty A"
    assert {m["tenant_name"] for m in res.json()["memberships"]} == {"Công ty A", "Công ty B"}

    res = await joined.post(
        "/api/v1/auth/switch-tenant", json={"tenant_id": body_b["tenant"]["id"]}
    )
    assert res.status_code == 200
    assert res.json()["tenant"]["name"] == "Công ty B"
    assert res.json()["role"] == "ADMIN"


async def test_last_admin_cannot_be_demoted_or_removed(api: Harness) -> None:
    admin, _ = await api.register("Công ty", "admin@ct.vn")
    me = next(m for m in (await admin.get("/api/v1/members")).json())
    res = await admin.patch(f"/api/v1/members/{me['id']}", json={"role": "VIEWER"})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "LAST_ADMIN"
    assert (await admin.delete(f"/api/v1/members/{me['id']}")).status_code == 409


async def test_role_change_takes_effect_immediately_and_removal_logs_out(api: Harness) -> None:
    admin, _ = await api.register("Công ty", "admin@ct.vn")
    member, _ = await api.invite_and_accept(admin, "nv@ct.vn", role="ADMIN")
    assert (await member.get("/api/v1/members")).status_code == 200

    target = next(
        m for m in (await admin.get("/api/v1/members")).json() if m["email"] == "nv@ct.vn"
    )
    res = await admin.patch(f"/api/v1/members/{target['id']}", json={"role": "VIEWER"})
    assert res.status_code == 200
    # Token cũ ghi ADMIN nhưng quyền lấy từ CSDL → bị chặn ngay.
    assert (await member.get("/api/v1/members")).status_code == 403

    assert (await admin.delete(f"/api/v1/members/{target['id']}")).status_code == 200
    assert (await member.get("/api/v1/auth/me")).status_code == 401
    assert (await member.post("/api/v1/auth/refresh")).status_code in (401, 403)


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("ADMIN", {"create_ws": 201, "members": 200, "invite": 201, "tenant": 200}),
        ("ANALYST", {"create_ws": 403, "members": 403, "invite": 403, "tenant": 403}),
        ("VIEWER", {"create_ws": 403, "members": 403, "invite": 403, "tenant": 403}),
    ],
)
async def test_permission_matrix(api: Harness, role: str, expected: dict[str, int]) -> None:
    admin, _ = await api.register("Công ty", "admin@ct.vn")
    client, _ = await api.invite_and_accept(admin, f"{role.lower()}-nv@ct.vn", role=role)
    got = {
        "create_ws": (await client.post("/api/v1/workspaces", json={"name": "Mới"})).status_code,
        "members": (await client.get("/api/v1/members")).status_code,
        "invite": (
            await client.post("/api/v1/invitations", json={"email": "x@ct.vn", "role": "VIEWER"})
        ).status_code,
        "tenant": (await client.patch("/api/v1/tenants/me", json={"name": "Tên mới"})).status_code,
    }
    assert got == expected


async def test_audit_log_records_sensitive_actions(api: Harness) -> None:
    from app.models import AuditLog

    admin, _ = await api.register("Công ty", "admin@ct.vn")
    await api.login("admin@ct.vn", "SaiMatKhau1")
    await api.invite_and_accept(admin, "nv@ct.vn")
    async with system_session(api.app.state.resources.session_factory) as db:
        actions = (await db.execute(select(AuditLog.action))).scalars().all()
    assert {
        "tenant.register",
        "auth.login_failed",
        "invitation.create",
        "invitation.accept",
    } <= set(actions)
