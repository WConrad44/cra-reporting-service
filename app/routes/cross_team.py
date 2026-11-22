from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import delete
from sqlalchemy.orm import Session

from .. import clock
from ..auth import require_token
from ..coverage_runtime import code_coverage_measure, start_session_coverage
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
    except KeyError:
        return JSONResponse(
            status_code=409,
            content={"message": "session_id already exists", "source": "system"},
        )

    # Pod K's shared test approach uses a reset baseline and a controllable clock.
    # Setup therefore clears project data and releases any previously fixed clock.
    db.execute(delete(AuditEntry))
    db.execute(delete(ReportRecord))
    db.execute(delete(TicketExtension))
    db.execute(delete(Ticket))
    db.commit()
    clock.clear_fixed()
    start_session_coverage()

    return {"session_id": body.session_id}


@router.get(
    "/report",
    response_model=SystemTestReportResponse,
    dependencies=[Depends(require_token)],
)
def get_system_test_report(session_id: str = Query(min_length=1)):
    session = get_session(session_id)
    if session is None:
        return JSONResponse(
            status_code=404,
            content={"message": "Unknown test session", "source": "system"},
        )
    if not session.ready:
        return JSONResponse(
            status_code=409,
            content={"message": "Test session is still preparing", "source": "system"},
        )

    return {
        "session_id": session_id,
        "coverage": {"code": code_coverage_measure()},
    }
