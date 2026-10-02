from __future__ import annotations

import asyncio
import calendar
import time
import uuid
from datetime import UTC, datetime, timedelta
from html import escape

import jwt
from sqlalchemy import or_, select

from app.core.config import get_settings
from app.core.resources import Resources
from app.db.tenant import system_session, tenant_session
from app.models import EmailDelivery, ExportJob, ReportSchedule, Tenant
from app.models.enums import ExportKind, JobStatus
from worker.celery_app import celery_app
from worker.tasks.email import send_email


def next_run(date:datetime,cadence:str)->datetime:
    if cadence=="day":return date+timedelta(days=1)
    if cadence=="week":return date+timedelta(days=7)
    year,month=(date.year+1,1) if date.month==12 else (date.year,date.month+1)
    return date.replace(year=year,month=month,day=min(date.day,calendar.monthrange(year,month)[1]))


async def tick()->int:
    settings=get_settings();resources=Resources.from_settings(settings);sent=0;now=datetime.now(UTC)
    try:
        async with system_session(resources.session_factory) as db:
            tenants=list((await db.execute(select(Tenant.id).where(Tenant.deleted_at.is_(None)))).scalars())
        for tid in tenants:
            async with tenant_session(resources.session_factory,tid) as db:
                schedules=(await db.execute(select(ReportSchedule).where(ReportSchedule.tenant_id==tid,ReportSchedule.enabled.is_(True),ReportSchedule.next_run_at<=now).with_for_update(skip_locked=True))).scalars().all()
                for schedule in schedules:
                    # Chạy bù một lần, sau đó chuyển sang kỳ tiếp theo trong tương lai.
                    job=ExportJob(tenant_id=tid,workspace_id=schedule.workspace_id,kind=ExportKind.PDF,created_by=schedule.created_by,params={"filters":schedule.filters,"anonymous":True},expires_at=now+timedelta(days=7))
                    db.add(job);await db.flush()
                    for recipient in schedule.recipients:
                        db.add(EmailDelivery(tenant_id=tid,workspace_id=schedule.workspace_id,recipient=recipient,kind="report",dedupe_key=f"report:{schedule.id}:{schedule.next_run_at.isoformat()}:{recipient}",payload={"export_id":str(job.id)}))
                    due=next_run(schedule.next_run_at,schedule.cadence)
                    while due<=now:due=next_run(due,schedule.cadence)
                    schedule.next_run_at=due
            async with tenant_session(resources.session_factory,tid) as db:
                deliveries=(await db.execute(select(EmailDelivery).where(EmailDelivery.tenant_id==tid,EmailDelivery.status.in_([JobStatus.PENDING,JobStatus.FAILED]),EmailDelivery.attempts<10,or_(EmailDelivery.next_attempt_at.is_(None),EmailDelivery.next_attempt_at<=now)).order_by(EmailDelivery.created_at).limit(20).with_for_update(skip_locked=True))).scalars().all()
                for delivery in deliveries:
                    try:
                        token=jwt.encode({"aud":"survey-invitation","sub":str(delivery.id),"survey":str(delivery.survey_id),"tenant":str(tid),"exp":int(time.time())+604800},settings.secret_key.get_secret_value(),algorithm="HS256")
                        base=settings.public_base_url.rstrip("/")
                        if delivery.kind=="invitation":
                            link=f"{base}/api/v1/public/email/{token}/click"
                            subject=f"[{settings.app_name}] Mời trả lời khảo sát"
                            text=f"Bạn được mời tham gia: {delivery.payload['title']}\n{link}"
                            html=f'<p>{escape(delivery.payload["title"])}</p><p><a href="{escape(link)}">Trả lời khảo sát</a></p><img src="{base}/api/v1/public/email/{token}/open" width="1" height="1" alt=""/>'
                        elif delivery.kind=="urgent":
                            subject=f"[{settings.app_name}] Phản hồi khẩn cấp"
                            link=f"{base}/responses"
                            text=f"{delivery.payload['text']}\nLý do: {', '.join(delivery.payload['reasons'])}\n{link}"
                            html=f"<p>{escape(text)}</p>"
                        else:
                            job=(await db.execute(select(ExportJob).where(ExportJob.id==uuid.UUID(delivery.payload["export_id"]),ExportJob.tenant_id==tid))).scalar_one_or_none()
                            if not job or job.status==JobStatus.FAILED:
                                raise RuntimeError("Báo cáo không tạo được.")
                            if job.status!=JobStatus.DONE:
                                continue
                            share=jwt.encode({"aud":"report-share","sub":str(job.id),"tenant":str(tid),"exp":int(job.expires_at.timestamp())},settings.secret_key.get_secret_value(),algorithm="HS256")
                            link=f"{base}/api/v1/public/reports/{share}"
                            subject=f"[{settings.app_name}] Báo cáo định kỳ"
                            text=f"Tải báo cáo (liên kết có hạn 7 ngày): {link}"
                            html=f'<p><a href="{escape(link)}">Tải báo cáo định kỳ</a></p>'
                        await asyncio.to_thread(send_email.run,delivery.recipient,subject,text,html)
                        delivery.status=JobStatus.DONE;delivery.sent_at=datetime.now(UTC);delivery.last_error=None;sent+=1
                    except Exception as exc:
                        delivery.status=JobStatus.FAILED;delivery.last_error=type(exc).__name__
                        delivery.next_attempt_at=now+timedelta(seconds=min(3600,10*2**delivery.attempts))
                    delivery.attempts+=1
        return sent
    finally:
        await resources.close()


@celery_app.task(name="worker.tasks.engagement.tick")
def process_outbox()->int:
    return asyncio.run(tick())
