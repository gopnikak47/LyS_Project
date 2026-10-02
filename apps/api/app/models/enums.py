"""Giá trị liệt kê dùng chung giữa model, schema và frontend (`packages/shared`)."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class TenantStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class SurveyStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"
    ARCHIVED = "archived"


class Channel(StrEnum):
    LINK = "link"
    QR = "qr"
    EMBED = "embed"
    EMAIL = "email"
    KIOSK = "kiosk"
    ZALO = "zalo"
    IMPORT = "import"


class ResponseStatus(StrEnum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    SPAM = "spam"


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class AnalysisStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class CorrectionField(StrEnum):
    SENTIMENT = "sentiment"
    TOPICS = "topics"
    URGENT = "urgent"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TicketStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TicketPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ImportKind(StrEnum):
    RESPONSES = "responses"
    QUESTIONS = "questions"


class ExportKind(StrEnum):
    XLSX = "xlsx"
    PDF = "pdf"
    DATASET_CSV = "dataset_csv"
    DATASET_JSONL = "dataset_jsonl"
    RESPONSES_CSV = "responses_csv"
