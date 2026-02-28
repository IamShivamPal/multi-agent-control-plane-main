# Live Wiring Validation Guide

## Overview

This guide validates that **Runtime → Agent → Decision → Orchestrator** works end-to-end with strict REST-only communication.

---

## Architecture

```
┌──────────────┐     HTTP      ┌──────────────┐     HTTP      ┌──────────────┐
│   Runtime    │ ──────────────▶│    Agent     │ ──────────────▶│ Orchestrator │
│  Service     │  POST /decide │   Service    │ POST /execute │   Service    │
│  Port 8001   │               │  Port 8002   │               │  Port 8003   │
└──────────────┘               └──────────────┘               └──────────────┘
      │                              │                              │
      │                              │                              │
   Emits Event              Makes Decision                 Executes Action
```

---

## Quick Start

### Option 1: Windows Batch Script

```bash
# Start all services automatically
START_SERVICES.bat
```

### Option 2: Manual Start (3 Terminals)

**Terminal 1 - Agent:**
```bash
cd antigravity/services/agent
python main.py
# Listening on http://localhost:8002
```

**Terminal 2 - Orchestrator:**
```bash
cd antigravity/services/orchestrator
python main.py
# Listening on http://localhost:8003
```

**Terminal 3 - Runtime:**
```bash
cd antigravity/services/runtime
python main.py
# Listening on http://localhost:8001
```

---

## Validation Tests

### Run Full Test Suite

```bash
cd antigravity/tests
bash test_live_wiring.sh
```

---

## Manual Testing

### Test 1: Agent Decision (Isolated)

```bash
curl -X POST http://localhost:8002/decide \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "app_crash",
    "app": "web-api",
    "env": "prod",
    "state": "critical",
    "metrics": {"error_count": 15}
  }'
```

**Expected:**
```json
{
  "decision": "restart",
  "reason": "state_critical",
  "confidence": 0.9
}
```

---

### Test 2: Orchestrator Execution (Isolated)

```bash
curl -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{
    "action": "restart",
    "app": "web-api",
    "env": "prod",
    "requested_by": "agent"
  }'
```

**Expected:**
```json
{
  "status": "executed",
  "action": "restart",
  "execution_id": "exec_..."
}
```

---

### Test 3: Full End-to-End Flow

```bash
curl -X POST http://localhost:8001/emit \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "app_crash",
    "app": "web-api",
    "env": "prod",
    "metadata": {
      "error_count": 15,
      "state": "critical"
    }
  }'
```

**Expected:**
```json
{
  "status": "processed",
  "event_id": "evt_...",
  "agent_decision": {
    "decision": "restart",
    "reason": "state_critical"
  },
  "orchestrator_result": {
    "status": "executed",
    "execution_id": "exec_..."
  }
}
```

---

## REST-Only Verification

### ✅ No Cross-Imports

Each service **MUST NOT** import code from other services:

**Violations:**
```python
# ❌ FORBIDDEN in agent/main.py
from runtime.main import something
from orchestrator.executor import something

# ❌ FORBIDDEN in orchestrator/main.py
from agent.decision_logic import something
```

**Correct:**
```python
# ✅ Agent communicates via HTTP
import requests
response = requests.post("http://orchestrator:8003/execute", json=data)
```

---

## Safety Guarantees

### 1. NOOP on Invalid Input

```bash
# Test malformed JSON
curl -X POST http://localhost:8002/decide \
  -H "Content-Type: application/json" \
  -d '{"invalid json'

# Expected: {"decision": "noop", "reason": "malformed_json"}
```

### 2. Environment Action Scopes

```bash
# Test unauthorized action in prod
curl -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{
    "action": "scale_up",
    "app": "web-api",
    "env": "prod",
    "requested_by": "agent"
  }'

# Expected: {"status": "rejected", "reason": "action_out_of_scope"}
```

### 3. Demo Mode

```bash
# Start orchestrator in demo mode
DEMO_MODE=true python services/orchestrator/main.py

# All actions return: {"status": "simulated", "demo_mode": true}
```

---

## Graceful Degradation

### Agent Down Test

```bash
# Kill agent service
kill $(lsof -t -i:8002)

# Emit event
curl -X POST http://localhost:8001/emit \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "app_crash",
    "app": "web-api",
    "env": "prod",
    "metadata": {"state": "critical"}
  }'

# Expected: {"status": "degraded", "fallback": "noop"}
```

---

## Service Logs

All services log in **structured JSON format**:

**Runtime:**
```json
{
  "timestamp": "2026-02-11T13:00:00Z",
  "service": "runtime",
  "event": "event_emitted",
  "event_id": "evt_123",
  "app": "web-api"
}
```

**Agent:**
```json
{
  "timestamp": "2026-02-11T13:00:01Z",
  "service": "agent",
  "event": "decision_made",
  "decision": "restart",
  "rl_engine": "rityadani"
}
```

**Orchestrator:**
```json
{
  "timestamp": "2026-02-11T13:00:05Z",
  "service": "orchestrator",
  "event": "action_executed",
  "action": "restart",
  "execution_id": "exec_789"
}
```

---

## Troub shooting

### Services Won't Start

```bash
# Check if ports are in use
netstat -ano | findstr :8001
netstat -ano | findstr :8002
netstat -ano | findstr :8003

# Kill processes if needed
taskkill /PID <PID> /F
```

### Timeout Errors

Default timeout is 5 seconds. Adjust in Runtime Service:
```python
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))
```

---

## Success Criteria

- [✅] All services start without errors
- [✅] Health checks return {"status": "healthy"}
- [✅] Agent returns decisions (no import errors)
- [✅] Orchestrator executes/rejects actions
- [✅] Full chain: Runtime → Agent → Orchestrator works
- [✅] No cross-imports between services
- [✅] NOOP on invalid input
- [✅] Action scopes enforced
- [✅] Graceful degradation when service down

---

**Status:** READY FOR VALIDATION
