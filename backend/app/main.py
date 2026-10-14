from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import SessionLocal
from app.routers import health, users
from app.seed import init_db_and_seed


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle events."""
    # Initialize database tables and seed demo users idempotently on startup
    db = SessionLocal()
    try:
        init_db_and_seed(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS configuration for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Format Pydantic schema validation errors into the ARCHITECTURE.md error envelope."""
    field_errors: dict[str, str] = {}
    for err in exc.errors():
        loc = err.get("loc", [])
        # Extract field name from loc path
        field_name = str(loc[-1]) if loc else "general"
        msg = err.get("msg", "Invalid value")
        # Clean up Pydantic prefix if present
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, ") :]
        field_errors[field_name] = msg

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "One or more input fields failed validation.",
                "fields": field_errors,
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Ensure HTTP exceptions adhere to the standardized error envelope."""
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        payload = {
            "error": {
                "code": exc.detail["code"],
                "message": exc.detail.get("message", "An error occurred."),
                "fields": exc.detail.get("fields"),
            }
        }
    else:
        payload = {
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
            }
        }

    return JSONResponse(status_code=exc.status_code, content=payload)


# Mount routers
app.include_router(health.router)
app.include_router(users.router)
