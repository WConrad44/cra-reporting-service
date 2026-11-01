from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete
from sqlalchemy.orm import Session

from .. import clock
from ..auth import require_token
from ..database import get_db
from ..models import AuditEntry, ReportRecord, Ticket, TicketExtension
from ..schemas import SessionResponse, SystemTestReportResponse, SystemTestSetupRequest
from ..test_sessions import create_session, get_session

router = APIRouter(prefix="/test", tags=["cross-team-testing"])


@router.post(
    "/setup",
    response_model=SessionResponse,
    status_code=201,
    dependencies=[Depends(require_token)],
)
def setup_system_test(body: SystemTestSetupRequest, db: Session = Depends(get_db)):
    """Prepare a clean target state for one externally supplied test session."""
    try:
        create_session(body.session_id)
    except KeyError as exc:
        raise HTTPException(status_code=409, detail="session_id already exists") from exc

    # Pod K's shared test approach uses a reset baseline and a controllable clock.
    # Setup therefore clears project data and releases any previously fixed clock.
    db.execute(delete(AuditEntry))
    db.execute(delete(ReportRecord))
    db.execute(delete(TicketExtension))
    db.execute(delete(Ticket))
    db.commit()
    clock.clear_fixed()

    return {"session_id": body.session_id}


@router.get(
    "/report",
    response_model=SystemTestReportResponse,
    dependencies=[Depends(require_token)],
)
def get_system_test_report(session_id: str = Query(min_length=1)):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown test session")
    if not session.ready:
        raise HTTPException(status_code=409, detail="Test session is still preparing")

    # The course interface explicitly allows code coverage to be unavailable when
    # the target is not instrumented, as long as null counts and a basis are returned.
    return {
        "session_id": session_id,
        "coverage": {
            "code": {
                "covered": None,
                "total": None,
                "basis": "Source-line coverage instrumentation is not enabled on the deployed Phase 3 service.",
            }
        },
    }
