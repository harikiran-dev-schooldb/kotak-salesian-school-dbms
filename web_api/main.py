from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

if __package__:
    from .auth import Principal, current_principal, require_admin
    from .config import Settings
    from .database import create_database_engine
    from .queries import (
        attendance_summary,
        audit_entries,
        concessions,
        fees,
        overview,
        pipeline_status,
        students,
        unmatched_transactions,
    )
    from .refresh import PIPELINES, RefreshManager
else:  # Vercel imports main.py directly when web_api is the project root.
    from auth import Principal, current_principal, require_admin
    from config import Settings
    from database import create_database_engine
    from queries import (
        attendance_summary,
        audit_entries,
        concessions,
        fees,
        overview,
        pipeline_status,
        students,
        unmatched_transactions,
    )
    from refresh import PIPELINES, RefreshManager


def create_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    app_settings = settings or Settings()
    configuration_error: str | None = None
    try:
        app_settings.validate()
    except RuntimeError as exc:
        configuration_error = str(exc)
    app_engine = engine
    if app_engine is None and configuration_error is None:
        try:
            app_engine = create_database_engine(app_settings.database_url)
        except (SQLAlchemyError, ModuleNotFoundError) as exc:
            configuration_error = f"DATABASE_URL setup failed ({type(exc).__name__})"

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # Do not make serverless startup depend on an external database. The
        # health route reports configuration/connectivity problems as JSON.
        yield
        if app_engine is not None:
            app_engine.dispose()

    application = FastAPI(
        title="Kotak School Data API",
        version="1.0.0",
        docs_url="/docs" if app_settings.environment != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.settings = app_settings
    application.state.engine = app_engine
    application.state.configuration_error = configuration_error
    application.state.refresh_manager = (
        RefreshManager(app_settings, app_engine) if app_engine is not None else None
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

    @application.get("/health")
    async def health(request: Request):
        if request.app.state.configuration_error:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "configuration_error",
                    "detail": request.app.state.configuration_error,
                },
            )
        try:
            with request.app.state.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "database_unavailable",
                    "detail": "The database connection could not be established.",
                },
            )
        return {"status": "healthy", "service": "kotak-school-data-api"}

    @application.get("/api/session")
    async def session(principal: Principal = Depends(current_principal)):
        return {"authenticated": True, "role": principal.role, "name": principal.name}

    @application.get("/api/overview")
    async def get_overview(
        request: Request,
        academic_year_id: int = Query(default=3, ge=1, le=20),
        _: Principal = Depends(current_principal),
    ):
        return overview(request.app.state.engine, academic_year_id)

    @application.get("/api/students")
    async def get_students(
        request: Request,
        academic_year_id: int = Query(default=3, ge=1, le=20),
        search: str = Query(default="", max_length=40),
        grade_id: str | None = Query(default=None, max_length=20),
        status_id: int | None = Query(default=None, ge=1, le=5),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0, le=100000),
        principal: Principal = Depends(current_principal),
    ):
        return students(
            request.app.state.engine,
            academic_year_id,
            search,
            grade_id,
            status_id,
            limit,
            offset,
            reveal_identity=principal.role == "admin",
        )

    @application.get("/api/fees")
    async def get_fees(
        request: Request,
        academic_year_id: int = Query(default=3, ge=1, le=20),
        limit: int = Query(default=20, ge=1, le=100),
        _: Principal = Depends(current_principal),
    ):
        return fees(request.app.state.engine, academic_year_id, limit)

    @application.get("/api/attendance")
    async def get_attendance(
        request: Request,
        academic_year_id: int = Query(default=3, ge=1, le=20),
        _: Principal = Depends(current_principal),
    ):
        return attendance_summary(request.app.state.engine, academic_year_id)

    @application.get("/api/concessions")
    async def get_concessions(
        request: Request,
        academic_year_id: int = Query(default=3, ge=1, le=20),
        limit: int = Query(default=50, ge=1, le=200),
        _: Principal = Depends(current_principal),
    ):
        return concessions(request.app.state.engine, academic_year_id, limit)

    @application.get("/api/transactions/unmatched")
    async def get_unmatched(
        request: Request,
        limit: int = Query(default=50, ge=1, le=200),
        _: Principal = Depends(current_principal),
    ):
        return unmatched_transactions(request.app.state.engine, limit)

    @application.get("/api/pipeline/status")
    async def get_pipeline_status(request: Request, _: Principal = Depends(current_principal)):
        return {
            **pipeline_status(request.app.state.engine),
            "refresh": request.app.state.refresh_manager.state(),
            "execution_enabled": request.app.state.settings.enable_pipeline_execution,
        }

    @application.get("/api/audit")
    async def get_audit(
        request: Request,
        limit: int = Query(default=50, ge=1, le=200),
        _: Principal = Depends(require_admin),
    ):
        return {"items": audit_entries(request.app.state.engine, limit)}

    @application.post("/api/refresh/{pipeline}", status_code=status.HTTP_202_ACCEPTED)
    async def refresh_pipeline(
        pipeline: str,
        request: Request,
        principal: Principal = Depends(require_admin),
    ):
        if pipeline not in PIPELINES:
            raise HTTPException(status_code=404, detail="Unknown pipeline")
        try:
            return request.app.state.refresh_manager.start(pipeline, principal.name)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Mount the compiled dashboard last so the API routes above retain priority.
    # This gives local and container deployments a same-origin option while the
    # separately hosted private dashboard can still connect over CORS.
    dashboard_directories = (
        Path(__file__).resolve().parents[1] / "web_dashboard" / "dist",
        Path(__file__).resolve().parent / "public",
        Path(__file__).resolve().parents[1] / "public",
    )
    dashboard_dir = next((path for path in dashboard_directories if path.is_dir()), None)
    if dashboard_dir:
        application.mount("/", StaticFiles(directory=dashboard_dir, html=True), name="dashboard")

    return application


app = create_app()

