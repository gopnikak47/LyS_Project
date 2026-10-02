"""FR-01: đăng ký doanh nghiệp, đăng nhập/đăng xuất, refresh xoay vòng, quên/đặt lại mật khẩu."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from tests.api.conftest import PASSWORD, Harness

pytestmark = pytest.mark.db


async def test_register_creates_tenant_admin_and_default_workspace(api: Harness) -> None:
    client, body = await api.register("Nhà hàng Hương Sen", "chu@huongsen.vn")
    assert body["role"] == "ADMIN"
    assert body["tenant"]["slug"] == "nha-hang-huong-sen"
    assert "member:manage" in body["permissions"]
    assert [m["tenant_name"] for m in body["memberships"]] == ["Nhà hàng Hương Sen"]

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "chu@huongsen.vn"

    workspaces = (await client.get("/api/v1/workspaces")).json()
    assert [w["name"] for w in workspaces] == ["Không gian chung"]


async def test_session_cookies_are_http_only_except_csrf(api: Harness) -> None:
    client = api.client()
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Quán Mộc",
            "full_name": "Chủ Quán",
            "email": "moc@quan.vn",
            "password": PASSWORD,
        },
    )
    cookies = {c.split("=", 1)[0]: c for c in res.headers.get_list("set-cookie")}
    assert "HttpOnly" in cookies["lys_access"]
    assert "HttpOnly" in cookies["lys_refresh"]
    assert "Path=/api/v1/auth" in cookies["lys_refresh"]
    assert "HttpOnly" not in cookies["lys_csrf"]
    assert all("SameSite=lax" in c for c in cookies.values())


async def test_register_duplicate_email_conflicts(api: Harness) -> None:
    await api.register("Công ty A", "trung@email.vn")
    client = api.client()
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Công ty B",
            "full_name": "Ai Đó",
            "email": "TRUNG@email.vn",
            "password": PASSWORD,
        },
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "EMAIL_TAKEN"


@pytest.mark.parametrize(
    ("password", "message"),
    [("ngan1", "at least 8"), ("chicochu", "chữ và số"), ("12345678", "chữ và số")],
)
async def test_register_rejects_weak_passwords(api: Harness, password: str, message: str) -> None:
    res = await api.client().post(
        "/api/v1/auth/register",
        json={
            "company_name": "Công ty",
            "full_name": "Tên Ai",
            "email": "a@b.vn",
            "password": password,
        },
    )
    assert res.status_code == 422
    assert message in str(res.json()["error"]["details"])


async def test_login_errors_do_not_reveal_whether_email_exists(api: Harness) -> None:
    await api.register("Công ty", "co@that.vn")
    _, wrong_pw = await api.login("co@that.vn", "SaiMatKhau1")
    _, unknown = await api.login("khong@co.vn", "SaiMatKhau1")
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json()["error"]["message"] == unknown.json()["error"]["message"]
    assert wrong_pw.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_account_locks_after_repeated_failures(api: Harness) -> None:
    await api.register("Công ty", "khoa@tk.vn")
    for _ in range(5):
        _, res = await api.login("khoa@tk.vn", "SaiMatKhau1")
        assert res.status_code == 401
    # Đúng mật khẩu nhưng vẫn bị khóa tạm.
    _, res = await api.login("khoa@tk.vn", PASSWORD)
    assert res.status_code == 423
    assert res.json()["error"]["code"] == "ACCOUNT_LOCKED"
    assert "phút" in res.json()["error"]["message"]


async def test_login_rate_limited_per_email(harness_factory: Callable[..., Any]) -> None:
    async with harness_factory(login_rate_per_minute=3, login_max_attempts=100) as api:
        await api.register("Công ty", "rl@tk.vn")
        codes = [(await api.login("rl@tk.vn", "SaiMatKhau1"))[1].status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]


async def test_unsafe_requests_require_csrf_header(api: Harness) -> None:
    client, _ = await api.register("Công ty", "csrf@tk.vn")
    del client.headers["X-CSRF-Token"]
    res = await client.post("/api/v1/workspaces", json={"name": "Không gian mới"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_FAILED"
    client.headers["X-CSRF-Token"] = "gia-mao"
    res = await client.post("/api/v1/workspaces", json={"name": "Không gian mới"})
    assert res.status_code == 403
    # GET không cần CSRF.
    assert (await client.get("/api/v1/workspaces")).status_code == 200


async def test_refresh_rotates_and_detects_reuse(api: Harness) -> None:
    client, _ = await api.register("Công ty", "rf@tk.vn")
    old_refresh = client.cookies.get("lys_refresh", path="/api/v1/auth")
    res = await client.post("/api/v1/auth/refresh")
    assert res.status_code == 200
    client.headers["X-CSRF-Token"] = res.json()["csrf_token"]
    new_refresh = client.cookies.get("lys_refresh", path="/api/v1/auth")
    assert new_refresh and new_refresh != old_refresh

    # Kẻ gian dùng lại refresh cũ → bị từ chối và cả "họ" token bị thu hồi.
    thief = api.client()
    thief.cookies.set(
        "lys_refresh", old_refresh or "", domain="testserver.local", path="/api/v1/auth"
    )
    thief.cookies.set("lys_csrf", "x", domain="testserver.local")
    thief.headers["X-CSRF-Token"] = "x"
    assert (await thief.post("/api/v1/auth/refresh")).status_code == 401
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401


async def test_logout_revokes_refresh(api: Harness) -> None:
    client, _ = await api.register("Công ty", "lo@tk.vn")
    refresh = client.cookies.get("lys_refresh", path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/logout")).status_code == 200
    assert client.cookies.get("lys_access") is None
    replay = api.client()
    replay.cookies.set("lys_refresh", refresh or "", domain="testserver.local", path="/api/v1/auth")
    replay.cookies.set("lys_csrf", "x", domain="testserver.local")
    replay.headers["X-CSRF-Token"] = "x"
    assert (await replay.post("/api/v1/auth/refresh")).status_code == 401


async def test_forgot_and_reset_password_flow(api: Harness) -> None:
    client, _ = await api.register("Công ty", "quen@tk.vn")
    res = await api.client().post("/api/v1/auth/forgot-password", json={"email": "quen@tk.vn"})
    assert res.status_code == 202
    # Email không tồn tại vẫn trả 202 (không dò được tài khoản).
    res = await api.client().post("/api/v1/auth/forgot-password", json={"email": "khong@co.vn"})
    assert res.status_code == 202

    emails = api.queue.of("worker.tasks.email.send_email")
    assert len(emails) == 1
    assert emails[0]["to"] == "quen@tk.vn"
    assert "Đặt lại mật khẩu" in emails[0]["subject"]
    token = emails[0]["text"].split("token=")[1].split()[0]

    reset = await api.client().post(
        "/api/v1/auth/reset-password", json={"token": token, "password": "MatKhauMoi9"}
    )
    assert reset.status_code == 200
    # Token chỉ dùng một lần.
    again = await api.client().post(
        "/api/v1/auth/reset-password", json={"token": token, "password": "MatKhauMoi9"}
    )
    assert again.status_code == 400
    assert again.json()["error"]["code"] == "TOKEN_INVALID"

    # Phiên cũ bị vô hiệu, mật khẩu cũ không dùng được, mật khẩu mới đăng nhập được.
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    assert (await api.login("quen@tk.vn", PASSWORD))[1].status_code == 401
    assert (await api.login("quen@tk.vn", "MatKhauMoi9"))[1].status_code == 200


async def test_change_password_keeps_current_session(api: Harness) -> None:
    client, _ = await api.register("Công ty", "doi@tk.vn")
    other_device, _ = await api.login("doi@tk.vn")
    res = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "MatKhauMoi9"},
    )
    assert res.status_code == 200
    client.headers["X-CSRF-Token"] = res.json()["csrf_token"]
    assert (await client.get("/api/v1/auth/me")).status_code == 200
    assert (await other_device.get("/api/v1/auth/me")).status_code == 401

    wrong = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "SaiMatKhau1", "new_password": "MatKhauMoi8"},
    )
    assert wrong.status_code == 401


async def test_update_profile(api: Harness) -> None:
    client, _ = await api.register("Công ty", "hs@tk.vn")
    res = await client.patch("/api/v1/auth/me", json={"full_name": "Tên Mới", "locale": "en"})
    assert res.status_code == 200
    assert res.json()["full_name"] == "Tên Mới"
    assert res.json()["locale"] == "en"


async def test_unauthenticated_requests_are_rejected(api: Harness) -> None:
    client = api.client()
    for path in ("/api/v1/auth/me", "/api/v1/workspaces", "/api/v1/members"):
        res = await client.get(path)
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "UNAUTHORIZED"
    client.cookies.set("lys_access", "token.gia.mao", domain="testserver.local")
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_concurrent_registrations_with_same_company_name(api: Harness) -> None:
    import asyncio

    async def register(i: int) -> Any:
        return await api.client().post(
            "/api/v1/auth/register",
            json={
                "company_name": "Quán Ăn Trùng Tên",
                "full_name": "Chủ Quán",
                "email": f"chu{i}@trung.vn",
                "password": PASSWORD,
            },
        )

    results = await asyncio.gather(*(register(i) for i in range(4)))
    assert [r.status_code for r in results] == [201] * 4
    slugs = {r.json()["tenant"]["slug"] for r in results}
    assert len(slugs) == 4
    assert "quan-an-trung-ten" in slugs


async def test_concurrent_registrations_with_same_email(api: Harness) -> None:
    import asyncio

    async def register(i: int) -> Any:
        return await api.client().post(
            "/api/v1/auth/register",
            json={
                "company_name": f"Công ty {i}",
                "full_name": "Chủ",
                "email": "cung@email.vn",
                "password": PASSWORD,
            },
        )

    codes = sorted(r.status_code for r in await asyncio.gather(*(register(i) for i in range(3))))
    assert codes == [201, 409, 409]
