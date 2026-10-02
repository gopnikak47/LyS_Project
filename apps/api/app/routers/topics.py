"""Chủ đề theo workspace (FR-12): /api/v1/workspaces/{id}/topics, /api/v1/topics/{id}."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.core.auth import Ctx, ResourcesDep
from app.domain.topic_templates import INDUSTRY_TEMPLATES
from app.schemas.common import OkResponse
from app.schemas.topics import (
    ApplyTemplate,
    ReanalyzeOut,
    TemplateOut,
    TemplateTopicOut,
    TopicCreate,
    TopicMerge,
    TopicOrder,
    TopicOut,
    TopicSetOut,
    TopicUpdate,
)
from app.services.topics import TopicService

router = APIRouter(tags=["topics"])


@router.get(
    "/topic-templates", response_model=list[TemplateOut], summary="Bộ chủ đề mẫu theo ngành"
)
async def list_templates(ctx: Ctx) -> list[TemplateOut]:
    return [
        TemplateOut(
            code=t.code,
            name=t.name,
            topics=[
                TemplateTopicOut(
                    name=x.name, description=x.description, keywords=list(x.keywords), color=x.color
                )
                for x in t.topics
            ],
        )
        for t in INDUSTRY_TEMPLATES.values()
    ]


@router.get("/workspaces/{workspace_id}/topics", response_model=TopicSetOut)
async def get_topics(workspace_id: uuid.UUID, ctx: Ctx) -> TopicSetOut:
    return await TopicService(ctx.db, ctx.principal).get_set(workspace_id)


@router.post(
    "/workspaces/{workspace_id}/topics",
    response_model=TopicOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_topic(workspace_id: uuid.UUID, data: TopicCreate, ctx: Ctx) -> TopicOut:
    topic = await TopicService(ctx.db, ctx.principal).create(workspace_id, data)
    return TopicOut.model_validate(topic)


@router.patch("/topics/{topic_id}", response_model=TopicOut)
async def update_topic(topic_id: uuid.UUID, data: TopicUpdate, ctx: Ctx) -> TopicOut:
    topic = await TopicService(ctx.db, ctx.principal).update(topic_id, data)
    return TopicOut.model_validate(topic)


@router.delete("/topics/{topic_id}", response_model=OkResponse)
async def delete_topic(topic_id: uuid.UUID, ctx: Ctx) -> OkResponse:
    await TopicService(ctx.db, ctx.principal).delete(topic_id)
    return OkResponse()


@router.post("/workspaces/{workspace_id}/topics/merge", response_model=TopicOut)
async def merge_topics(workspace_id: uuid.UUID, data: TopicMerge, ctx: Ctx) -> TopicOut:
    topic = await TopicService(ctx.db, ctx.principal).merge(
        workspace_id, data.source_ids, data.target_id
    )
    return TopicOut.model_validate(topic)


@router.put("/workspaces/{workspace_id}/topics/order", response_model=OkResponse)
async def reorder_topics(workspace_id: uuid.UUID, data: TopicOrder, ctx: Ctx) -> OkResponse:
    await TopicService(ctx.db, ctx.principal).reorder(workspace_id, data.ids)
    return OkResponse()


@router.post("/workspaces/{workspace_id}/topics/apply-template", response_model=TopicSetOut)
async def apply_template(workspace_id: uuid.UUID, data: ApplyTemplate, ctx: Ctx) -> TopicSetOut:
    service = TopicService(ctx.db, ctx.principal)
    await service.apply_template(workspace_id, data.template_code, data.replace)
    return await service.get_set(workspace_id)


@router.post(
    "/workspaces/{workspace_id}/topics/reanalyze",
    response_model=ReanalyzeOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Phân tích lại phản hồi cũ theo bộ chủ đề mới (job nền)",
)
async def reanalyze(workspace_id: uuid.UUID, ctx: Ctx, resources: ResourcesDep) -> ReanalyzeOut:
    pending = await TopicService(ctx.db, ctx.principal).request_reanalysis(
        workspace_id, resources.queue
    )
    return ReanalyzeOut(queued=True, pending=pending)
