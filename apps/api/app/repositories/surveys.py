"""Mọi truy vấn khảo sát có tenant scope; khóa hàng khi cập nhật/xuất bản."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from app.models import Question, Survey, SurveyVersion
from app.repositories.base import TenantRepository


class SurveyRepository(TenantRepository[Survey]):
    model = Survey
    not_found_message = "Không tìm thấy khảo sát."

    async def lock(self, survey_id: uuid.UUID) -> Survey:
        from app.core.errors import found

        row: Survey = found(
            (
                await self.session.execute(
                    self._scoped().where(Survey.id == survey_id).with_for_update()
                )
            ).scalar_one_or_none(),
            self.not_found_message,
        )
        return row


class QuestionRepository(TenantRepository[Question]):
    model = Question

    async def for_survey(self, survey_id: uuid.UUID) -> Sequence[Question]:
        return await self.list(Question.survey_id == survey_id, order_by=Question.position)


class VersionRepository(TenantRepository[SurveyVersion]):
    model = SurveyVersion
