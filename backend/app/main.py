from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import SessionLocal, engine
from app.routers import health, issues, users
from app.seed import init_db_and_seed

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle events.

    In test environments, app.state.skip_startup_init is set to True,
    ensuring that the production database is not initialized or modified.
    """
    if not getattr(app.state, "skip_startup_init", False):
        db = SessionLocal()
        try:
            init_db_and_seed(db, bind=engine)
        finally:
            db.close()
    yield


def create_app(init_db_on_startup: bool = True) -> FastAPI:
    """Application factory configuring routes, middleware, and lifecycle management."""
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    application.state.skip_startup_init = not init_db_on_startup

    # CORS configuration for local frontend development
    application.add_middleware(
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

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Format Pydantic schema validation errors into the ARCHITECTURE.md error envelope."""
        field_errors: dict[str, str] = {}
        for err in exc.errors():
            loc = err.get("loc", [])
            field_name = str(loc[-1]) if loc else "general"
            msg = err.get("msg", "Invalid value")
            if msg.startswith("Value error, "):
                msg = msg[len("Value error, ") :]
            field_errors[field_name] = msg

        return JSONResponse(
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "One or more input fields failed validation.",
                    "fields": field_errors,
                }
            },
        )

    @application.exception_handler(HTTPException)
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

    @application.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Ensure internal database errors are logged without exposing stack traces or SQL details."""
        logger.error("Database operation failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "A database error occurred while processing your request. Please try again.",
                }
            },
        )

    # Mount routers
    application.include_router(health.router)
    application.include_router(users.router)
    application.include_router(issues.router)

    return application


# Global application instance for uvicorn
app = create_app(init_db_on_startup=True)
