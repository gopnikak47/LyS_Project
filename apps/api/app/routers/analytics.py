from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.auth import Ctx, _extract_token, load_principal
from app.core.tokens import decode_access_token
from app.db.tenant import tenant_session
from app.schemas.feedback import FeedbackFilter
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])
Filters = Annotated[FeedbackFilter, Depends()]


@router.get("/per-question")
async def per_question(ctx: Ctx, filters: Filters) -> list[dict[str, Any]]:
    return await AnalyticsService(ctx.db, ctx.principal).per_question(filters)


@router.get("/pivot")
async def pivot(
    ctx: Ctx,
    filters: Filters,
    row: Literal["channel", "survey", "branch", "sentiment"] = "channel",
    column: Literal["channel", "survey", "branch", "sentiment"] = "sentiment",
    value: Literal["count", "rating", "csat"] = "count",
) -> list[dict[str, Any]]:
    return await AnalyticsService(ctx.db, ctx.principal).pivot(filters, row, column, value)


@router.get("/overview")
async def overview(ctx: Ctx, filters: Filters) -> dict[str, Any]:
    return await AnalyticsService(ctx.db, ctx.principal).overview(filters)


@router.get("/trends")
async def trends(
    ctx: Ctx, filters: Filters, period: Literal["day", "week", "month", "quarter"] = "day"
) -> list[dict[str, Any]]:
    return await AnalyticsService(ctx.db, ctx.principal).trends(filters, period)


@router.get("/topics")
async def topics(
    ctx: Ctx, filters: Filters, period: Literal["week", "month", "quarter"] = "week"
) -> list[dict[str, Any]]:
    return await AnalyticsService(ctx.db, ctx.principal).topics(filters, period)


@router.get("/wordcloud")
async def wordcloud(ctx: Ctx, filters: Filters) -> list[dict[str, Any]]:
    return await AnalyticsService(ctx.db, ctx.principal).wordcloud(filters)


@router.get("/events")
async def events(ctx: Ctx, filters: Filters, request: Request) -> StreamingResponse:
    # Không giữ connection/transaction trong suốt SSE. Nạp lại quyền mỗi vòng.
    from app.services.workspaces import WorkspaceService

    await WorkspaceService(ctx.db, ctx.principal).get(filters.workspace_id)

    raw_token, _ = _extract_token(request)
    await ctx.db.close()

    async def stream() -> AsyncIterator[str]:
        for _ in range(60):
            if await request.is_disconnected():
                break
            try:
                async with tenant_session(
                    ctx.resources.session_factory, ctx.principal.tenant_id, ctx.principal.user_id
                ) as db:
                    claims = decode_access_token(ctx.settings, raw_token or "")
                    if claims is None:
                        raise ValueError("Expired access")
                    principal = await load_principal(
                        db, ctx.principal.user_id, ctx.principal.tenant_id, claims.token_version
                    )
                    payload = await AnalyticsService(db, principal).overview(filters)
                yield f"event: overview\ndata: {json.dumps(payload)}\n\n"
            except Exception:
                yield "event: expired\ndata: {}\n\n"
                break
            await asyncio.sleep(10)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
