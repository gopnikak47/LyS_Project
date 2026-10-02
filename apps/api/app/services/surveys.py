"""Lưu nháp độc lập snapshot xuất bản; không thay đổi câu trả lời lịch sử."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.errors import AppError, ConflictError
from app.core.permissions import Permission
from app.models import Question, Survey, SurveyVersion
from app.models.enums import SurveyStatus
from app.repositories.surveys import QuestionRepository, SurveyRepository, VersionRepository
from app.schemas.common import Page
from app.schemas.surveys import QuestionInput, SurveyCreate, SurveyInput, SurveyOut
from app.services.audit import audit
from app.services.workspaces import WorkspaceService


class SurveyService:
    def __init__(self, db: AsyncSession, principal: Principal) -> None:
        self.db = db
        self.principal = principal
        self.repo = SurveyRepository(db, principal.tenant_id)
        self.questions = QuestionRepository(db, principal.tenant_id)
        self.versions = VersionRepository(db, principal.tenant_id)

    async def get(self, survey_id: uuid.UUID, *, lock: bool = False) -> Survey:
        survey = await self.repo.lock(survey_id) if lock else await self.repo.get_or_404(survey_id)
        await WorkspaceService(self.db, self.principal).get(survey.workspace_id)
        return survey

    async def describe(self, survey: Survey) -> SurveyOut:
        out = SurveyOut.model_validate(survey)
        out.questions = [
            QuestionInput.model_validate(q) for q in await self.questions.for_survey(survey.id)
        ]
        return out

    async def list(
        self,
        workspace_id: uuid.UUID,
        page: int,
        page_size: int,
        search: str,
        status: SurveyStatus | None,
    ) -> Page[SurveyOut]:
        await WorkspaceService(self.db, self.principal).get(workspace_id)
        filters = [Survey.workspace_id == workspace_id]
        if search:
            filters.append(Survey.title.ilike(f"%{search}%"))
        if status:
            filters.append(Survey.status == status)
        items = await self.repo.list(
            *filters,
            order_by=Survey.updated_at.desc(),
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return Page(
            items=[SurveyOut.model_validate(s) for s in items],
            total=await self.repo.count(*filters),
            page=page,
            page_size=page_size,
        )

    async def create(self, data: SurveyCreate) -> SurveyOut:
        self.principal.require(Permission.SURVEY_EDIT)
        await WorkspaceService(self.db, self.principal).get(data.workspace_id)
        from app.services.billing import enforce_limit

        await enforce_limit(self.db, self.principal.tenant_id, "surveys")
        survey = self.repo.add(
            Survey(
                workspace_id=data.workspace_id,
                title=data.title.strip(),
                slug=secrets.token_urlsafe(18),
                created_by=self.principal.user_id,
            )
        )
        await self.db.flush()
        return await self.save(survey.id, data)

    async def save(self, survey_id: uuid.UUID, data: SurveyInput) -> SurveyOut:
        self.principal.require(Permission.SURVEY_EDIT)
        survey = await self.get(survey_id, lock=True)
        if data.expected_updated_at is not None and survey.updated_at != data.expected_updated_at:
            raise ConflictError(
                "Khảo sát đã được sửa ở cửa sổ khác. Vui lòng tải lại trước khi lưu."
            )
        survey.title = data.title.strip()
        survey.description = data.description
        survey.theme = data.theme.model_dump(mode="json")
        survey.settings = data.settings
        survey.languages = list(dict.fromkeys(data.languages))
        survey.default_language = data.default_language
        survey.opens_at = data.opens_at
        survey.closes_at = data.closes_at
        survey.is_quiz = data.is_quiz
        survey.updated_at = datetime.now(UTC)
        old = {q.id: q for q in await self.questions.for_survey(survey.id)}
        for position, item in enumerate(data.questions):
            # Không chấp nhận ID câu hỏi thuộc khảo sát/tenant khác.
            question = old.pop(item.id, None)
            if question is None:
                existing = await self.questions.get(item.id)
                if existing is not None:
                    raise AppError("ID câu hỏi không hợp lệ.")
                question = self.questions.add(Question(id=item.id, survey_id=survey.id))
            for key, value in item.model_dump(mode="json", exclude={"id"}).items():
                setattr(question, key, value)
            question.position = position
        for question in old.values():
            await self.db.delete(question)
        await self.db.flush()
        return await self.describe(survey)

    async def publish(self, survey_id: uuid.UUID) -> SurveyOut:
        self.principal.require(Permission.SURVEY_EDIT)
        survey = await self.get(survey_id, lock=True)
        out = await self.describe(survey)
        if not out.questions:
            raise AppError("Cần ít nhất một câu hỏi để xuất bản.")
        versions = await self.versions.list(
            SurveyVersion.survey_id == survey.id, order_by=SurveyVersion.version.desc(), limit=1
        )
        version = self.versions.add(
            SurveyVersion(
                survey_id=survey.id,
                version=versions[0].version + 1 if versions else 1,
                snapshot=out.model_dump(
                    mode="json",
                    exclude={
                        "settings",
                        "updated_at",
                        "status",
                        "response_count",
                        "current_version_id",
                    },
                ),
                published_by=self.principal.user_id,
            )
        )
        # Snapshot giữ cấu hình khách; không chứa đáp án bí mật (quiz thêm ở GĐ11).
        version.snapshot = {**version.snapshot, "settings": survey.settings}
        await self.db.flush()
        version.snapshot = {**version.snapshot, "current_version_id": str(version.id)}
        survey.current_version_id = version.id
        survey.status = SurveyStatus.PUBLISHED
        survey.published_at = datetime.now(UTC)
        survey.closed_at = None
        await audit(
            self.db,
            tenant_id=self.principal.tenant_id,
            user_id=self.principal.user_id,
            action="survey.publish",
            entity_type="survey",
            entity_id=survey.id,
            data={"version": version.version},
        )
        await self.db.flush()
        return await self.describe(survey)

    async def close(self, survey_id: uuid.UUID) -> SurveyOut:
        self.principal.require(Permission.SURVEY_EDIT)
        survey = await self.get(survey_id, lock=True)
        survey.status = SurveyStatus.CLOSED
        survey.closed_at = datetime.now(UTC)
        await self.db.flush()
        return await self.describe(survey)

    async def duplicate(self, survey_id: uuid.UUID) -> SurveyOut:
        self.principal.require(Permission.SURVEY_EDIT)
        original = await self.describe(await self.get(survey_id))
        data = SurveyCreate.model_validate(
            {
                **original.model_dump(),
                "title": f"{original.title[:285]} (bản sao)",
                "questions": [
                    q.model_copy(update={"id": uuid.uuid4()}) for q in original.questions
                ],
            }
        )
        return await self.create(data)
