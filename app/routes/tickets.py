import json

from pydantic import ValidationError
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import clock
from ..auth import require_actor, require_token
from ..database import get_db
from ..models import Ticket
from ..schemas import (
    FixInfo,
    TicketCreate,
    TicketResponse,
    TriageDecision,
    TriageRequest,
)
from ..services.tickets import create_ticket, serialize_ticket


router = APIRouter(prefix="/tickets", tags=["tickets"])


def without_reporter(ticket: Ticket) -> dict:
    result = serialize_ticket(ticket)
    result.pop("reporter", None)
    return result


@router.post(
    "",
    response_model=TicketResponse,
    response_model_exclude={"reporter"},
    status_code=201,
    dependencies=[Depends(require_token), Depends(require_actor)],
)
def submit_ticket(
    body: TicketCreate,
    db: Session = Depends(get_db),
):
    try:
        ticket = create_ticket(db, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "field": "fix.available_at",
                "message": str(exc),
            },
        ) from exc

    return serialize_ticket(ticket)


@router.get(
    "",
    dependencies=[Depends(require_token)],
)
def list_tickets(
    db: Session = Depends(get_db),
):
    tickets = db.query(Ticket).all()
    return [
        without_reporter(ticket)
        for ticket in tickets
    ]


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    dependencies=[Depends(require_token)],
)
def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Unknown ticket",
        )

    return serialize_ticket(ticket)


@router.patch(
    "/{ticket_id}",
    dependencies=[
        Depends(require_token),
        Depends(require_actor),
    ],
)
def update_ticket(
    ticket_id: str,
    body: dict = Body(...),
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Unknown ticket",
        )

    if ticket.state == "closed":
        raise HTTPException(
            status_code=409,
            detail="Closed tickets cannot be changed",
        )

    allowed = {
        "title",
        "description",
        "fix",
    }

    unknown = set(body) - allowed

    if unknown:
        raise HTTPException(
            status_code=400,
            detail="Unsupported update field",
        )

    if "title" in body:
        ticket.title = body["title"]

    if "description" in body:
        ticket.description = body["description"]

    if "fix" in body:
        if body["fix"] is None:
            ticket.fix_json = None

        else:
            try:
                fix = FixInfo.model_validate(
                    body["fix"]
                )

            except ValidationError as exc:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "field": "fix",
                        "message": "invalid fix data",
                    },
                ) from exc

            if (
                fix.available_at is not None
                and clock.normalize_utc(
                    fix.available_at
                )
                > clock.now()
            ):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "field": "fix.available_at",
                        "message": (
                            "must not be later than "
                            "the current time"
                        ),
                    },
                )

            ticket.fix_json = json.dumps(
                fix.model_dump(
                    mode="json"
                )
            )

    db.commit()
    db.refresh(ticket)

    return without_reporter(ticket)


@router.post(
    "/{ticket_id}/triage",
    response_model=TicketResponse,
    response_model_exclude={"reporter"},
    dependencies=[
        Depends(require_token),
        Depends(require_actor),
    ],
)
def triage_ticket(
    ticket_id: str,
    body: TriageRequest,
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Unknown ticket",
        )

    if ticket.state != "received":
        raise HTTPException(
            status_code=409,
            detail="Ticket has already been triaged",
        )

    if (
        body.decision
        == TriageDecision.actively_exploited
    ):
        if body.aware_at is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "field": "aware_at",
                    "message": (
                        "required for "
                        "actively_exploited"
                    ),
                },
            )

        try:
            aware_at = clock.normalize_utc(
                body.aware_at
            )

        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "field": "aware_at",
                    "message": str(exc),
                },
            ) from exc

        if aware_at > clock.now():
            raise HTTPException(
                status_code=422,
                detail={
                    "field": "aware_at",
                    "message": (
                        "must not be later than "
                        "the current time"
                    ),
                },
            )

        ticket.state = "reportable"
        ticket.resolution = None
        ticket.aware_at = aware_at

    else:
        if body.aware_at is not None:
            raise HTTPException(
                status_code=422,
                detail={
                    "field": "aware_at",
                    "message": (
                        "must be omitted for "
                        "non-reportable decisions"
                    ),
                },
            )

        ticket.state = "closed"
        ticket.resolution = body.decision.value
        ticket.aware_at = None

    ticket.triage_reason = body.reason

    db.commit()
    db.refresh(ticket)

    return serialize_ticket(ticket)


@router.get(
    "/{ticket_id}/reports/{report_type}",
    dependencies=[Depends(require_token)],
)
def get_report(
    ticket_id: str,
    report_type: str,
):
    raise HTTPException(
        status_code=404,
        detail=(
            "Report endpoint not implemented "
            "in Phase 3"
        ),
    )


@router.post(
    "/{ticket_id}/reports/{report_type}/submission",
    dependencies=[
        Depends(require_token),
        Depends(require_actor),
    ],
)
def record_submission(
    ticket_id: str,
    report_type: str,
):
    raise HTTPException(
        status_code=404,
        detail=(
            "Report submission not implemented "
            "in Phase 3"
        ),
    )


@router.post(
    "/{ticket_id}/close",
    dependencies=[
        Depends(require_token),
        Depends(require_actor),
    ],
)
def close_ticket(
    ticket_id: str,
):
    raise HTTPException(
        status_code=404,
        detail=(
            "Close operation not implemented "
            "in Phase 3"
        ),
    )


@router.get(
    "/{ticket_id}/audit",
    dependencies=[Depends(require_token)],
)
def get_audit(
    ticket_id: str,
):
    raise HTTPException(
        status_code=404,
        detail=(
            "Audit endpoint not implemented "
            "in Phase 3"
        ),
    )