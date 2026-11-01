from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import MAX_BODY_BYTES
from .database import Base, engine
from .routes import cross_team, health, test_controls, tickets

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CRA Vulnerability Ticketing Service",
    version="0.4.0",
    description="Phase 4 implementation of the Pod K CRA Article 14 reporting service.",
)


@app.middleware("http")
async def body_size_limit(request: Request, call_next):
    length = request.headers.get("content-length")

    if length is not None:
        try:
            if int(length) > MAX_BODY_BYTES:
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
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
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

    if isinstance(exc.detail, dict):
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