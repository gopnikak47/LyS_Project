from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import exists, select

from app.core.auth import Ctx
from app.core.permissions import Permission
from app.domain.tabular import csv_bytes
from app.models import LabelCorrection, TextAnalysis
from app.models.enums import ReviewStatus
from app.schemas.feedback import BulkCorrection, CorrectionInput, FeedbackFilter
from app.services.feedback import FeedbackService, describe

router = APIRouter(tags=["feedback"])


@router.get("/responses")
async def list_feedback(ctx: Ctx, filters: Annotated[FeedbackFilter, Depends()]) -> dict[str, Any]:
    return await FeedbackService(ctx.db, ctx.principal).list(filters)


@router.get("/responses/{analysis_id}")
async def detail(analysis_id: uuid.UUID, ctx: Ctx) -> dict[str, Any]:
    return describe(await FeedbackService(ctx.db, ctx.principal).get(analysis_id))


@router.post("/analyses/{analysis_id}/corrections")
async def correct(analysis_id: uuid.UUID, data: CorrectionInput, ctx: Ctx) -> dict[str, Any]:
    return describe(await FeedbackService(ctx.db, ctx.principal).correct(analysis_id, data))


@router.post("/responses/bulk-corrections")
async def bulk(data: BulkCorrection, ctx: Ctx) -> dict[str, int]:
    service = FeedbackService(ctx.db, ctx.principal)
    for analysis_id in sorted(set(data.ids)):
        await service.correct(analysis_id, data.correction)
    return {"updated": len(set(data.ids))}


@router.get("/analyses/{analysis_id}/corrections")
async def history(analysis_id: uuid.UUID, ctx: Ctx) -> list[dict[str, Any]]:
    return await FeedbackService(ctx.db, ctx.principal).history(analysis_id)


@router.post("/corrections/{correction_id}/undo")
async def undo(correction_id: uuid.UUID, ctx: Ctx) -> dict[str, Any]:
    return describe(await FeedbackService(ctx.db, ctx.principal).undo(correction_id))


@router.post("/corrections/{correction_id}/review")
async def review(correction_id: uuid.UUID, ctx: Ctx, approved: bool) -> dict[str, bool]:
    await FeedbackService(ctx.db, ctx.principal).review(correction_id, approved)
    return {"ok": True}


@router.get("/model-quality")
async def quality(workspace_id: uuid.UUID, ctx: Ctx) -> dict[str, Any]:
    return await FeedbackService(ctx.db, ctx.principal).quality(workspace_id)


@router.get("/model-quality/dataset")
async def dataset(workspace_id: uuid.UUID, ctx: Ctx, format: str = "csv") -> StreamingResponse:
    from app.core.errors import AppError
    from app.services.workspaces import WorkspaceService

    ctx.principal.require(Permission.DATA_EXPORT)
    await WorkspaceService(ctx.db, ctx.principal).get(workspace_id)
    if format not in {"csv", "jsonl"}:
        raise AppError("Định dạng không hợp lệ.")
    blocked = exists(
        select(LabelCorrection.id).where(
            LabelCorrection.analysis_id == TextAnalysis.id,
            LabelCorrection.tenant_id == ctx.principal.tenant_id,
            LabelCorrection.reverted_at.is_(None),
            LabelCorrection.review_status != ReviewStatus.APPROVED,
        )
    )
    query = (
        select(TextAnalysis)
        .where(
            TextAnalysis.tenant_id == ctx.principal.tenant_id,
            TextAnalysis.workspace_id == workspace_id,
            TextAnalysis.is_verified.is_(True),
            TextAnalysis.sentiment.is_not(None),
            ~blocked,
        )
        .order_by(TextAnalysis.id)
    )

    # Giữ transaction RLS tới khi stream hoàn tất; không đổ toàn bộ dataset vào RAM.
    async def stream() -> AsyncIterator[bytes]:
        if format == "csv":
            yield csv_bytes(["text", "label", "topics", "urgent", "model_version"], [])
        result = await ctx.db.stream_scalars(query.execution_options(yield_per=200))
        async for row in result:
            if format == "jsonl":
                yield (
                    json.dumps(
                        {
                            "text": row.text,
                            "label": row.sentiment,
                            "topics": [str(t) for t in row.topic_ids],
                            "urgent": row.is_urgent,
                            "model_version": row.model_version,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                ).encode()
            else:
                yield csv_bytes(
                    [],
                    [
                        [
                            row.text,
                            row.sentiment,
                            "|".join(str(t) for t in row.topic_ids),
                            row.is_urgent,
                            row.model_version,
                        ]
                    ],
                ).split(b"\r\n", 1)[1]

    return StreamingResponse(
        stream(),
        media_type="text/csv" if format == "csv" else "application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="verified-labels.{format}"'},
    )
