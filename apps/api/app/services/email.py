"""Email giao dịch (tiếng Việt): dựng nội dung và đẩy sang worker gửi qua SMTP.

API không gửi SMTP trực tiếp để request không bị chậm; worker có retry/backoff (xem
`worker.tasks.email`). Nội dung do người dùng nhập luôn được escape trong HTML.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from html import escape

from app.core.queue import TaskQueue

SEND_EMAIL_TASK = "worker.tasks.email.send_email"


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to: str
    subject: str
    text: str
    html: str


def enqueue_email(queue: TaskQueue, message: EmailMessage) -> None:
    queue.send(SEND_EMAIL_TASK, kwargs=asdict(message), queue="default")


def _layout(app_name: str, title: str, body_html: str, button: tuple[str, str] | None) -> str:
    button_html = ""
    if button:
        label, href = button
        button_html = (
            f'<p style="margin:28px 0"><a href="{escape(href)}" '
            'style="background:#3b55d9;color:#fff;padding:12px 22px;border-radius:10px;'
            f'text-decoration:none;font-weight:600">{escape(label)}</a></p>'
        )
    return (
        '<div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#1f2937">'
        f'<h2 style="color:#3b55d9">{escape(app_name)}</h2>'
        f"<h3>{escape(title)}</h3>{body_html}{button_html}"
        '<p style="color:#6b7280;font-size:12px">Email tự động, vui lòng không trả lời.</p></div>'
    )


def password_reset_email(
    *, app_name: str, to: str, full_name: str, link: str, ttl_minutes: int
) -> EmailMessage:
    subject = f"[{app_name}] Đặt lại mật khẩu"
    text = (
        f"Xin chào {full_name},\n\n"
        f"Chúng tôi nhận được yêu cầu đặt lại mật khẩu. Mở liên kết sau trong {ttl_minutes} phút:\n"
        f"{link}\n\nNếu bạn không yêu cầu, hãy bỏ qua email này."
    )
    html = _layout(
        app_name,
        "Đặt lại mật khẩu",
        f"<p>Xin chào {escape(full_name)},</p><p>Chúng tôi nhận được yêu cầu đặt lại mật khẩu "
        f"cho tài khoản của bạn. Liên kết có hiệu lực trong {ttl_minutes} phút.</p>"
        "<p>Nếu bạn không yêu cầu, hãy bỏ qua email này.</p>",
        ("Đặt lại mật khẩu", link),
    )
    return EmailMessage(to=to, subject=subject, text=text, html=html)


def invitation_email(
    *, app_name: str, to: str, tenant_name: str, inviter_name: str, role_label: str, link: str
) -> EmailMessage:
    subject = f"[{app_name}] {inviter_name} mời bạn tham gia {tenant_name}"
    text = (
        f"{inviter_name} mời bạn tham gia {tenant_name} với vai trò {role_label}.\n"
        f"Nhận lời mời tại: {link}\n\nLiên kết có hạn sử dụng."
    )
    html = _layout(
        app_name,
        f"Lời mời tham gia {tenant_name}",
        f"<p><strong>{escape(inviter_name)}</strong> mời bạn tham gia "
        f"<strong>{escape(tenant_name)}</strong> với vai trò "
        f"<strong>{escape(role_label)}</strong>.</p><p>Liên kết có hạn sử dụng.</p>",
        ("Nhận lời mời", link),
    )
    return EmailMessage(to=to, subject=subject, text=text, html=html)


ROLE_LABELS = {"ADMIN": "Quản trị viên", "ANALYST": "Nhân viên phân tích", "VIEWER": "Người xem"}
