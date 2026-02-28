# Input Schema Definitions

## Agent Service - POST /decide

### Required Fields

| Field | Type | Valid Values | Description |
|-------|------|--------------|-------------|
| event_type | string | non-empty | Type of runtime event |
| app | string | non-empty | Application name |
| env | string | "dev", "stage", "prod" | Environment |
| state | string | "healthy", "degraded", "critical", "unknown" | Application state |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| metrics | object/dict | Metrics dictionary (error_count, latency_ms, etc.) |

### Valid Request Example

```json
{
  "event_type": "app_crash",
  "app": "web-api",
  "env": "prod",
  "state": "critical",
  "metrics": {
    "error_count": 15,
    "latency_ms": 3000
  }
}
```

### Response Schema

**Success Response:**
```json
{
  "decision": "restart",
  "reason": "state_critical",
  "confidence": 0.9,
  "metadata": {
    "timestamp": "2026-02-11T10:00:00Z",
    "agent_version": "1.0.0-rityadani-rl",
    "rule_matched": "critical_state",
    "rl_engine": "rityadani"
  }
}
```

**Validation Error Response:**
```json
{
  "decision": "noop",
  "reason": "invalid_input",
  "confidence": 0.0,
  "metadata": {
    "timestamp": "2026-02-11T10:00:00Z",
    "agent_version": "1.0.0",
    "validation_errors": ["missing: env"]
  }
}
```

---

## Orchestrator Service - POST /execute

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| action | string | Action to execute (restart, scale_up, etc.) |
| app | string | Application name |
| env | string | Environment (dev/stage/prod) |
| requested_by | string | Who requested the action |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| decision_metadata | object | Metadata from agent decision |

### Valid Request Example

```json
{
  "action": "restart",
  "app": "web-api",
  "env": "prod",
  "requested_by": "agent",
  "decision_metadata": {
    "confidence": 0.9,
    "reason": "state_critical"
  }
}
```

### Response Schema

**Success Response:**
```json
{
  "status": "executed",
  "action": "restart",
  "app": "web-api",
  "env": "prod",
  "execution_id": "exec_a1b2c3d4",
  "demo_mode": false,
  "timestamp": "2026-02-11T10:00:05Z"
}
```

**Validation Error Response:**
```json
{
  "status": "rejected",
  "reason": "missing_required_field_action",
  "action": "unknown",
  "app": "web-api",
  "env": "prod",
  "execution_id": "err_x9y8z7w6",
  "demo_mode": false,
  "timestamp": "2026-02-11T10:00:05Z"
}
```

---

## Validation Rules

### All Services

1. **Reject Empty Payloads**
   - `{}` → Error response
   - No JSON body → Error response

2. **Reject Missing Required Fields**
   - Missing any required field → Error response
   - Reason includes field name

3. **Reject Wrong Data Types**
   - String field with number → Error response
   - Dict field with string → Error response

4. **Reject Malformed JSON**
   - `{"invalid json` → Error response
   - Invalid JSON syntax → Error response

5. **Reject Empty Strings**
   - `"app": ""` → Error response
   - Whitespace-only strings → Error response

6. **Reject Invalid Enum Values**
   - env not in [dev, stage, prod] → Error response
   - state not in valid states → Error response

---

## HTTP Status Codes

| Scenario | Status Code | Guaranteed |
|----------|-------------|------------|
| Valid request | 200 OK | ✅ |
| Validation error | 200 OK | ✅ |
| Malformed JSON | 200 OK | ✅ |
| Missing fields | 200 OK | ✅ |
| Wrong data types | 200 OK | ✅ |
| Internal server error | **NEVER 500** | ✅ |

**Critical:** Services **NEVER** return HTTP 500, even on unexpected errors.

---

## Error Response Formats

### Agent Service

All validation errors return:
```json
{
  "decision": "noop",
  "reason": "<error_reason>",
  "confidence": 0.0,
  "metadata": {
    "timestamp": "...",
    "agent_version": "...",
    "validation_errors": [...]  // Optional
  }
}
```

**Reason Values:**
- `malformed_json` - Invalid JSON syntax
- `invalid_input_empty_payload` - Empty payload
- `invalid_input_missing_required_field_<field>` - Missing field
- `invalid_env` - Invalid environment value
- `invalid_state` - Invalid state value
- `invalid_app` - Invalid app (empty or wrong type)
- `invalid_event_type` - Invalid event_type
- `invalid_metrics_type` - Metrics not a dict
- `internal_error` - Unexpected error

### Orchestrator Service

All validation errors return:
```json
{
  "status": "rejected",
  "reason": "<error_reason>",
  "action": "...",
  "app": "...",
  "env": "...",
  "execution_id": "err_...",
  "demo_mode": false,
  "timestamp": "..."
}
```

**Reason Values:**
- `malformed_json` - Invalid JSON syntax
- `invalid_json` - JSON parsing error
- `empty_payload` - Empty payload
- `missing_required_field_<field>` - Missing field
- `action_must_be_non_empty_string` - Invalid action
- `app_must_be_non_empty_string` - Invalid app
- `env_must_be_non_empty_string` - Invalid env
- `action_out_of_scope` - Action not allowed in environment

---

## Logging

### Validation Success

```json
{
  "timestamp": "2026-02-11T10:00:00Z",
  "service": "agent",
  "event": "decision_request_received",
  "app": "web-api",
  "env": "prod",
  "state": "critical",
  "level": "INFO"
}
```

### Validation Failure

```json
{
  "timestamp": "2026-02-11T10:00:00Z",
  "service": "agent",
  "event": "input_validation_failed",
  "reason": "invalid_input_missing_required_field_env",
  "level": "WARNING"
}
```

### Malformed JSON

```json
{
  "timestamp": "2026-02-11T10:00:00Z",
  "service": "agent",
  "event": "malformed_json",
  "error": "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)",
  "level": "WARNING"
}
```

---

## Testing Commands

### Test Malformed JSON

```bash
# Agent
curl -X POST http://localhost:8002/decide \
  -H "Content-Type: application/json" \
  -d '{"invalid json'

# Orchestrator
curl -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{"malformed'
```

### Test Empty Payload

```bash
# Agent
curl -X POST http://localhost:8002/decide \
  -H "Content-Type: application/json" \
  -d '{}'

# Orchestrator
curl -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Test Missing Field

```bash
# Agent (missing env)
curl -X POST http://localhost:8002/decide \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "test",
    "app": "web-api",
    "state": "healthy"
  }'

# Orchestrator (missing action)
curl -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{
    "app": "web-api",
    "env": "prod",
    "requested_by": "test"
  }'
```

### Test Wrong Data Type

```bash
# Agent (env as number)
curl -X POST http://localhost:8002/decide \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "test",
    "app": "web-api",
    "env": 123,
    "state": "healthy"
  }'
```

### Run Full Test Suite

```bash
cd antigravity/tests
python test_json_validation.py
```

---

**Status:** All services hardened with strict JSON validation  
**Guarantee:** No HTTP 500 errors, ever  
**Validation:** 14 test cases across 2 services
