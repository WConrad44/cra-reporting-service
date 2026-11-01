from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    product_json: Mapped[str] = mapped_column(Text, nullable=False)
    reporter_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    member_states_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    vulnerability_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fix_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    state: Mapped[str] = mapped_column(String(20), nullable=False, default="received")
    resolution: Mapped[str | None] = mapped_column(String(40), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aware_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    triage_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class TicketExtension(Base):
    """Phase 4 fields kept in a side table so Phase 3 databases stay compatible."""

    __tablename__ = "ticket_extensions"

    ticket_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    exploit_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    mitigations_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    malicious_actor: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensitivity: Mapped[str | None] = mapped_column(String(20), nullable=True)


class ReportRecord(Base):
    __tablename__ = "report_records"
    __table_args__ = (
        UniqueConstraint("ticket_id", "report_type", name="uq_report_ticket_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_type: Mapped[str] = mapped_column(String(32), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)


class AuditEntry(Base):
    __tablename__ = "audit_entries"
    __table_args__ = (
        UniqueConstraint("ticket_id", "seq", name="uq_audit_ticket_seq"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    changes_json: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
