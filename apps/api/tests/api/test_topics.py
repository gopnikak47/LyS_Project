"""FR-12 (quản lý chủ đề theo workspace) và FR-13 (nạp đúng bộ chủ đề cho pipeline)."""

from __future__ import annotations

import uuid
from typing import Any

import httpx2 as httpx
import pytest
from sqlalchemy import select

from app.core.errors import NotFoundError
from app.db.tenant import system_session
from app.models import Response, Survey, TextAnalysis
from app.services.topics import load_topic_catalog
from tests.api.conftest import Harness

pytestmark = pytest.mark.db


async def _workspace(client: httpx.AsyncClient) -> dict[str, Any]:
    data: dict[str, Any] = (await client.get("/api/v1/workspaces")).json()[0]
    return data


async def _topics(client: httpx.AsyncClient, ws_id: str) -> dict[str, Any]:
    res = await client.get(f"/api/v1/workspaces/{ws_id}/topics")
    assert res.status_code == 200, res.text
    data: dict[str, Any] = res.json()
    return data


async def _add_analysis(api: Harness, tenant_id: str, ws_id: str, topic_ids: list[str]) -> str:
    """Tạo một phân tích giả có gắn sẵn chủ đề (bỏ qua NLP) để kiểm tra xóa/gộp."""
    async with system_session(api.app.state.resources.session_factory) as db:
        survey = Survey(
            tenant_id=uuid.UUID(tenant_id),
            workspace_id=uuid.UUID(ws_id),
            title="KS",
            slug=f"ks-{uuid.uuid4().hex[:8]}",
        )
        db.add(survey)
        await db.flush()
        response = Response(
            tenant_id=survey.tenant_id, survey_id=survey.id, workspace_id=survey.workspace_id
        )
        db.add(response)
        await db.flush()
        analysis = TextAnalysis(
            tenant_id=survey.tenant_id,
            response_id=response.id,
            workspace_id=survey.workspace_id,
            survey_id=survey.id,
            text="Món ngon nhưng phục vụ chậm",
            topic_ids=[uuid.UUID(t) for t in topic_ids],
            topic_scores=dict.fromkeys(topic_ids, 0.8),
            status="done",
        )
        db.add(analysis)
        await db.flush()
        return str(analysis.id)


async def _analysis_topics(api: Harness, analysis_id: str) -> list[str]:
    async with system_session(api.app.state.resources.session_factory) as db:
        row = await db.get(TextAnalysis, uuid.UUID(analysis_id))
        assert row is not None
        return sorted(str(t) for t in row.topic_ids)


async def test_registered_restaurant_gets_industry_template(api: Harness) -> None:
    client, _ = await api.register("Quán Phở", "pho@pho.vn", industry="restaurant")
    data = await _topics(client, (await _workspace(client))["id"])
    assert [t["name"] for t in data["topics"]] == [
        "Món ăn",
        "Phục vụ",
        "Giá cả",
        "Không gian",
        "Vệ sinh",
    ]
    assert data["template_code"] == "restaurant"
    assert all(t["keywords"] for t in data["topics"])


async def test_topic_crud_validates_and_bumps_version(api: Harness) -> None:
    client, _ = await api.register("Quán Phở", "pho@pho.vn")
    ws = await _workspace(client)
    before = (await _topics(client, ws["id"]))["version"]

    res = await client.post(
        f"/api/v1/workspaces/{ws['id']}/topics",
        json={"name": "Giao hàng", "keywords": ["ship", "Ship ", "giao trễ"], "color": "#ef4444"},
    )
    assert res.status_code == 201
    topic = res.json()
    assert topic["keywords"] == [
        "ship",
        "giao trễ",
    ]  # gộp từ khóa trùng (không phân biệt hoa thường)

    dup = await client.post(f"/api/v1/workspaces/{ws['id']}/topics", json={"name": "giao hàng"})
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "TOPIC_EXISTS"

    res = await client.patch(
        f"/api/v1/topics/{topic['id']}",
        json={"description": "Tốc độ giao đồ ăn", "is_active": False},
    )
    assert res.status_code == 200
    assert res.json()["is_active"] is False
    assert (await _topics(client, ws["id"]))["version"] == before + 2


async def test_delete_and_merge_update_existing_analyses(api: Harness) -> None:
    client, body = await api.register("Quán Phở", "pho@pho.vn")
    ws = await _workspace(client)
    topics = {t["name"]: t["id"] for t in (await _topics(client, ws["id"]))["topics"]}
    tenant_id = body["tenant"]["id"]
    a1 = await _add_analysis(api, tenant_id, ws["id"], [topics["Món ăn"], topics["Phục vụ"]])
    a2 = await _add_analysis(api, tenant_id, ws["id"], [topics["Vệ sinh"]])

    # Gộp "Phục vụ" + "Vệ sinh" vào "Món ăn": a1 không bị trùng, a2 được chuyển nhãn.
    res = await client.post(
        f"/api/v1/workspaces/{ws['id']}/topics/merge",
        json={"source_ids": [topics["Phục vụ"], topics["Vệ sinh"]], "target_id": topics["Món ăn"]},
    )
    assert res.status_code == 200
    assert "Phục vụ" in res.json()["keywords"]
    assert await _analysis_topics(api, a1) == [topics["Món ăn"]]
    assert await _analysis_topics(api, a2) == [topics["Món ăn"]]
    usage = {t["name"]: t["usage_count"] for t in (await _topics(client, ws["id"]))["topics"]}
    assert usage["Món ăn"] == 2
    assert "Phục vụ" not in usage

    assert (await client.delete(f"/api/v1/topics/{topics['Món ăn']}")).status_code == 200
    assert await _analysis_topics(api, a1) == []


async def test_reorder_and_apply_template(api: Harness) -> None:
    client, _ = await api.register("Phần mềm X", "it@x.vn", industry="it")
    ws = await _workspace(client)
    ids = [t["id"] for t in (await _topics(client, ws["id"]))["topics"]]
    res = await client.put(f"/api/v1/workspaces/{ws['id']}/topics/order", json={"ids": ids[::-1]})
    assert res.status_code == 200
    assert [t["id"] for t in (await _topics(client, ws["id"]))["topics"]] == ids[::-1]
    bad = await client.put(f"/api/v1/workspaces/{ws['id']}/topics/order", json={"ids": ids[:2]})
    assert bad.status_code == 400

    res = await client.post(
        f"/api/v1/workspaces/{ws['id']}/topics/apply-template",
        json={"template_code": "hotel", "replace": False},
    )
    names = [t["name"] for t in res.json()["topics"]]
    assert "Giao diện" in names and "Phòng ở" in names

    res = await client.post(
        f"/api/v1/workspaces/{ws['id']}/topics/apply-template",
        json={"template_code": "education", "replace": True},
    )
    assert res.json()["topics"][0]["name"] == "Giảng viên"
    assert "Giao diện" not in [t["name"] for t in res.json()["topics"]]


async def test_reanalyze_marks_pending_and_enqueues_nlp_job(api: Harness) -> None:
    client, body = await api.register("Quán Phở", "pho@pho.vn")
    ws = await _workspace(client)
    analysis = await _add_analysis(api, body["tenant"]["id"], ws["id"], [])
    res = await client.post(f"/api/v1/workspaces/{ws['id']}/topics/reanalyze")
    assert res.status_code == 202
    assert res.json() == {"queued": True, "pending": 1}
    jobs = [(name, kw, q) for name, kw, q in api.queue.sent if name.endswith("reanalyze_workspace")]
    assert jobs == [
        (
            "worker.tasks.nlp.reanalyze_workspace",
            {"tenant_id": body["tenant"]["id"], "workspace_id": ws["id"]},
            "nlp",
        )
    ]
    async with system_session(api.app.state.resources.session_factory) as db:
        status = (
            await db.execute(select(TextAnalysis.status).where(TextAnalysis.id == analysis))
        ).scalar_one()
    assert status == "pending"


async def test_viewer_cannot_manage_topics(api: Harness) -> None:
    admin, _ = await api.register("Quán Phở", "pho@pho.vn")
    ws = await _workspace(admin)
    viewer, _ = await api.invite_and_accept(admin, "xem@pho.vn", role="VIEWER")
    assert (await viewer.get(f"/api/v1/workspaces/{ws['id']}/topics")).status_code == 200
    res = await viewer.post(f"/api/v1/workspaces/{ws['id']}/topics", json={"name": "Mới"})
    assert res.status_code == 403


async def test_topic_catalog_never_mixes_industries_or_tenants(api: Harness) -> None:
    """FR-13: pipeline chỉ nạp đúng bộ chủ đề của workspace đang phân tích."""
    rest, body_r = await api.register("Nhà hàng", "a@nh.vn", industry="restaurant")
    tech, body_t = await api.register("Phần mềm", "b@pm.vn", industry="it")
    ws_r = await _workspace(rest)
    ws_t = await _workspace(tech)
    # Tắt một chủ đề: không được nạp vào pipeline.
    pv = next(t for t in (await _topics(rest, ws_r["id"]))["topics"] if t["name"] == "Phục vụ")
    await rest.patch(f"/api/v1/topics/{pv['id']}", json={"is_active": False})

    factory = api.app.state.resources.session_factory
    async with system_session(factory) as db:
        cat_r = await load_topic_catalog(
            db, uuid.UUID(body_r["tenant"]["id"]), uuid.UUID(ws_r["id"])
        )
        cat_t = await load_topic_catalog(
            db, uuid.UUID(body_t["tenant"]["id"]), uuid.UUID(ws_t["id"])
        )
        with pytest.raises(NotFoundError):
            # Workspace của tenant nhà hàng nhưng truyền tenant phần mềm → từ chối.
            await load_topic_catalog(db, uuid.UUID(body_t["tenant"]["id"]), uuid.UUID(ws_r["id"]))

    assert [t.name for t in cat_r.topics] == ["Món ăn", "Giá cả", "Không gian", "Vệ sinh"]
    assert [t.name for t in cat_t.topics] == [
        "Giao diện",
        "Tính năng",
        "Hiệu năng",
        "Lỗi hệ thống",
        "Hỗ trợ",
    ]
    assert not {t.id for t in cat_r.topics} & {t.id for t in cat_t.topics}
    assert cat_r.threshold == pytest.approx(0.35)
