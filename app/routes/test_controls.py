from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete
from sqlalchemy.orm import Session

from .. import clock
from ..auth import require_token
from ..database import get_db
from ..models import AuditEntry, ReportRecord, Ticket, TicketExtension
from ..schemas import ClockSetRequest

router = APIRouter(prefix="/test", tags=["test-controls"])


@router.post(
    "/reset",
    status_code=204,
    dependencies=[Depends(require_token)]
)
def reset(db: Session = Depends(get_db)):
    db.execute(delete(AuditEntry))
    db.execute(delete(ReportRecord))
    db.execute(delete(TicketExtension))
    db.execute(delete(Ticket))
    db.commit()
    clock.clear_fixed()
    return Response(status_code=204)


def _utc_string(value):
    return value.isoformat().replace("+00:00", "Z")


@router.get(
    "/clock",
    dependencies=[Depends(require_token)]
)
def get_clock():
    return {
        "now": _utc_string(clock.now())
    }


@router.put(
    "/clock",
    dependencies=[Depends(require_token)]
)
def set_clock(body: ClockSetRequest):
    fixed = clock.set_fixed(body.now)
    return {
        "now": _utc_string(fixed)
    }


@router.delete(
    "/clock",
    status_code=204,
    dependencies=[Depends(require_token)]
)
def clear_clock():
    clock.clear_fixed()
    return Response(status_code=204)