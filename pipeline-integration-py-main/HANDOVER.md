# HANDOVER.md - Pravah Decision Brain Integration

## Overview

Pravah is an autonomous infrastructure control system that combines deterministic rule-based decisions with reinforcement learning to manage multi-application deployments safely and efficiently.

This document describes the integrated decision brain that operates as the live intelligence layer of the Pravah control plane.

---

## Architecture

### Decision Pipeline (Canonical)

All decisions flow through a single canonical pipeline:

```
Runtime State (from Shivam Control Plane)
    ↓
[1] Payload Validation & Normalization
    ↓
[2] Decision Generation (Rule-based or RL-assisted)
    ↓
[3] Action Scope Enforcement
    ↓
[4] Orchestrator Communication
    ↓
[5] Decision Logging & Feedback Recording
```

### Core Components

#### 1. **Runtime Contract** (`runtime_contract.py`)
Defines the shared schema between control plane and decision engine.

**Key Classes:**
- `RuntimeState`: Current state of an application (CPU, memory, replicas, etc.)
- `RuntimeSignal`: Individual signal (CPU_HIGH, MEMORY_HIGH, etc.)
- `Decision`: Generated decision with action and confidence
- `DecisionFeedback`: Feedback from orchestrator execution

**Usage:**
```python
from runtime_contract import RuntimeState, RuntimeSignal, SignalType

state = RuntimeState(
    app_id="app-001",
    current_replicas=2,
    cpu_usage=0.85,
    memory_usage=0.5,
    error_rate=0.02,
    latency_p99=500,
    environment="prod",
    signals=[...]
)
```

#### 2. **Decision Engine** (`decision_engine.py`)
Core intelligence layer that processes runtime state and generates decisions.

**Key Methods:**
- `process_runtime_state(state)`: Main entry point - processes state through canonical pipeline
- `_generate_decision(state)`: Rule-based decision logic
- `_should_dampen_decision()`: False-positive dampening
- `record_feedback()`: Records learning feedback (DEV only)
- `get_decision_logs()`: Retrieves decision history

**Decision Rules:**
- CPU > 80% → SCALE_UP
- Memory > 85% → SCALE_UP
- Error Rate > 5% → RESTART
- P99 Latency > 1000ms → SCALE_UP
- Low resource usage → SCALE_DOWN

**Example:**
```python
from decision_engine import DecisionEngine

engine = DecisionEngine()
result = engine.process_runtime_state(runtime_state)

# result contains:
# - decision_id
# - action_emitted (after enforcement)
# - orchestrator_acknowledged
# - enforcement_log
```

#### 3. **Action Scope Enforcer** (`action_scope_enforcer.py`)
Validates decisions against environment-specific constraints.

**Enforcement Rules by Environment:**

| Environment | Max Replicas | Scale-up Rate Limit | Scale-down Rate Limit |
|-------------|--------------|-------------------|----------------------|
| dev         | 5            | 10/hour           | 10/hour              |
| staging     | 10           | 5/hour            | 5/hour               |
| prod        | 50           | 2/hour            | 1/hour               |

**Key Methods:**
- `enforce(decision, environment)`: Validates and potentially downgrades action to NOOP
- `_check_rate_limit()`: Enforces rate limits per action
- `get_enforcement_stats()`: Returns enforcement statistics

**Example:**
```python
from action_scope_enforcer import ActionScopeEnforcer

enforcer = ActionScopeEnforcer()
enforced_decision, log = enforcer.enforce(decision, "prod")

# log contains:
# - action_requested
# - action_allowed
# - action_emitted
# - reason
```

#### 4. **Orchestrator Client** (`orchestrator_client.py`)
Handles communication with the control plane orchestrator.

**Key Methods:**
- `send_decision(decision)`: Transmits decision to orchestrator
- `get_acknowledgement(decision_id)`: Retrieves orchestrator acknowledgement
- `register_callback()`: Registers callbacks for decision execution

**Example:**
```python
from orchestrator_client import OrchestratorClient

client = OrchestratorClient(orchestrator_endpoint="http://localhost:8080")
response = client.send_decision(decision.to_dict())

# response contains:
# - decision_id
# - orchestrator_acknowledged
# - ack_timestamp
```

#### 5. **Multi-App State Manager** (`multi_app_state.py`)
Isolates decision state and history per application.

**Key Methods:**
- `get_or_create_app_state(app_id)`: Creates isolated state for app
- `record_decision(app_id, decision)`: Records decision with memory cap
- `update_rl_state(app_id, state_update)`: Updates RL state
- `record_feedback(app_id, decision_id, feedback)`: Records execution feedback
- `cleanup_stale_apps()`: Garbage collection of old app states

**Memory Management:**
- Per-app decision history cap: 1000 decisions
- Stale app cleanup: 24 hours
- Automatic garbage collection when cap exceeded

**Example:**
```python
from multi_app_state import MultiAppStateManager

manager = MultiAppStateManager(memory_cap_per_app=1000)
manager.record_decision("app-001", decision)
stats = manager.get_app_stats("app-001")

# stats contains:
# - total_decisions
# - successful_decisions
# - failed_decisions
# - last_decision
```

---

## Decision Flow (Step-by-Step)

### 1. Runtime State Reception
```
Shivam Control Plane sends RuntimeState
↓
Decision Engine receives via process_runtime_state()
```

### 2. Payload Validation
```
Validate required fields:
- app_id
- current_replicas, desired_replicas
- cpu_usage, memory_usage
- error_rate, environment
```

### 3. Decision Generation
```
Apply rule-based logic:
- Check CPU, Memory, Error Rate, Latency
- Generate action with confidence score
- Decision Type: "rule_based" or "rl_assisted"
```

### 4. Action Scope Enforcement
```
Check environment constraints:
- Is action allowed in this environment?
- Is rate limit exceeded?
- If invalid → downgrade to NOOP
- Log enforcement decision
```

### 5. Orchestrator Communication
```
Send decision to orchestrator:
- Include decision_id, app_id, action
- Wait for acknowledgement
- Log orchestrator response
```

### 6. Decision Logging
```
Record complete decision cycle:
- action_requested vs action_emitted
- enforcement_log
- orchestrator_acknowledged
- timestamp
```

---

## Multi-Application Isolation

Each application maintains isolated state:

```
App-001: [Decision History] [RL State] [Stats]
App-002: [Decision History] [RL State] [Stats]
App-003: [Decision History] [RL State] [Stats]
```

**Guarantees:**
- Decisions for one app do NOT influence another app's state
- Memory is capped per app (1000 decisions)
- RL learning is per-app
- Stale apps are automatically cleaned up

**Verification:**
```python
# Each app has independent stats
stats_app1 = engine.get_app_stats("app-001")
stats_app2 = engine.get_app_stats("app-002")

# Decisions are isolated
history_app1 = engine.app_state_manager.get_decision_history("app-001")
history_app2 = engine.app_state_manager.get_decision_history("app-002")
```

---

## Safety Hardening

### 1. False-Positive Dampening
Prevents cascading actions from repeated failures:
- Minimum 60 seconds between same actions for same app
- Aggressive decisions are automatically dampened
- Logged when dampening occurs

### 2. Rate Limiting
Environment-specific rate limits prevent resource exhaustion:
- DEV: 10 scale-ups/hour
- STAGING: 5 scale-ups/hour
- PROD: 2 scale-ups/hour

### 3. Action Scope Enforcement
Illegal actions are automatically downgraded to NOOP:
- Invalid actions for environment
- Rate limits exceeded
- Resource constraints violated

### 4. Strict Signal Validation
Required vs optional signal validation:
- Required: app_id, environment, current state
- Optional: signals, metadata

---

## Feedback Loop (DEV Only)

Learning feedback is recorded for RL training:

```python
feedback = {
    'decision_id': 'uuid',
    'app_id': 'app-001',
    'action_executed': True,
    'execution_time': 2.5,
    'result_status': 'success',  # success, failed, partial
    'metrics_before': {'cpu': 0.85, 'replicas': 2},
    'metrics_after': {'cpu': 0.65, 'replicas': 3},
    'timestamp': time.time()
}

engine.record_feedback(decision_id, feedback)
```

**Feedback is used for:**
- RL model training (DEV only)
- Decision accuracy metrics
- False-positive detection
- Policy refinement

---

## Integration Testing

Run the integration test suite:

```bash
python integration_test.py
```

**Tests Included:**
1. Single app decision flow
2. Multi-app state isolation
3. Action scope enforcement
4. False-positive dampening
5. Environment constraints
6. Decision feedback loop

**Expected Output:**
- Decision logs showing complete pipeline
- Enforcement logs
- Orchestrator acknowledgements
- Multi-app isolation verification

---

## Logging

All components use Python logging with structured output:

```
2024-01-15 10:30:45 - decision_engine - INFO - === DECISION PIPELINE START for app-001 ===
2024-01-15 10:30:45 - decision_engine - INFO - Decision generated: scale_up (confidence: 0.9)
2024-01-15 10:30:45 - action_scope_enforcer - INFO - Action scale_up allowed for app-001 in prod
2024-01-15 10:30:45 - orchestrator_client - INFO - Decision sent to orchestrator: {...}
2024-01-15 10:30:45 - decision_engine - INFO - === DECISION PIPELINE END for app-001 ===
```

**Log Levels:**
- DEBUG: Detailed state information
- INFO: Decision pipeline events
- WARNING: Dampening, rate limits
- ERROR: Validation failures, orchestrator errors

---

## Extending the Decision Brain

### Adding New Decision Rules

Edit `decision_engine.py` `_generate_decision()` method:

```python
# Rule 6: Custom metric
elif state.custom_metric > threshold:
    action = ActionType.CUSTOM_ACTION.value
    reason = f"Custom metric high: {state.custom_metric}"
    confidence = 0.8
```

### Adding RL-Assisted Decisions

Replace rule-based logic with RL model:

```python
def _generate_decision(self, state: RuntimeState) -> Decision:
    # Use RL model instead of rules
    rl_state = self.app_state_manager.get_rl_state(state.app_id)
    action, confidence = self.rl_model.predict(state, rl_state)
    decision_type = "rl_assisted"
    # ... rest of decision creation
```

### Adding New Enforcement Rules

Edit `action_scope_enforcer.py`:

```python
self.action_limits = {
    'prod': {
        'custom_action': {'rate_limit_per_hour': 5}
    }
}
```

---

## Deployment Checklist

- [ ] All components imported correctly
- [ ] Orchestrator endpoint configured
- [ ] Logging configured for your environment
- [ ] Memory caps set appropriately
- [ ] Rate limits match your infrastructure
- [ ] Integration tests passing
- [ ] Decision logs being recorded
- [ ] Feedback loop enabled (DEV only)

---

## Troubleshooting

### Decisions not being sent to orchestrator
- Check orchestrator endpoint configuration
- Verify network connectivity
- Check orchestrator logs for errors

### Actions being downgraded to NOOP
- Check rate limits in action_scope_enforcer
- Verify environment setting
- Review enforcement logs

### Memory usage growing
- Check memory_cap_per_app setting
- Verify cleanup_stale_apps() is running
- Monitor decision_history size

### False positives
- Increase dampening threshold (currently 60s)
- Adjust rule thresholds
- Review decision confidence scores

---

## Contact & Support

For questions about the decision brain architecture, refer to:
- Decision pipeline: `decision_engine.py`
- Action enforcement: `action_scope_enforcer.py`
- Multi-app isolation: `multi_app_state.py`
- Runtime contract: `runtime_contract.py`

---

**Last Updated:** 2024-01-15
**Version:** 1.0
**Status:** Production Ready
