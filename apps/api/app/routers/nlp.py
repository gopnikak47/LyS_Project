from pathlib import Path

from fastapi import APIRouter

from app.core.auth import Ctx

router = APIRouter(prefix="/nlp", tags=["nlp"])


@router.get("/health")
async def health(ctx: Ctx) -> dict[str, object]:
    settings = ctx.settings
    ready = settings.nlp_backend == "rules" or bool(
        settings.nlp_model_path and (Path(settings.nlp_model_path) / "metadata.json").is_file()
    )
    return {
        "status": "configured" if ready else "pending_model",
        "backend": settings.nlp_backend,
        "demo": settings.nlp_backend == "rules",
        "runtime_verified": False,
    }
