from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from analytics.api_models import (
    ActiveWorkspaceContext,
    AdvertisingResponse,
    AuthProfileResponse,
    AuthSessionResponse,
    ExportCreateRequest,
    ExportRecord,
    ExportRecordResponse,
    ExportsResponse,
    AdvisorQueryRequest,
    AdvisorQueryResponse,
    AdvisorResponse,
    ApiErrorResponse,
    BusinessResponse,
    CabinetList,
    CabinetSummary,
    JobRecord,
    JobRecordResponse,
    JobsResponse,
    ExecutiveResponse,
    FinanceResponse,
    HealthResponse,
    InventoryResponse,
    NotificationChannel,
    NotificationChannelsResponse,
    NotificationDelivery,
    NotificationEvent,
    NotificationHistoryResponse,
    NotificationRule,
    NotificationRuleCreateRequest,
    NotificationRuleResponse,
    NotificationRuleUpdateRequest,
    NotificationRulesResponse,
    NotificationStatus,
    NotificationTestRequest,
    NotificationTestResponse,
    NotificationsResponse,
    OrganizationList,
    OrganizationResponse,
    OrganizationProfile,
    OrganizationSummary,
    ProductsResponse,
    ReportsResponse,
    ScheduleCreateRequest,
    ScheduleRecord,
    ScheduleRecordResponse,
    ScheduleUpdateRequest,
    SchedulesResponse,
    StatusResponse,
    SystemResponse,
    MetricsResponse,
    UserProfile,
    VersionResponse,
    WbCabinetProfile,
    WbCabinetResponse,
    WorkspaceSelection,
)
from analytics.advertising import get_advertising_payload
from analytics.advisor import (
    get_advisor_payload,
    get_advisor_payload_fast,
    get_advisor_query_degraded_payload,
    get_advisor_query_payload,
)
from analytics.business import get_business_payload
from analytics.common import BUILD_VERSION, DEFAULT_USER_ID, PRODUCT_NAME
from analytics.degraded import (
    advertising_degraded,
    advisor_degraded,
    business_degraded,
    executive_degraded,
    finance_degraded,
    inventory_degraded,
    products_degraded,
    reports_degraded,
    system_degraded,
)
from analytics.executive import get_executive_payload, get_executive_payload_fast
from analytics.finance import get_finance_payload
from analytics.inventory import get_inventory_payload
from analytics.logging_config import configure_logging, get_logger, safe_log_extra
from analytics.monitoring import get_health_snapshot, get_metrics_snapshot
from analytics.performance import build_runtime_metadata, now_monotonic_ms, record_endpoint_result
from analytics.runtime import run_with_timeout
from analytics.products import get_products_payload
from analytics.reports import get_reports_payload, get_reports_payload_fast
from analytics.runtime import safe_build_snapshot
from analytics.startup import validate_startup
from analytics.system import get_status_payload, get_system_payload, get_version_payload
from analytics.build_info import get_build_environment
from analytics.env import get_allowed_origins, get_trusted_hosts
from analytics.multi_tenant import (
    get_active_cabinet,
    get_active_organization,
    get_workspace_context,
    list_cabinets,
    list_organizations,
    scoped_record,
    scoped_records,
    select_cabinet,
    select_organization,
    set_active_cabinet_connection,
)

READ_ONLY_MODE = "read_only"
DEFAULT_API_HOST = "0.0.0.0"
DEFAULT_API_PORT = 8000
EXPORT_COUNTER = 3
NOTIFICATION_RULE_COUNTER = 7
configure_logging()
LOGGER = get_logger("api")
STARTUP_VALIDATION = validate_startup()

ENDPOINT_RUNTIME = {
    "/api/command-center": {"cache_key": "executive", "ttl_seconds": 120, "timeout_ms": 5000},
    "/api/executive": {"cache_key": "executive", "ttl_seconds": 120, "timeout_ms": 5000},
    "/api/business": {"cache_key": "business", "ttl_seconds": 180, "timeout_ms": 10000},
    "/api/finance": {"cache_key": "finance", "ttl_seconds": 180, "timeout_ms": 10000},
    "/api/advertising": {"cache_key": "advertising", "ttl_seconds": 180, "timeout_ms": 10000},
    "/api/products": {"cache_key": "products", "ttl_seconds": 180, "timeout_ms": 10000},
    "/api/inventory": {"cache_key": "inventory", "ttl_seconds": 180, "timeout_ms": 10000},
    "/api/advisor": {"cache_key": "advisor", "ttl_seconds": 120, "timeout_ms": 5000},
    "/api/advisor/query": {"cache_key": "advisor_query", "ttl_seconds": 0, "timeout_ms": 5000},
    "/api/reports": {"cache_key": "reports", "ttl_seconds": 120, "timeout_ms": 5000},
    "/api/system": {"cache_key": "system", "ttl_seconds": 120, "timeout_ms": 5000},
}

app = FastAPI(title=f"{PRODUCT_NAME} Analytics Engine API", version=BUILD_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=get_trusted_hosts())


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

DEV_EXPORTS: list[dict[str, Any]] = [
    {
        "id": "export_001",
        "name": "CEO Daily Report",
        "workspace": "executive",
        "format": "PDF",
        "status": "completed",
        "source": "dev",
        "owner": "Andrey Voronov",
        "size": "1.8 MB",
        "createdAt": "2026-06-30T09:00:00Z",
        "downloadUrl": None,
    },
    {
        "id": "export_002",
        "name": "Finance Profit Audit",
        "workspace": "finance",
        "format": "CSV",
        "status": "completed",
        "source": "dev",
        "owner": "Andrey Voronov",
        "size": "420 KB",
        "createdAt": "2026-06-30T10:15:00Z",
        "downloadUrl": None,
    },
    {
        "id": "export_003",
        "name": "Advertising Weekly Review",
        "workspace": "advertising",
        "format": "JSON",
        "status": "running",
        "source": "dev",
        "owner": "Andrey Voronov",
        "size": None,
        "createdAt": "2026-06-30T10:45:00Z",
        "downloadUrl": None,
    },
]

DEV_SCHEDULES: list[dict[str, Any]] = [
    {
        "id": "schedule_ceo_daily",
        "name": "CEO Daily",
        "workspace": "executive",
        "enabled": True,
        "time": "09:00",
        "timezone": "Europe/Moscow",
        "cadence": "daily",
        "format": "PDF",
        "status": "healthy",
        "lastRunAt": "2026-06-30T09:00:00Z",
        "nextRunAt": "2026-07-01T09:00:00Z",
        "owner": "Andrey Voronov",
    },
    {
        "id": "schedule_profit_daily",
        "name": "Profit Audit Daily",
        "workspace": "finance",
        "enabled": True,
        "time": "10:00",
        "timezone": "Europe/Moscow",
        "cadence": "daily",
        "format": "CSV",
        "status": "watch",
        "lastRunAt": "2026-06-30T10:00:00Z",
        "nextRunAt": "2026-07-01T10:00:00Z",
        "owner": "Andrey Voronov",
    },
    {
        "id": "schedule_advisor_digest",
        "name": "Advisor Digest",
        "workspace": "advisor",
        "enabled": False,
        "time": "18:00",
        "timezone": "Europe/Moscow",
        "cadence": "daily",
        "format": "JSON",
        "status": "paused",
        "lastRunAt": None,
        "nextRunAt": None,
        "owner": "Andrey Voronov",
    },
]

DEV_JOBS: list[dict[str, Any]] = [
    {
        "id": "job_001",
        "type": "export",
        "workspace": "executive",
        "status": "completed",
        "progress": 100,
        "duration": "18s",
        "startedAt": "2026-06-30T09:00:00Z",
        "finishedAt": "2026-06-30T09:00:18Z",
        "source": "dev",
        "owner": "Andrey Voronov",
        "message": "CEO daily report placeholder completed.",
    },
    {
        "id": "job_002",
        "type": "scheduler",
        "workspace": "finance",
        "status": "running",
        "progress": 62,
        "duration": "31s",
        "startedAt": "2026-06-30T10:45:00Z",
        "finishedAt": None,
        "source": "dev",
        "owner": "Andrey Voronov",
        "message": "Finance audit bundle is assembling placeholder artifacts.",
    },
    {
        "id": "job_003",
        "type": "export",
        "workspace": "inventory",
        "status": "failed",
        "progress": 100,
        "duration": "9s",
        "startedAt": "2026-06-30T08:15:00Z",
        "finishedAt": "2026-06-30T08:15:09Z",
        "source": "dev",
        "owner": "Andrey Voronov",
        "message": "Placeholder job kept the contract but marked exporter unavailable.",
    },
]

DEV_NOTIFICATION_CHANNELS: list[dict[str, Any]] = [
    {
        "id": "channel_telegram",
        "type": "telegram",
        "status": "pending",
        "connected": False,
        "lastTestAt": None,
        "deliveryHealth": "Placeholder",
        "setupAction": "Connect backend-side bot credentials",
    },
    {
        "id": "channel_email",
        "type": "email",
        "status": "pending",
        "connected": False,
        "lastTestAt": None,
        "deliveryHealth": "Placeholder",
        "setupAction": "Configure backend SMTP transport",
    },
    {
        "id": "channel_webhook",
        "type": "webhook",
        "status": "disabled",
        "connected": False,
        "lastTestAt": None,
        "deliveryHealth": "Idle",
        "setupAction": "Register backend-side webhook secret",
    },
    {
        "id": "channel_in_app",
        "type": "in_app",
        "status": "enabled",
        "connected": True,
        "lastTestAt": "2026-06-30T11:20:00Z",
        "deliveryHealth": "Healthy",
        "setupAction": "Open notifications hub",
    },
]

DEV_NOTIFICATION_RULES: list[dict[str, Any]] = [
    {
        "id": "notification_rule_001",
        "name": "Daily CEO Report",
        "enabled": True,
        "channel": "in_app",
        "severity": "info",
        "trigger": "Scheduled CEO report delivery",
        "schedule": "Daily 09:00 Europe/Moscow",
        "owner": "Andrey Voronov",
        "lastTriggeredAt": "2026-06-30T09:00:00Z",
        "deepLink": "/executive",
    },
    {
        "id": "notification_rule_002",
        "name": "Profit Drop Alert",
        "enabled": True,
        "channel": "telegram",
        "severity": "high",
        "trigger": "Operating profit week-over-week drop > 10%",
        "schedule": "Event-driven",
        "owner": "Andrey Voronov",
        "lastTriggeredAt": "2026-06-29T14:10:00Z",
        "deepLink": "/finance",
    },
    {
        "id": "notification_rule_003",
        "name": "Out Of Stock Risk",
        "enabled": True,
        "channel": "in_app",
        "severity": "high",
        "trigger": "Stock coverage below threshold",
        "schedule": "Every 2 hours",
        "owner": "Andrey Voronov",
        "lastTriggeredAt": "2026-06-30T08:25:00Z",
        "deepLink": "/inventory",
    },
    {
        "id": "notification_rule_004",
        "name": "High Advertising Spend",
        "enabled": True,
        "channel": "email",
        "severity": "medium",
        "trigger": "Spend exceeds daily efficiency plan",
        "schedule": "Event-driven",
        "owner": "Andrey Voronov",
        "lastTriggeredAt": "2026-06-30T10:35:00Z",
        "deepLink": "/advertising",
    },
    {
        "id": "notification_rule_005",
        "name": "Finance Data Quality Warning",
        "enabled": False,
        "channel": "in_app",
        "severity": "medium",
        "trigger": "Finance confidence below 80%",
        "schedule": "After finance snapshot",
        "owner": "Andrey Voronov",
        "lastTriggeredAt": None,
        "deepLink": "/finance",
    },
    {
        "id": "notification_rule_006",
        "name": "Weekly Report",
        "enabled": True,
        "channel": "email",
        "severity": "info",
        "trigger": "Weekly report bundle available",
        "schedule": "Weekly Monday 08:00",
        "owner": "Andrey Voronov",
        "lastTriggeredAt": "2026-06-30T08:00:00Z",
        "deepLink": "/reports",
    },
    {
        "id": "notification_rule_007",
        "name": "Advisor Critical Recommendation",
        "enabled": True,
        "channel": "in_app",
        "severity": "critical",
        "trigger": "Advisor emits critical recommendation",
        "schedule": "Event-driven",
        "owner": "Andrey Voronov",
        "lastTriggeredAt": "2026-06-30T11:10:00Z",
        "deepLink": "/advisor",
    },
]

DEV_NOTIFICATION_HISTORY: list[dict[str, Any]] = [
    {
        "id": "notification_event_001",
        "title": "CEO daily report is ready",
        "channel": "in_app",
        "status": "sent",
        "time": "2026-06-30T09:00:12Z",
        "target": "Executive inbox",
        "relatedWorkspace": "executive",
        "error": None,
        "deepLink": "/executive",
    },
    {
        "id": "notification_event_002",
        "title": "Profit drop alert",
        "channel": "telegram",
        "status": "failed",
        "time": "2026-06-30T10:12:00Z",
        "target": "Telegram placeholder",
        "relatedWorkspace": "finance",
        "error": "Production delivery is not enabled in dev mode.",
        "deepLink": "/finance",
    },
    {
        "id": "notification_event_003",
        "title": "Advisor critical recommendation",
        "channel": "in_app",
        "status": "sent",
        "time": "2026-06-30T11:10:00Z",
        "target": "Advisor workspace",
        "relatedWorkspace": "advisor",
        "error": None,
        "deepLink": "/advisor",
    },
]


@app.on_event("startup")
async def on_startup() -> None:
    app.state.startup_validation = STARTUP_VALIDATION
    app.state.environment = get_build_environment()
    LOGGER.info(
        "API startup validation completed",
        extra=safe_log_extra(startup_ok=STARTUP_VALIDATION.get("ok"), environment=app.state.environment),
    )


@app.exception_handler(Exception)
async def api_exception_handler(request: Request, exc: Exception):
    LOGGER.exception(
        "Unhandled API exception",
        extra=safe_log_extra(path=str(request.url.path), error_type=exc.__class__.__name__),
    )
    environment = str(getattr(app.state, "environment", get_build_environment()))
    public_message = str(exc) if environment != "production" else "Internal server error."
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": public_message,
            "details": {
                "path": str(request.url.path),
                "type": exc.__class__.__name__,
            },
        },
    )


@app.get("/api/health", response_model=HealthResponse, responses={500: {"model": ApiErrorResponse}})
def api_health() -> dict[str, str]:
    started_at = now_monotonic_ms()
    health = get_health_snapshot(runtime_mode=READ_ONLY_MODE, backend_status="ok")
    payload = {
        "status": "ok",
        "product": PRODUCT_NAME,
        "mode": READ_ONLY_MODE,
        **health,
        "startup": STARTUP_VALIDATION,
        "runtime": build_runtime_metadata(
            duration_ms=now_monotonic_ms() - started_at,
            cached=False,
            stale=False,
            degraded=False,
            source="live",
        ),
    }
    record_endpoint_result(
        "/api/health",
        duration_ms=float((payload.get("runtime") or {}).get("duration_ms") or 0.0),
        success=True,
        source="live",
        cached=False,
        stale=False,
        degraded=False,
    )
    return payload


@app.get("/api/metrics", response_model=MetricsResponse, responses={500: {"model": ApiErrorResponse}})
def api_metrics() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    payload = get_metrics_snapshot(
        performance=get_status_payload().get("endpoints"),
        startup=STARTUP_VALIDATION,
    )
    payload["runtime"] = build_runtime_metadata(
        duration_ms=now_monotonic_ms() - started_at,
        cached=False,
        stale=False,
        degraded=False,
        source="live",
    )
    return payload


def _cached_snapshot(
    endpoint: str,
    builder,
    degraded_builder,
) -> dict[str, Any]:
    config = ENDPOINT_RUNTIME[endpoint]
    return safe_build_snapshot(
        endpoint=endpoint,
        cache_key=str(config["cache_key"]),
        ttl_seconds=int(config["ttl_seconds"]),
        timeout_ms=int(config["timeout_ms"]),
        builder=builder,
        degraded_builder=degraded_builder,
    )


def _auth_runtime(source: str = "dev", started_at: float | None = None) -> dict[str, Any]:
    duration_ms = 0.0 if started_at is None else now_monotonic_ms() - started_at
    return build_runtime_metadata(
        duration_ms=duration_ms,
        cached=False,
        stale=False,
        degraded=False,
        source=source,
    )


def _automation_runtime(started_at: float | None = None, source: str = "dev") -> dict[str, Any]:
    return _auth_runtime(source=source, started_at=started_at)


def _notifications_runtime(started_at: float | None = None, source: str = "dev") -> dict[str, Any]:
    return _auth_runtime(source=source, started_at=started_at)


def _find_by_id(rows: list[dict[str, Any]], item_id: str) -> dict[str, Any]:
    for row in rows:
        if str(row.get("id")) == item_id:
            return row
    raise KeyError(item_id)


def _build_notification_status() -> dict[str, Any]:
    enabled_rules = sum(1 for item in DEV_NOTIFICATION_RULES if bool(item.get("enabled")))
    muted_rules = sum(
        1
        for item in DEV_NOTIFICATION_RULES
        if str(item.get("severity", "")).lower() == "muted" or not bool(item.get("enabled"))
    )
    failed_deliveries = sum(1 for item in DEV_NOTIFICATION_HISTORY if item.get("status") == "failed")
    active_channels = sum(1 for item in DEV_NOTIFICATION_CHANNELS if bool(item.get("connected")))
    health = "Watch" if failed_deliveries > 0 else "Healthy"
    return NotificationStatus(
        enabledRules=enabled_rules,
        mutedRules=muted_rules,
        failedDeliveries=failed_deliveries,
        lastDelivery=(DEV_NOTIFICATION_HISTORY[0].get("time") if DEV_NOTIFICATION_HISTORY else None),
        activeChannels=active_channels,
        health=health,
    ).model_dump()


def _build_dev_auth_payload(*, cabinet_connected: bool | None = None) -> dict[str, Any]:
    organization = OrganizationProfile(**get_active_organization())
    cabinet_row = get_active_cabinet()
    resolved_connected = bool(cabinet_row.get("connected")) if cabinet_connected is None else cabinet_connected
    timestamp = datetime.now(timezone.utc).isoformat()
    user = UserProfile(
        id="user_dev_founder",
        name="Andrey Voronov",
        email="andrey@vooglii.local",
        role="owner",
        avatarUrl=None,
        createdAt="2026-06-01T09:00:00Z",
    )
    cabinet = WbCabinetProfile(
        id=str(cabinet_row["id"]),
        name=str(cabinet_row["name"]),
        sellerId=str(cabinet_row["sellerId"]),
        status="connected" if resolved_connected else "disconnected",
        connected=resolved_connected,
        lastSyncAt=(str(cabinet_row.get("lastSyncAt")) if cabinet_row.get("lastSyncAt") else timestamp) if resolved_connected else None,
        dataQuality=str(cabinet_row.get("dataQuality") or ("high" if resolved_connected else "pending")),
        tokenStatus=str(cabinet_row.get("tokenStatus") or "safe_placeholder"),
    )
    return {
        "authenticated": True,
        "user": user.model_dump(),
        "organization": organization.model_dump(),
        "cabinet": cabinet.model_dump(),
    }


@app.get("/api/command-center", response_model=ExecutiveResponse, responses={500: {"model": ApiErrorResponse}})
def api_command_center() -> dict[str, Any]:
    return _cached_snapshot("/api/command-center", get_executive_payload_fast, executive_degraded)


@app.get("/api/executive", response_model=ExecutiveResponse, responses={500: {"model": ApiErrorResponse}})
def api_executive() -> dict[str, Any]:
    return _cached_snapshot("/api/executive", get_executive_payload_fast, executive_degraded)


@app.get("/api/business", response_model=BusinessResponse, responses={500: {"model": ApiErrorResponse}})
def api_business() -> dict[str, Any]:
    return _cached_snapshot("/api/business", get_business_payload, business_degraded)


@app.get("/api/finance", response_model=FinanceResponse, responses={500: {"model": ApiErrorResponse}})
def api_finance() -> dict[str, Any]:
    return _cached_snapshot("/api/finance", get_finance_payload, finance_degraded)


@app.get("/api/advertising", response_model=AdvertisingResponse, responses={500: {"model": ApiErrorResponse}})
def api_advertising() -> dict[str, Any]:
    return _cached_snapshot("/api/advertising", get_advertising_payload, advertising_degraded)


@app.get("/api/products", response_model=ProductsResponse, responses={500: {"model": ApiErrorResponse}})
def api_products() -> dict[str, Any]:
    return _cached_snapshot("/api/products", get_products_payload, products_degraded)


@app.get("/api/inventory", response_model=InventoryResponse, responses={500: {"model": ApiErrorResponse}})
def api_inventory() -> dict[str, Any]:
    return _cached_snapshot("/api/inventory", get_inventory_payload, inventory_degraded)


@app.get("/api/advisor", response_model=AdvisorResponse, responses={500: {"model": ApiErrorResponse}})
def api_advisor() -> dict[str, Any]:
    return _cached_snapshot("/api/advisor", get_advisor_payload_fast, advisor_degraded)


@app.get("/api/auth/session", response_model=AuthSessionResponse, responses={500: {"model": ApiErrorResponse}})
def api_auth_session() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    payload = _build_dev_auth_payload()
    payload["runtime"] = _auth_runtime(started_at=started_at)
    return payload


@app.get("/api/auth/profile", response_model=AuthProfileResponse, responses={500: {"model": ApiErrorResponse}})
def api_auth_profile() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    payload = _build_dev_auth_payload()
    return {
        "authenticated": payload["authenticated"],
        "user": payload["user"],
        "runtime": _auth_runtime(started_at=started_at),
    }


@app.get("/api/organization", response_model=OrganizationResponse, responses={500: {"model": ApiErrorResponse}})
def api_organization() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    payload = _build_dev_auth_payload()
    return {
        "organization": payload["organization"],
        "runtime": _auth_runtime(started_at=started_at),
    }


@app.get("/api/wb-cabinet", response_model=WbCabinetResponse, responses={500: {"model": ApiErrorResponse}})
def api_wb_cabinet() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    payload = _build_dev_auth_payload()
    return {
        "cabinet": payload["cabinet"],
        "runtime": _auth_runtime(started_at=started_at),
    }


@app.get("/api/organizations", response_model=OrganizationList, responses={500: {"model": ApiErrorResponse}})
def api_organizations() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    return {
        "organizations": list_organizations(),
        "activeOrganizationId": get_workspace_context().get("organizationId"),
        "runtime": _auth_runtime(started_at=started_at),
    }


@app.get("/api/organizations/{organization_id}", response_model=OrganizationResponse, responses={500: {"model": ApiErrorResponse}})
def api_organization_detail(organization_id: str) -> dict[str, Any]:
    started_at = now_monotonic_ms()
    organization = OrganizationSummary(**next(item for item in list_organizations() if str(item.get("id")) == organization_id)).model_dump()
    return {
        "organization": organization,
        "runtime": _auth_runtime(started_at=started_at),
    }


@app.post("/api/organizations/select", response_model=ActiveWorkspaceContext, responses={500: {"model": ApiErrorResponse}})
def api_select_organization(request: WorkspaceSelection) -> dict[str, Any]:
    started_at = now_monotonic_ms()
    if not request.organizationId:
        raise ValueError("organizationId is required.")
    context = select_organization(request.organizationId)
    context["runtime"] = _auth_runtime(started_at=started_at)
    return context


@app.get("/api/wb-cabinets", response_model=CabinetList, responses={500: {"model": ApiErrorResponse}})
def api_wb_cabinets() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    context = get_workspace_context()
    organization_id = str(context.get("organizationId") or "")
    return {
        "cabinets": list_cabinets(organization_id),
        "activeCabinetId": context.get("cabinetId"),
        "organizationId": organization_id,
        "runtime": _auth_runtime(started_at=started_at),
    }


@app.get("/api/wb-cabinets/{cabinet_id}", response_model=WbCabinetResponse, responses={500: {"model": ApiErrorResponse}})
def api_wb_cabinet_detail(cabinet_id: str) -> dict[str, Any]:
    started_at = now_monotonic_ms()
    cabinet = CabinetSummary(**next(item for item in list_cabinets() if str(item.get("id")) == cabinet_id)).model_dump()
    return {
        "cabinet": cabinet,
        "runtime": _auth_runtime(started_at=started_at),
    }


@app.post("/api/wb-cabinets/select", response_model=ActiveWorkspaceContext, responses={500: {"model": ApiErrorResponse}})
def api_select_wb_cabinet(request: WorkspaceSelection) -> dict[str, Any]:
    started_at = now_monotonic_ms()
    if not request.cabinetId:
        raise ValueError("cabinetId is required.")
    context = select_cabinet(request.cabinetId)
    context["runtime"] = _auth_runtime(started_at=started_at)
    return context


@app.get("/api/workspace/context", response_model=ActiveWorkspaceContext, responses={500: {"model": ApiErrorResponse}})
def api_workspace_context() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    context = get_workspace_context()
    context["runtime"] = _auth_runtime(started_at=started_at)
    return context


@app.get("/api/exports", response_model=ExportsResponse, responses={500: {"model": ApiErrorResponse}})
def api_exports() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    return {
        "exports": scoped_records(DEV_EXPORTS),
        "runtime": _automation_runtime(started_at=started_at),
    }


@app.post("/api/exports", response_model=ExportRecordResponse, responses={500: {"model": ApiErrorResponse}})
def api_create_export(request: ExportCreateRequest) -> dict[str, Any]:
    global EXPORT_COUNTER
    started_at = now_monotonic_ms()
    EXPORT_COUNTER += 1
    export = ExportRecord(
        id=f"export_{EXPORT_COUNTER:03d}",
        name=request.name or f"{request.workspace.title()} Export",
        workspace=request.workspace,
        format=request.format,
        status="queued",
        source="dev",
        owner="Andrey Voronov",
        size=None,
        createdAt=datetime.now(timezone.utc).isoformat(),
        downloadUrl=None,
    ).model_dump()
    DEV_EXPORTS.insert(0, export)
    DEV_JOBS.insert(
        0,
        JobRecord(
            id=f"job_{EXPORT_COUNTER:03d}",
            type="export",
            workspace=request.workspace,
            status="queued",
            progress=15,
            duration=None,
            startedAt=datetime.now(timezone.utc).isoformat(),
            finishedAt=None,
            source="dev",
            owner="Andrey Voronov",
            message=f"Placeholder export job created for {request.workspace}.",
        ).model_dump(),
    )
    return {
        "export": scoped_record(export),
        "runtime": _automation_runtime(started_at=started_at),
    }


@app.get("/api/exports/{export_id}", response_model=ExportRecordResponse, responses={500: {"model": ApiErrorResponse}})
def api_export_detail(export_id: str) -> dict[str, Any]:
    started_at = now_monotonic_ms()
    export = _find_by_id(DEV_EXPORTS, export_id)
    return {
        "export": scoped_record(export),
        "runtime": _automation_runtime(started_at=started_at),
    }


@app.get("/api/schedules", response_model=SchedulesResponse, responses={500: {"model": ApiErrorResponse}})
def api_schedules() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    return {
        "schedules": scoped_records(DEV_SCHEDULES),
        "runtime": _automation_runtime(started_at=started_at),
    }


@app.post("/api/schedules", response_model=ScheduleRecordResponse, responses={500: {"model": ApiErrorResponse}})
def api_create_schedule(request: ScheduleCreateRequest) -> dict[str, Any]:
    started_at = now_monotonic_ms()
    schedule = ScheduleRecord(
        id=f"schedule_{request.workspace}_{len(DEV_SCHEDULES) + 1}",
        name=request.name,
        workspace=request.workspace,
        enabled=request.enabled,
        time=request.time,
        timezone=request.timezone,
        cadence=request.cadence,
        format=request.format,
        status="healthy" if request.enabled else "paused",
        lastRunAt=None,
        nextRunAt=None,
        owner="Andrey Voronov",
    ).model_dump()
    DEV_SCHEDULES.insert(0, schedule)
    return {
        "schedule": scoped_record(schedule),
        "runtime": _automation_runtime(started_at=started_at),
    }


@app.patch("/api/schedules/{schedule_id}", response_model=ScheduleRecordResponse, responses={500: {"model": ApiErrorResponse}})
def api_update_schedule(schedule_id: str, request: ScheduleUpdateRequest) -> dict[str, Any]:
    started_at = now_monotonic_ms()
    schedule = _find_by_id(DEV_SCHEDULES, schedule_id)
    updates = request.model_dump(exclude_none=True)
    schedule.update(updates)
    if "enabled" in updates and "status" not in updates:
        schedule["status"] = "healthy" if bool(schedule["enabled"]) else "paused"
    return {
        "schedule": scoped_record(schedule),
        "runtime": _automation_runtime(started_at=started_at),
    }


@app.delete("/api/schedules/{schedule_id}", response_model=ScheduleRecordResponse, responses={500: {"model": ApiErrorResponse}})
def api_delete_schedule(schedule_id: str) -> dict[str, Any]:
    started_at = now_monotonic_ms()
    schedule = _find_by_id(DEV_SCHEDULES, schedule_id)
    DEV_SCHEDULES.remove(schedule)
    schedule["status"] = "deleted"
    schedule["enabled"] = False
    return {
        "schedule": scoped_record(schedule),
        "runtime": _automation_runtime(started_at=started_at),
    }


@app.get("/api/jobs", response_model=JobsResponse, responses={500: {"model": ApiErrorResponse}})
def api_jobs() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    return {
        "jobs": scoped_records(DEV_JOBS),
        "runtime": _automation_runtime(started_at=started_at),
    }


@app.get("/api/jobs/{job_id}", response_model=JobRecordResponse, responses={500: {"model": ApiErrorResponse}})
def api_job_detail(job_id: str) -> dict[str, Any]:
    started_at = now_monotonic_ms()
    job = _find_by_id(DEV_JOBS, job_id)
    return {
        "job": scoped_record(job),
        "runtime": _automation_runtime(started_at=started_at),
    }


@app.get("/api/notifications", response_model=NotificationsResponse, responses={500: {"model": ApiErrorResponse}})
def api_notifications() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    return {
        "status": _build_notification_status(),
        "rules": scoped_records(DEV_NOTIFICATION_RULES),
        "channels": scoped_records(DEV_NOTIFICATION_CHANNELS),
        "unreadCount": sum(1 for item in DEV_NOTIFICATION_HISTORY if item.get("status") in {"failed", "pending"}),
        "runtime": _notifications_runtime(started_at=started_at),
    }


@app.get("/api/notifications/rules", response_model=NotificationRulesResponse, responses={500: {"model": ApiErrorResponse}})
def api_notification_rules() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    return {
        "rules": scoped_records(DEV_NOTIFICATION_RULES),
        "runtime": _notifications_runtime(started_at=started_at),
    }


@app.post("/api/notifications/rules", response_model=NotificationRuleResponse, responses={500: {"model": ApiErrorResponse}})
def api_create_notification_rule(request: NotificationRuleCreateRequest) -> dict[str, Any]:
    global NOTIFICATION_RULE_COUNTER
    started_at = now_monotonic_ms()
    NOTIFICATION_RULE_COUNTER += 1
    rule = NotificationRule(
        id=f"notification_rule_{NOTIFICATION_RULE_COUNTER:03d}",
        name=request.name,
        enabled=request.enabled,
        channel=request.channel,
        severity=request.severity,
        trigger=request.trigger,
        schedule=request.schedule,
        owner=request.owner,
        lastTriggeredAt=None,
        deepLink=request.deepLink,
    ).model_dump()
    DEV_NOTIFICATION_RULES.insert(0, rule)
    return {
        "rule": scoped_record(rule),
        "runtime": _notifications_runtime(started_at=started_at),
    }


@app.patch("/api/notifications/rules/{rule_id}", response_model=NotificationRuleResponse, responses={500: {"model": ApiErrorResponse}})
def api_update_notification_rule(rule_id: str, request: NotificationRuleUpdateRequest) -> dict[str, Any]:
    started_at = now_monotonic_ms()
    rule = _find_by_id(DEV_NOTIFICATION_RULES, rule_id)
    rule.update(request.model_dump(exclude_none=True))
    return {
        "rule": scoped_record(rule),
        "runtime": _notifications_runtime(started_at=started_at),
    }


@app.delete("/api/notifications/rules/{rule_id}", response_model=NotificationRuleResponse, responses={500: {"model": ApiErrorResponse}})
def api_delete_notification_rule(rule_id: str) -> dict[str, Any]:
    started_at = now_monotonic_ms()
    rule = _find_by_id(DEV_NOTIFICATION_RULES, rule_id)
    DEV_NOTIFICATION_RULES.remove(rule)
    rule["enabled"] = False
    rule["severity"] = "muted"
    return {
        "rule": scoped_record(rule),
        "runtime": _notifications_runtime(started_at=started_at),
    }


@app.get("/api/notifications/history", response_model=NotificationHistoryResponse, responses={500: {"model": ApiErrorResponse}})
def api_notification_history() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    return {
        "history": scoped_records(DEV_NOTIFICATION_HISTORY),
        "runtime": _notifications_runtime(started_at=started_at),
    }


@app.get("/api/notifications/channels", response_model=NotificationChannelsResponse, responses={500: {"model": ApiErrorResponse}})
def api_notification_channels() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    return {
        "channels": scoped_records(DEV_NOTIFICATION_CHANNELS),
        "runtime": _notifications_runtime(started_at=started_at),
    }


@app.post("/api/notifications/test", response_model=NotificationTestResponse, responses={500: {"model": ApiErrorResponse}})
def api_notification_test(request: NotificationTestRequest) -> dict[str, Any]:
    started_at = now_monotonic_ms()
    status = "sent" if request.channel in {"in_app", "webhook"} else "failed"
    delivery = NotificationDelivery(
        id=f"delivery_test_{request.channel}",
        channel=request.channel,
        status=status,
        target=request.target or f"{request.channel}-placeholder",
        message=request.message or "Test notification placeholder result.",
        simulated=True,
    ).model_dump()
    history_event = NotificationEvent(
        id=f"notification_event_{len(DEV_NOTIFICATION_HISTORY) + 1:03d}",
        title=f"Test notification via {request.channel}",
        channel=request.channel,
        status=status,
        time=datetime.now(timezone.utc).isoformat(),
        target=delivery["target"],
        relatedWorkspace="notifications",
        error=None if status == "sent" else "Real delivery is disabled in the current environment.",
        deepLink="/notifications",
    ).model_dump()
    DEV_NOTIFICATION_HISTORY.insert(0, history_event)

    for channel in DEV_NOTIFICATION_CHANNELS:
        if channel.get("type") == request.channel:
            channel["lastTestAt"] = history_event["time"]
            channel["status"] = "sent" if status == "sent" else "failed"
            channel["deliveryHealth"] = "Healthy" if status == "sent" else "Watch"
            break

    return {
        "delivery": scoped_record(delivery),
        "runtime": _notifications_runtime(started_at=started_at),
    }


@app.post("/api/wb-cabinet/connect", response_model=WbCabinetResponse, responses={500: {"model": ApiErrorResponse}})
def api_wb_cabinet_connect() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    cabinet = set_active_cabinet_connection(True)
    payload = _build_dev_auth_payload(cabinet_connected=True)
    payload["cabinet"]["status"] = str(cabinet.get("status") or "connected_dev")
    return {
        "cabinet": payload["cabinet"],
        "runtime": _auth_runtime(started_at=started_at),
    }


@app.post("/api/wb-cabinet/disconnect", response_model=WbCabinetResponse, responses={500: {"model": ApiErrorResponse}})
def api_wb_cabinet_disconnect() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    cabinet = set_active_cabinet_connection(False)
    payload = _build_dev_auth_payload(cabinet_connected=False)
    payload["cabinet"]["status"] = str(cabinet.get("status") or "disconnected_dev")
    return {
        "cabinet": payload["cabinet"],
        "runtime": _auth_runtime(started_at=started_at),
    }


@app.post(
    "/api/advisor/query",
    response_model=AdvisorQueryResponse,
    responses={500: {"model": ApiErrorResponse}},
)
def api_advisor_query(request: AdvisorQueryRequest) -> dict[str, Any]:
    endpoint = "/api/advisor/query"
    started_at = now_monotonic_ms()
    try:
        payload = run_with_timeout(
            lambda: get_advisor_query_payload(
                request.message,
                request.context.model_dump(exclude_none=True) if request.context else None,
            ),
            int(ENDPOINT_RUNTIME[endpoint]["timeout_ms"]),
        )
        duration_ms = now_monotonic_ms() - started_at
        runtime = build_runtime_metadata(
            duration_ms=duration_ms,
            cached=False,
            stale=False,
            degraded=payload.get("status") == "degraded",
            source="live" if payload.get("status") == "ok" else "degraded",
        )
        payload["runtime"] = runtime
        record_endpoint_result(
            endpoint,
            duration_ms=duration_ms,
            success=payload.get("status") != "error",
            source=str(runtime.get("source") or "live"),
            cached=False,
            stale=False,
            degraded=bool(runtime.get("degraded")),
        )
        return payload
    except Exception as exc:
        duration_ms = now_monotonic_ms() - started_at
        payload = get_advisor_query_degraded_payload(str(exc))
        runtime = build_runtime_metadata(
            duration_ms=duration_ms,
            cached=False,
            stale=False,
            degraded=True,
            source="degraded",
        )
        payload["runtime"] = runtime
        record_endpoint_result(
            endpoint,
            duration_ms=duration_ms,
            success=False,
            source="degraded",
            cached=False,
            stale=False,
            degraded=True,
            error=str(exc),
        )
        return payload


@app.get("/api/reports", response_model=ReportsResponse, responses={500: {"model": ApiErrorResponse}})
def api_reports() -> dict[str, Any]:
    return _cached_snapshot("/api/reports", get_reports_payload_fast, reports_degraded)


@app.get("/api/system", response_model=SystemResponse, responses={500: {"model": ApiErrorResponse}})
def api_system() -> dict[str, Any]:
    return _cached_snapshot("/api/system", get_system_payload, system_degraded)


@app.get("/api/status", response_model=StatusResponse, responses={500: {"model": ApiErrorResponse}})
def api_status() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    payload = dict(get_status_payload())
    payload["runtime"] = build_runtime_metadata(
        duration_ms=now_monotonic_ms() - started_at,
        cached=False,
        stale=False,
        degraded=False,
        source="live",
    )
    record_endpoint_result(
        "/api/status",
        duration_ms=float((payload.get("runtime") or {}).get("duration_ms") or 0.0),
        success=True,
        source="live",
        cached=False,
        stale=False,
        degraded=False,
    )
    return payload


@app.get("/api/version", response_model=VersionResponse, responses={500: {"model": ApiErrorResponse}})
def api_version() -> dict[str, Any]:
    started_at = now_monotonic_ms()
    payload = dict(get_version_payload())
    payload["runtime"] = build_runtime_metadata(
        duration_ms=now_monotonic_ms() - started_at,
        cached=False,
        stale=False,
        degraded=False,
        source="live",
    )
    record_endpoint_result(
        "/api/version",
        duration_ms=float((payload.get("runtime") or {}).get("duration_ms") or 0.0),
        success=True,
        source="live",
        cached=False,
        stale=False,
        degraded=False,
    )
    return payload


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", DEFAULT_API_HOST)
    port = int(os.getenv("API_PORT", str(DEFAULT_API_PORT)))
    uvicorn.run("api_server:app", host=host, port=port, reload=False)
