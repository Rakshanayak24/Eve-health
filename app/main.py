import logging
import sys
import time
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import Base, engine
from app.routers import auth, centres, bookings, payments

# ---------------------------------------------------------------------------
# Structured logging: one JSON-ish line per request with a request id, so
# individual requests (including webhook retries) can be traced through logs.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
    stream=sys.stdout,
)
logger = logging.getLogger("eve.api")

app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend service for diagnostic test discovery, bookings, and simulated "
        "payments. See /docs for interactive API documentation."
    ),
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(centres.router)
app.include_router(bookings.router)
app.include_router(payments.router)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 2)
    logger.info(
        f"{request.method} {request.url.path} status={response.status_code} "
        f"duration_ms={duration_ms} request_id={request_id}"
    )
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Invalid request", "errors": exc.errors()},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.on_event("startup")
def on_startup() -> None:
    """
    Create tables if they don't exist yet.

    NOTE: for this assignment, schema management is done via `create_all`
    rather than Alembic migrations, to keep local setup to a single command
    (see README "What I'd improve" for how this should evolve in a real
    project). This is wrapped in a try/except so that, in test environments
    where the DB dependency is overridden with an isolated test database
    (see tests/conftest.py), a not-yet-reachable *default* production
    database configured via settings does not crash app startup - actual
    request handling always goes through the `get_db` dependency, which
    tests override independently of this call.
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # pragma: no cover - defensive, environment-dependent
        logger.warning(f"Could not create tables at startup: {exc}")


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": settings.app_name}
