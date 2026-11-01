from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import clock
from ..models import AuditEntry, ReportRecord, Ticket, TicketExtension
from ..schemas import TicketCreate
from .deadlines import calculate_deadlines


REPORT_TYPES = ("early_warning", "notification", "final_report")
ALL_DRAFT_TYPES = REPORT_TYPES + ("user_advisory",)


def _loads(value: str | None):
    return json.loads(value) if value else None


def _utc_string(value: datetime | None) -> str | None:
    if value is None:
        return None
    value = clock.normalize_utc(value)
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _jsonable(value):
    if isinstance(value, datetime):
        return _utc_string(value)
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _extension(db: Session, ticket_id: str, *, create: bool = False) -> TicketExtension | None:
    ext = db.get(TicketExtension, ticket_id)
    if ext is None and create:
        ext = TicketExtension(ticket_id=ticket_id)
        db.add(ext)
        db.flush()
    return ext


def _fix_available(ticket: Ticket) -> datetime | None:
    fix = _loads(ticket.fix_json)
    if not fix or not fix.get("available_at"):
        return None
    return datetime.fromisoformat(fix["available_at"].replace("Z", "+00:00"))


def _reports(db: Session | None, ticket_id: str) -> dict[str, ReportRecord]:
    if db is None:
        return {}
    rows = db.query(ReportRecord).filter(ReportRecord.ticket_id == ticket_id).all()
    return {row.report_type: row for row in rows}


def _status(
    due_at: datetime | None,
    current: datetime,
    report: ReportRecord | None,
    *,
    awaiting_fix: bool = False,
) -> str:
    if report is not None:
        if due_at is None:
            return "submitted"
        submitted = clock.normalize_utc(report.submitted_at)
        return "submitted" if submitted <= due_at else "submitted_late"
    if awaiting_fix:
        return "awaiting_fix"
    if due_at is None:
        return "not_applicable"
    return "overdue" if current > due_at else "pending"


def serialize_ticket(ticket: Ticket, db: Session | None = None) -> dict:
    current = clock.now()
    product = _loads(ticket.product_json) or {}
    reporter = _loads(ticket.reporter_json)
    member_states = _loads(ticket.member_states_json) or []
    vulnerability = _loads(ticket.vulnerability_json)
    fix = _loads(ticket.fix_json)
    ext = _extension(db, ticket.id) if db is not None else None
    reports = _reports(db, ticket.id)

    is_nonreportable_closed = (
        ticket.state == "closed"
        and ticket.resolution in {"not_actively_exploited", "invalid"}
    )
    applies = (
        ticket.aware_at is not None
        and not is_nonreportable_closed
        and ticket.state in {"reportable", "closed"}
    )

    if not applies:
        obligations = {
            name: {
                "status": "not_applicable",
                "due_at": None,
                "submitted_at": None,
                "reference": None,
            }
            for name in REPORT_TYPES
        }
        next_due = None
    else:
        deadlines = calculate_deadlines(ticket.aware_at, _fix_available(ticket))
        obligations = {}
        unmet = []
        for name in REPORT_TYPES:
            report = reports.get(name)
            due = deadlines[name]
            status = _status(
                due,
                current,
                report,
                awaiting_fix=(name == "final_report" and due is None),
            )
            obligations[name] = {
                "status": status,
                "due_at": _utc_string(due),
                "submitted_at": _utc_string(report.submitted_at) if report else None,
                "reference": report.reference if report else None,
            }
            if report is None and due is not None:
                unmet.append(due)
        next_due = min(unmet) if unmet else None

    return {
        "id": ticket.id,
        "source": ticket.source,
        "title": ticket.title,
        "description": ticket.description,
        "product": product,
        "reporter": reporter,
        "member_states": member_states,
        "vulnerability": vulnerability,
        "exploit": _loads(ext.exploit_json) if ext else None,
        "mitigations": _loads(ext.mitigations_json) if ext else None,
        "impact": ext.impact if ext else None,
        "malicious_actor": ext.malicious_actor if ext else None,
        "sensitivity": ext.sensitivity if ext else None,
        "severity": ticket.severity,
        "fix": fix,
        "state": ticket.state,
        "resolution": ticket.resolution,
        "received_at": _utc_string(ticket.received_at),
        "aware_at": _utc_string(ticket.aware_at),
        "obligations": obligations,
        "next_due_at": _utc_string(next_due),
    }


def create_ticket(db: Session, data: TicketCreate) -> Ticket:
    current = clock.now()
    fix = data.fix.model_dump(mode="json") if data.fix else None
    if data.fix and data.fix.available_at is not None:
        if clock.normalize_utc(data.fix.available_at) > current:
            raise ValueError("fix.available_at cannot be in the future")

    ticket = Ticket(
        id=f"t_{uuid.uuid4().hex[:12]}",
        source=data.source.value,
        title=data.title,
        description=data.description,
        product_json=json.dumps(data.product.model_dump(mode="json")),
        reporter_json=(
            json.dumps(data.reporter.model_dump(mode="json")) if data.reporter else None
        ),
        member_states_json=json.dumps(data.member_states),
        vulnerability_json=(
            json.dumps(data.vulnerability.model_dump(mode="json"))
            if data.vulnerability
            else None
        ),
        severity=data.severity.value if data.severity else None,
        fix_json=json.dumps(fix) if fix else None,
        state="received",
        resolution=None,
        received_at=current,
        aware_at=None,
    )
    db.add(ticket)
    db.flush()

    ext_values = {
        "exploit_json": (
            json.dumps(data.exploit.model_dump(mode="json")) if data.exploit else None
        ),
        "mitigations_json": (
            json.dumps(data.mitigations.model_dump(mode="json"))
            if data.mitigations
            else None
        ),
        "impact": data.impact,
        "malicious_actor": data.malicious_actor,
        "sensitivity": data.sensitivity.value if data.sensitivity else None,
    }
    if any(value is not None for value in ext_values.values()):
        db.add(TicketExtension(ticket_id=ticket.id, **ext_values))

    db.flush()
    return ticket


def add_audit(
    db: Session,
    ticket_id: str,
    actor: str,
    action: str,
    changes: list[dict],
    reason: str | None = None,
) -> AuditEntry:
    last_seq = (
        db.query(func.max(AuditEntry.seq))
        .filter(AuditEntry.ticket_id == ticket_id)
        .scalar()
        or 0
    )
    entry = AuditEntry(
        ticket_id=ticket_id,
        seq=last_seq + 1,
        at=clock.now(),
        actor=actor,
        action=action,
        changes_json=json.dumps(changes, default=_jsonable),
        reason=reason,
    )
    db.add(entry)
    return entry


def serialize_audit(entry: AuditEntry) -> dict:
    return {
        "seq": entry.seq,
        "at": _utc_string(entry.at),
        "actor": entry.actor,
        "action": entry.action,
        "changes": _loads(entry.changes_json) or [],
        "reason": entry.reason,
    }


def _value(data: dict, path: str):
    current = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


DRAFT_FIELDS = {
    "early_warning": {
        "required": [
            "product.manufacturer",
            "product.name",
            "product.affected_versions",
            "member_states",
        ],
        "include": ["product", "member_states"],
    },
    "notification": {
        "required": [
            "product.manufacturer",
            "product.name",
            "product.affected_versions",
            "member_states",
            "vulnerability.description",
            "exploit.description",
            "mitigations.taken",
            "mitigations.for_users",
            "sensitivity",
        ],
        "include": [
            "product",
            "member_states",
            "vulnerability",
            "exploit",
            "mitigations",
            "sensitivity",
        ],
    },
    "final_report": {
        "required": [
            "product.manufacturer",
            "product.name",
            "product.affected_versions",
            "member_states",
            "vulnerability.description",
            "exploit.description",
            "mitigations.taken",
            "mitigations.for_users",
            "sensitivity",
            "severity",
            "impact",
            "fix.available_at",
            "fix.description",
            "fix.fixed_versions",
        ],
        "include": [
            "product",
            "member_states",
            "vulnerability",
            "exploit",
            "mitigations",
            "sensitivity",
            "severity",
            "impact",
            "malicious_actor",
            "fix",
        ],
    },
    "user_advisory": {
        "required": [
            "product.manufacturer",
            "product.name",
            "product.affected_versions",
            "vulnerability.description",
            "mitigations.for_users",
        ],
        "include": ["product", "vulnerability", "mitigations", "severity", "impact", "fix"],
    },
}


def draft_content(ticket_data: dict, report_type: str) -> tuple[dict, list[str]]:
    rule = DRAFT_FIELDS[report_type]
    content = {
        "ticket_id": ticket_data["id"],
        "aware_at": ticket_data["aware_at"],
    }
    for field in rule["include"]:
        value = ticket_data.get(field)
        if value is not None:
            content[field] = value

    if report_type == "user_advisory" and "mitigations" in content:
        content["mitigations"] = {
            "for_users": content["mitigations"].get("for_users")
        }

    missing = []
    for path in rule["required"]:
        value = _value(ticket_data, path)
        if value is None or value == "" or value == []:
            missing.append(path)
    return content, missing


def get_draft(db: Session, ticket: Ticket, report_type: str) -> dict:
    if report_type not in ALL_DRAFT_TYPES:
        raise KeyError(report_type)
    if ticket.aware_at is None or (
        ticket.state == "closed"
        and ticket.resolution in {"not_actively_exploited", "invalid"}
    ):
        raise ValueError("Report drafts require a reportable ticket")

    ticket_data = serialize_ticket(ticket, db)
    if report_type == "user_advisory":
        content, missing = draft_content(ticket_data, report_type)
        return {
            "ticket_id": ticket.id,
            "type": report_type,
            "status": None,
            "due_at": None,
            "submitted_at": None,
            "reference": None,
            "content": content,
            "missing_fields": missing,
        }

    existing = (
        db.query(ReportRecord)
        .filter(
            ReportRecord.ticket_id == ticket.id,
            ReportRecord.report_type == report_type,
        )
        .one_or_none()
    )
    if existing:
        content = _loads(existing.content_json) or {}
        missing = []
    else:
        content, missing = draft_content(ticket_data, report_type)

    obligation = ticket_data["obligations"][report_type]
    return {
        "ticket_id": ticket.id,
        "type": report_type,
        "status": obligation["status"],
        "due_at": obligation["due_at"],
        "submitted_at": obligation["submitted_at"],
        "reference": obligation["reference"],
        "content": content,
        "missing_fields": missing,
    }


def snapshot_fields(ticket: Ticket, db: Session) -> dict:
    data = serialize_ticket(ticket, db)
    return {
        key: value
        for key, value in data.items()
        if key not in {"obligations", "next_due_at"}
    }
