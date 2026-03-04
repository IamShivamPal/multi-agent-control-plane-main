export type HealthResponse = {
  status: "healthy";
  demo_frozen: boolean;
  stateless: boolean;
  success_rate: number;
};

export type ActionScopeResponse = {
  DEV: string[];
  STAGE: string[];
  PROD: string[];
};

export type DecisionResponse = {
  decision_id: string;
  environment: "DEV" | "STAGE" | "PROD";
  selected_action: string;
  reason: string;
  confidence: number;
  timestamp: string;
};

export type RecentActivityResponse = {
  items: DecisionResponse[];
};

export type DecisionSummaryResponse = {
  total_decisions: number;
  last_action: string;
  success_rate: number;
  demo_frozen: boolean;
  stateless: boolean;
};

export type DashboardMetric = {
  label: string;
  value: string;
  tone?: "default" | "green" | "orange" | "blue" | "red";
};

export type DomainStatus = {
  name: string;
  domain: string;
  url: string;
  status: string;
  health_score: number;
  response_time_ms: number;
  cpu_percent: number;
  memory_percent: number;
  uptime_percent: number;
  last_action: string;
  errors_24h: number;
};

export type FileStatusGroup = {
  title: string;
  icon: string;
  active: number;
  total: number;
  files: Array<{
    filename: string;
    status: string;
    size: string;
  }>;
};

export type ErrorAnalytics = {
  recent_errors: Array<{
    code: string;
    severity: string;
  }>;
  statistics: {
    total_errors: number;
    avg_impact_score: number;
  };
};

export type LivePayload = {
  generated_at: string;
  header: {
    title: string;
    subtitle: string;
  };
  live_production_monitoring: DomainStatus[];
  summary_metrics: DashboardMetric[];
  ai_learning_status: DashboardMetric[];
  system_health: DashboardMetric[];
  performance_metrics: DashboardMetric[];
  project_files_status: FileStatusGroup[];
  enhanced_telemetry: {
    status: string;
    avg_latency: string;
    cost: string;
    success: string;
    requests: string;
  };
  policy_evolution: {
    title: string;
    metrics: DashboardMetric[];
  };
  error_analytics: ErrorAnalytics;
  auto_failover_status: {
    active_domain: string;
    failure_threshold: number;
    domains: Array<{
      name: string;
      status: string;
    }>;
  };
  live_events: Array<{
    title: string;
    time_ago: string;
    tone: string;
  }>;
};

export type OrchestrationMetrics = {
  rl_brain: {
    status: string;
    monitored_links: number;
    total_commits: number;
    total_contributors: number;
    avg_test_coverage: number;
    total_decisions: number;
  };
  control_plane: {
    rl_brain_status: string;
    control_plane_status: string;
    total_apps_monitored: number;
    rl_decisions_made: number;
    integration_enabled: boolean;
    last_sync: string;
  };
  unified: {
    total_entities_monitored: number;
    total_decisions_made: number;
    system_status: string;
    integration_enabled: boolean;
  };
};

export type ControlPlaneStatus = {
  integration_enabled: boolean;
  control_plane_available: boolean;
  rl_brain_status: string;
  control_plane_status: string;
  apps_monitored: number;
  last_sync: string;
};

export type ControlPlaneApps = {
  total_apps: number;
  apps: Array<Record<string, unknown>>;
  integration_status: string;
};

const BACKEND_PORT = process.env.NEXT_PUBLIC_BACKEND_PORT ?? "7999";
const API_BASE = process.env.NEXT_PUBLIC_DECISION_BRAIN_API_URL ?? `http://localhost:${BACKEND_PORT}`;



export async function getAutonomousStatus() {
  return fetchJson<Record<string, unknown>>("/autonomous-status");
}









type DecisionRequestPayload = {
  environment: "DEV" | "STAGE" | "PROD";
  event_type: "HIGH_CPU" | "HIGH_MEMORY" | "LATENCY";
  cpu: number;
  memory: number;
};

type DecisionWithControlPlaneResponse = {
  decision: DecisionResponse;
  control_plane_sync: {
    status: string;
    timestamp: string;
  };
};

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed for ${path}: ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function getHealth() {
  return fetchJson<HealthResponse>("/health");
}

export async function getActionScope() {
  return fetchJson<ActionScopeResponse>("/action-scope");
}

export async function getRecentActivity() {
  return fetchJson<RecentActivityResponse>("/recent-activity");
}

export async function getDecisionSummary() {
  return fetchJson<DecisionSummaryResponse>("/decision-summary");
}

export async function getLiveDashboard() {
  return fetchJson<LivePayload>("/live-dashboard");
}

export async function getOrchestrationMetrics() {
  return fetchJson<OrchestrationMetrics>("/orchestration/metrics");
}

export async function getControlPlaneStatus() {
  return fetchJson<ControlPlaneStatus>("/control-plane/status");
}

export async function getControlPlaneApps() {
  return fetchJson<ControlPlaneApps>("/control-plane/apps");
}

export async function ingestLink(link: string) {
  return fetchJson<{ success: boolean; message?: string; error?: string }>("/ingest-link", {
    method: "POST",
    body: JSON.stringify({ link }),
  });
}

export async function removeLink(link: string) {
  return fetchJson<{ success: boolean; message?: string; error?: string }>("/remove-link", {
    method: "POST",
    body: JSON.stringify({ link }),
  });
}

export async function makeDecision(payload: DecisionRequestPayload) {
  return fetchJson<DecisionResponse>("/decision", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function makeDecisionWithControlPlane(payload: DecisionRequestPayload) {
  return fetchJson<DecisionWithControlPlaneResponse>("/decision-with-control-plane", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
