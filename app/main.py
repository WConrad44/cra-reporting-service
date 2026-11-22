from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import API_TOKEN, MAX_BODY_BYTES
from .database import Base, SessionLocal, engine
from .models import Ticket
from .routes import cross_team, health, test_controls, tickets

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CRA Vulnerability Ticketing Service",
    version="0.5.0",
    description="Phase 5 implementation of the Pod K CRA Article 14 reporting service.",
)

# The common contract permits content encoding. Large 1,000-ticket list responses
# transfer substantially less JSON when clients advertise gzip support.
# Fast compression limits additional CPU use on small Render instances.
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=1)


@app.middleware("http")
async def body_size_limit(request: Request, call_next):
    length = request.headers.get("content-length")

    if length is not None:
        try:
            if int(length) > MAX_BODY_BYTES:
                if request.url.path != "/health":
                    authorization = request.headers.get("authorization", "")
                    scheme, _, token = authorization.partition(" ")
                    if scheme.lower() != "bearer" or token != API_TOKEN:
                        return JSONResponse(
                            status_code=401,
                            content={
                                "title": "Unauthorized",
                                "status": 401,
                                "detail": "Missing or invalid bearer token",
                            },
                            media_type="application/problem+json",
                        )
                return JSONResponse(
                    status_code=413,
                    content={
                        "title": "Request body too large",
                        "status": 413,
                    },
                    media_type="application/problem+json",
                )
        except ValueError:
            pass

    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    if request.url.path in {"/test/setup", "/test/report"}:
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid test-interface request", "source": "system"},
        )

    # FastAPI parses JSON before calling route dependencies. For unknown write
    # targets, the Pod K contract requires 404 before body/actor validation,
    # while authentication must still take precedence over 404.
    segments = request.url.path.strip("/").split("/")
    is_ticket_write = (
        len(segments) >= 2
        and segments[0] == "tickets"
        and (
            (request.method == "PATCH" and len(segments) == 2)
            or (request.method == "POST" and len(segments) == 3 and segments[2] == "triage")
        )
    )
    if is_ticket_write:
        scheme, _, token = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or token != API_TOKEN:
            return JSONResponse(
                status_code=401,
                content={
                    "title": "Unauthorized",
                    "status": 401,
                    "detail": "Missing or invalid bearer token",
                },
                media_type="application/problem+json",
            )
        with SessionLocal() as db:
            if db.get(Ticket, segments[1]) is None:
                return JSONResponse(
                    status_code=404,
                    content={
                        "title": "Not found",
                        "status": 404,
                        "detail": "Unknown ticket",
                    },
                    media_type="application/problem+json",
                )

    errors = []

    for error in exc.errors():
        loc = [
            str(x)
            for x in error.get("loc", [])
            if x != "body"
        ]

        errors.append(
            {
                "field": ".".join(loc) or "body",
                "message": error.get("msg", "invalid"),
            }
        )

    return JSONResponse(
        status_code=400,
        content={
            "title": "Invalid request",
            "status": 400,
            "errors": errors,
        },
        media_type="application/problem+json",
    )


@app.exception_handler(HTTPException)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    if request.url.path in {"/test/setup", "/test/report"}:
        detail = exc.detail
        if isinstance(detail, dict):
            message = str(detail.get("message") or detail.get("detail") or detail)
        else:
            message = str(detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": message or "Test-interface request failed", "source": "system"},
        )

    titles = {
        400: "Invalid request",
        401: "Unauthorized",
        404: "Not found",
        405: "Method not allowed",
        409: "State conflict",
        413: "Request body too large",
        422: "Rule violation",
    }

    content = {
        "title": titles.get(
            exc.status_code,
            "Request failed",
        ),
        "status": exc.status_code,
    }

    if isinstance(exc.detail, list):
        content["detail"] = "multiple validation errors"
        if exc.status_code in {400, 422}:
            content["errors"] = exc.detail
    elif isinstance(exc.detail, dict):
        field = exc.detail.get("field", "request")
        message = exc.detail.get("message", "invalid")

        content["detail"] = message

        if exc.status_code in {400, 422}:
            content["errors"] = [
                {
                    "field": field,
                    "message": message,
                }
            ]

    else:
        content["detail"] = str(exc.detail)

        if exc.status_code == 400:
            detail_lower = str(exc.detail).lower()

            if "actor" in detail_lower:
                content["errors"] = [
                    {
                        "field": "X-Actor",
                        "message": str(exc.detail),
                    }
                ]
            else:
                content["errors"] = [
                    {
                        "field": "request",
                        "message": str(exc.detail),
                    }
                ]

        elif exc.status_code == 422:
            content["errors"] = [
                {
                    "field": "request",
                    "message": str(exc.detail),
                }
            ]

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        media_type="application/problem+json",
    )


app.include_router(health.router)
app.include_router(cross_team.router)
app.include_router(tickets.router)
app.include_router(test_controls.router)