from collections import deque
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any
import sys
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .execution_simulator import execute_action


def _parse_cors_origins() -> list[str]:
    """Parse explicit CORS origins from env with sane defaults for local and prod."""
    raw = os.getenv(
        "BACKEND_CORS_ORIGINS",
        ",".join(
            [
                "http://localhost:4500",
                "http://localhost:3000",
                "https://multi-agent-control-plane-frontend.vercel.app",
            ]
        ),
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _cors_origin_regex() -> str:
    """Allow Vercel preview URLs and localhost ports unless overridden."""
    return os.getenv(
        "BACKEND_CORS_ORIGIN_REGEX",
        r"^https://.*\.vercel\.app$|^http://localhost:\d+$",
    )

try:
    from .config import ACTION_SCOPE, DEMO_FROZEN, STATELESS, SUCCESS_RATE
    from .decision_engine import DecisionEngine
    from .schemas import (
        ActionScopeResponse,
        DecisionDashboardSummary,
        DecisionRequest,
        DecisionResponse,
        HealthResponse,
        LiveDashboardResponse,
        RecentActivityResponse,
    )
    from .integration_bridge import get_bridge
except ImportError:
    from .config import ACTION_SCOPE, DEMO_FROZEN, STATELESS, SUCCESS_RATE
    from .decision_engine import DecisionEngine
    from .schemas import (
        ActionScopeResponse,
        DecisionDashboardSummary,
        DecisionRequest,
        DecisionResponse,
        HealthResponse,
        LiveDashboardResponse,
        RecentActivityResponse,
    )
    from integration_bridge import get_bridge


# Initialize integration bridge
_bridge = get_bridge()

# Create FastAPI app
app = FastAPI(
    title="Pravah Decision Brain API",
    version="1.0.0",
    description="Pravah RL Decision Brain integrated with Multi-Agent Control Plane",
)

# CORS middleware for local dev + Vercel deploys (stateless API, no credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_origin_regex=_cors_origin_regex(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,
)


# Startup event: Initialize demo links for realistic dashboard
@app.on_event("startup")
async def startup_event():
    """Initialize dashboard with demo data on app startup."""
    _initialize_demo_links()


# In-memory recent activity only (reset on process restart).
_RECENT_DECISIONS: deque[DecisionResponse] = deque(maxlen=10)


_AUTONOMOUS_DECISIONS: deque[dict] = deque(maxlen=20)
_LAST_AUTONOMOUS_RUNTIME: dict | None = None
_LAST_EXECUTED_ACTION: str | None = None







# In-memory ingested links for monitoring with rich metadata
_INGESTED_LINKS: list[dict[str, Any]] = []

# Track link ingestion history for events and analytics
_LINK_EVENTS: deque[dict[str, Any]] = deque(maxlen=20)

# Simulated project metadata for ingested links
_LINK_METADATA: dict[str, dict[str, Any]] = {}

# Initialize with demo links for realistic dashboard on startup
def _initialize_demo_links():
    """Populate demo links with realistic metadata on app startup."""
    demo_links = [
        {
            "link": "https://github.com/I-am-ShivamPal/multi-agents-control-plane",
            "name": "multi-agents-control-plane",
        },
        {
            "link": "https://github.com/I-am-ShivamPal/multi-agent-control-plane-frontend",
            "name": "multi-agent-control-plane-frontend",
        },
    ]
    
    for demo_link in demo_links:
        link = demo_link["link"]
        name = demo_link["name"]
        
        # Only add if not already ingested
        if not any(item["link"] == link for item in _INGESTED_LINKS):
            _INGESTED_LINKS.append({
                "link": link,
                "name": name,
                "added_at": datetime.now(timezone.utc).isoformat(),
                "status": "HEALTHY",
                "response_time_ms": 300 + (_get_link_hash(link) % 200),
                "uptime_percent": 99.0 + (_get_link_hash(link) % 10) / 100,
                "errors_24h": _get_link_hash(link) % 3,
            })
            
            # Generate and store metadata
            _LINK_METADATA[link] = _generate_link_metadata(link)
            
            # Log the ingestion event
            _LINK_EVENTS.appendleft({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "link_ingested",
                "link": link,
                "name": name,
            })


def _extract_link_name(link: str) -> str:
    """Extract a clean, readable name from a URL."""
    link = link.strip().rstrip('/')
    
    # Remove protocol
    if "://" in link:
        link = link.split("://", 1)[1]
    
    # Handle GitHub-style URLs
    if link.startswith("github.com/"):
        parts = link.split("/")
        if len(parts) >= 3:
            return parts[2]  # repo name
    
    # Handle other git platforms
    if any(platform in link for platform in ["gitlab.com", "bitbucket.org", "gitea"]):
        parts = link.split("/")
        if len(parts) >= 3:
            return parts[2]  # repo name
    
    # For web URLs, extract domain
    domain = link.split("/")[0]  # Remove path
    domain = domain.replace("www.", "")  # Remove www prefix
    
    # Extract main domain name
    if "." in domain:
        domain = domain.split(".")[0]  # Get first part (e.g., "youtube" from "youtube.com")
    
    # Capitalize first letter
    return domain.capitalize()


def _get_link_hash(link: str) -> int:
    """Generate deterministic hash for a link for consistent metrics."""
    return hash(link) % 10000


def _generate_link_metadata(link: str) -> dict[str, Any]:
    """Generate realistic metadata for an ingested link."""
    link_hash = _get_link_hash(link)
    
    # Simulate project characteristics
    is_github = "github.com" in link.lower()
    is_repo = is_github or "bitbucket" in link.lower() or "gitlab" in link.lower()
    
    if is_repo:
        # Repository metadata
        base_commits = 150 + (link_hash % 500)
        base_branches = 3 + (link_hash % 12)
        base_prs = 5 + (link_hash % 20)
        base_stars = 50 + (link_hash % 500) if is_github else 0
        base_files = 45 + (link_hash % 200)
        test_coverage = 65 + (link_hash % 30)
        ci_status = "passing" if link_hash % 4 != 0 else "failing"
    else:
        # Website metadata
        base_commits = 0
        base_branches = 0
        base_prs = 0
        base_stars = 0
        base_files = 10 + (link_hash % 100)
        test_coverage = 55 + (link_hash % 40)  # Web services often have lower test coverage
        ci_status = "passing" if link_hash % 3 != 0 else "degraded"
    
    return {
        "type": "repository" if is_repo else "website",
        "commits": base_commits,
        "branches": base_branches,
        "pull_requests": base_prs,
        "stars": base_stars,
        "files": base_files,
        "contributors": 2 + (link_hash % 25),
        "last_commit": "2h ago" if link_hash % 3 == 0 else ("4h ago" if link_hash % 3 == 1 else "8h ago"),
        "test_coverage": test_coverage,
        "ci_status": ci_status,
        "deployment_frequency": 2 + (link_hash % 8),
        "avg_response_time": 120 + (link_hash % 300),
        "error_rate": (link_hash % 5),
        "active_issues": link_hash % 15,
        "code_quality_score": 70 + (link_hash % 25),
    }


def _bytes_label(size_bytes: int) -> str:
    """Return a compact size label for UI display."""

    if size_bytes <= 0:
        return "0 bytes"
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    return f"{round(size_bytes / 1024, 1)} KB"


def _collect_files(base_path: Path, expected_files: list[str]) -> dict[str, Any]:
    """Collect file state rows for a section, preserving expected order."""

    rows: list[dict[str, str]] = []
    active_count = 0

    for relative_name in expected_files:
        candidate = base_path / relative_name
        exists = candidate.exists() and candidate.is_file()
        size_bytes = candidate.stat().st_size if exists else 0
        if exists:
            active_count += 1
        rows.append(
            {
                "filename": relative_name,
                "status": "ACTIVE" if exists else "MISSING",
                "size": _bytes_label(size_bytes),
            }
        )

    return {"active": active_count, "total": len(expected_files), "files": rows}


def _calculate_health_score(link: str) -> int:
    """Calculate a health score (0-100) for a link based on its metadata."""
    meta = _LINK_METADATA.get(link, {})
    
    # Base score
    score = 85
    
    # Adjust based on CI status
    if meta.get("ci_status") == "passing":
        score += 10
    elif meta.get("ci_status") == "failing":
        score -= 15
    elif meta.get("ci_status") == "degraded":
        score -= 5
    
    # Adjust based on error rate
    error_rate = meta.get("error_rate", 0)
    score -= (error_rate * 3)
    
    # Adjust based on test coverage
    test_coverage = meta.get("test_coverage", 70)
    if test_coverage < 50:
        score -= 10
    elif test_coverage > 80:
        score += 5
    
    # Clamp to 0-100
    return max(0, min(100, score))


def _calculate_aggregate_metrics() -> dict[str, Any]:
    """Calculate aggregate metrics from all ingested links."""
    
    if not _INGESTED_LINKS:
        return {
            "total_commits": 0,
            "total_files": 0,
            "total_contributors": 0,
            "avg_test_coverage": 0,
            "avg_response_time": 513,
            "total_errors": 0,
            "total_issues": 0,
            "avg_quality_score": 70,
            "total_files_list": [],
        }
    
    # Calculate aggregates
    total_commits = sum(_LINK_METADATA.get(item["link"], {}).get("commits", 0) for item in _INGESTED_LINKS)
    total_files = sum(_LINK_METADATA.get(item["link"], {}).get("files", 0) for item in _INGESTED_LINKS)
    total_contributors = sum(_LINK_METADATA.get(item["link"], {}).get("contributors", 0) for item in _INGESTED_LINKS)
    avg_test_coverage = sum(_LINK_METADATA.get(item["link"], {}).get("test_coverage", 0) for item in _INGESTED_LINKS) / len(_INGESTED_LINKS) if _INGESTED_LINKS else 0
    avg_response_time = sum(_LINK_METADATA.get(item["link"], {}).get("avg_response_time", 513) for item in _INGESTED_LINKS) / len(_INGESTED_LINKS) if _INGESTED_LINKS else 513
    total_errors = sum(_LINK_METADATA.get(item["link"], {}).get("error_rate", 0) for item in _INGESTED_LINKS)
    total_issues = sum(_LINK_METADATA.get(item["link"], {}).get("active_issues", 0) for item in _INGESTED_LINKS)
    avg_quality_score = sum(_LINK_METADATA.get(item["link"], {}).get("code_quality_score", 70) for item in _INGESTED_LINKS) / len(_INGESTED_LINKS) if _INGESTED_LINKS else 70
    
    # Generate file list from all repos
    all_files = []
    for item in _INGESTED_LINKS:
        meta = _LINK_METADATA.get(item["link"], {})
        num_files = meta.get("files", 0)
        repo_name = item["name"]
        all_files.extend([f"{repo_name}/file_{i}.py" for i in range(min(num_files, 5))])
    
    return {
        "total_commits": total_commits,
        "total_files": total_files,
        "total_contributors": total_contributors,
        "avg_test_coverage": int(avg_test_coverage),
        "avg_response_time": int(avg_response_time),
        "total_errors": total_errors,
        "total_issues": total_issues,
        "avg_quality_score": int(avg_quality_score),
        "total_files_list": all_files[:50],
    }


def _resolve_control_plane_root() -> Path:
    """Resolve project root for control-plane file checks across old/new layouts."""

    configured_root = os.getenv("PROJECT_ROOT", "").strip()
    if configured_root:
        candidate = Path(configured_root).resolve()
        if (candidate / "core").exists() and (candidate / "agent_runtime.py").exists():
            return candidate

    # Current layout: <project>/backend/app/main.py -> project root is parents[2]
    current_project_root = Path(__file__).resolve().parents[2]
    if (current_project_root / "core").exists() and (current_project_root / "agent_runtime.py").exists():
        return current_project_root

    # Legacy layout fallback where repo sat beside backend
    legacy_sibling = current_project_root / "multi-agent-control-plane-main"
    if (legacy_sibling / "core").exists() and (legacy_sibling / "agent_runtime.py").exists():
        return legacy_sibling

    return current_project_root


def _build_live_dashboard_payload() -> dict[str, Any]:
    """Build full dashboard payload consumed by Pravah Dashboard."""

    recent_count = len(_RECENT_DECISIONS)
    success_rate_percent = int(SUCCESS_RATE * 100)
    now_iso = datetime.now(timezone.utc).isoformat()
    requests_count = max(recent_count, 1)
    estimated_cost = requests_count * 0.0025
    
    # Calculate aggregate metrics from ingested links
    agg_metrics = _calculate_aggregate_metrics()
    avg_latency_ms = agg_metrics["avg_response_time"]

    control_plane_root = _resolve_control_plane_root()

    # Load real runtime telemetry
    runtime_metrics = {}

    runtime_file = control_plane_root / "data" / "runtime_metrics.json"

    if runtime_file.exists():
        try:
            with open(runtime_file) as f:
                runtime_metrics = json.load(f)
        except Exception:
            runtime_metrics = {}
                
    core_files = _collect_files(
        control_plane_root,
        [
            "core/base_agent.py",
            "core/decision_arbitrator.py",
            "core/event_bus.py",
            "core/env_validator.py",
            "core/rl_engine.py",
        ],
    )
    data_files = _collect_files(
        control_plane_root,
        [
            "dataset/student_scores.csv",
            "data/decision_history.json",
            "data/runtime_metrics.json",
            "feedback/production_feedback.json",
            "logs/prod/orchestrator_decisions.jsonl",
        ],
    )
    integration_files = _collect_files(
        control_plane_root,
        [
            "integration/api_adapter.py",
            "integration/unified_event_pipe.py",
            "integration/realtime_sync.py",
            "integration/monitoring_bridge.py",
            "integration/event_schema.py",
        ],
    )
    production_files = _collect_files(
        control_plane_root,
        [
            "deploy.py",
            "deploy_orchestrator.py",
            "docker-compose.yml",
            "render.yaml",
            "scripts/production_healthcheck.py",
        ],
    )

    return {
        "generated_at": now_iso,
        "header": {
            "title": "🚀 Pravah Dashboard",
            "subtitle": "Real-time Production Monitoring",
        },
        
        
        
        
        "live_production_monitoring": (
    [
        {
            "name": app_name,
            "domain": f"{app_name}.local",
            "url": f"http://localhost/{app_name}",
            "status": metrics.get("status", "UNKNOWN").upper(),
            "health_score": 95 if metrics.get("status") == "running" else 60,
            "response_time_ms": int(avg_latency_ms),
            "cpu_percent": metrics.get("cpu_percent", 0),
            "memory_percent": metrics.get("memory_percent", 0),
            "uptime_percent": 99.9 if metrics.get("status") == "running" else 90,
            "last_action": _RECENT_DECISIONS[0].selected_action if recent_count else "noop",
            "errors_24h": 0,
        }
        for app_name, metrics in runtime_metrics.items()
    ]
    if runtime_metrics
    else [
        {
            "name": "BlackHole Universe",
            "domain": "blackhole.rlreality.ai",
            "url": "https://blackhole.rlreality.ai",
            "status": "CONNECTED",
            "health_score": 95,
            "response_time_ms": 320,
            "cpu_percent": 18,
            "memory_percent": 35,
            "uptime_percent": 99.8,
            "last_action": _RECENT_DECISIONS[0].selected_action if recent_count else "noop",
            "errors_24h": 0,
        },
        {
            "name": "Uni-Guru Platform",
            "domain": "uni-guru.rlreality.ai",
            "url": "https://uni-guru.rlreality.ai",
            "status": "CONNECTED",
            "health_score": 98,
            "response_time_ms": 513,
            "cpu_percent": 22,
            "memory_percent": 43,
            "uptime_percent": 99.9,
            "last_action": _RECENT_DECISIONS[0].selected_action if recent_count else "noop",
            "errors_24h": 1,
        },
    ]
),
        
        
        
        
        
        
        
        
        
        "summary_metrics": [
            {"label": "Total Commits", "value": str(agg_metrics["total_commits"])},
            {"label": "Contributors", "value": str(agg_metrics["total_contributors"])},
            {"label": "Test Coverage", "value": f"{agg_metrics['avg_test_coverage']}%"},
            {"label": "Monitored Links", "value": str(len(_INGESTED_LINKS))},
        ],
        "ai_learning_status": [
            {"label": "Learning Status", "value": "Optimizing" if len(_INGESTED_LINKS) > 0 else "Idle", "tone": "green"},
            {"label": "Code Quality Score", "value": f"{agg_metrics['avg_quality_score']}%", "tone": "blue"},
            {"label": "Policy Updates", "value": str(320 + recent_count + len(_INGESTED_LINKS) * 10), "tone": "blue"},
            {"label": "Q-Table Size", "value": str(100 + recent_count + len(_INGESTED_LINKS) * 50), "tone": "blue"},
            {"label": "Training Progress", "value": f"{min(100, 73 + len(_INGESTED_LINKS) * 5)}%", "tone": "blue" if len(_INGESTED_LINKS) > 0 else "red"},
        ],
        "system_health": [
            {"label": "Overall Health", "value": f"{max(85, success_rate_percent - (agg_metrics['total_errors'] * 2))}%", "tone": "green"},
            {"label": "CPU Usage", "value": f"{22 + (len(_INGESTED_LINKS) * 2)}%", "tone": "orange"},
            {"label": "Memory Usage", "value": f"{43 + (len(_INGESTED_LINKS) * 1.5)}%", "tone": "blue"},
            {"label": "Active Issues", "value": str(agg_metrics["total_issues"]), "tone": "red" if agg_metrics["total_issues"] > 10 else "green"},
            {"label": "Error Rate", "value": f"{agg_metrics['total_errors']}%", "tone": "red"},
        ],
        "performance_metrics": [
            {"label": "Response Time (ms)", "value": str(int(agg_metrics["avg_response_time"]))},
            {"label": "Throughput/sec", "value": str(128 + len(_INGESTED_LINKS) * 15)},
            {"label": "Success Rate", "value": f"{max(90, success_rate_percent - len(_INGESTED_LINKS) * 2)}%"},
            {"label": "Requests/min", "value": str(45 + recent_count + len(_INGESTED_LINKS) * 5)},
            {"label": "Total Files Tracked", "value": str(agg_metrics["total_files"])},
        ],
        "project_files_status": [
            {"title": "Core RL System", "icon": "🧠", **core_files},
            {"title": "Data Files", "icon": "🗂️", **data_files},
            {"title": "Integration Layer", "icon": "🔌", **integration_files},
            {"title": "Production Layer", "icon": "🏭", **production_files},
        ] + [
            {
                "title": f"📦 {item['name']}",
                "icon": "📁",
                "active": _LINK_METADATA.get(item["link"], {}).get("files", 0),
                "total": _LINK_METADATA.get(item["link"], {}).get("files", 0),
                "files": [
                    {
                        "filename": f"main.py",
                        "status": "ACTIVE",
                        "size": f"{100 + (_get_link_hash(item['link']) % 500)} KB",
                    },
                    {
                        "filename": f"config.yaml",
                        "status": "ACTIVE",
                        "size": "5.2 KB",
                    },
                    {
                        "filename": f"requirements.txt",
                        "status": "ACTIVE",
                        "size": "2.1 KB",
                    }
                ]
            }
            for item in _INGESTED_LINKS
        ],
        "enhanced_telemetry": {
            "status": "HEALTHY" if agg_metrics["total_errors"] < 5 else "DEGRADED",
            "avg_latency": f"{int(avg_latency_ms)}ms",
            "cost": f"${estimated_cost:.4f}",
            "success": f"{success_rate_percent - (agg_metrics['total_errors'] * 2)}%",
            "requests": str(requests_count + len(_INGESTED_LINKS)),
        },
        "policy_evolution": {
            "title": "Q-Table Evolution",
            "metrics": [
                {"label": "Q-Table Size", "value": str(100 + recent_count + len(_INGESTED_LINKS) * 50)},
                {"label": "Learning Progress", "value": f"{min(100, 73 + len(_INGESTED_LINKS) * 5)}%"},
                {"label": "Policy Actions", "value": f"{3 + len(_INGESTED_LINKS)} actions learned"},
                {"label": "Code Quality Impact", "value": f"+{agg_metrics['avg_quality_score'] - 70}%" if agg_metrics['avg_quality_score'] > 70 else f"{agg_metrics['avg_quality_score'] - 70}%"},
            ],
        },
        "error_analytics": {
            "recent_errors": [
                {"code": f"REPO_ERROR_{i}", "severity": "LOW" if agg_metrics["total_errors"] < 3 else "MEDIUM"} 
                for i in range(min(3, agg_metrics["total_errors"] + 1))
            ] or [{"code": "NO_ERRORS", "severity": "NONE"}],
            "statistics": {
                "total_errors": agg_metrics["total_errors"],
                "avg_impact_score": 5.0 + (agg_metrics["total_errors"] * 0.5),
                "critical_issues": sum(1 for item in _INGESTED_LINKS if _LINK_METADATA.get(item["link"], {}).get("ci_status") == "failing"),
                "test_coverage_avg": agg_metrics["avg_test_coverage"],
            },
        },
        "auto_failover_status": {
            "active_domain": "UNI_GURU" if len(_INGESTED_LINKS) > 0 else "BLACKHOLE",
            "failure_threshold": 3,
            "domains": [
                {"name": item["name"], "status": item["status"]} 
                for item in _INGESTED_LINKS[:5]
            ] + [
                {"name": "BLACKHOLE", "status": "CONNECTED"},
                {"name": "UNI_GURU", "status": "HEALTHY"},
            ],
        },
        "live_events": [
            {"title": f"Tracking {len(_INGESTED_LINKS)} projects", "time_ago": "now", "tone": "green"},
            {"title": f"Code quality: {agg_metrics['avg_quality_score']}%", "time_ago": "1m ago", "tone": "blue"},
            {"title": f"{agg_metrics['total_commits']} commits detected", "time_ago": "2m ago", "tone": "indigo"},
            {"title": f"{agg_metrics['total_contributors']} contributors contributing", "time_ago": "3m ago", "tone": "purple"},
            {"title": f"Test coverage: {agg_metrics['avg_test_coverage']}%", "time_ago": "5m ago", "tone": "orange"},
            {"title": f"{agg_metrics['total_issues']} active issues", "time_ago": "8m ago", "tone": "red" if agg_metrics["total_issues"] > 5 else "green"},
            {"title": "RL model updated", "time_ago": "10m ago", "tone": "teal"},
        ],
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return service health and runtime safety guarantees."""

    return HealthResponse(
        status="healthy",
        demo_frozen=DEMO_FROZEN,
        stateless=STATELESS,
        success_rate=SUCCESS_RATE,
    )


@app.get("/action-scope", response_model=ActionScopeResponse)
def action_scope() -> ActionScopeResponse:
    """Return environment-specific allowed actions for policy enforcement."""

    return ActionScopeResponse(**ACTION_SCOPE)


@app.post("/decision", response_model=DecisionResponse)
def decision(payload: DecisionRequest) -> DecisionResponse:
    """Compute a deterministic decision and append it to in-memory recent activity."""

    result = DecisionEngine.decide(payload)
    _RECENT_DECISIONS.appendleft(result)
    return result


@app.get("/recent-activity", response_model=RecentActivityResponse)
def recent_activity() -> RecentActivityResponse:
    """Return the last ten in-memory decisions, newest first."""

    return RecentActivityResponse(items=list(_RECENT_DECISIONS))


@app.get("/", response_model=LiveDashboardResponse)
def root_dashboard() -> dict[str, Any]:
    """Map root URL directly to the live dashboard payload."""
    return _build_live_dashboard_payload()


@app.get("/live-dashboard", response_model=LiveDashboardResponse)
def live_dashboard() -> dict[str, Any]:
    """Return full real-time dashboard payload consumed by RL Reality UI."""

    return _build_live_dashboard_payload()


@app.get("/decision-summary", response_model=DecisionDashboardSummary)
def decision_summary() -> DecisionDashboardSummary:
    """Return aggregate summary metrics consumed by the Decision Brain UI."""

    return DecisionDashboardSummary(
        total_decisions=len(_RECENT_DECISIONS),
        last_action=_RECENT_DECISIONS[0].selected_action if _RECENT_DECISIONS else "-",
        success_rate=SUCCESS_RATE,
        demo_frozen=DEMO_FROZEN,
        stateless=STATELESS,
    )


@app.post("/ingest-link")
def ingest_link(payload: dict[str, Any]) -> dict[str, Any]:
    """Ingest a repository or website link for monitoring."""

    link = payload.get("link", "").strip()
    if not link:
        return {"success": False, "error": "Link cannot be empty"}

    # Check if link already exists
    existing = next((item for item in _INGESTED_LINKS if item["link"] == link), None)
    if existing:
        return {"success": False, "error": "Link already being monitored"}

    # Generate metadata for this link
    metadata = _generate_link_metadata(link)
    _LINK_METADATA[link] = metadata
    
    # Extract clean name from URL
    link_name = _extract_link_name(link)
    
    # Add new link with monitoring metadata
    ingested_item = {
        "link": link,
        "name": link_name,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "status": "HEALTHY" if metadata["ci_status"] == "passing" else "DEGRADED",
        "response_time_ms": metadata["avg_response_time"],
        "uptime_percent": 99.2 + ((_get_link_hash(link) % 7) * 0.1),
        "errors_24h": metadata["error_rate"],
    }
    _INGESTED_LINKS.append(ingested_item)
    
    # Record event
    _LINK_EVENTS.appendleft({
        "type": "link_added",
        "link": link,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": f"Added {metadata['type']} with {metadata['files']} files",
    })

    return {"success": True, "message": f"Link ingested: {link}", "ingested_link": ingested_item}


@app.post("/remove-link")
def remove_link(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove a monitored link from the dashboard."""

    link = payload.get("link", "").strip()
    if not link:
        return {"success": False, "error": "Link cannot be empty"}

    # Find and remove the link
    global _INGESTED_LINKS, _LINK_METADATA
    original_count = len(_INGESTED_LINKS)
    _INGESTED_LINKS = [item for item in _INGESTED_LINKS if item["link"] != link]
    
    # Remove metadata
    if link in _LINK_METADATA:
        del _LINK_METADATA[link]
    
    # Record event
    if len(_INGESTED_LINKS) < original_count:
        _LINK_EVENTS.appendleft({
            "type": "link_removed",
            "link": link,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"Removed {link}",
        })
        return {"success": True, "message": f"Link removed: {link}"}
    else:
        return {"success": False, "error": "Link not found"}


# ============================================================================
# INTEGRATION WITH MULTI-AGENT CONTROL PLANE
# ============================================================================

@app.get("/control-plane/status")
def control_plane_status() -> dict[str, Any]:
    """Get integrated control plane orchestration status."""
    return _bridge.get_control_plane_status()


@app.get("/control-plane/apps")
def control_plane_apps() -> dict[str, Any]:
    """Get list of apps managed by the control plane."""
    apps = _bridge.get_app_registry()
    return {
        "total_apps": len(apps),
        "apps": apps,
        "integration_status": "connected" if _bridge.sync_enabled else "disconnected",
    }


@app.get("/orchestration/metrics")
def orchestration_metrics() -> dict[str, Any]:
    """Get unified orchestration metrics combining RL Brain and Control Plane."""
    agg_metrics = _calculate_aggregate_metrics()
    cp_metrics = _bridge.get_orchestration_metrics()
    
    return {
        "rl_brain": {
            "status": "active",
            "monitored_links": len(_INGESTED_LINKS),
            "total_commits": agg_metrics["total_commits"],
            "total_contributors": agg_metrics["total_contributors"],
            "avg_test_coverage": agg_metrics["avg_test_coverage"],
            "total_decisions": len(_RECENT_DECISIONS),
        },
        "control_plane": cp_metrics,
        "unified": {
            "total_entities_monitored": len(_INGESTED_LINKS) + cp_metrics.get("total_apps_monitored", 0),
            "total_decisions_made": len(_RECENT_DECISIONS) + cp_metrics.get("rl_decisions_made", 0),
            "system_status": "operational",
            "integration_enabled": _bridge.sync_enabled,
        },
    }








@app.get("/api/health")
def api_health():
    return {"status": "ok"}









@app.post("/decision-with-control-plane")
def decision_with_control_plane(payload: DecisionRequest) -> dict[str, Any]:
    """Make a decision and sync with control plane."""
    # Make RL decision
    result = DecisionEngine.decide(payload)
    _RECENT_DECISIONS.appendleft(result)
    
    # Record decision in integration bridge
    _bridge.record_rl_decision({
        "action": result.selected_action,
        "cpu": payload.cpu,
        "memory": payload.memory,
        "environment": payload.environment,
    })
    
    return {
        "decision": result.dict(),
        "control_plane_sync": {
            "status": "synced" if _bridge.sync_enabled else "skipped",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }








import threading
import time
from .runtime_adapter import runtime_decision_cycle


from .execution_simulator import execute_action

def autonomous_loop():
    global _LAST_AUTONOMOUS_RUNTIME, _LAST_EXECUTED_ACTION

    while True:
        try:
            result = runtime_decision_cycle(
                service_name="local-backend",
                base_url="http://127.0.0.1:8000"
            )

            runtime_payload = result["runtime_payload"]
            decision = result["decision"]

            print("[AUTONOMOUS LOOP]", result)

            execute_action(decision)

            # Store autonomous activity separately
            _LAST_AUTONOMOUS_RUNTIME = runtime_payload
            _LAST_EXECUTED_ACTION = decision.selected_action
            _AUTONOMOUS_DECISIONS.appendleft({
                "runtime": runtime_payload,
                "decision": decision.dict(),
            })

        except Exception as e:
            print("[AUTONOMOUS LOOP ERROR]", str(e))

        time.sleep(10)


@app.on_event("startup")
def start_autonomous_loop():
    thread = threading.Thread(target=autonomous_loop, daemon=True)
    thread.start()


@app.get("/autonomous-status")
def autonomous_status():
    return {
        "last_runtime": _LAST_AUTONOMOUS_RUNTIME,
        "last_action": _LAST_EXECUTED_ACTION,
        "recent_autonomous_decisions": list(_AUTONOMOUS_DECISIONS),
        "loop_running": True,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("BACKEND_PORT", os.getenv("PORT", "8000")))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)


