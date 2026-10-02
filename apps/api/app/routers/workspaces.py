"""/api/v1/workspaces — không gian khảo sát (FR-02)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.core.auth import Ctx
from app.schemas.common import OkResponse
from app.schemas.workspaces import WorkspaceCreate, WorkspaceDelete, WorkspaceOut, WorkspaceUpdate
from app.services.workspaces import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _out(ws: object, survey_count: int = 0) -> WorkspaceOut:
    out = WorkspaceOut.model_validate(ws)
    out.survey_count = survey_count
    return out


@router.get(
    "", response_model=list[WorkspaceOut], summary="Danh sách không gian được phép truy cập"
)
async def list_workspaces(ctx: Ctx) -> list[WorkspaceOut]:
    rows = await WorkspaceService(ctx.db, ctx.principal).list_accessible()
    return [_out(ws, count) for ws, count in rows]


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(data: WorkspaceCreate, ctx: Ctx) -> WorkspaceOut:
    ws = await WorkspaceService(ctx.db, ctx.principal).create(
        name=data.name, industry=data.industry, description=data.description, color=data.color
    )
    return _out(ws)


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(workspace_id: uuid.UUID, ctx: Ctx) -> WorkspaceOut:
    return _out(await WorkspaceService(ctx.db, ctx.principal).get(workspace_id))


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
async def update_workspace(
    workspace_id: uuid.UUID, data: WorkspaceUpdate, ctx: Ctx
) -> WorkspaceOut:
    ws = await WorkspaceService(ctx.db, ctx.principal).update(
        workspace_id,
        name=data.name,
        description=data.description,
        industry=data.industry,
        color=data.color,
        settings=data.settings.model_dump() if data.settings else None,
    )
    return _out(ws)


@router.post(
    "/{workspace_id}/delete",
    response_model=OkResponse,
    summary="Xóa mềm (phải nhập đúng tên để xác nhận)",
)
async def delete_workspace(workspace_id: uuid.UUID, data: WorkspaceDelete, ctx: Ctx) -> OkResponse:
    await WorkspaceService(ctx.db, ctx.principal).delete(workspace_id, data.confirm_name)
    return OkResponse()
