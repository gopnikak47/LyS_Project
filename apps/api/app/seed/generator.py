"""Sinh dữ liệu minh họa tiếng Việt thực tế cho dashboard (mục 13.7).

- ≥ 2 doanh nghiệp, ≥ 3 không gian, ≥ 1.500 phản hồi nhiều sắc thái, có teencode và ca khẩn cấp.
- Toàn bộ là DỮ LIỆU GIẢ, sinh ngẫu nhiên có hạt giống cố định (chạy lại cho cùng kết quả).
- Văn bản nhận xét được lưu với `text_analyses.status = pending` để pipeline NLP phân tích như thật.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domain.topic_templates import INDUSTRY_TEMPLATES
from app.models import (
    Answer,
    Membership,
    Question,
    Response,
    Survey,
    SurveyChannel,
    SurveyVersion,
    Tenant,
    TextAnalysis,
    Topic,
    TopicSet,
    User,
    Workspace,
)
from app.models.enums import Channel, Role, SurveyStatus
from app.seed.phrases import CLOSINGS, CUSTOMER_NAMES, EMOJIS, PHRASES, TEENCODE

DEMO_PASSWORD = "MatKhau@123"  # noqa: S105 — chỉ dùng cho dữ liệu minh họa ở môi trường dev


@dataclass(frozen=True)
class SurveySpec:
    title: str
    slug: str
    industry: str
    responses: int
    # Tăng phản hồi tiêu cực về một chủ đề trong 30 ngày gần nhất (demo phát hiện bất thường).
    spike_topic: str | None = None


@dataclass(frozen=True)
class WorkspaceSpec:
    name: str
    industry: str
    color: str
    surveys: tuple[SurveySpec, ...]


@dataclass(frozen=True)
class TenantSpec:
    name: str
    slug: str
    industry: str
    plan: str
    users: tuple[tuple[str, str, Role], ...]
    workspaces: tuple[WorkspaceSpec, ...]


SEED_TENANTS: tuple[TenantSpec, ...] = (
    TenantSpec(
        name="Chuỗi nhà hàng Phố Xưa",
        slug="pho-xua",
        industry="restaurant",
        plan="pro",
        users=(
            ("admin@phoxua.vn", "Nguyễn Minh An", Role.ADMIN),
            ("analyst@phoxua.vn", "Trần Thu Hà", Role.ANALYST),
            ("viewer@phoxua.vn", "Lê Văn Bình", Role.VIEWER),
        ),
        workspaces=(
            WorkspaceSpec(
                "Nhà hàng Quận 1",
                "restaurant",
                "#f97316",
                (
                    SurveySpec(
                        "Khảo sát hài lòng – Chi nhánh Quận 1",
                        "phoxua-q1",
                        "restaurant",
                        520,
                        spike_topic="Phục vụ",
                    ),
                ),
            ),
            WorkspaceSpec(
                "Nhà hàng Hoàn Kiếm",
                "restaurant",
                "#eab308",
                (
                    SurveySpec(
                        "Đánh giá bữa ăn – Chi nhánh Hoàn Kiếm",
                        "phoxua-hk",
                        "restaurant",
                        380,
                    ),
                ),
            ),
        ),
    ),
    TenantSpec(
        name="Tập đoàn Du lịch Biển Xanh",
        slug="bien-xanh",
        industry="hotel",
        plan="business",
        users=(
            ("admin@bienxanh.vn", "Phạm Quốc Việt", Role.ADMIN),
            ("analyst@bienxanh.vn", "Hoàng Mai Anh", Role.ANALYST),
        ),
        workspaces=(
            WorkspaceSpec(
                "Khách sạn Biển Xanh Nha Trang",
                "hotel",
                "#0ea5e9",
                (SurveySpec("Đánh giá kỳ nghỉ tại Nha Trang", "bienxanh-nt", "hotel", 430),),
            ),
            WorkspaceSpec(
                "Ứng dụng đặt phòng Biển Xanh",
                "it",
                "#6366f1",
                (
                    SurveySpec(
                        "Phản hồi ứng dụng đặt phòng",
                        "bienxanh-app",
                        "it",
                        330,
                        spike_topic="Lỗi hệ thống",
                    ),
                ),
            ),
        ),
    ),
)

SEED_TENANT_SLUGS = tuple(t.slug for t in SEED_TENANTS)


def _loc(vi: str, en: str | None = None) -> dict[str, str]:
    return {"vi": vi, "en": en or vi}


def _opt(option_id: str, vi: str, en: str) -> dict[str, Any]:
    return {"id": option_id, "label": _loc(vi, en)}


def survey_questions(industry: str) -> list[dict[str, Any]]:
    """Bộ câu hỏi P0 tiêu biểu theo ngành."""
    overall = {
        "restaurant": ("Bạn đánh giá chung về bữa ăn hôm nay thế nào?", "How was your meal?"),
        "hotel": ("Bạn đánh giá chung về kỳ nghỉ thế nào?", "How was your stay overall?"),
        "it": ("Bạn đánh giá ứng dụng bao nhiêu sao?", "How many stars would you give the app?"),
    }[industry]
    csat = {
        "restaurant": ("Bạn hài lòng với chất lượng phục vụ ở mức nào?", "Service satisfaction"),
        "hotel": ("Bạn hài lòng với nhân viên khách sạn ở mức nào?", "Staff satisfaction"),
        "it": ("Ứng dụng có đáp ứng nhu cầu của bạn không?", "Does the app meet your needs?"),
    }[industry]
    choice = {
        "restaurant": (
            "Bạn dùng bữa vào lúc nào?",
            [
                ("sang", "Bữa sáng", "Breakfast"),
                ("trua", "Bữa trưa", "Lunch"),
                ("toi", "Bữa tối", "Dinner"),
            ],
        ),
        "hotel": (
            "Mục đích chuyến đi của bạn?",
            [
                ("du_lich", "Du lịch", "Leisure"),
                ("cong_tac", "Công tác", "Business"),
                ("gia_dinh", "Gia đình", "Family"),
            ],
        ),
        "it": (
            "Bạn dùng ứng dụng trên thiết bị nào?",
            [
                ("android", "Android", "Android"),
                ("ios", "iPhone", "iPhone"),
                ("web", "Trình duyệt", "Web"),
            ],
        ),
    }[industry]
    likes = [
        (t.name.lower().replace(" ", "_").replace("&", "va"), t.name, t.name)
        for t in INDUSTRY_TEMPLATES[industry].topics[:4]
    ]
    return [
        {
            "code": "q_overall",
            "type": "rating",
            "title": _loc(*overall),
            "config": {"max": 5, "icon": "star"},
            "required": True,
        },
        {
            "code": "q_csat",
            "type": "csat",
            "title": _loc(*csat),
            "config": {"scale": 5, "style": "emoji"},
            "required": True,
        },
        {
            "code": "q_choice",
            "type": "single_choice",
            "title": _loc(choice[0]),
            "options": [_opt(*o) for o in choice[1]],
            "config": {"shuffle": False},
            "required": False,
        },
        {
            "code": "q_likes",
            "type": "multi_choice",
            "title": _loc("Bạn hài lòng nhất với điều gì?", "What did you like most?"),
            "options": [_opt(*o) for o in likes],
            "config": {"min": 0, "max": len(likes)},
            "required": False,
        },
        {
            "code": "q_comment",
            "type": "text",
            "title": _loc("Bạn có góp ý gì thêm cho chúng tôi?", "Any other feedback for us?"),
            "config": {"multiline": True, "max_length": 1000, "analyze": True},
            "required": False,
        },
    ]


class CommentGenerator:
    """Ghép câu nhận xét + biến thể teencode/emoji theo sắc thái."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def _teencode(self, text: str) -> str:
        for src, dst in TEENCODE:
            if src in text and self.rng.random() < 0.35:
                text = text.replace(src, dst, 1)
        if self.rng.random() < 0.08:
            # Bỏ dấu một phần như khi gõ vội trên điện thoại.
            text = text.replace("ă", "a").replace("ơ", "o").replace("ư", "u")
        return text

    def make(self, industry: str, tone: str, spike_topic: str | None = None) -> tuple[str, str]:
        pool = PHRASES[industry][tone]
        if spike_topic:
            spiked = [p for p in pool if p[0] == spike_topic]
            pool = spiked or pool
        picks = self.rng.sample(pool, k=min(len(pool), self.rng.choice([1, 1, 2, 2, 3])))
        # Khen chê lẫn lộn: phản hồi trung lập/tiêu cực đôi khi kèm một ý khen.
        if tone in ("negative", "neutral") and self.rng.random() < 0.25:
            picks.append(self.rng.choice(PHRASES[industry]["positive"]))
        sentences = [p[1] for p in picks]
        closing = self.rng.choice(CLOSINGS[tone])
        if closing:
            sentences.append(closing)
        text = ". ".join(sentences)
        if self.rng.random() < 0.6:
            text = self._teencode(text)
        if self.rng.random() < 0.15:
            text = text.lower()
        emoji = self.rng.choice(EMOJIS[tone])
        if emoji and self.rng.random() < 0.45:
            text = f"{text} {emoji}"
        if tone == "urgent" and self.rng.random() < 0.5:
            text = text + "!!!"
        return text, picks[0][0]


def _random_time(rng: random.Random, now: datetime, days: int = 180) -> datetime:
    # Nhiều phản hồi hơn ở thời gian gần (phân phối lệch về hiện tại).
    day_offset = int(days * (rng.random() ** 1.6))
    hour = rng.choice([7, 8, 11, 11, 12, 12, 13, 17, 18, 18, 19, 19, 20, 21])
    return (now - timedelta(days=day_offset)).replace(
        hour=hour, minute=rng.randint(0, 59), second=rng.randint(0, 59), microsecond=0
    )


async def reset_seed_data(session: AsyncSession) -> None:
    await session.execute(delete(Tenant).where(Tenant.slug.in_(SEED_TENANT_SLUGS)))
    emails = [u[0] for t in SEED_TENANTS for u in t.users]
    await session.execute(delete(User).where(User.email.in_(emails)))


async def seed(
    session: AsyncSession, *, scale: float = 1.0, seed_value: int = 2026
) -> dict[str, int]:
    """Sinh dữ liệu vào phiên hệ thống (bỏ qua RLS). Trả về số lượng bản ghi đã tạo."""
    rng = random.Random(seed_value)
    gen = CommentGenerator(rng)
    now = datetime.now(UTC)
    password_hash = hash_password(DEMO_PASSWORD)
    stats = {
        "tenants": 0,
        "users": 0,
        "workspaces": 0,
        "surveys": 0,
        "responses": 0,
        "answers": 0,
        "texts": 0,
    }

    existing = (
        (await session.execute(select(Tenant.slug).where(Tenant.slug.in_(SEED_TENANT_SLUGS))))
        .scalars()
        .all()
    )
    if existing:
        raise RuntimeError("Dữ liệu minh họa đã tồn tại. Chạy lại với --reset để xóa và sinh mới.")

    for tspec in SEED_TENANTS:
        tenant = Tenant(
            name=tspec.name, slug=tspec.slug, industry=tspec.industry, plan_code=tspec.plan
        )
        session.add(tenant)
        await session.flush()
        stats["tenants"] += 1

        admin_id: uuid.UUID | None = None
        for email, full_name, role in tspec.users:
            user = User(
                email=email, full_name=full_name, password_hash=password_hash, email_verified_at=now
            )
            session.add(user)
            await session.flush()
            session.add(Membership(tenant_id=tenant.id, user_id=user.id, role=role))
            admin_id = admin_id or user.id
            stats["users"] += 1

        for wspec in tspec.workspaces:
            workspace = Workspace(
                tenant_id=tenant.id,
                name=wspec.name,
                industry=wspec.industry,
                color=wspec.color,
                created_by=admin_id,
            )
            session.add(workspace)
            await session.flush()
            stats["workspaces"] += 1

            template = INDUSTRY_TEMPLATES[wspec.industry]
            topic_set = TopicSet(
                tenant_id=tenant.id,
                workspace_id=workspace.id,
                name=f"Chủ đề {template.name}",
                template_code=template.code,
            )
            session.add(topic_set)
            await session.flush()
            for pos, tt in enumerate(template.topics):
                session.add(
                    Topic(
                        tenant_id=tenant.id,
                        workspace_id=workspace.id,
                        topic_set_id=topic_set.id,
                        name=tt.name,
                        description=tt.description,
                        keywords=list(tt.keywords),
                        color=tt.color,
                        sort_order=pos,
                    )
                )

            for sspec in wspec.surveys:
                counts = await _seed_survey(
                    session, rng, gen, now, tenant.id, workspace.id, admin_id, sspec, scale
                )
                stats["surveys"] += 1
                for key in ("responses", "answers", "texts"):
                    stats[key] += counts[key]
    return stats


async def _seed_survey(
    session: AsyncSession,
    rng: random.Random,
    gen: CommentGenerator,
    now: datetime,
    tenant_id: uuid.UUID,
    workspace_id: uuid.UUID,
    admin_id: uuid.UUID | None,
    spec: SurveySpec,
    scale: float,
) -> dict[str, int]:
    questions_spec = survey_questions(spec.industry)
    survey = Survey(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        title=spec.title,
        slug=spec.slug,
        description="Cảm ơn bạn đã dành 1 phút chia sẻ trải nghiệm.",
        status=SurveyStatus.PUBLISHED,
        published_at=now - timedelta(days=181),
        created_by=admin_id,
        theme={"primary": "#3b55d9", "layout": "one_per_page"},
        settings={
            "voucher": {
                "enabled": True,
                "mode": "fixed",
                "code": "CAMON10",
                "message": "Giảm 10% cho lần ghé tiếp theo",
            }
        },
    )
    session.add(survey)
    await session.flush()

    questions: list[Question] = []
    for pos, q in enumerate(questions_spec):
        question = Question(
            tenant_id=tenant_id,
            survey_id=survey.id,
            type=q["type"],
            code=q["code"],
            title=q["title"],
            options=q.get("options", []),
            config=q.get("config", {}),
            required=q["required"],
            position=pos,
        )
        session.add(question)
        questions.append(question)
    await session.flush()

    snapshot = {
        "title": survey.title,
        "description": survey.description,
        "theme": survey.theme,
        "settings": survey.settings,
        "questions": [
            {
                "id": str(q.id),
                "code": q.code,
                "type": q.type,
                "title": q.title,
                "description": {},
                "options": q.options,
                "config": q.config,
                "logic": {},
                "required": q.required,
                "position": q.position,
                "points": None,
            }
            for q in questions
        ],
    }
    version = SurveyVersion(
        tenant_id=tenant_id,
        survey_id=survey.id,
        version=1,
        snapshot=snapshot,
        published_by=admin_id,
    )
    session.add(version)
    await session.flush()
    survey.current_version_id = version.id

    channels = [
        SurveyChannel(
            tenant_id=tenant_id,
            survey_id=survey.id,
            name=f"Bàn {i}",
            channel=Channel.QR,
            code=f"ban-{i}",
            params={"table": str(i)},
        )
        for i in range(1, 9)
    ]
    channels.append(
        SurveyChannel(
            tenant_id=tenant_id,
            survey_id=survey.id,
            name="Quầy thu ngân",
            channel=Channel.QR,
            code="quay",
            params={"counter": "1"},
        )
    )
    session.add_all(channels)
    await session.flush()

    by_code = {q.code: q for q in questions}
    responses: list[dict[str, Any]] = []
    answers: list[dict[str, Any]] = []
    texts: list[dict[str, Any]] = []
    total = max(1, int(spec.responses * scale))

    for _ in range(total):
        submitted = _random_time(rng, now)
        recent = (now - submitted).days <= 30
        roll = rng.random()
        spike = spec.spike_topic if (spec.spike_topic and recent and rng.random() < 0.5) else None
        if spike:
            tone = "negative"
        elif roll < 0.03:
            tone = "urgent"
        elif roll < 0.27:
            tone = "negative"
        elif roll < 0.44:
            tone = "neutral"
        else:
            tone = "positive"

        rating = {
            "positive": rng.choice([4, 5, 5]),
            "neutral": rng.choice([3, 3, 4]),
            "negative": rng.choice([1, 2, 2, 3]),
            "urgent": 1,
        }[tone]
        csat = max(1, min(5, rating + rng.choice([-1, 0, 0, 1])))
        channel = rng.choices(
            [Channel.QR, Channel.LINK, Channel.EMAIL, Channel.KIOSK], weights=[50, 35, 10, 5]
        )[0]
        ch = rng.choice(channels) if channel == Channel.QR else None
        response_id = uuid.uuid4()
        respondent: dict[str, Any] = {}
        if rng.random() < 0.2:
            respondent = {
                "name": rng.choice(CUSTOMER_NAMES),
                "phone": f"09{rng.randint(10_000_000, 99_999_999)}",
            }
        duration = rng.randint(25, 240)
        responses.append(
            {
                "id": response_id,
                "tenant_id": tenant_id,
                "survey_id": survey.id,
                "workspace_id": workspace_id,
                "survey_version_id": version.id,
                "channel": channel,
                "channel_id": ch.id if ch else None,
                "source_params": ch.params if ch else {},
                "respondent": respondent,
                "language": "vi",
                "status": "completed",
                "started_at": submitted - timedelta(seconds=duration),
                "submitted_at": submitted,
                "duration_seconds": duration,
                "rating": Decimal(rating),
                "csat": Decimal(csat),
                "created_at": submitted,
            }
        )

        def add_answer(
            code: str,
            value: Any,
            text: str | None = None,
            _response_id: uuid.UUID = response_id,
            _submitted: datetime = submitted,
        ) -> uuid.UUID:
            answer_id = uuid.uuid4()
            q = by_code[code]
            answers.append(
                {
                    "id": answer_id,
                    "tenant_id": tenant_id,
                    "response_id": _response_id,
                    "question_id": q.id,
                    "question_code": code,
                    "question_type": q.type,
                    "value": value,
                    "text_value": text,
                    "created_at": _submitted,
                }
            )
            return answer_id

        add_answer("q_overall", rating)
        add_answer("q_csat", csat)
        if rng.random() < 0.8:
            opts = by_code["q_choice"].options
            add_answer("q_choice", rng.choice(opts)["id"])
        if rng.random() < 0.6:
            opts = by_code["q_likes"].options
            chosen = rng.sample(opts, k=rng.randint(1, min(2, len(opts))))
            add_answer("q_likes", [o["id"] for o in chosen])
        if rng.random() < 0.82 or tone == "urgent":
            comment, _topic = gen.make(spec.industry, tone, spike)
            answer_id = add_answer("q_comment", comment, comment)
            texts.append(
                {
                    "id": uuid.uuid4(),
                    "tenant_id": tenant_id,
                    "response_id": response_id,
                    "answer_id": answer_id,
                    "workspace_id": workspace_id,
                    "survey_id": survey.id,
                    "channel": channel,
                    "rating": Decimal(rating),
                    "responded_at": submitted,
                    "text": comment,
                    "status": "pending",
                    "created_at": submitted,
                    "updated_at": submitted,
                }
            )

    for chunk_start in range(0, len(responses), 500):
        await session.execute(insert(Response), responses[chunk_start : chunk_start + 500])
    for chunk_start in range(0, len(answers), 1000):
        await session.execute(insert(Answer), answers[chunk_start : chunk_start + 1000])
    for chunk_start in range(0, len(texts), 500):
        await session.execute(insert(TextAnalysis), texts[chunk_start : chunk_start + 500])
    survey.response_count = len(responses)
    await session.flush()
    return {"responses": len(responses), "answers": len(answers), "texts": len(texts)}
