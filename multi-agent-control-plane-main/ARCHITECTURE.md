# Canonical Architecture Blueprint

## Objective

This document is the single source of truth for system architecture and removes fragmented interpretations.

Canonical rules:

1. **One entry point** for autonomous control-plane execution.
2. **One runtime contract** for Runtime → RL decision input.
3. **One decision flow** for all autonomous actions.

---

## Final System Diagram

```mermaid
flowchart TD
    A[External Trigger\nAPI / Event Bus / Manual Signal] --> B[AgentRuntime\nagent_runtime.py]
    B --> C[Perception Layer\ncollect + shape observation]
    C --> D[Validation Gate\nruntime contract check]
    D --> E[RuntimeRLPipe\ncore/runtime_rl_pipe.py]
    E --> F[RL Decision Brain\n(remote/local client)]
    F --> G[Decision Arbitrator\ncore/decision_arbitrator.py]
    G --> H[Enforcement Gate\nself-restraint + governance]
    H --> I[Safe Orchestrator\ncore/rl_orchestrator_safe.py]
    I --> J[Action Adapter\nrestart / scale / noop / rollback]
    J --> K[System State + Metrics]
    K --> L[Observe + Explain + Proof Logs]
    L --> B

    M[(runtime_payload_schema.json)] -. frozen contract .-> D
    N[(proof logs / telemetry)] -. auditability .-> L
```

---

## One Entry Point

### Canonical Entry

- **Runtime entry point:** `agent_runtime.py`
- **Owning class:** `AgentRuntime`
- **Canonical loop:** `sense -> validate -> decide -> enforce -> act -> observe -> explain`

### Entry-Point Policy

- Any CLI, API, scheduler, demo, or worker path must delegate execution to `AgentRuntime`.
- Wrapper files (for example HTTP servers such as `api/agent_api.py`, `app.py`, `wsgi.py`) are **transport adapters**, not independent runtime engines.
- Legacy or alternate launchers are allowed only if they call into the same `AgentRuntime` control loop.

---

## One Runtime Contract

### Canonical Contract File

- **File:** `runtime_payload_schema.json`
- **Status:** frozen
- **Mutation policy:** no field renaming, no silent defaulting, no implicit aliasing

### Required Payload

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

### Contract Rules

- Runtime emits this contract as-is to the RL decision path.
- Validation is fail-fast: invalid payloads are rejected, logged, and never executed.
- Additional data must be carried as out-of-band metadata; it must not break or reshape canonical fields.

---

## One Decision Flow

### Canonical Sequence (Authoritative)

1. **Sense**
   - `AgentRuntime` gathers observations from adapters/event sources.
2. **Validate**
   - Runtime payload is checked against the canonical contract.
   - Invalid payloads stop here with explicit refusal logging.
3. **Decide (RL + Rules)**
   - `RuntimeRLPipe` queries RL decision provider.
   - `DecisionArbitrator` resolves RL vs rule-based advice to one proposed action.
4. **Enforce**
   - Self-restraint and action governance apply confidence, cooldown, repetition, and eligibility gates.
5. **Execute**
   - `SafeOrchestrator.execute_action(...)` is the centralized execution gate.
   - Unsafe or disallowed actions are converted to explicit refusals/noop with reasons.
6. **Observe + Explain**
   - Results are observed, persisted, and written to proof logs.
   - System state/memory is updated for the next cycle.

### Invariants

- Every executed action has one validated input payload.
- Every refused action has one explicit reason.
- Every cycle produces auditable artifacts (decision source, enforcement result, execution status).

---

## Canonical Component Boundaries

### Core Runtime Components
- `agent_runtime.py`: lifecycle and loop ownership.
- `core/runtime_rl_pipe.py`: Runtime → RL decision query.
- `core/decision_arbitrator.py`: single final action proposal.
- `core/action_governance.py`: eligibility/cooldown/repetition policy.
- `core/rl_orchestrator_safe.py`: centralized execution gate.
- `runtime_payload_schema.json`: immutable Runtime → RL contract.

### Production Hardening Components (Day 6)
- `core/input_validator.py`: Centralized input validation (type checking, bounds, enum constraints, regex validation).
- `core/resilience.py`: Production resilience patterns (timeout decorator, retry logic, circuit breaker, failure tracking).
- `core/prod_logging.py`: Production logging configuration (ProductionFormatter, JsonFormatter, vendor log suppression).

### Multi-Tenant Support Components (Day 5-7)
- `control_plane/multi_app_control_plane.py`: Multi-app orchestration and decision history.
- `core/app_registry.py`: Application registry and metadata management.
- `api/agent_api.py`: Extended API with rate limiting and multi-app endpoints.

No other module may redefine these core responsibilities.

---

## Production Hardening Layer (Day 6)

### Rate Limiting
- **Library:** flask-limiter v4.1.1
- **Per-Endpoint Limits:**
  - `/api/health`: 100 req/min
  - `/api/status`: 60 req/min
  - `/api/runtime`: 30 req/min (highest resource cost)
  - `/api/control-plane/*`: 40 req/min each
- **Protection:** DoS prevention, resource consumption control

### Input Validation
- **Module:** `core/input_validator.py`
- **Validation Rules:**
  - Type checking (enum, string, integer constraints)
  - Bounds validation (latency_ms < 60000, workers < 10000, errors < 1000)
  - String length limits (app_name < 100 chars, reason < 500 chars)
  - Regex pattern matching
  - Array size bounds
- **Policy:** "Fail fast, fail loudly" - reject invalid inputs before core logic

### Timeout & Failure Escalation
- **Module:** `core/resilience.py`
- **Patterns Implemented:**
  - `@timeout(seconds)` decorator - graceful timeout with warning logging
  - `@retry(max_attempts, backoff_factor)` - exponential backoff retry logic
  - `CircuitBreaker` - 3-state pattern (CLOSED → OPEN → HALF_OPEN)
  - `FailureTracker` - per-operation failure accumulation and escalation detection
- **Usage:** External API calls, third-party integrations

### Production Logging
- **Module:** `core/prod_logging.py`
- **Features:**
  - ProductionFormatter - minimal output, no debug spam
  - JsonFormatter - structured logging for observability
  - Automatic suppression of verbose third-party loggers (urllib3, redis, flask, werkzeug)
  - Environment-aware configuration (INFO in prod, DEBUG in dev)
- **Integration:** Auto-initialized in `agent_runtime.__init__()` when env="prod"

### Determinism Assurance
- **Module:** `testing/test_determinism.py`
- **Test Suites:**
  1. Deterministic decisions (identical input → identical output)
  2. Governance consistency (rules applied uniformly)
  3. State isolation (no leakage between app decisions)
  4. Environment gating (autonomy levels enforced)
- **Guarantee:** Reproducible execution across runs

## Multi-Tenant Architecture (Day 5-7)

### Multi-App Control Plane
- **Capacity:** 30+ applications simultaneously
- **Per-App Features:**
  - Decision history with audit trail
  - Manual freeze override with time-based expiry
  - Real-time health status
  - Isolated governance state
- **Endpoints:**
  - `GET /api/control-plane/apps` - list all registered apps
  - `GET /api/control-plane/health` - multi-app health overview
  - `GET /api/control-plane/history/<app_name>` - per-app decision history
  - `POST /api/control-plane/override` - manual freeze enforcement

### Environment-Based Autonomy Levels
| Environment | Badge | Autonomy Level | Eligible Actions |
|-------------|-------|----------------|-----------------|
| dev | 🟢 | FULL | restart, scale_up, scale_down, noop |
| staging | 🟡 | DECISIONS | restart, noop only |
| prod | 🧊 | FROZEN | restart, noop only |
| prod-emergency | 🔴 | EMERGENCY | noop only |

### Governance Constraints
- **Cooldown Periods:**
  - Restart: 60 seconds
  - Scale-up: 120 seconds
  - Scale-down: 120 seconds
  - Rollback: 300 seconds
- **Production Rules:**
  - ✅ Restart allowed (recovery action)
  - ✅ Noop allowed (safe default)
  - ❌ Scale-up BLOCKED (requires manual approval)
  - ❌ Scale-down BLOCKED (requires manual approval)
- **Proof Logging:** Every decision logged to `logs/prod/orchestrator_decisions.jsonl`

## Fragmentation Elimination Checklist

- [x] One runtime entry point defined.
- [x] One runtime contract defined and frozen.
- [x] One decision flow defined end-to-end.
- [x] Wrapper/adapters explicitly separated from runtime core.
- [x] Execution gate centralized.
- [x] Production hardening layer implemented (rate limiting, validation, resilience, logging).
- [x] Multi-tenant support with per-app isolation.
- [x] Environment-based autonomy enforcement.
- [x] Governance constraints verified and tested.
