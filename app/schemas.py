from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}"
    r"T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?"
    r"(?:Z|[+-]\d{2}:\d{2})$"
)

EU_MEMBER_STATES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
}


def validate_timestamp_string(value):
    if value is None:
        return value
    if isinstance(value, str) and not TIMESTAMP_PATTERN.fullmatch(value):
        raise ValueError("timestamp must include seconds and a UTC offset")
    return value


def validate_versions(value: list[str]) -> list[str]:
    if len(value) > 50:
        raise ValueError("must contain at most 50 versions")
    if any(not (1 <= len(v) <= 100) for v in value):
        raise ValueError("each version must be 1-100 characters")
    return value


def validate_member_states(value: list[str]) -> list[str]:
    if len(value) != len(set(value)):
        raise ValueError("member_states must be unique")
    for code in value:
        if code != "unknown" and code not in EU_MEMBER_STATES:
            raise ValueError("member_states must contain EU member-state codes or unknown")
    return value


class Source(str, Enum):
    external_researcher = "external_researcher"
    customer = "customer"
    internal = "internal"
    scanner = "scanner"
    csirt = "csirt"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Sensitivity(str, Enum):
    clear = "CLEAR"
    green = "GREEN"
    amber = "AMBER"
    amber_strict = "AMBER+STRICT"
    red = "RED"


class Product(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manufacturer: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    affected_versions: list[str] = Field(default_factory=list, max_length=50)

    _validate_versions = field_validator("affected_versions")(validate_versions)


class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manufacturer: str | None = Field(default=None, min_length=1, max_length=200)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    affected_versions: list[str] | None = None

    @field_validator("affected_versions")
    @classmethod
    def check_versions(cls, value):
        return validate_versions(value) if value is not None else value


class Reporter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=200)
    contact: str | None = Field(default=None, max_length=200)


class Vulnerability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cve_id: str | None = None
    description: str | None = Field(default=None, min_length=1, max_length=10_000)

    @field_validator("cve_id")
    @classmethod
    def validate_cve(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"CVE-\d{4}-\d{4,}", value):
            raise ValueError("must match CVE-YYYY-NNNN")
        return value


class Exploit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str | None = Field(default=None, min_length=1, max_length=10_000)


class Mitigations(BaseModel):
    model_config = ConfigDict(extra="forbid")
    taken: str | None = Field(default=None, min_length=1, max_length=10_000)
    for_users: str | None = Field(default=None, min_length=1, max_length=10_000)


class FixInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available_at: datetime | None = None
    description: str | None = Field(default=None, min_length=1, max_length=10_000)
    fixed_versions: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("available_at", mode="before")
    @classmethod
    def validate_available_at_format(cls, value):
        return validate_timestamp_string(value)

    @field_validator("available_at")
    @classmethod
    def timestamp_must_have_offset(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp must include a UTC offset")
        return value

    _validate_fixed_versions = field_validator("fixed_versions")(validate_versions)


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Source
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10_000)
    product: Product
    reporter: Reporter | None = None
    member_states: list[str] = Field(default_factory=list)
    vulnerability: Vulnerability | None = None
    exploit: Exploit | None = None
    mitigations: Mitigations | None = None
    impact: str | None = Field(default=None, min_length=1, max_length=10_000)
    malicious_actor: str | None = Field(default=None, min_length=1, max_length=10_000)
    sensitivity: Sensitivity | None = None
    severity: Severity | None = None
    fix: FixInfo | None = None

    _validate_member_states = field_validator("member_states")(validate_member_states)


class TicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=10_000)
    product: ProductUpdate | None = None
    reporter: Reporter | None = None
    member_states: list[str] | None = None
    vulnerability: Vulnerability | None = None
    exploit: Exploit | None = None
    mitigations: Mitigations | None = None
    impact: str | None = Field(default=None, min_length=1, max_length=10_000)
    malicious_actor: str | None = Field(default=None, min_length=1, max_length=10_000)
    sensitivity: Sensitivity | None = None
    severity: Severity | None = None
    fix: FixInfo | None = None
    aware_at: datetime | None = None
    change_reason: str | None = Field(default=None, min_length=1, max_length=10_000)

    @field_validator("member_states")
    @classmethod
    def check_member_states(cls, value):
        return validate_member_states(value) if value is not None else value

    @field_validator("aware_at", mode="before")
    @classmethod
    def validate_aware_at_format(cls, value):
        return validate_timestamp_string(value)

    @field_validator("aware_at")
    @classmethod
    def aware_at_must_have_offset(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp must include a UTC offset")
        return value


class TriageDecision(str, Enum):
    actively_exploited = "actively_exploited"
    not_actively_exploited = "not_actively_exploited"
    invalid = "invalid"


class TriageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: TriageDecision
    reason: str = Field(min_length=1, max_length=10_000)
    aware_at: datetime | None = None

    @field_validator("aware_at", mode="before")
    @classmethod
    def validate_aware_at_format(cls, value):
        return validate_timestamp_string(value)

    @field_validator("aware_at")
    @classmethod
    def timestamp_must_have_offset(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp must include a UTC offset")
        return value


class SubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submitted_at: datetime | None = None
    reference: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("submitted_at", mode="before")
    @classmethod
    def validate_submitted_at_format(cls, value):
        return validate_timestamp_string(value)

    @field_validator("submitted_at")
    @classmethod
    def submitted_at_must_have_offset(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp must include a UTC offset")
        return value


class ClockSetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    now: datetime

    @field_validator("now", mode="before")
    @classmethod
    def validate_now_format(cls, value):
        return validate_timestamp_string(value)

    @field_validator("now")
    @classmethod
    def timestamp_must_have_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include a UTC offset")
        return value


class Obligation(BaseModel):
    status: Literal[
        "not_applicable",
        "awaiting_fix",
        "pending",
        "overdue",
        "submitted",
        "submitted_late",
    ]
    due_at: str | None = None
    submitted_at: str | None = None
    reference: str | None = None


class TicketResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    source: str
    title: str
    description: str
    product: dict
    reporter: dict | None = None
    member_states: list[str]
    vulnerability: dict | None = None
    exploit: dict | None = None
    mitigations: dict | None = None
    impact: str | None = None
    malicious_actor: str | None = None
    sensitivity: str | None = None
    severity: str | None = None
    fix: dict | None = None
    state: Literal["received", "reportable", "closed"]
    resolution: str | None
    received_at: str
    aware_at: str | None
    obligations: dict[str, Obligation]
    next_due_at: str | None


class DraftResponse(BaseModel):
    ticket_id: str
    type: Literal["early_warning", "notification", "final_report", "user_advisory"]
    status: str | None
    due_at: str | None
    submitted_at: str | None
    reference: str | None
    content: dict
    missing_fields: list[str]


class AuditEntryResponse(BaseModel):
    seq: int
    at: str
    actor: str
    action: Literal["created", "triaged", "updated", "report_submitted", "closed"]
    changes: list[dict]
    reason: str | None = None


class ErrorItem(BaseModel):
    field: str
    message: str


class ProblemDetails(BaseModel):
    title: str
    status: int
    detail: str | None = None
    errors: list[ErrorItem] | None = None


class SystemTestSetupRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=200)
    setup: dict = Field(default_factory=dict)


class SessionResponse(BaseModel):
    session_id: str


class CoverageMeasure(BaseModel):
    covered: int | None
    total: int | None
    basis: str = Field(min_length=1)


class SystemCoverageReport(BaseModel):
    code: CoverageMeasure


class SystemTestReportResponse(BaseModel):
    session_id: str
    coverage: SystemCoverageReport
