"""Versioned HTTP transport with centralized authorization and safe error envelopes."""

import json
import logging
import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from marketreadiness.ai.runtime import OllamaRuntime
from marketreadiness.data.store import Conflict, Store
from marketreadiness.domain.schemas import (
    Brief,
    ComparisonResult,
    ConfigResponse,
    Contract,
    Dataset,
    ErrorEnvelope,
    ForecastResult,
    Guardrails,
    MarketDetail,
    PlanningResult,
    SavedScenario,
    Scenario,
    Transfer,
    ValidationReport,
)
from marketreadiness.services.portfolio import PortfolioService
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

ROOT = Path(__file__).resolve().parents[2]
MAX_BODY = 20 * 1024 * 1024


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(
            {
                "level": record.levelname,
                "event": record.getMessage(),
                **getattr(record, "event_data", {}),
            },
            default=str,
        )


logger = logging.getLogger("marketreadiness")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


class BriefRequest(Contract):
    run_id: str | None = None
    period: Literal["daily", "weekly"] = "weekly"


class TransferRequest(Contract):
    run_id: str | None = None
    guardrails: Guardrails = Field(default_factory=Guardrails)


class Page(BaseModel):
    items: list[dict]
    total: int
    offset: int
    limit: int


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > MAX_BODY:
                response = JSONResponse(
                    {
                        "error": {
                            "code": "body_too_large",
                            "message": "Maximum request size is 20 MiB",
                            "trace_id": scope.get("state", {}).get("trace_id"),
                        }
                    },
                    status_code=413,
                )
                return await response(scope, receive, send)
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def create_app(
    database_url: str | None = None, mode: str | None = None, sample_path: Path | None = None
):
    mode = mode or os.getenv("APP_MODE", "demo")
    read_token = os.getenv("READ_API_TOKEN", "")
    write_token = os.getenv("WRITE_API_TOKEN", "")
    if mode not in {"demo", "secured"}:
        raise ValueError("APP_MODE must be demo or secured")
    if mode == "secured" and (
        min(len(read_token), len(write_token)) < 32 or read_token == write_token
    ):
        raise ValueError(
            "Secured mode requires distinct read/write tokens of at least 32 characters"
        )

    @asynccontextmanager
    async def lifespan(app):
        store = Store(
            database_url or os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'marketreadiness.db'}"),
            None if database_url else os.getenv("READ_DATABASE_URL"),
        )
        provider = os.getenv("LLM_PROVIDER", "none")
        if provider not in {"none", "ollama"}:
            raise ValueError("LLM_PROVIDER must be none or ollama")
        runtime = (
            OllamaRuntime(
                os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                os.getenv("LLM_MODEL", "qwen3:4b"),
            )
            if provider == "ollama"
            else None
        )
        app.state.service = PortfolioService(store, runtime)
        app.state.service.seed(sample_path or ROOT / "data/sample/portfolio.json")
        yield
        store.close()

    app = FastAPI(
        title="MarketReadiness AI",
        version="0.1.0",
        lifespan=lifespan,
        description="Deterministic material readiness with optional local AI briefs.",
        responses={
            code: {"model": ErrorEnvelope} for code in (400, 401, 403, 404, 409, 413, 415, 422, 500)
        },
        docs_url=None,
        redoc_url=None,
        openapi_url="/openapi.json" if mode == "demo" else None,
    )
    if mode == "demo":
        app.mount(
            "/docs-assets", StaticFiles(directory=ROOT / "apps/api/static"), name="docs-assets"
        )

        @app.get("/docs", include_in_schema=False)
        def documentation():
            return get_swagger_ui_html(
                openapi_url="/openapi.json",
                title="MarketReadiness API",
                swagger_js_url="/docs-assets/swagger-ui-bundle.js",
                swagger_css_url="/docs-assets/swagger-ui.css",
                swagger_favicon_url="/docs-assets/favicon-32x32.png",
                swagger_ui_parameters={"validatorUrl": None, "persistAuthorization": False},
            )

    app.add_middleware(BodyLimit)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,api,testserver").split(","),
    )

    @app.middleware("http")
    async def trace(request: Request, call_next):
        trace_id = str(uuid4())
        request.state.trace_id = trace_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                "request_failed",
                extra={"event_data": {"trace_id": trace_id, "error_type": type(exc).__name__}},
            )
            response = JSONResponse(
                {
                    "error": {
                        "code": "internal_error",
                        "message": "Request failed; consult server trace",
                        "trace_id": trace_id,
                    }
                },
                status_code=500,
            )
        if response.status_code == 400 and response.headers.get("content-type", "").startswith(
            "text/plain"
        ):
            response = JSONResponse(
                {
                    "error": {
                        "code": "invalid_host",
                        "message": "Host is not allowed",
                        "trace_id": trace_id,
                    }
                },
                status_code=400,
            )
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        logger.info(
            "request_complete",
            extra={
                "event_data": {
                    "trace_id": trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                }
            },
        )
        return response

    def error_response(request, code, message, status, details=None):
        return JSONResponse(
            {
                "error": {
                    "code": code,
                    "message": message,
                    "trace_id": getattr(request.state, "trace_id", None),
                    "details": details,
                }
            },
            status_code=status,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        return error_response(request, f"http_{exc.status_code}", str(exc.detail), exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        details = [
            {"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()
        ]
        return error_response(
            request, "validation_error", "Request validation failed", 422, details
        )

    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        return error_response(request, "invalid_operation", str(exc), 422)

    @app.exception_handler(LookupError)
    async def missing(request, exc):
        return error_response(request, "not_found", str(exc), 404)

    @app.exception_handler(Conflict)
    async def conflict(request, exc):
        return error_response(request, "conflict", str(exc), 409)

    def authorize(write=False):
        def check(request: Request, authorization: str | None = Header(default=None)):
            if (
                request.method == "POST"
                and request.headers.get("content-type", "").split(";")[0] != "application/json"
            ):
                raise HTTPException(415, "Use application/json")
            if mode == "demo":
                origin = request.headers.get("origin")
                allowed = {
                    f"http://{h}:{p}"
                    for h in ("localhost", "127.0.0.1")
                    for p in (8080, 5173, 8000)
                }
                if origin and origin not in allowed:
                    raise HTTPException(403, "Demo access is restricted to local origins")
                return
            token = (
                authorization.removeprefix("Bearer ")
                if authorization and authorization.startswith("Bearer ")
                else ""
            )
            allowed_tokens = [write_token] if write else [read_token, write_token]
            if not any(secrets.compare_digest(token, t) for t in allowed_tokens):
                raise HTTPException(401, "Valid bearer token required for this operation")

        return check

    def service(request: Request):
        return request.app.state.service

    def idempotency(idempotency_key: str = Header(min_length=8, max_length=128)):
        if not re.fullmatch(r"[a-zA-Z0-9_.:-]+", idempotency_key):
            raise HTTPException(422, "Invalid Idempotency-Key")
        return idempotency_key

    reads = APIRouter(prefix="/api/v1", dependencies=[Depends(authorize())], tags=["Read-only"])
    writes = APIRouter(
        prefix="/api/v1", dependencies=[Depends(authorize(write=True))], tags=["Mutations"]
    )
    queries = APIRouter(
        prefix="/api/v1",
        dependencies=[Depends(authorize())],
        tags=["Computed queries (no state changes)"],
    )

    @app.get("/health/live", tags=["Health"])
    def live():
        return {"status": "ok"}

    @app.get("/health/ready", tags=["Health"])
    def ready(svc=Depends(service)):
        try:
            svc.store.healthy()
            active = svc.dataset()
            return {"status": "ready", "dataset_id": active.id}
        except Exception:
            raise HTTPException(503, "Data service unavailable") from None

    @reads.get("/config", response_model=ConfigResponse)
    def config():
        return {
            "mode": mode,
            "llm_provider": os.getenv("LLM_PROVIDER", "none"),
            "version": "0.1.0",
            "upload_limit_bytes": MAX_BODY,
        }

    @reads.get("/portfolio", response_model=PlanningResult)
    def portfolio(svc=Depends(service)):
        return svc.baseline()

    @reads.get("/markets/{market_id}", response_model=MarketDetail)
    def market(market_id: str, svc=Depends(service)):
        result = svc.baseline()
        m = next((m for m in result.markets if m.market_id == market_id), None)
        if not m:
            raise LookupError("Market not found")
        return {
            "market": m,
            "requirements": [r for r in result.requirements if r.market_id == market_id],
            "phases": [p for p in result.phases if p.market_id == market_id],
            "ledger": [p for p in result.ledger if p.market_id == market_id],
        }

    @reads.get("/records/{table}", response_model=Page)
    def records(
        table: str,
        offset: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=500),
        svc=Depends(service),
    ):
        return svc.records(table, offset, limit)

    @reads.get("/validation-reports", response_model=list[ValidationReport])
    def validations(
        offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), svc=Depends(service)
    ):
        return svc.store.list("validation", offset, limit)

    @reads.get("/scenarios", response_model=list[SavedScenario])
    def scenarios(
        offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), svc=Depends(service)
    ):
        return [
            {
                "id": x["id"],
                "name": x["scenario"]["name"],
                "readiness": x["readiness"],
                "dataset_id": x["dataset_id"],
            }
            for x in svc.store.list("scenario", offset, limit)
        ]

    @reads.get("/scenarios/{run_id}", response_model=PlanningResult)
    def scenario_result(run_id: str, svc=Depends(service)):
        return svc.result(run_id)

    @reads.get("/compare", response_model=ComparisonResult)
    def compare(right: str, left: str | None = None, svc=Depends(service)):
        return svc.compare(left, right)

    @reads.get("/forecast", response_model=ForecastResult, response_model_exclude_none=True)
    def forecasts(svc=Depends(service)):
        return svc.forecasts()

    @reads.get("/exports/readiness.csv", response_class=Response)
    def export(svc=Depends(service)):
        return Response(
            svc.csv(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="market-readiness.csv"'},
        )

    @queries.post("/transfers", response_model=list[Transfer])
    def transfers(body: TransferRequest, svc=Depends(service)):
        return svc.transfers(body.run_id, body.guardrails)

    @queries.post("/briefs", response_model=Brief)
    def brief(body: BriefRequest, request: Request, svc=Depends(service)):
        return svc.brief(body.run_id, body.period, request.state.trace_id)

    @writes.post("/scenarios", response_model=PlanningResult, status_code=201)
    def simulate(body: Scenario, key=Depends(idempotency), svc=Depends(service)):
        return svc.scenario(body, key)

    @writes.post("/imports", response_model=ValidationReport)
    async def ingest(request: Request, key=Depends(idempotency), svc=Depends(service)):
        try:
            raw = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise HTTPException(400, "Malformed JSON") from None
        if not isinstance(raw, dict):
            raise HTTPException(422, "Dataset must be a JSON object")
        # No client filename is ever accepted or written; payload is schema-validated.
        return await run_in_threadpool(svc.ingest, raw, key)

    app.include_router(reads)
    app.include_router(queries)
    app.include_router(writes)

    def openapi_with_import_contract():
        # Imports validate in the service to persist all errors, so register the
        # same Dataset contract explicitly for the interactive OpenAPI editor.
        if app.openapi_schema is None:
            spec = get_openapi(
                title=app.title, version=app.version, routes=app.routes, description=app.description
            )
            dataset_schema = Dataset.model_json_schema(ref_template="#/components/schemas/{model}")
            components = spec.setdefault("components", {}).setdefault("schemas", {})
            components.update(dataset_schema.pop("$defs", {}))
            components["Dataset"] = dataset_schema
            spec["paths"]["/api/v1/imports"]["post"]["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/Dataset"}}
                },
            }
            app.openapi_schema = spec
        return app.openapi_schema

    app.openapi = openapi_with_import_contract
    return app


app = create_app()
