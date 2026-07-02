from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ApiBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class RuntimeMetadata(ApiBaseModel):
    duration_ms: float | None = None
    cached: bool | None = None
    stale: bool | None = None
    degraded: bool | None = None
    source: str | None = None


class ApiErrorResponse(ApiBaseModel):
    status: str = "error"
    message: str
    details: Any | None = None


class UserProfile(ApiBaseModel):
    id: str
    name: str
    email: str
    role: str
    permissions: list[str] = []
    enabled: bool = True
    avatarUrl: str | None = None
    createdAt: str
    lastActiveAt: str | None = None
    deactivatedAt: str | None = None


class OrganizationProfile(ApiBaseModel):
    id: str
    name: str
    plan: str
    status: str
    createdAt: str


class WbCabinetProfile(ApiBaseModel):
    id: str
    name: str
    organizationId: str | None = None
    organizationName: str | None = None
    sellerId: str
    status: str
    connected: bool
    lastSyncAt: str | None = None
    dataQuality: str
    tokenStatus: str
    health: str | None = None
    lastSyncStatus: str | None = None
    syncMessage: str | None = None
    lastCheckedAt: str | None = None
    createdAt: str | None = None
    updatedAt: str | None = None
    scopes: list[str] = []
    tokens: dict[str, str | None] = {}


class OrganizationSummary(ApiBaseModel):
    id: str
    name: str
    plan: str
    status: str
    createdAt: str
    cabinetCount: int = 0
    health: str | None = None


class OrganizationList(ApiBaseModel):
    organizations: list[OrganizationSummary]
    activeOrganizationId: str | None = None
    runtime: RuntimeMetadata | None = None


class CabinetSummary(ApiBaseModel):
    id: str
    organizationId: str
    organizationName: str | None = None
    name: str
    sellerId: str
    status: str
    connected: bool
    lastSyncAt: str | None = None
    dataQuality: str
    tokenStatus: str
    health: str | None = None


class CabinetList(ApiBaseModel):
    cabinets: list[CabinetSummary]
    activeCabinetId: str | None = None
    organizationId: str | None = None
    runtime: RuntimeMetadata | None = None


class ActiveWorkspaceContext(ApiBaseModel):
    organizationId: str | None = None
    cabinetId: str | None = None
    mode: str
    lastChanged: str
    organizationCount: int = 0
    cabinetCount: int = 0
    organization: OrganizationSummary | None = None
    cabinet: CabinetSummary | None = None
    runtime: RuntimeMetadata | None = None


class WorkspaceSelection(ApiBaseModel):
    organizationId: str | None = None
    cabinetId: str | None = None


class AuthSessionResponse(ApiBaseModel):
    authenticated: bool
    user: UserProfile
    organization: OrganizationProfile
    cabinet: WbCabinetProfile
    runtime: RuntimeMetadata | None = None


class AuthProfileResponse(ApiBaseModel):
    authenticated: bool
    user: UserProfile
    runtime: RuntimeMetadata | None = None


class AuditEventRecord(ApiBaseModel):
    id: str
    event: str
    actorId: str
    targetId: str | None = None
    outcome: str
    detail: str | None = None
    metadata: dict[str, Any] = {}
    createdAt: str


class UsersResponse(ApiBaseModel):
    users: list[UserProfile]
    availableRoles: list[str] = []
    runtime: RuntimeMetadata | None = None


class AuditLogResponse(ApiBaseModel):
    events: list[AuditEventRecord]
    runtime: RuntimeMetadata | None = None


class UserRoleUpdateRequest(ApiBaseModel):
    role: str


class UserStatusUpdateRequest(ApiBaseModel):
    enabled: bool


class UserRecordResponse(ApiBaseModel):
    user: UserProfile
    runtime: RuntimeMetadata | None = None


class OrganizationResponse(ApiBaseModel):
    organization: OrganizationProfile
    runtime: RuntimeMetadata | None = None


class WbCabinetResponse(ApiBaseModel):
    cabinet: WbCabinetProfile
    runtime: RuntimeMetadata | None = None


class WbCabinetUpsertRequest(ApiBaseModel):
    organizationId: str | None = None
    name: str
    sellerId: str | None = None
    scopes: list[str] | None = None
    connected: bool | None = None
    tokens: dict[str, str | None] | None = None


class WbCabinetDiscoveryRequest(ApiBaseModel):
    organizationId: str | None = None
    name: str
    sellerId: str | None = None
    scopes: list[str] | None = None
    tokens: dict[str, str | None] | None = None


class WbCabinetSyncRequest(ApiBaseModel):
    type: str = "all"
    dateFrom: str | None = None
    dateTo: str | None = None


class WbApiHealthRecord(ApiBaseModel):
    section: str
    status: str
    lastSuccessAt: str | None = None
    lastErrorAt: str | None = None
    lastErrorMessage: str | None = None
    rateLimitState: str | None = None
    message: str | None = None
    requiredAction: str | None = None


class WbApiHealthResponse(ApiBaseModel):
    cabinetId: str
    health: list[WbApiHealthRecord]
    runtime: RuntimeMetadata | None = None


class WbSyncJobRecord(ApiBaseModel):
    id: str
    cabinetId: str
    type: str
    status: str
    startedAt: str | None = None
    finishedAt: str | None = None
    durationMs: int | None = None
    recordsLoaded: int = 0
    errorMessage: str | None = None
    runtimeSource: str | None = None
    meta: dict[str, Any] = {}


class WbSyncStatusResponse(ApiBaseModel):
    cabinetId: str
    latestJob: WbSyncJobRecord | None = None
    history: list[WbSyncJobRecord] = []
    runtime: RuntimeMetadata | None = None


class WbCabinetTestResponse(ApiBaseModel):
    cabinet: WbCabinetProfile
    status: str
    checks: list[dict[str, Any]]
    runtime: RuntimeMetadata | None = None


class WbCabinetSyncResponse(ApiBaseModel):
    cabinet: WbCabinetProfile
    job: WbSyncJobRecord | None = None
    results: dict[str, Any]
    runtime: RuntimeMetadata | None = None


class WbCabinetDiscoveryResponse(ApiBaseModel):
    cabinetName: str
    sellerId: str | None = None
    sellerName: str | None = None
    organizationName: str | None = None
    availableApis: list[dict[str, Any]] = []
    capabilities: dict[str, Any] = {}
    canConnect: bool = False
    runtime: RuntimeMetadata | None = None


class WbCabinetConnectResponse(ApiBaseModel):
    cabinet: WbCabinetProfile
    status: str
    checks: list[dict[str, Any]] = []
    job: WbSyncJobRecord | None = None
    results: dict[str, Any] = {}
    runtime: RuntimeMetadata | None = None


class WbConnectionSummaryResponse(ApiBaseModel):
    organization: OrganizationSummary | None = None
    activeCabinet: WbCabinetProfile | None = None
    connectedCabinets: int = 0
    totalCabinets: int = 0
    hasActiveConnection: bool = False
    lastChanged: str | None = None
    runtime: RuntimeMetadata | None = None


class ExportRecord(ApiBaseModel):
    id: str
    name: str
    workspace: str
    format: str
    status: str
    source: str
    owner: str
    size: str | None = None
    createdAt: str
    downloadUrl: str | None = None


class ExportCreateRequest(ApiBaseModel):
    workspace: str
    format: str
    name: str | None = None
    sku: str | None = None


class ExportRecordResponse(ApiBaseModel):
    export: ExportRecord
    runtime: RuntimeMetadata | None = None


class ExportsResponse(ApiBaseModel):
    exports: list[ExportRecord]
    runtime: RuntimeMetadata | None = None


class ScheduleRecord(ApiBaseModel):
    id: str
    name: str
    workspace: str
    enabled: bool
    time: str
    timezone: str
    cadence: str
    format: str
    status: str
    lastRunAt: str | None = None
    nextRunAt: str | None = None
    owner: str


class ScheduleCreateRequest(ApiBaseModel):
    name: str
    workspace: str
    time: str
    timezone: str
    cadence: str
    format: str
    enabled: bool = True


class ScheduleUpdateRequest(ApiBaseModel):
    enabled: bool | None = None
    time: str | None = None
    timezone: str | None = None
    cadence: str | None = None
    format: str | None = None
    status: str | None = None
    intervalMinutes: int | None = None


class ScheduleRecordResponse(ApiBaseModel):
    schedule: ScheduleRecord
    runtime: RuntimeMetadata | None = None


class SchedulesResponse(ApiBaseModel):
    schedules: list[ScheduleRecord]
    runtime: RuntimeMetadata | None = None


class JobRecord(ApiBaseModel):
    id: str
    type: str
    workspace: str
    status: str
    progress: int
    duration: str | None = None
    startedAt: str | None = None
    finishedAt: str | None = None
    source: str
    owner: str
    message: str | None = None


class JobRecordResponse(ApiBaseModel):
    job: JobRecord
    runtime: RuntimeMetadata | None = None


class JobsResponse(ApiBaseModel):
    jobs: list[JobRecord]
    runtime: RuntimeMetadata | None = None


class NotificationChannel(ApiBaseModel):
    id: str
    type: Literal["telegram", "email", "webhook", "in_app"]
    status: Literal["enabled", "disabled", "pending", "sent", "failed", "muted"]
    connected: bool
    lastTestAt: str | None = None
    deliveryHealth: str
    setupAction: str | None = None


class NotificationRule(ApiBaseModel):
    id: str
    name: str
    enabled: bool
    channel: Literal["telegram", "email", "webhook", "in_app"]
    severity: str
    trigger: str
    schedule: str
    owner: str
    lastTriggeredAt: str | None = None
    deepLink: str | None = None


class NotificationEvent(ApiBaseModel):
    id: str
    title: str
    channel: Literal["telegram", "email", "webhook", "in_app"]
    status: Literal["enabled", "disabled", "pending", "sent", "failed", "muted"]
    time: str
    target: str
    relatedWorkspace: str | None = None
    error: str | None = None
    deepLink: str | None = None


class NotificationDelivery(ApiBaseModel):
    id: str
    channel: Literal["telegram", "email", "webhook", "in_app"]
    status: Literal["enabled", "disabled", "pending", "sent", "failed", "muted"]
    target: str
    message: str
    simulated: bool = True


class NotificationPreference(ApiBaseModel):
    owner: str
    quietHours: str | None = None
    mutedSeverities: list[str] = []


class NotificationStatus(ApiBaseModel):
    enabledRules: int
    mutedRules: int
    failedDeliveries: int
    lastDelivery: str | None = None
    activeChannels: int
    health: str


class NotificationsResponse(ApiBaseModel):
    status: NotificationStatus
    rules: list[NotificationRule]
    channels: list[NotificationChannel]
    unreadCount: int = 0
    runtime: RuntimeMetadata | None = None


class NotificationRulesResponse(ApiBaseModel):
    rules: list[NotificationRule]
    runtime: RuntimeMetadata | None = None


class NotificationRuleCreateRequest(ApiBaseModel):
    name: str
    enabled: bool = True
    channel: Literal["telegram", "email", "webhook", "in_app"]
    severity: str
    trigger: str
    schedule: str
    owner: str
    deepLink: str | None = None


class NotificationRuleUpdateRequest(ApiBaseModel):
    name: str | None = None
    enabled: bool | None = None
    channel: Literal["telegram", "email", "webhook", "in_app"] | None = None
    severity: str | None = None
    trigger: str | None = None
    schedule: str | None = None
    owner: str | None = None
    lastTriggeredAt: str | None = None
    deepLink: str | None = None


class NotificationRuleResponse(ApiBaseModel):
    rule: NotificationRule
    runtime: RuntimeMetadata | None = None


class NotificationHistoryResponse(ApiBaseModel):
    history: list[NotificationEvent]
    runtime: RuntimeMetadata | None = None


class NotificationChannelsResponse(ApiBaseModel):
    channels: list[NotificationChannel]
    runtime: RuntimeMetadata | None = None


class NotificationTestRequest(ApiBaseModel):
    channel: Literal["telegram", "email", "webhook", "in_app"]
    target: str | None = None
    message: str | None = None


class NotificationTestResponse(ApiBaseModel):
    delivery: NotificationDelivery
    runtime: RuntimeMetadata | None = None


class HealthResponse(ApiBaseModel):
    status: str
    product: str
    mode: str
    runtime: RuntimeMetadata | None = None


class ExecutiveResponse(ApiBaseModel):
    product: str
    screen: str
    period: dict[str, Any]
    business_health: dict[str, Any]
    executive_brief: dict[str, Any]
    kpis: list[dict[str, Any]]
    workspaces: list[dict[str, Any]]
    today_actions: list[dict[str, Any]]
    critical_alerts: list[dict[str, Any]]
    recent_events: list[dict[str, Any]]
    decision_engine: dict[str, Any] | None = None
    system: dict[str, Any]
    runtime: RuntimeMetadata | None = None


class DecisionEngineResponse(ApiBaseModel):
    summary: dict[str, Any]
    whatChanged: list[dict[str, Any]]
    mainRisk: dict[str, Any] | None = None
    mainOpportunity: dict[str, Any] | None = None
    todayActions: list[dict[str, Any]]
    forecast: dict[str, Any]
    evidence: list[dict[str, Any]]
    sources: list[str] | None = None
    period: dict[str, Any] | None = None
    runtime: RuntimeMetadata | None = None


class ForecastSimulateRequest(ApiBaseModel):
    type: Literal["increase_ads", "reduce_ads", "restock", "pause_sku", "scale_sku"]
    sku: str | None = None
    value: float | None = None


class ForecastResponse(ApiBaseModel):
    summary: dict[str, Any]
    periods: dict[str, Any]
    salesForecast: dict[str, Any]
    profitForecast: dict[str, Any]
    inventoryForecast: dict[str, Any]
    advertisingForecast: dict[str, Any]
    risks: list[dict[str, Any]]
    opportunities: list[dict[str, Any]]
    scenarios: list[dict[str, Any]]
    runtime: RuntimeMetadata | None = None


class ForecastSimulationResponse(ApiBaseModel):
    status: str
    expectedEffect: dict[str, Any]
    risks: list[str]
    recommendation: str
    confidence: int | None = None
    runtime: RuntimeMetadata | None = None


class BusinessResponse(ApiBaseModel):
    summary: dict[str, Any]
    trends: dict[str, Any]
    healthScore: int | None = None
    healthStatus: str | None = None
    periods: dict[str, Any]
    topProducts: list[dict[str, Any]]
    generatedAt: str | None = None
    runtime: RuntimeMetadata | None = None


class FinanceResponse(ApiBaseModel):
    summary: dict[str, Any]
    quality: dict[str, Any]
    difference: dict[str, Any]
    metrics: list[dict[str, Any]]
    alerts: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    lastUpdated: str | None = None
    runtime: RuntimeMetadata | None = None


class AdvertisingResponse(ApiBaseModel):
    summary: dict[str, Any]
    health: dict[str, Any]
    metrics: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    alerts: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    campaigns: list[dict[str, Any]]
    lastUpdated: str | None = None
    runtime: RuntimeMetadata | None = None


class ProductsResponse(ApiBaseModel):
    summary: dict[str, Any]
    products: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    history: list[dict[str, Any]]
    inventoryPreview: list[dict[str, Any]]
    alerts: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    lastUpdated: str | None = None
    runtime: RuntimeMetadata | None = None


class InventoryResponse(ApiBaseModel):
    summary: dict[str, Any]
    health: dict[str, Any]
    items: list[dict[str, Any]]
    restockPlan: list[dict[str, Any]]
    supplyPriority: list[dict[str, Any]]
    warehouses: list[dict[str, Any]]
    history: list[dict[str, Any]]
    alerts: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    metrics: list[dict[str, Any]]
    lastUpdated: str | None = None
    runtime: RuntimeMetadata | None = None


class AdvisorResponse(ApiBaseModel):
    summary: dict[str, Any]
    recommendations: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    opportunities: list[dict[str, Any]]
    priorities: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    conversation: dict[str, Any]
    insights: list[dict[str, Any]]
    lastUpdated: str | None = None
    runtime: RuntimeMetadata | None = None


class AdvisorQueryContext(ApiBaseModel):
    workspace: str | None = None
    sku: str | None = None
    dateFrom: str | None = None
    dateTo: str | None = None
    organizationId: str | None = None
    cabinetId: str | None = None


class AdvisorQueryRequest(ApiBaseModel):
    message: str
    context: AdvisorQueryContext | None = None


class AdvisorQueryRecommendation(ApiBaseModel):
    id: str
    title: str
    reason: str
    priority: str
    confidence: str
    href: str


class AdvisorQueryEvidence(ApiBaseModel):
    id: str
    label: str
    detail: str
    metrics: list[str]
    href: str


class AdvisorQueryLink(ApiBaseModel):
    id: str
    label: str
    href: str
    description: str


class AdvisorQueryRelated(ApiBaseModel):
    id: str
    type: Literal["workspace", "sku", "campaign", "report"]
    label: str
    href: str | None = None
    note: str | None = None


class AdvisorQueryResponse(ApiBaseModel):
    status: Literal["ok", "degraded", "error"]
    answer: str
    summary: str
    recommendations: list[AdvisorQueryRecommendation]
    evidence: list[AdvisorQueryEvidence]
    links: list[AdvisorQueryLink]
    related: list[AdvisorQueryRelated]
    confidence: float
    runtime: RuntimeMetadata | None = None


class ReportsResponse(ApiBaseModel):
    summary: dict[str, Any]
    catalog: list[dict[str, Any]]
    recent: list[dict[str, Any]]
    templates: list[dict[str, Any]]
    exports: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    lastUpdated: str | None = None
    runtime: RuntimeMetadata | None = None


class SystemResponse(ApiBaseModel):
    product: str
    mode: str
    status: str
    health: dict[str, Any]
    quality: dict[str, Any]
    adsHealth: dict[str, Any]
    financeHealth: dict[str, Any]
    cache: dict[str, Any]
    writeSafety: dict[str, Any]
    cooldowns: dict[str, Any]
    lastUpdates: dict[str, Any]
    coreV2Status: dict[str, Any]
    controlCenter: dict[str, Any]
    financeApi: dict[str, Any]
    lastUpdated: str
    runtime: RuntimeMetadata | None = None


class StatusResponse(ApiBaseModel):
    status: str
    wbApi: str
    database: str
    analytics: str
    ads: str
    finance: str
    system: str
    cache: dict[str, Any] | None = None
    slowEndpoints: list[dict[str, Any]] | None = None
    lastSuccessfulSnapshot: dict[str, Any] | None = None
    lastError: dict[str, Any] | None = None
    endpoints: dict[str, Any] | None = None
    version: str
    build: str
    timestamp: str | None = None
    runtime: RuntimeMetadata | None = None


class VersionResponse(ApiBaseModel):
    version: str
    build: str
    git: str
    apiVersion: str
    runtime: RuntimeMetadata | None = None


class MetricsResponse(ApiBaseModel):
    timestamp: str
    runtime: RuntimeMetadata | None = None
