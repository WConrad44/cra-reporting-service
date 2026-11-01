import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from .. import clock
from ..auth import require_actor, require_token, validate_actor
from ..database import get_db
from ..models import AuditEntry, ReportRecord, Ticket, TicketExtension
from ..schemas import (
    AuditEntryResponse,
    DraftResponse,
    SubmissionRequest,
    TicketCreate,
    TicketResponse,
    TicketUpdate,
    TriageDecision,
    TriageRequest,
)
from ..services.tickets import (
    ALL_DRAFT_TYPES,
    REPORT_TYPES,
    _loads,
    _utc_string,
    add_audit,
    create_ticket,
    get_draft,
    serialize_audit,
    serialize_ticket,
    snapshot_fields,
)


router = APIRouter(prefix="/tickets", tags=["tickets"])


def _ticket_or_404(db: Session, ticket_id: str) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Unknown ticket")
    return ticket


def _extension(db: Session, ticket_id: str) -> TicketExtension:
    ext = db.get(TicketExtension, ticket_id)
    if ext is None:
        ext = TicketExtension(ticket_id=ticket_id)
        db.add(ext)
        db.flush()
    return ext


def _merge_json(current_raw: str | None, update_model) -> str | None:
    if update_model is None:
        return None
    current = _loads(current_raw) or {}
    patch = update_model.model_dump(mode="json", exclude_unset=True)
    current.update(patch)
    return json.dumps(current)


def _changes(before: dict, after: dict, fields: set[str]) -> list[dict]:
    changes = []
    for field in sorted(fields):
        if field == "change_reason":
            continue
        old = before.get(field)
        new = after.get(field)
        if old == new:
            continue
        if field == "reporter":
            old = "[redacted]" if old is not None else None
            new = "[redacted]" if new is not None else None
        changes.append({"field": field, "old": old, "new": new})
    return changes


def without_reporter(ticket: Ticket, db: Session) -> dict:
    result = serialize_ticket(ticket, db)
    result.pop("reporter", None)
    return result


@router.post(
    "",
    response_model=TicketResponse,
    response_model_exclude={"reporter"},
    status_code=201,
    dependencies=[Depends(require_token)],
)
def submit_ticket(
    body: TicketCreate,
    actor: str = Depends(require_actor),
    db: Session = Depends(get_db),
):
    try:
        ticket = create_ticket(db, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"field": "fix.available_at", "message": str(exc)},
        ) from exc

    add_audit(
        db,
        ticket.id,
        actor,
        "created",
        [{"field": "state", "old": None, "new": "received"}],
    )
    db.commit()
    db.refresh(ticket)
    return serialize_ticket(ticket, db)


@router.get("", dependencies=[Depends(require_token)])
def list_tickets(
    state: str | None = Query(default=None),
    obligation_status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    allowed_states = {"received", "reportable", "closed"}
    allowed_statuses = {
        "not_applicable",
        "awaiting_fix",
        "pending",
        "overdue",
        "submitted",
        "submitted_late",
    }
    if state is not None and state not in allowed_states:
        raise HTTPException(
            status_code=400,
            detail={"field": "state", "message": "invalid ticket state"},
        )
    if obligation_status is not None and obligation_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail={"field": "obligation_status", "message": "invalid obligation status"},
        )

    rows = db.query(Ticket).all()
    data = []
    for ticket in rows:
        item = without_reporter(ticket, db)
        if state is not None and item["state"] != state:
            continue
        if obligation_status is not None and not any(
            obligation["status"] == obligation_status
            for obligation in item["obligations"].values()
        ):
            continue
        data.append(item)

    data.sort(
        key=lambda item: (
            item["next_due_at"] is None,
            item["next_due_at"] or "",
            item["received_at"],
            item["id"],
        )
    )
    return data


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    dependencies=[Depends(require_token)],
)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    return serialize_ticket(_ticket_or_404(db, ticket_id), db)


@router.patch(
    "/{ticket_id}",
    response_model=TicketResponse,
    response_model_exclude={"reporter"},
    dependencies=[Depends(require_token)],
)
def update_ticket(
    ticket_id: str,
    body: TicketUpdate,
    actor: str = Depends(require_actor),
    db: Session = Depends(get_db),
):
    ticket = _ticket_or_404(db, ticket_id)
    if ticket.state == "closed":
        raise HTTPException(status_code=409, detail="Closed tickets cannot be changed")

    fields = set(body.model_fields_set)
    if not fields:
        raise HTTPException(
            status_code=400,
            detail={"field": "body", "message": "at least one update field is required"},
        )

    before = snapshot_fields(ticket, db)
    ext = _extension(db, ticket.id)

    if "title" in fields:
        if body.title is None:
            raise HTTPException(
                status_code=400,
                detail={"field": "title", "message": "must not be null"},
            )
        ticket.title = body.title

    if "description" in fields:
        if body.description is None:
            raise HTTPException(
                status_code=400,
                detail={"field": "description", "message": "must not be null"},
            )
        ticket.description = body.description

    if "product" in fields:
        if body.product is None:
            raise HTTPException(
                status_code=400,
                detail={"field": "product", "message": "must not be null"},
            )
        current = _loads(ticket.product_json) or {}
        patch = body.product.model_dump(mode="json", exclude_unset=True)
        for required in ("manufacturer", "name"):
            if required in patch and patch[required] is None:
                raise HTTPException(
                    status_code=400,
                    detail={"field": f"product.{required}", "message": "must not be null"},
                )
        if patch.get("affected_versions", object()) is None:
            patch["affected_versions"] = []
        current.update(patch)
        ticket.product_json = json.dumps(current)

    if "reporter" in fields:
        ticket.reporter_json = (
            json.dumps(body.reporter.model_dump(mode="json"))
            if body.reporter is not None
            else None
        )

    if "member_states" in fields:
        ticket.member_states_json = json.dumps(body.member_states or [])

    if "vulnerability" in fields:
        ticket.vulnerability_json = _merge_json(ticket.vulnerability_json, body.vulnerability)

    if "exploit" in fields:
        ext.exploit_json = _merge_json(ext.exploit_json, body.exploit)

    if "mitigations" in fields:
        ext.mitigations_json = _merge_json(ext.mitigations_json, body.mitigations)

    if "impact" in fields:
        ext.impact = body.impact

    if "malicious_actor" in fields:
        ext.malicious_actor = body.malicious_actor

    if "sensitivity" in fields:
        ext.sensitivity = body.sensitivity.value if body.sensitivity is not None else None

    if "severity" in fields:
        ticket.severity = body.severity.value if body.severity is not None else None

    if "fix" in fields:
        if body.fix is None:
            ticket.fix_json = None
        else:
            if (
                "available_at" in body.fix.model_fields_set
                and body.fix.available_at is not None
                and clock.normalize_utc(body.fix.available_at) > clock.now()
            ):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "field": "fix.available_at",
                        "message": "must not be later than the current time",
                    },
                )
            ticket.fix_json = _merge_json(ticket.fix_json, body.fix)

    if "aware_at" in fields:
        if ticket.state != "reportable":
            raise HTTPException(
                status_code=409,
                detail="Awareness time can only be changed while reportable",
            )
        if body.aware_at is None:
            raise HTTPException(
                status_code=400,
                detail={"field": "aware_at", "message": "must not be null"},
            )
        aware_at = clock.normalize_utc(body.aware_at)
        if aware_at > clock.now():
            raise HTTPException(
                status_code=422,
                detail={"field": "aware_at", "message": "must not be later than the current time"},
            )
        old_aware = clock.normalize_utc(ticket.aware_at) if ticket.aware_at else None
        if aware_at != old_aware and not body.change_reason:
            raise HTTPException(
                status_code=400,
                detail={"field": "change_reason", "message": "required when aware_at changes"},
            )
        ticket.aware_at = aware_at

    db.flush()
    after = snapshot_fields(ticket, db)
    changes = _changes(before, after, fields)

    if changes:
        add_audit(
            db,
            ticket.id,
            actor,
            "updated",
            changes,
            body.change_reason,
        )

    db.commit()
    db.refresh(ticket)
    return without_reporter(ticket, db)


@router.post(
    "/{ticket_id}/triage",
    response_model=TicketResponse,
    response_model_exclude={"reporter"},
    dependencies=[Depends(require_token)],
)
def triage_ticket(
    ticket_id: str,
    body: TriageRequest,
    actor: str = Depends(require_actor),
    db: Session = Depends(get_db),
):
    ticket = _ticket_or_404(db, ticket_id)
    if ticket.state != "received":
        raise HTTPException(status_code=409, detail="Ticket has already been triaged")

    before = snapshot_fields(ticket, db)

    if body.decision == TriageDecision.actively_exploited:
        if body.aware_at is None:
            raise HTTPException(
                status_code=400,
                detail={"field": "aware_at", "message": "required for actively_exploited"},
            )
        aware_at = clock.normalize_utc(body.aware_at)
        if aware_at > clock.now():
            raise HTTPException(
                status_code=422,
                detail={"field": "aware_at", "message": "must not be later than the current time"},
            )
        ticket.state = "reportable"
        ticket.resolution = None
        ticket.aware_at = aware_at
    else:
        # Pod agreement for Phase 4: an irrelevant awareness time is accepted and ignored.
        ticket.state = "closed"
        ticket.resolution = body.decision.value
        ticket.aware_at = None

    ticket.triage_reason = body.reason
    db.flush()
    after = snapshot_fields(ticket, db)
    changes = _changes(before, after, {"state", "resolution", "aware_at"})
    add_audit(db, ticket.id, actor, "triaged", changes, body.reason)
    db.commit()
    db.refresh(ticket)
    return without_reporter(ticket, db)


@router.get(
    "/{ticket_id}/reports/{report_type}",
    response_model=DraftResponse,
    dependencies=[Depends(require_token)],
)
def get_report(ticket_id: str, report_type: str, db: Session = Depends(get_db)):
    if report_type not in ALL_DRAFT_TYPES:
        raise HTTPException(status_code=404, detail="Unknown report type")
    ticket = _ticket_or_404(db, ticket_id)
    try:
        return get_draft(db, ticket, report_type)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/{ticket_id}/reports/{report_type}/submission",
    response_model=DraftResponse,
    dependencies=[Depends(require_token)],
)
async def record_submission(
    ticket_id: str,
    report_type: str,
    request: Request,
    db: Session = Depends(get_db),
):
    if report_type not in REPORT_TYPES:
        raise HTTPException(status_code=404, detail="Unknown or non-submittable report type")

    ticket = _ticket_or_404(db, ticket_id)
    actor = validate_actor(request.headers.get("X-Actor"))

    raw = await request.body()
    if raw:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(
                status_code=400,
                detail={"field": "body", "message": "invalid JSON"},
            ) from exc
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=400,
                detail={"field": "body", "message": "request body must be a JSON object"},
            )
        try:
            body = SubmissionRequest.model_validate(payload)
        except ValidationError as exc:
            errors = []
            for error in exc.errors():
                errors.append(
                    {
                        "field": ".".join(str(part) for part in error["loc"]) or "body",
                        "message": error.get("msg", "invalid"),
                    }
                )
            raise HTTPException(status_code=400, detail=errors) from exc
    else:
        body = SubmissionRequest()

    if ticket.state != "reportable":
        raise HTTPException(status_code=409, detail="Ticket is not reportable")

    existing = (
        db.query(ReportRecord)
        .filter(
            ReportRecord.ticket_id == ticket.id,
            ReportRecord.report_type == report_type,
        )
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Report has already been submitted")

    previous = {
        "notification": "early_warning",
        "final_report": "notification",
    }.get(report_type)
    if previous is not None:
        prior = (
            db.query(ReportRecord)
            .filter(
                ReportRecord.ticket_id == ticket.id,
                ReportRecord.report_type == previous,
            )
            .one_or_none()
        )
        if prior is None:
            raise HTTPException(
                status_code=409,
                detail=f"{report_type} cannot be recorded before {previous}",
            )

    draft = get_draft(db, ticket, report_type)
    submitted_at = (
        clock.normalize_utc(body.submitted_at)
        if body.submitted_at is not None
        else clock.now()
    )
    aware_at = clock.normalize_utc(ticket.aware_at)

    rule_errors = [
        {"field": field, "message": "required before submission"}
        for field in draft["missing_fields"]
    ]
    if submitted_at < aware_at or submitted_at > clock.now():
        rule_errors.append(
            {
                "field": "submitted_at",
                "message": "must be between awareness time and the current time",
            }
        )
    if rule_errors:
        raise HTTPException(status_code=422, detail=rule_errors)

    record = ReportRecord(
        ticket_id=ticket.id,
        report_type=report_type,
        submitted_at=submitted_at,
        reference=body.reference,
        content_json=json.dumps(draft["content"]),
    )
    db.add(record)
    add_audit(
        db,
        ticket.id,
        actor,
        "report_submitted",
        [
            {
                "field": f"obligations.{report_type}.submitted_at",
                "old": None,
                "new": _utc_string(submitted_at),
            }
        ],
    )
    db.commit()
    db.refresh(ticket)
    return get_draft(db, ticket, report_type)


@router.post(
    "/{ticket_id}/close",
    response_model=TicketResponse,
    response_model_exclude={"reporter"},
    dependencies=[Depends(require_token)],
)
def close_ticket(
    ticket_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    ticket = _ticket_or_404(db, ticket_id)
    actor = validate_actor(request.headers.get("X-Actor"))
    if ticket.state != "reportable":
        raise HTTPException(status_code=409, detail="Ticket is not reportable")

    submitted = {
        row.report_type
        for row in db.query(ReportRecord)
        .filter(ReportRecord.ticket_id == ticket.id)
        .all()
    }
    if not set(REPORT_TYPES).issubset(submitted):
        raise HTTPException(status_code=409, detail="All three reports must be submitted")

    old_state = ticket.state
    old_resolution = ticket.resolution
    ticket.state = "closed"
    ticket.resolution = "resolved"
    add_audit(
        db,
        ticket.id,
        actor,
        "closed",
        [
            {"field": "state", "old": old_state, "new": "closed"},
            {"field": "resolution", "old": old_resolution, "new": "resolved"},
        ],
    )
    db.commit()
    db.refresh(ticket)
    return without_reporter(ticket, db)


@router.get(
    "/{ticket_id}/audit",
    response_model=list[AuditEntryResponse],
    dependencies=[Depends(require_token)],
)
def get_audit(ticket_id: str, db: Session = Depends(get_db)):
    _ticket_or_404(db, ticket_id)
    entries = (
        db.query(AuditEntry)
        .filter(AuditEntry.ticket_id == ticket_id)
        .order_by(AuditEntry.seq.asc())
        .all()
    )
    return [serialize_audit(entry) for entry in entries]
