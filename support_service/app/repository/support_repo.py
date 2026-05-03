from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.support_model import SupportTicket
from app.utils.constants import TicketPriority, TicketStatus


class SupportRepository:
    @staticmethod
    def create_ticket(db: Session, data: dict) -> SupportTicket:
        ticket = SupportTicket(
            **data,
            status=TicketStatus.OPEN,
            priority=data.get("priority") or TicketPriority.MEDIUM,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def get_user_tickets(db: Session, user_id: str):
        return (
            db.query(SupportTicket)
            .filter(SupportTicket.user_id == user_id)
            .order_by(SupportTicket.created_at.desc())
            .all()
        )

    @staticmethod
    def get_all_tickets(db: Session):
        return db.query(SupportTicket).order_by(SupportTicket.created_at.desc()).all()

    @staticmethod
    def get_ticket(db: Session, ticket_id: int) -> SupportTicket | None:
        return db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    @staticmethod
    def update_ticket(db: Session, ticket: SupportTicket, updates: dict) -> SupportTicket:
        for key, value in updates.items():
            setattr(ticket, key, value)
        db.commit()
        db.refresh(ticket)
        return ticket
