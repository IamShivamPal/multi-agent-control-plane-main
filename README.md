# Pravah: Multi-Agent Control Plane

Pravah is an autonomous control-plane platform for multi-application operations. It combines a guarded runtime loop, deterministic decisioning, per-app governance, and a real-time dashboard stack.

## Status

- Version: 1.0.0
- Python: 3.10+
- Primary runtime layout: control_plane/*

## What Is Implemented

- Autonomous runtime loop: sense -> validate -> decide -> enforce -> act -> observe -> explain
- Multi-app registry and history
- Per-app manual freeze overrides with expiry
- Governance gates: eligibility, cooldown, repetition
- Safe execution gate with refusal semantics
- Runtime payload contract and fail-fast validation
- FastAPI decision-brain backend for dashboard and decision simulation
- Flask control-plane API for canonical /api/runtime and control-plane endpoints
- Next.js dashboard frontend

## Repository Layout (Key Paths)

- Runtime core: agent_runtime.py
- Runtime contract: runtime_payload_schema.json
- Control-plane Flask API: control_plane/api/agent_api.py
- Multi-app control plane: control_plane/multi_app_control_plane.py
- Safety/governance:
  - control_plane/core/rl_orchestrator_safe.py
  - control_plane/core/action_governance.py
  - control_plane/core/input_validator.py
- Decision-brain FastAPI backend:
  - control_plane/backend/app/main.py
  - control_plane/backend/run.py
- Frontend (Next.js): dashboard/frontend

## Service Topology

Local topology typically runs 3 services:

1. Flask Control Plane API
- Default port: 7000
- Entrypoint: control_plane/api/agent_api.py
- Owns: /api/runtime, /api/status, /api/health, /api/control-plane/*

2. FastAPI Decision Brain API
- Default port: 8000
- Entrypoint: control_plane/backend/run.py
- Owns: /health, /decision, /live-dashboard, /orchestration/metrics, /autonomous-status

3. Next.js Frontend
- Default port: 4500
- Entrypoint: dashboard/frontend (npm run dev)

## Quick Start (Windows PowerShell)

From repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Terminal 1: Flask Control Plane API

```powershell
cd control_plane
$env:ENVIRONMENT="dev"
$env:CONTROL_PLANE_PORT="7000"
..\.venv\Scripts\python.exe api\agent_api.py
```

Terminal 2: FastAPI Decision Brain API

```powershell
cd control_plane
$env:BACKEND_PORT="8000"
..\.venv\Scripts\python.exe backend\run.py
```

Terminal 3: Frontend

```powershell
cd dashboard\frontend
npm install
npm run dev
```

## Health Checks

```bash
curl http://localhost:7000/api/health
curl http://localhost:7000/api/status
curl http://localhost:8000/health
```

Frontend:

- http://localhost:4500

## API Summary

### Flask Control Plane API (port 7000)

- GET /api/health
- GET /api/status
- POST /api/runtime
- GET /api/control-plane/apps
- GET /api/control-plane/health
- GET /api/control-plane/history/<app_name>
- POST /api/control-plane/override

### FastAPI Decision Brain API (port 8000)

- GET /health
- GET /action-scope
- POST /decision
- GET /recent-activity
- GET /live-dashboard
- GET /decision-summary
- POST /decision-with-control-plane
- GET /control-plane/status
- GET /control-plane/apps
- GET /orchestration/metrics
- GET /autonomous-status
- POST /ingest-link
- POST /remove-link

## Runtime Contract

Canonical runtime payload is defined in:

- runtime_payload_schema.json

Required shape:

```json
{
  "app": "string",
  "env": "dev|stage|prod",
  "state": "running|crashed|degraded|starting|stopped",
  "latency_ms": 0,
  "errors_last_min": 0,
  "workers": 0
}
```

## Governance and Safety

- Environment allowlists:
  - dev: restart, scale_up, scale_down, noop, rollback
  - stage: restart, noop
  - prod: restart, noop
- Cooldowns:
  - restart: 60s
  - scale_up: 120s
  - scale_down: 120s
  - rollback: 300s
- Additional gates:
  - per-app manual freeze
  - emergency freeze
  - illegal action rejection
  - demo-mode intake and safety checks

## Configuration

Common variables:

```bash
ENVIRONMENT=dev
CONTROL_PLANE_PORT=7000
BACKEND_PORT=8000
NEXT_PUBLIC_BACKEND_PORT=8000
NEXT_PUBLIC_DECISION_BRAIN_API_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CONTROL_PLANE_URL=http://localhost:7000
BACKEND_CORS_ORIGINS=http://localhost:4500,http://localhost:3000
BACKEND_CORS_ORIGIN_REGEX=^https://.*\.vercel\.app$|^http://localhost:\d+$
```

## Deployment Notes

- Render backend start command is configured in render.yaml:
  - uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
- Existing docker-compose.yml includes legacy/parallel services (Streamlit agents and monitors).
  - Treat it as a separate deployment profile from the current FastAPI + Next.js local stack.

## Documentation Map

- Architecture blueprint: ARCHITECTURE.md
- Current implementation architecture: ARCHITECTURE_CURRENT.md
- Backend setup: BACKEND_SETUP.md
- Runtime contract details: RUNTIME_CONTRACT.md
- Project implementation review: Review_Packet.md


# SYSTEM FLOW

Monitoring → Control Plane → Decision → Execution

1. Monitoring sends runtime signal
2. Control plane ingests via /runtime-ingest
3. Decision engine computes action
4. Governance validates action
5. Action executed via external system

# CANONICAL BACKEND
FastAPI

# ENTRY POINT
/control-plane/runtime-ingest

FastAPI is the canonical backend