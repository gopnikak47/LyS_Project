from __future__ import annotations

from sqlalchemy import select

from app.models import EmailDelivery, Membership, TextAnalysis, Ticket, User
from app.models.enums import MembershipStatus, Role, TicketPriority


async def create_alert(db, analysis: TextAnalysis) -> None:
    # Ticket và outbox trong cùng transaction, khóa analysis chống tạo trùng.
    existing=(await db.execute(select(Ticket).where(Ticket.analysis_id==analysis.id,Ticket.tenant_id==analysis.tenant_id))).scalar_one_or_none()
    if existing or not (analysis.is_urgent or analysis.sentiment == "negative" or (analysis.rating is not None and analysis.rating <= 2)):
        return
    db.add(Ticket(tenant_id=analysis.tenant_id,workspace_id=analysis.workspace_id,response_id=analysis.response_id,analysis_id=analysis.id,title=analysis.text[:300],priority=TicketPriority.URGENT if analysis.is_urgent else TicketPriority.HIGH))
    if analysis.is_urgent:
        recipients=(await db.execute(select(User.email).join(Membership,Membership.user_id==User.id).where(Membership.tenant_id==analysis.tenant_id,Membership.role==Role.ADMIN,Membership.status==MembershipStatus.ACTIVE,User.deleted_at.is_(None)))).scalars().all()
        for recipient in recipients:
            db.add(EmailDelivery(tenant_id=analysis.tenant_id,workspace_id=analysis.workspace_id,survey_id=analysis.survey_id,recipient=recipient,kind="urgent",dedupe_key=f"urgent:{analysis.id}:{recipient}",payload={"analysis_id":str(analysis.id),"text":analysis.text,"reasons":analysis.urgent_reasons}))
