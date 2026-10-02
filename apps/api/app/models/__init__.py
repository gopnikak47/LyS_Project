"""Model ORM SQLAlchemy. Import tại đây để Alembic nhìn thấy toàn bộ metadata."""

from app.models.base import Base
from app.models.engagement import EmailDelivery, ReportSchedule
from app.models.jobs import ExportJob, ImportJob, NlpModel
from app.models.responses import Answer, LabelCorrection, Response, TextAnalysis, Ticket
from app.models.surveys import Question, Survey, SurveyChannel, SurveyVersion
from app.models.tenancy import (
    AuditLog,
    Invitation,
    Membership,
    PasswordResetToken,
    Plan,
    RefreshToken,
    Subscription,
    Tenant,
    User,
    Workspace,
    WorkspaceMember,
)
from app.models.topics import Topic, TopicSet

# Bảng chịu RLS theo tenant_id (bảng `tenants` có chính sách riêng theo id).
TENANT_SCOPED_TABLES: tuple[str, ...] = tuple(
    sorted(
        mapper.class_.__tablename__
        for mapper in Base.registry.mappers
        if getattr(mapper.class_, "__tenant_scoped__", False)
    )
)

__all__ = [
    "TENANT_SCOPED_TABLES",
    "Answer",
    "AuditLog",
    "Base",
    "EmailDelivery",
    "ExportJob",
    "ImportJob",
    "Invitation",
    "LabelCorrection",
    "Membership",
    "NlpModel",
    "PasswordResetToken",
    "Plan",
    "Question",
    "RefreshToken",
    "ReportSchedule",
    "Response",
    "Subscription",
    "Survey",
    "SurveyChannel",
    "SurveyVersion",
    "Tenant",
    "TextAnalysis",
    "Ticket",
    "Topic",
    "TopicSet",
    "User",
    "Workspace",
    "WorkspaceMember",
]
