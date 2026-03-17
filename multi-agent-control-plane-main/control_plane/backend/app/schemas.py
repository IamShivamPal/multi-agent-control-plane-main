"""Pydantic schemas for the stateless RL-style Decision Brain API."""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Environment(str, Enum):
    """Supported deployment environments."""

    DEV = "DEV"
    STAGE = "STAGE"
    PROD = "PROD"


class EventType(str, Enum):
    """Supported event classifications used by the decision engine."""

    HIGH_CPU = "HIGH_CPU"
    HIGH_MEMORY = "HIGH_MEMORY"
    LATENCY = "LATENCY"


class HealthResponse(BaseModel):
    """Health response model exposed by the API."""

    status: Literal["healthy"] = "healthy"
    demo_frozen: bool = True
    stateless: bool = True
    success_rate: float = 1.0


class ActionScopeResponse(BaseModel):
    """Environment to action-scope mapping response."""

    DEV: list[str]
    STAGE: list[str]
    PROD: list[str]


class DecisionRequest(BaseModel):
    """Input payload for deterministic decision generation."""

    model_config = ConfigDict(extra="forbid")

    environment: Environment
    event_type: EventType
    cpu: int = Field(ge=0, le=100)
    memory: int = Field(ge=0, le=100)


class DecisionResponse(BaseModel):
    """Decision output returned by the API."""

    decision_id: UUID
    environment: Environment
    selected_action: str
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime


class RecentActivityResponse(BaseModel):
    """Container for last ten in-memory decisions."""

    items: list[DecisionResponse]


class DashboardMetric(BaseModel):
    """Generic metric item used across dashboard sections."""

    label: str
    value: str
    tone: str | None = None


class DashboardHeader(BaseModel):
    """Header metadata for the RL Reality dashboard."""

    title: str
    subtitle: str


class LiveDomainStatus(BaseModel):
    """Live status card payload for each monitored domain."""

    name: str
    domain: str
    url: str
    status: str
    health_score: float
    response_time_ms: int
    cpu_percent: float
    memory_percent: float
    uptime_percent: float
    last_action: str
    errors_24h: int


class ProjectFileRow(BaseModel):
    """Per-file status row in project files section."""

    filename: str
    status: str
    size: str


class ProjectFileGroup(BaseModel):
    """Group of project files shown in one status card."""

    title: str
    icon: str
    active: int
    total: int
    files: list[ProjectFileRow]


class EnhancedTelemetry(BaseModel):
    """Telemetry block payload for error-state section."""

    status: str
    avg_latency: str
    cost: str
    success: str
    requests: str


class PolicyEvolution(BaseModel):
    """Policy evolution panel payload."""

    title: str
    metrics: list[DashboardMetric]


class ErrorItem(BaseModel):
    """Single error item in recent error analytics list."""

    code: str
    severity: str


class ErrorStatistics(BaseModel):
    """Aggregate statistics for errors."""

    total_errors: int
    avg_impact_score: float


class ErrorAnalytics(BaseModel):
    """Error analytics section payload."""

    recent_errors: list[ErrorItem]
    statistics: ErrorStatistics


class DomainHealth(BaseModel):
    """Single domain health row for auto-failover section."""

    name: str
    status: str


class AutoFailoverStatus(BaseModel):
    """Auto-failover configuration/status payload."""

    active_domain: str
    failure_threshold: int
    domains: list[DomainHealth]


class LiveEvent(BaseModel):
    """Live event timeline row payload."""

    title: str
    time_ago: str
    tone: str


class LiveDashboardResponse(BaseModel):
    """Top-level response model for RL Reality Live Dashboard."""

    generated_at: datetime
    header: DashboardHeader
    live_production_monitoring: list[LiveDomainStatus]
    summary_metrics: list[DashboardMetric]
    ai_learning_status: list[DashboardMetric]
    system_health: list[DashboardMetric]
    performance_metrics: list[DashboardMetric]
    project_files_status: list[ProjectFileGroup]
    enhanced_telemetry: EnhancedTelemetry
    policy_evolution: PolicyEvolution
    error_analytics: ErrorAnalytics
    auto_failover_status: AutoFailoverStatus
    live_events: list[LiveEvent]


class DecisionDashboardSummary(BaseModel):
    """Aggregated summary for the RL Decision Brain UI."""

    total_decisions: int
    last_action: str
    success_rate: float
    demo_frozen: bool
    stateless: bool
