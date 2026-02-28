# Pravah Production API Reference (v1.0.0)

**Last Updated:** February 20, 2026  
**Environment:** Production Ready  
**Version:** 1.0.0 Final Release

---

## Overview

Pravah exposes a **canonical 7-endpoint API** with production-grade hardening:
- Rate limiting (per-endpoint, memory-backed)
- Input validation (strict type/bounds checking)
- Resilience patterns (timeout, retry, circuit breaker)
- Production logging (structured, vendor-suppressed)
- Multi-app control plane support (30+ apps simultaneously)

**Base URL:** `http://localhost:5000` (configurable)

---

## Core Decision Endpoints

### 1. POST /api/runtime
**Emit a runtime event and trigger autonomous decision → execution chain.**

- **Rate Limit:** 30 req/min
- **Required Field:** `app_name` (validated app from registry)

#### Request

```json
{
  "app": "payment-service",
  "env": "prod",
  "state": "crashed",
  "latency_ms": 1200,
  "errors_last_min": 15,
  "workers": 3
}
```

**Field Validation:**
- `app`: String, 1-100 chars, alphanumeric + dash/underscore
- `env`: Enum: `dev`, `staging`, `prod`
- `state`: Enum: `running`, `crashed`, `degraded`, `starting`, `stopped`
- `latency_ms`: Integer, 0-60000
- `errors_last_min`: Integer, 0-1000
- `workers`: Integer, 0-10000

#### Response (Success)

```json
{
  "status": "processed",
  "event_id": "runtime-1708363800.1234",
  "autonomy_level": "frozen",
  "agent_decision": {
    "action": "restart",
    "reason": "crash_detected_in_prod",
    "confidence": 0.95,
    "metadata": {
      "timestamp": "2026-02-20T14:30:00Z",
      "governance_check": "passed",
      "cooldown_remaining": 0
    }
  },
  "orchestrator_result": {
    "status": "executed",
    "action": "restart",
    "execution_id": "exec_abc123",
    "proof_logged": true
  }
}
```

#### Response (Validation Error)

```json
{
  "status": "invalid",
  "event_id": null,
  "error": "ValidationError: app must be 1-100 characters",
  "details": {
    "field": "app",
    "constraint": "length",
    "message": "expected max 100 chars, got 150"
  }
}
```

#### Response (Governance Block)

```json
{
  "status": "blocked_by_governance",
  "event_id": "runtime-1708363800.5678",
  "reason": "restart_cooldown_active",
  "cooldown_remaining_seconds": 45,
  "hint": "Please wait 45 seconds before next restart"
}
```

---

### 2. GET /api/status
**Get current agent and control plane status.**

- **Rate Limit:** 60 req/min
- **Query Parameters:** None required

#### Response

```json
{
  "agent_status": "healthy",
  "autonomy_level": "frozen",
  "environment": "prod",
  "uptime_seconds": 86400,
  "decisions_made": 1247,
  "last_decision": "2026-02-20T14:29:30Z",
  "infrastructure": {
    "runtime_healthy": true,
    "decision_arbitrator_healthy": true,
    "orchestrator_healthy": true,
    "database_connection": "active"
  },
  "multi_app_stats": {
    "total_apps": 28,
    "apps_healthy": 26,
    "apps_degraded": 2,
    "apps_frozen": 1
  }
}
```

---

### 3. GET /api/health
**Simple health check for load balancers and monitoring.**

- **Rate Limit:** 100 req/min
- **HTTP Status:** 200 OK (healthy) or 503 (unhealthy)

#### Response (Healthy)

```json
{
  "status": "OK",
  "timestamp": "2026-02-20T14:30:00Z"
}
```

---

## Multi-App Control Plane Endpoints

### 4. GET /api/control-plane/apps
**List all registered applications with health status.**

- **Rate Limit:** 40 req/min
- **Query Parameters:**
  - `status_filter`: Optional - `healthy`, `degraded`, `critical` or `all` (default: `all`)
  - `limit`: Optional - max 200, default 100
  - `offset`: Optional - pagination, default 0

#### Response

```json
{
  "total_apps": 28,
  "returned": 10,
  "apps": [
    {
      "app_id": "payment-service",
      "environment": "prod",
      "status": "healthy",
      "autonomy_level": "frozen",
      "last_decision": "2026-02-20T14:25:00Z",
      "decision_count_24h": 42,
      "metrics": {
        "latency_ms": 250,
        "errors_last_min": 0,
        "workers": 4
      },
      "manual_freeze": {
        "active": false,
        "expires_at": null,
        "reason": null
      }
    },
    {
      "app_id": "auth-service",
      "environment": "staging",
      "status": "healthy",
      "autonomy_level": "decisions",
      "last_decision": "2026-02-20T14:28:00Z",
      "decision_count_24h": 156,
      "metrics": {
        "latency_ms": 450,
        "errors_last_min": 2,
        "workers": 2
      },
      "manual_freeze": {
        "active": true,
        "expires_at": "2026-02-20T15:30:00Z",
        "reason": "maintenance_window"
      }
    }
  ]
}
```

---

### 5. GET /api/control-plane/health
**Multi-app health overview with aggregated metrics.**

- **Rate Limit:** 40 req/min
- **Query Parameters:** None

#### Response

```json
{
  "timestamp": "2026-02-20T14:30:00Z",
  "overview": {
    "total_apps": 28,
    "healthy": 26,
    "degraded": 2,
    "critical": 0
  },
  "environment_summary": {
    "dev": {
      "apps": 5,
      "healthy": 5,
      "autonomy_level": "full"
    },
    "staging": {
      "apps": 8,
      "healthy": 7,
      "degraded": 1,
      "autonomy_level": "decisions"
    },
    "prod": {
      "apps": 15,
      "healthy": 14,
      "degraded": 1,
      "autonomy_level": "frozen"
    }
  },
  "decisions_24h": 3421,
  "avg_decision_latency_ms": 245
}
```

---

### 6. GET /api/control-plane/history/<app_name>
**Retrieve per-app decision history with full audit trail.**

- **Rate Limit:** 40 req/min
- **Path Parameters:**
  - `app_name`: String, validated against app registry
- **Query Parameters:**
  - `limit`: Integer, 1-200, default 50
  - `offset`: Integer, default 0
  - `filter_action`: Optional - `restart`, `scale_up`, `scale_down`, `noop` (default: all)
  - `filter_state`: Optional - `healthy`, `degraded`, `critical` (default: all)

#### Response

```json
{
  "app_name": "payment-service",
  "environment": "prod",
  "total_decisions": 1247,
  "returned": 5,
  "history": [
    {
      "decision_id": "dec_xyz789",
      "timestamp": "2026-02-20T14:29:30Z",
      "event_type": "crash",
      "action": "restart",
      "reason": "crash_detected",
      "confidence": 0.95,
      "app_state_before": {
        "state": "crashed",
        "latency_ms": 5000,
        "errors_last_min": 25,
        "workers": 0
      },
      "governance_checks": {
        "cooldown_check": "passed",
        "eligibility_check": "passed",
        "autonomy_level": "frozen",
        "action_allowed": true
      },
      "execution": {
        "status": "executed",
        "execution_id": "exec_abc123",
        "result": "success"
      },
      "proof_logged": true,
      "audit_trail": {
        "source": "autonomous_agent",
        "approval_required": false,
        "approved_by": null
      }
    },
    {
      "decision_id": "dec_xyz788",
      "timestamp": "2026-02-20T14:25:00Z",
      "event_type": "overload",
      "action": "noop",
      "reason": "scale_up_blocked_in_production",
      "confidence": 0.88,
      "app_state_before": {
        "state": "degraded",
        "latency_ms": 3200,
        "errors_last_min": 12,
        "workers": 4
      },
      "governance_checks": {
        "cooldown_check": "passed",
        "eligibility_check": "failed",
        "autonomy_level": "frozen",
        "action_allowed": false,
        "blocked_reason": "scale_up_not_eligible_in_prod"
      },
      "execution": {
        "status": "blocked",
        "execution_id": null,
        "result": "noop_applied_safely"
      },
      "proof_logged": true,
      "audit_trail": {
        "source": "autonomous_agent",
        "approval_required": true,
        "approved_by": null
      }
    }
  ]
}
```

#### Field Validation
- `app_name`: Must be registered in app registry
- `limit`: Integer, 1-200
- `offset`: Integer ≥ 0

---

### 7. POST /api/control-plane/override
**Apply manual control plane override (freeze/unfreeze app decisions).**

- **Rate Limit:** 40 req/min
- **Body Validation:** Strict field validation + string length constraints

#### Request

```json
{
  "app_name": "payment-service",
  "action": "set_freeze",
  "duration_minutes": 30,
  "reason": "scheduled_maintenance_window"
}
```

**Field Validation:**
- `app_name`: String, 1-100 chars, must be registered
- `action`: Enum: `set_freeze`, `unfreeze`
- `duration_minutes`: Integer, 1-1440 (1 min to 24 hours)
- `reason`: String, 1-500 chars (required for audit trail)

#### Response (Success)

```json
{
  "status": "applied",
  "app_name": "payment-service",
  "freeze_status": "active",
  "expires_at": "2026-02-20T15:00:00Z",
  "reason": "scheduled_maintenance_window",
  "applied_at": "2026-02-20T14:30:00Z",
  "message": "App manual override active for 30 minutes"
}
```

#### Response (Validation Error)

```json
{
  "status": "invalid",
  "error": "ValidationError: duration_minutes must be 1-1440",
  "details": {
    "field": "duration_minutes",
    "value": 2880,
    "constraint": "max 1440"
  }
}
```

#### Response (App Not Found)

```json
{
  "status": "not_found",
  "error": "App 'unknown-service' not found in registry",
  "available_apps": ["payment-service", "auth-service", "api-gateway"]
}
```

---

## Error Handling

### HTTP Status Codes

| Status | Meaning | Example |
|--------|---------|---------|
| 200 | Success | Valid decision, governance check passed |
| 400 | Bad Request | Invalid input, validation failure |
| 404 | Not Found | App not in registry |
| 429 | Rate Limited | Too many requests on this endpoint |
| 500 | Server Error | Unexpected runtime error |
| 503 | Service Down | Agent runtime unavailable |

### Error Response Format

```json
{
  "error": "ErrorType: descriptive message",
  "error_code": "VALIDATION_FAILED",
  "timestamp": "2026-02-20T14:30:00Z",
  "request_id": "req_abc123",
  "details": {
    "field": "app",
    "validation_rule": "length",
    "message": "must be 1-100 chars"
  }
}
```

### Graceful Degradation

- If agent is unavailable: Returns 503 with fallback suggestion
- If governance is down: Returns decision but marks as `unverified`
- If logging fails: Decision still processed, error logged separately
- No unhandled exceptions returned to client

---

## Rate Limiting Details

### Limits by Endpoint

| Endpoint | Limit | Purpose |
|----------|-------|---------|
| `/api/health` | 100 req/min | Load balancer health probes |
| `/api/status` | 60 req/min | Monitoring dashboards |
| `/api/runtime` | 30 req/min | Decision triggering (highest CPU cost) |
| `/api/control-plane/apps` | 40 req/min | App listing/monitoring |
| `/api/control-plane/health` | 40 req/min | Multi-app health queries |
| `/api/control-plane/history/<app>` | 40 req/min | Audit trail queries |
| `/api/control-plane/override` | 40 req/min | Manual override commands |

### Rate Limiting Headers

```
RateLimit-Limit: 30
RateLimit-Remaining: 28
RateLimit-Reset: 1708363860
```

### Rate Limit Exceeded Response

```json
{
  "error": "RateLimitError: too many requests",
  "status": 429,
  "retry_after_seconds": 45,
  "limit": 30,
  "window": "1 minute",
  "message": "Please wait 45 seconds before next request"
}
```

---

## Input Validation

### Global Validation Rules

**All Endpoints:**
1. Request must be valid JSON
2. Required fields must be present
3. String fields must be valid UTF-8
4. No null values in required fields
5. Enum fields must match allowed values
6. Numeric fields must be in valid range

### Type Constraints

| Type | Constraint | Example |
|------|-----------|---------|
| `app_name` | 1-100 chars, alphanumeric + dash/underscore | `payment-service`, `auth_svc` |
| `reason` | 0-500 chars, printable UTF-8 | `"maintenance window"` |
| `env` | One of: `dev`, `staging`, `prod` | `"prod"` |
| `state` | One of: `running`, `crashed`, `degraded`, `starting`, `stopped` | `"crashed"` |
| `latency_ms` | 0-60000 | `1200` |
| `errors_last_min` | 0-1000 | `15` |
| `workers` | 0-10000 | `4` |
| `duration_minutes` | 1-1440 | `30` |

### Validation Failure Response

```json
{
  "status": "invalid",
  "error": "ValidationError: field validation failed",
  "failures": [
    {
      "field": "errors_last_min",
      "rule": "max_value",
      "expected": 1000,
      "got": 5000,
      "message": "must be <= 1000"
    }
  ]
}
```

---

## Production Logging

All requests logged to `logs/prod/api_requests.jsonl`:

```json
{
  "timestamp": "2026-02-20T14:30:00Z",
  "request_id": "req_abc123",
  "method": "POST",
  "endpoint": "/api/runtime",
  "client_ip": "192.168.1.100",
  "status_code": 200,
  "latency_ms": 245,
  "app_name": "payment-service",
  "rate_limit_remaining": 28,
  "auth_status": "none",
  "user_agent": "python-requests/2.28.0"
}
```

---

## Examples

### Python Example: Trigger Decision

```python
import requests
import json

url = "http://localhost:5000/api/runtime"
headers = {"Content-Type": "application/json"}

payload = {
    "app": "payment-service",
    "env": "prod",
    "state": "crashed",
    "latency_ms": 5000,
    "errors_last_min": 25,
    "workers": 0
}

response = requests.post(url, json=payload, headers=headers)
result = response.json()

print(f"Status: {result['status']}")
print(f"Action: {result['agent_decision']['action']}")
print(f"Reason: {result['agent_decision']['reason']}")
```

### Curl Example: Get App History

```bash
curl -X GET "http://localhost:5000/api/control-plane/history/payment-service?limit=10" \
  -H "Accept: application/json"
```

### Curl Example: Apply Freeze

```bash
curl -X POST "http://localhost:5000/api/control-plane/override" \
  -H "Content-Type: application/json" \
  -d '{
    "app_name": "payment-service",
    "action": "set_freeze",
    "duration_minutes": 30,
    "reason": "maintenance_window"
  }'
```

---

## Deployment

### Local Development

```bash
python app.py
# API available at http://localhost:5000
```

### Production Deployment

```bash
python deploy_pravah.py --env prod --port 5000 --workers 4
# Starts agent runtime + gunicorn API server
# Access at http://localhost:5000
```

### Health Check

```bash
curl http://localhost:5000/api/health
# Response: {"status": "OK", "timestamp": "..."}
```

---

## Monitoring & Compliance

### Audit Trail

Every decision stored in `logs/prod/orchestrator_decisions.jsonl`:

```json
{
  "decision_id": "dec_xyz789",
  "timestamp": "2026-02-20T14:29:30Z",
  "app_id": "payment-service",
  "action": "restart",
  "reason": "crash_detected",
  "governance_approved": true,
  "execution_status": "success"
}
```

### Metrics Available

- Decision count (total, per app, per action type)
- Execution latency (p50, p95, p99)
- Governance approval rate
- Rate limiting hits
- Error rates by type

---

## API Versioning

**Current Version:** v1.0.0 (canonical APIs - no versioning planned)

**Stability:** Production-grade (no breaking changes without notice)

**Deprecation Policy:** 30-day notice before removing endpoints

---

**Document Version:** 1.0.0  
**Last Updated:** February 20, 2026  
**Next Review:** March 20, 2026
