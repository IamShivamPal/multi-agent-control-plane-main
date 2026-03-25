# Review Packet: Multi-Agent Control Plane (Pravah)

Date: 2026-03-19
Documentation refresh: 2026-03-19

## 1) Executive Summary

This repository contains a mature, multi-module autonomous control-plane platform that combines:
- A runtime agent loop for autonomous decisions and guarded action execution.
- A multi-app control plane for app registry, timeline history, health overview, and manual freeze overrides.
- A FastAPI decision-brain/dashboard backend with live monitoring payloads and integration hooks.
- A Next.js dashboard frontend for real-time telemetry, orchestration visibility, and decision testing.

The implementation is feature-rich and production-oriented in several areas (validation, rate limiting, governance gates, proof logging), but there are architectural transitions and duplicate/legacy paths that create ambiguity (Flask vs FastAPI ownership, mixed path/layout assumptions, and older orchestration/test code quality issues).

## 2) System Topology (As Implemented)

### Runtime and Control Plane
- Agent runtime entrypoint: `agent_runtime.py` (`AgentRuntime` class).
- Canonical runtime loop: sense -> validate -> decide -> enforce -> act -> observe -> explain.
- Canonical runtime payload contract: `runtime_payload_schema.json`.
- Control-plane aggregation and per-app history: `control_plane/multi_app_control_plane.py`.
- Manual override/freeze state: `control_plane/app_override_manager.py`.
- Guarded execution gate: `control_plane/core/rl_orchestrator_safe.py`.
- Governance policy layer: `control_plane/core/action_governance.py`.

### API Surfaces
- Flask API adapter (control-plane endpoints + runtime submit): `control_plane/api/agent_api.py`.
- FastAPI decision-brain backend (dashboard + RL decision endpoints + integration): `control_plane/backend/app/main.py`.

### Frontend
- Next.js dashboard shell and live monitoring page: `dashboard/frontend/app/page.tsx`.
- Decision-brain page for decision simulation/testing: `dashboard/frontend/app/decision-brain/page.tsx`.
- Frontend API client: `dashboard/frontend/services/api.ts`.

## 3) Component Review

### A) Agent Runtime Core
Primary file: `agent_runtime.py`

Implemented responsibilities:
- Initializes agent identity, memory, state manager, perception adapters, event bus, and safety/governance modules.
- Supports Redis event bus with fallback to local in-process bus.
- Runs a synchronized loop with lock protection and graceful shutdown signals.
- Stores/logs agent lifecycle, heartbeats, and autonomous operations.

Working model:
1. Collects observation (manual or sensed).
2. Validates observation.
3. Obtains RL and/or rule-based action inputs.
4. Arbitrates decisions.
5. Applies self-restraint + governance checks.
6. Routes action through safe executor.
7. Logs outcome + proof artifacts.

Notable strengths:
- Structured lifecycle and state-machine intent.
- Explicit production logging hook for prod env.
- Thread-safe loop lock and shutdown handling.

### B) Governance and Safety Gates
Primary files:
- `control_plane/core/action_governance.py`
- `control_plane/core/rl_orchestrator_safe.py`

Implemented controls:
- Action eligibility per environment.
- Cooldowns by action type.
- Repetition suppression windows.
- Prerequisite checks (for app presence/rollback conditions).
- Manual per-app freeze override enforcement.
- Emergency global freeze enforcement.
- Illegal action rejection.
- Demo-mode intake/safety gates and proof events.

Working model:
- Requested action is evaluated through sequential safety gates.
- On refusal, returns structured noop/refusal payload with reason and reason_code.
- On allow, executes mapped action adapter and logs to orchestrator decision logs.

Observation:
- Safety model is layered and auditable; this is one of the strongest parts of the codebase.

### C) Multi-App Control Plane
Primary file: `control_plane/multi_app_control_plane.py`

Implemented features:
- App discovery via registry JSON specs.
- Decision history append/read with timestamped JSONL.
- Per-app history retrieval with limit bounds.
- Health overview composition (latest action/reason/status/freeze flags).
- Manual freeze set/clear delegation.

Working model:
- Registry + decision logs are combined into dashboard-friendly app summaries.

### D) FastAPI Decision-Brain Backend
Primary file: `control_plane/backend/app/main.py`

Implemented endpoint groups:
- Health and policy scope: `/health`, `/action-scope`, `/decision-summary`.
- Decision APIs: `/decision`, `/recent-activity`, `/decision-with-control-plane`.
- Dashboard APIs: `/`, `/live-dashboard`, `/dashboard/state`.
- Link monitoring APIs: `/ingest-link`, `/remove-link`.
- Integration metrics: `/control-plane/status`, `/control-plane/apps`, `/orchestration/metrics`.
- Autonomous loop visibility: `/autonomous-status`, runtime-cycle test routes.

Working model:
- Uses deterministic `DecisionEngine` for action selection based on thresholds and environment action scope.
- Maintains in-memory recent activity and monitored links state.
- Builds comprehensive live dashboard payloads combining telemetry, synthetic/derived metrics, and control-plane integration details.
- Starts autonomous background loop on startup.

### E) Flask Control-Plane API
Primary file: `control_plane/api/agent_api.py`

Implemented features:
- Canonical runtime event intake endpoint (`/api/runtime`) with schema + hard input validation.
- Rate-limited control-plane and health/status endpoints.
- Shared `AgentRuntime` singleton + background runtime loop.
- Control-plane app listing/health/history/override endpoints.

Working model:
- Translates canonical runtime payload into internal event envelope.
- Delegates execution path to `AgentRuntime`.

### F) Frontend Dashboard and Decision UI
Primary files:
- `dashboard/frontend/app/page.tsx`
- `dashboard/frontend/app/decision-brain/page.tsx`
- `dashboard/frontend/services/api.ts`

Implemented features:
- Auto-refreshing live dashboard.
- Link ingestion/removal UI for monitored repos/sites.
- Integration metrics cards for RL brain + control plane.
- System health, performance, policy evolution, and event timeline rendering.
- Decision test form (environment/event/cpu/memory) with recent decision history.
- Fallback behavior for decision endpoint path variants.

Working model:
- Polls backend periodically for live payloads and status.
- Uses typed API client models to normalize response handling.

### G) Security Modules
Primary files:
- `security/signing.py`
- `security/nonce_store.py`
- `security/auth.py`
- `security/test_security.py`

Implemented features:
- HMAC payload signing and signature verification.
- Nonce replay protection with TTL and file-backed persistence.
- JWT token generation/verification helper.
- Script-style security validation flows.

### H) Monitoring and Orchestration Utilities
Primary files:
- `monitoring/runtime_poller.py`
- `monitoring/runtime_observer.py`
- `orchestrator/app_orchestrator.py`
- `orchestrator/test_orchestrator.py`

Implemented features:
- HTTP health polling + runtime payload construction.
- Runtime telemetry reading from telemetry JSON source.
- Deploy/scale/stop orchestration with state file tracking.
- Workflow simulation script for orchestrator lifecycle.

## 4) Implemented Tasks and Milestones (Evidence-Based)

### Day/Milestone Signals in Repo
- README states Day 1-7 completion and production-ready status.
- Architecture docs describe Day 5-7 multi-tenant and Day 6 hardening layers.
- RL/day scripts and demo artifacts include Day 1-3 verification paths.
- Proof logger includes governance/day2 event taxonomy.

### Task Patterns Observed as Implemented
1. Runtime contract freezing and validation gates.
2. Deterministic decision behavior with environment-scoped action constraints.
3. Closed-loop orchestration path with refusal semantics.
4. Production hardening elements:
   - Input validation module
   - Resilience patterns (retry/timeouts/circuit breaker)
   - Rate limiting in Flask API
5. Multi-app control-plane operations:
   - App registry discovery
   - Decision history per app
   - Manual freeze overrides
6. FastAPI dashboard integration with control-plane bridge metrics.
7. Frontend dashboard and decision-brain operational UI.

## 5) End-to-End Feature Working (How Features Operate)

### Runtime Decision Intake (Flask path)
1. Client posts canonical runtime payload.
2. Payload validated (schema + hard validator).
3. Payload transformed to internal event envelope.
4. Agent runtime executes decision loop.
5. Governance and safe orchestrator gate action.
6. Result + logs + proof emitted.

### Decision-Brain Dashboard Flow (FastAPI path)
1. Frontend calls live dashboard and status endpoints.
2. Backend composes live payload from:
   - in-memory decision/link state
   - runtime metrics files
   - integration bridge metrics
3. Frontend renders cards, lists, timelines, and control-plane sections.

### Link Monitoring Flow
1. User ingests repository/site URL.
2. Backend stores link and generates deterministic metadata profile.
3. Dashboard aggregates multi-link metrics into telemetry and summary cards.
4. User can remove links and see live dashboard updates.

### Manual Freeze Override Flow
1. Client posts override action to control-plane endpoint.
2. Override manager writes freeze state with expiry.
3. Safe orchestrator checks override before action execution.
4. Non-noop actions are refused when freeze is active.

## 6) API and Interface Coverage

### FastAPI (Decision Brain)
- Health/status, decisioning, dashboard, orchestration metrics, link ingest/remove, autonomous status.

### Flask (Control Plane)
- Runtime intake, runtime status/health, control-plane app list/health/history/override.

### Contracts
- Canonical payload schema file and associated markdown contract.

## 7) Deployment and Operations Review

Artifacts present:
- `render.yaml` for FastAPI deployment on Render.
- `docker-compose.yml` with multi-service stack (dashboard/agents/redis/workers/monitors).
- `control_plane/backend/run.py` for uvicorn startup.
- Requirements files for different install contexts.

Operational note:
- The docker-compose stack appears oriented to older Streamlit/agent services and may not fully reflect the newer FastAPI + Next.js topology described in docs.

## 8) Testing and Validation Coverage

Observed test/validation scripts:
- Security tests (`security/test_security.py`).
- Orchestrator workflow script test (`orchestrator/test_orchestrator.py`).
- Environment validator (`validate_env.py`).
- Demo lock validator (`validate_demo_lock.py`).
- Integration sample modules under `tests/integration`.

Current state:
- There are validation and scenario scripts, but limited conventional unit-test structure in the scanned paths.
- Some test files are script-style and contain quality issues (see risks).

## 9) Risks, Gaps, and Inconsistencies

1. Backend ownership ambiguity:
- Docs conflict between FastAPI-only guidance and Flask canonical API references.
- Both API stacks are implemented and active in code.

2. Path/layout coupling:
- Some modules contain legacy path fallback logic and mixed import assumptions.

3. Governance state persistence bug risk:
- `SafeOrchestrator` creates a fresh `ActionGovernance` object per call, which may reset cooldown/repetition history each execution rather than preserving across runtime lifetime.

4. Environment naming drift:
- Some places use `stage`, others `staging`; mappings exist but inconsistencies persist across modules/docs.

5. Test/orchestrator script quality:
- `orchestrator/test_orchestrator.py` contains malformed references (`fos.path.join`) and appears non-production-grade.

6. Frontend duplicated API client definitions:
- There are multiple API client files (`dashboard/frontend/services/api.ts` and `dashboard/frontend/lib/api.ts`) with slightly different fallback behavior.

7. Runtime observer simplification:
- `monitoring/runtime_observer.py` currently reads a telemetry file and prints state; older richer psutil logic is commented out.

8. Docker/runtime mismatch:
- Compose services reference streamlit and legacy paths, while current docs emphasize FastAPI + Next.js topology.

## 10) Suggested Consolidation Actions

1. Define single canonical backend entry and mark the other as adapter-only in code and docs.
2. Persist governance state across action executions (inject shared `ActionGovernance` instance).
3. Unify env naming (`stage` vs `staging`) at contract boundaries.
4. Remove or archive deprecated/legacy launcher paths and duplicate API clients.
5. Repair script-level test quality issues and add true pytest suites around:
   - governance cooldown/repetition behavior
   - override/freeze refusal path
   - runtime contract validation
   - FastAPI and Flask compatibility expectations (if both retained)
6. Align docker-compose with current runtime architecture.

## 11) Overall Assessment

Project maturity: High feature breadth, medium architectural coherence.

What is clearly strong:
- Safety/governance layering and refusal semantics.
- Runtime contract formalization and payload validation intent.
- Multi-app control-plane observability and override controls.
- Rich dashboard payload and UI coverage.

What should be prioritized next:
- Architectural convergence (single source of runtime/API truth).
- Reliability hardening in stateful governance behavior.
- Cleanup of legacy/test quality debt.

---

Review Packet prepared by repository implementation scan across architecture docs, runtime/control-plane/backend/frontend/security/monitoring modules, and task milestone artifacts.
