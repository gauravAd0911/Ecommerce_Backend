from __future__ import annotations

from datetime import datetime, UTC

from sqlalchemy.orm import Session

from app.models.support_model import SupportTicket
from app.repository.support_repo import SupportRepository
from app.utils.constants import TicketStatus


class SupportService:
    @staticmethod
    def create_support_ticket(db: Session, payload: dict, user_id: str | None = None):
        data = payload.copy()
        data["user_id"] = user_id
        return SupportRepository.create_ticket(db, data)

    @staticmethod
    def list_support_tickets(db: Session):
        return SupportRepository.get_all_tickets(db)

    @staticmethod
    def update_support_ticket(
        db: Session,
        ticket: SupportTicket,
        updates: dict,
        actor_user_id: str,
        actor_role: str,
    ) -> SupportTicket:
        next_updates = {}

        if "status" in updates and updates["status"]:
            next_status = str(updates["status"]).upper()
            next_updates["status"] = next_status
            if next_status == TicketStatus.RESOLVED:
                next_updates["resolved_by"] = actor_user_id
                next_updates["resolved_at"] = datetime.now(UTC)

        if "priority" in updates and updates["priority"]:
            next_updates["priority"] = str(updates["priority"]).upper()

        if actor_role == "admin" and "assigned_to_employee_id" in updates:
            next_updates["assigned_to_employee_id"] = updates["assigned_to_employee_id"]
            next_updates["assigned_by_admin_id"] = actor_user_id

        if "internal_note" in updates:
            next_updates["internal_note"] = updates["internal_note"]

        if "resolution_note" in updates:
            next_updates["resolution_note"] = updates["resolution_note"]

        return SupportRepository.update_ticket(db, ticket, next_updates)
