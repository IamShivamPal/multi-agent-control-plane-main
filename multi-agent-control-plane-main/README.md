# Pravah: Autonomous DevOps Control Plane

**Pravah** is a production-grade autonomous control plane for multi-product DevOps orchestration. It manages 10+ applications simultaneously with intelligent decision-making, deterministic governance, and safety constraints.

**Status:** Production Ready (Day 7 Final Release)  
**Version:** 1.0.0  
**Python:** 3.10+  
**License:** MIT

---

## 📋 What is Pravah?

Pravah (Sanskrit: "flow") is an autonomous system that:

- **Manages Multiple Products:** Orchestrates decisions across 10+ independent applications simultaneously
- **Autonomous Decisions:** Makes deterministic, governance-constrained decisions in seconds
- **Safety First:** Enforces action governance with cooldown periods and repetition limits per environment
- **Multi-Tenant Ready:** Per-app decision histories, manual overrides, and independent freeze controls
- **Production Hardened:** Rate limiting, input validation, timeout handling, comprehensive logging

### Core Features

| Feature | Description |
|---------|-------------|
| **Multi-App Registry** | Aggregates 30+ onboarded apps with metadata |
| **Decision Engine** | Event → Policy → Decision → Governance → Execute pipeline |
| **Health Dashboard** | Real-time status of all apps with last action and freeze state |
| **Decision Timeline** | Full audit trail per app with timestamps and reasons |
| **Manual Override** | Temporary per-app freeze with time-based expiry |
| **Environment Gating** | Dev (full autonomy) → Stage (decisions-only) → Prod (frozen) |
| **Proof Logging** | Immutable decision proof for compliance and audit |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Canonical Decision API                    │
│  (Rate Limited • Validated Input • RESTful)                 │
└────────────────┬────────────────────────────────────────────┘
                 │
       ┌─────────▼──────────┐
       │  Event Validation  │  Schemas • Type Checking • Bounds
       └─────────┬──────────┘
                 │
       ┌─────────▼──────────┐
       │  Event → Policies  │  Deterministic Decision Logic
       └─────────┬──────────┘
                 │
       ┌─────────▼──────────┐
       │  Governance Layer  │  Cooldown • Repetition • Eligibility
       └─────────┬──────────┘
                 │
       ┌─────────▼──────────┐
       │ SafeOrchestrator   │  Manual Freeze Enforcement
       └─────────┬──────────┘
                 │
       ┌─────────▼──────────┐
       │ Action Execution   │  Simulated DevOps Adapters
       └─────────┬──────────┘
                 │
    ┌────────────▼────────────┐
    │  Decision Proof Logging │  Immutable Audit Trail
    └─────────────────────────┘
```

### Environment Autonomy Levels

| Environment | Autonomy | Actions | Use Case |
|-------------|----------|---------|----------|
| **dev** | 🟢 FULL | restart, scale_up, noop | Development & testing |
| **staging** | 🟡 DECISIONS | restart, noop | Pre-production validation |
| **prod** | 🧊 FROZEN | restart, noop | Production (manual intervention) |
| **prod (emergency)** | 🔴 EMERGENCY | noop-only | Emergency lockdown mode |

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone <repo-url>
cd multi-agent-control-plane-main

# Create virtual environment
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Linux/Mac
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Decision Brain backend deps
pip install -r backend/requirements.txt

# Verify installation
python agent_runtime.py --help
```

### Run Locally (Current Service Topology)

| Service | Port | Entrypoint |
|---------|------|------------|
| Control Plane API (Flask) | `7000` | `api/agent_api.py` |
| Decision Brain API (FastAPI) | `7999` | `backend/run.py` |
| Frontend (Next.js) | `3200` | `frontend` (`npm run dev`) |

### Local Startup (PowerShell)

```powershell
# from repo root: multi-agent-control-plane-main
$env:ENVIRONMENT="dev"
$env:CONTROL_PLANE_PORT="7000"
.\.venv\Scripts\python.exe api\agent_api.py
```

In a second terminal:

```powershell
# from repo root: multi-agent-control-plane-main
$env:BACKEND_PORT="7999"
.\.venv\Scripts\python.exe backend\run.py
```

In a third terminal:

```powershell
# from repo root: multi-agent-control-plane-main
cd frontend
npm install
npm run dev
```

### Health Checks

```bash
curl http://localhost:7000/api/health
curl http://localhost:7000/api/status
curl http://localhost:7999/health
```

Frontend: `http://localhost:3200`

### Run with Docker (Production)

```bash
# Build and start
docker-compose up --build -d

# View logs
docker-compose logs -f api

# Access API
curl http://localhost:7000/api/control-plane/health
```

---

## 📡 API Reference

### Core Decision Endpoint

**POST /api/runtime** - Submit an event for autonomous decision

```bash
curl -X POST http://localhost:7000/api/runtime \
  -H "Content-Type: application/json" \
  -d '{
    "app": "my-app",
    "env": "dev",
    "state": "crashed",
    "latency_ms": 100,
    "errors_last_min": 0,
    "workers": 2
  }'
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "action": "restart",
    "reason": "event_policy:crash",
    "confidence": 1.0
  }
}
```

### Control Plane Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Current agent status & autonomy level |
| `/api/health` | GET | Service health check |
| `/api/control-plane/apps` | GET | List all onboarded apps |
| `/api/control-plane/health` | GET | Dashboard: status of all apps |
| `/api/control-plane/history/<app>` | GET | Decision timeline for app (limit param) |
| `/api/control-plane/override` | POST | Set/clear temporary app freeze |

### Rate Limits

- **Health Check** (`/api/health`): 100 req/min
- **Status** (`/api/status`): 60 req/min  
- **Runtime Decision** (`/api/runtime`): 30 req/min (most resource-intensive)
- **Control Plane**: 40 req/min each

---

## ⚙️ Configuration

### Environment Variables

```bash
# Control Plane (Flask API)
ENVIRONMENT=dev                  # dev | staging | prod
CONTROL_PLANE_PORT=7000          # Flask API port (fallback: PORT)

# Decision Brain (FastAPI backend)
BACKEND_PORT=7999                # FastAPI port (fallback: PORT)

# Multi-product configuration
APPS_REGISTRY_DIR=apps/registry    # Path to app specs
LOG_DIR=logs/

# Redis (mock mode by default)
REDIS_MODE=mock         # mock | real (set REDIS_URL for real)
REDIS_URL=redis://localhost:6379

# Frontend (Next.js)
NEXT_PUBLIC_BACKEND_PORT=7999
NEXT_PUBLIC_DECISION_BRAIN_API_URL=http://localhost:7999
NEXT_PUBLIC_API_URL=http://localhost:7999
NEXT_PUBLIC_CONTROL_PLANE_URL=http://localhost:7000
```

### Governance Configuration

Governance cooldown periods (seconds):

```python
COOLDOWN = {
    "restart": 60,       # 60s before restart allowed again
    "scale_up": 120,     # 120s before scaling allowed
    "scale_down": 120,   # 120s before downscaling allowed
    "rollback": 300,     # 5min before rollback allowed
}
```

---

## 📊 Multi-App Control Plane

### Registry Management

Apps are discovered from `apps/registry/*.json`:

```json
{
  "name": "my-app",
  "type": "pod",
  "source_type": "kubernetes",
  "health_endpoint": "http://my-app/health"
}
```

### Health Overview

```bash
curl http://localhost:7000/api/control-plane/health | jq .
```

Returns per-app status:
```json
{
  "app_name": "my-app",
  "status": "healthy",
  "last_action": "restart",
  "last_reason": "event_policy:crash",
  "last_seen": "2026-02-20T12:34:56Z",
  "manual_freeze": false
}
```

### Per-App Manual Override

```bash
# Freeze app for 30 minutes
curl -X POST http://localhost:7000/api/control-plane/override \
  -H "Content-Type: application/json" \
  -d '{
    "app_name": "my-app",
    "action": "set_freeze",
    "duration_minutes": 30,
    "reason": "maintenance_window"
  }'

# Clear freeze
curl -X POST http://localhost:7000/api/control-plane/override \
  -H "Content-Type: application/json" \
  -d '{
    "app_name": "my-app",
    "action": "clear_freeze"
  }'
```

---

## 🔒 Governance & Safety

### Decision Governance Rules

**Production Environment (Frozen Mode):**
- ✅ `restart` - Allowed (recovery action)
- ✅ `noop` - Allowed (safe default)
- ❌ `scale_up` - BLOCKED (requires manual approval)
- ❌ `scale_down` - BLOCKED (requires manual approval)

**Staging Environment (Decisions Only):**
- ✅ `restart` - Allowed
- ✅ `noop` - Allowed
- ⚠️ `scale_up`/`scale_down` - BLOCKED (decisions only)

**Development Environment (Full Autonomy):**
- ✅ All actions allowed
- 🟢 Full autonomous scalability

### Cooldown Enforcement

Once an action is executed:
- **Restart:** Can't restart same app for 60 seconds
- **Scale-up:** Can't scale up for 120 seconds
- **Scale-down:** Can't scale down for 120 seconds
- **Rollback:** Can't rollback for 300 seconds

---

## 🧪 Testing & Validation

### Run Determinism Tests

Validates system produces reproducible decisions:

```bash
python testing/test_determinism.py
```

Output:
```
❯ ✓ Deterministic decisions: PASS
❯ ✓ Governance consistency: PASS
❯ ✓ State isolation: PASS
❯ ✓ Environment gating: PASS

DETERMINISM TEST SUITE: PASS
Checkpoint: System stable under stress
```

### Run Multi-App Load Test

Simulates 10-app scenario (validates checkpoint):

```bash
python testing/multi_app_load_test.py
```

Output:
```json
{
  "status": "success",
  "checkpoint": "Pravah manages multiple products simultaneously",
  "processed_apps": 10,
  "successful_actions": 10
}
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [STRUCTURE.md](STRUCTURE.md) | Repository structure & module overview |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | Command reference & quick tips |
| [GOVERNANCE_EXPLAINED.md](docs/GOVERNANCE_EXPLAINED.md) | Deep dive on decision governance |
| [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | Production deployment procedures |

---

## 🔐 Production Hardening

Pravah includes production-grade features:

- ✅ **Rate Limiting** - Per-endpoint limits (30-100 req/min)
- ✅ **Input Validation** - Strict type checking, bounds validation, enum constraints
- ✅ **Timeout Handling** - Function timeouts, retry with exponential backoff
- ✅ **Circuit Breaker** - Graceful failure escalation
- ✅ **Structured Logging** - Production-grade log format (text or JSON)
- ✅ **Proof Logging** - Immutable decision audit trail
- ✅ **Determinism Testing** - Reproducibility validation

---

## 📦 Deployment

### Single Instance Deployment

```bash
# Set environment to production
export ENVIRONMENT=prod

# Start agent runtime + API
python agent_runtime.py &
gunicorn -w 4 -b 0.0.0.0:7000 api/agent_api:app

# Monitor
tail -f logs/prod/orchestrator_decisions.jsonl
```

### Docker Deployment

```bash
# Build image
docker build -t pravah:latest .

# Run container
docker run -d \
  --name pravah-api \
  -e ENVIRONMENT=prod \
  -p 7000:7000 \
  -v $(pwd)/logs:/app/logs \
  pravah:latest

# Health check
curl http://localhost:7000/api/health
```

### Kubernetes Deployment

See [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) for K8s manifests and helm configurations.

---

## 📈 Monitoring & Observability

### Decision Proof Log

Every autonomous decision is logged to `logs/prod/orchestrator_decisions.jsonl`:

```json
{
  "timestamp": "2026-02-20T12:34:56Z",
  "app_name": "my-app",
  "event_type": "crash",
  "action": "restart",
  "success": true,
  "reason": "event_policy:crash",
  "governance_applied": true,
  "cooldown_remaining_sec": 45
}
```

### Status Endpoint

```bash
curl http://localhost:7000/api/status | jq .
```

Response includes:
```json
{
  "autonomy": {
    "level": "full",
    "badge": "🟢 DEV FULL",
    "decisions_enabled": true,
    "learning_enabled": true
  },
  "decisions_this_epoch": 42,
  "app_count": 10
}
```

---

## 🐛 Troubleshooting

### Agent not making decisions

```bash
# Check agent status
curl http://localhost:7000/api/status

# Check logs
tail -f logs/prod/orchestrator_decisions.jsonl

# Is environment frozen?
grep "FROZEN" logs/*
```

### Rate limit errors (429)

- API rejected request due to rate limit
- Wait 60 seconds and retry
- Verify requests are within limits

### Validation errors (400)

- Check JSON schema compliance: `runtime_payload_schema.json`
- Ensure `app`, `env`, `state` are provided
- Verify numeric bounds (latency_ms < 60000, workers > 0)

---

## 📝 Final State

**Pravah = One Unified DevOps Autonomous Control Plane**

```
✅ Multi-app management (10+ apps)
✅ Autonomous decision-making (event → action)
✅ Governance constraints (environment-based)
✅ Safety enforcement (cooldowns & limits)
✅ Production hardening (rate limits, validation)
✅ Deterministic & reproducible
✅ Full audit trail (proof logs)
✅ Multi-tenant control (per-app history & overrides)
```

### Checkpoint: System Production Ready

- Status: ✅ PASS
- All Day 1-7 milestones complete
- Load tested with 10+ apps
- Governance verified
- Production deployment ready

---

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

For contribution guidelines, see CONTRIBUTING.md

## 📞 Support

For issues and feature requests, create an issue on GitHub or contact the team.

---

**Last Updated:** February 20, 2026  
**Maintained by:** Pravah Development Team
