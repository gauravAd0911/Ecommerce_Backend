from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_optional_actor, require_operational_actor
from app.repository.support_repo import SupportRepository
from app.schemas.support_schema import SupportCreate, SupportTicketResponse, SupportTicketUpdate
from app.services.support_service import SupportService

router = APIRouter(tags=["Support"])
versioned_router = APIRouter(prefix="/api/v1", tags=["Support"])


def _success(message: str, data):
    return {"success": True, "message": message, "data": data, "error": None}


def _failure(status_code: int, code: str, message: str):
    raise HTTPException(
        status_code=status_code,
        detail={
            "success": False,
            "message": message,
            "data": None,
            "error": {"code": code, "message": message, "details": []},
        },
    )


def _ticket_payload(ticket) -> dict:
    return SupportTicketResponse.model_validate(ticket).model_dump(by_alias=True)


@versioned_router.post("/support/queries")
@router.post("/queries")
def create_support(
    payload: SupportCreate,
    db: Session = Depends(get_db),
    actor: dict | None = Depends(get_optional_actor),
):
    ticket = SupportService.create_support_ticket(db, payload.model_dump(), user_id=actor.get("user_id") if actor else None)
    return _success("Support query created successfully.", {"query": _ticket_payload(ticket)})


@versioned_router.get("/support/options")
@router.get("/support/options")
def get_support_options():
    return _success(
        "Support options fetched successfully.",
        {
            "options": [
                {"type": "email", "value": "support@company.com"},
                {"type": "phone", "value": "+91 9999999999"},
            ]
        },
    )


@versioned_router.get("/admin/queries")
@router.get("/admin/queries")
def list_all_queries(
    db: Session = Depends(get_db),
    actor: dict = Depends(require_operational_actor),
):
    tickets = SupportService.list_support_tickets(db)
    if actor["role"] == "employee":
        tickets = [ticket for ticket in tickets if not ticket.assigned_to_employee_id or ticket.assigned_to_employee_id == actor["user_id"]]
    return _success("Support queries fetched successfully.", {"queries": [_ticket_payload(ticket) for ticket in tickets]})


@versioned_router.patch("/admin/queries/{ticket_id}")
@router.patch("/admin/queries/{ticket_id}")
def update_query(
    ticket_id: int,
    payload: SupportTicketUpdate,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_operational_actor),
):
    ticket = SupportRepository.get_ticket(db, ticket_id)
    if not ticket:
        _failure(status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Support query not found.")

    if actor["role"] == "employee" and payload.assigned_to_employee_id is not None:
        _failure(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Employees cannot reassign support queries.")

    ticket = SupportService.update_support_ticket(
        db,
        ticket,
        payload.model_dump(exclude_none=False, by_alias=False),
        actor_user_id=actor["user_id"],
        actor_role=actor["role"],
    )
    return _success("Support query updated successfully.", {"query": _ticket_payload(ticket)})


@versioned_router.get("/admin/queries/{ticket_id}")
@router.get("/admin/queries/{ticket_id}")
def get_query(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_operational_actor),
):
    ticket = SupportRepository.get_ticket(db, ticket_id)
    if not ticket:
        _failure(status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Support query not found.")
    return _success("Support query fetched successfully.", {"query": _ticket_payload(ticket)})
