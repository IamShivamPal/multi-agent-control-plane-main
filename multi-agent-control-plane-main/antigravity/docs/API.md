# Antigravity REST API Reference

Complete REST API documentation for all services.

---

## Runtime Service (Port 8001)

### POST /emit
Emit a runtime event and trigger full decision → execution chain.

**Request:**
```json
{
  "event_type": "app_crash",          // Type of event
  "app": "web-api",                   // Application name
  "env": "prod",                      // Environment (dev/stage/prod)
  "metadata": {                       // Optional additional data
    "error_count": 15,
    "latency_ms": 5000,
    "state": "critical"
  }
}
```

**Response (Success):**
```json
{
  "status": "processed",
  "event_id": "evt_abc123",
  "agent_decision": {
    "decision": "restart",
    "reason": "error_count_exceeded_threshold",
    "confidence": 0.9
  },
  "orchestrator_result": {
    "status": "executed",
    "action": "restart",
    "execution_id": "exec_xyz789"
  }
}
```

**Response (Agent Down):**
```json
{
  "status": "degraded",
  "event_id": "evt_abc124",
  "error": "agent_unavailable",
  "fallback": "noop"
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "runtime",
  "version": "1.0.0"
}
```

---

## Agent Service (Port 8002)

### POST /decide
Make decision based on runtime event.

**Request:**
```json
{
  "event_type": "app_crash",         // Required
  "app": "web-api",                  // Required
  "env": "prod",                     // Required (dev/stage/prod)
  "state": "critical",               // Required (healthy/degraded/critical/unknown)
  "metrics": {                       // Optional
    "error_count": 15,
    "latency_ms": 5000
  }
}
```

**Response (Valid Decision):**
```json
{
  "decision": "restart",
  "reason": "error_count_exceeded_threshold",
  "confidence": 0.9,
  "metadata": {
    "timestamp": "2026-02-11T10:30:00Z",
    "agent_version": "1.0.0",
    "rule_matched": "high_error_count"
  }
}
```

**Response (Invalid Input - Missing Field):**
```json
{
  "decision": "noop",
  "reason": "invalid_input_missing_required_field_env",
  "confidence": 0.0,
  "metadata": {
    "timestamp": "2026-02-11T10:30:00Z",
    "validation_errors": ["missing: env"]
  }
}
```

**Response (Malformed JSON):**
```json
{
  "decision": "noop",
  "reason": "malformed_json",
  "confidence": 0.0,
  "metadata": {
    "timestamp": "2026-02-11T10:30:00Z"
  }
}
```

### Decision Logic Rules

| Condition | Decision | Confidence |
|-----------|----------|------------|
| state == "critical" | restart | 0.9 |
| error_count > 10 | restart | 0.85 |
| latency_ms > 5000 | scale_up | 0.75 |
| else | noop | 0.95 |

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "agent",
  "version": "1.0.0"
}
```

---

## Orchestrator Service (Port 8003)

### POST /execute
Execute action with allowlist enforcement.

**Request:**
```json
{
  "action": "restart",              // Required
  "app": "web-api",                 // Required
  "env": "prod",                    // Required
  "requested_by": "agent",          // Required
  "decision_metadata": {            // Optional
    "confidence": 0.9,
    "reason": "error_count_exceeded"
  }
}
```

**Response (Allowed - Real Execution):**
```json
{
  "status": "executed",
  "action": "restart",
  "app": "web-api",
  "env": "prod",
  "execution_id": "exec_abc123",
  "demo_mode": false,
  "timestamp": "2026-02-11T10:30:05Z"
}
```

**Response (Allowed - Demo Mode):**
```json
{
  "status": "simulated",
  "action": "restart",
  "app": "web-api",
  "env": "prod",
  "execution_id": "exec_abc124",
  "demo_mode": true,
  "message": "DEMO MODE – action simulated",
  "timestamp": "2026-02-11T10:30:05Z"
}
```

**Response (Rejected - Out of Scope):**
```json
{
  "status": "rejected",
  "reason": "action_out_of_scope",
  "action": "scale_up",
  "app": "web-api",
  "env": "prod",
  "execution_id": "exec_abc125",
  "demo_mode": false,
  "timestamp": "2026-02-11T10:30:05Z",
  "allowed_actions": ["restart", "noop"]
}
```

### Action Allowlist

| Environment | Allowed Actions |
|-------------|-----------------|
| **dev** | restart, scale_up, scale_down, deploy, rollback, noop |
| **stage** | restart, scale_up, scale_down, noop |
| **prod** | restart, noop |

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "orchestrator",
  "version": "1.0.0",
  "demo_mode": false
}
```

---

## Error Handling

All services implement consistent error handling:

1. **Invalid JSON** → Returns valid JSON with error
2. **Missing fields** → Returns NOOP decision
3. **Service down** → Graceful degradation
4. **Timeout** → Fallback to safe default

**No service ever returns:**
- Stack traces to clients
- Unhandled exceptions
- Raw Python errors

---

## Authentication & Authorization

**Current:** None (demo/development)

**Production Recommendation:**
- API keys via headers
- JWT tokens
- mTLS between services
- Network policies (Kubernetes)

---

## Rate Limiting

**Current:** None

**Production Recommendation:**
- 100 req/min per IP for Runtime
- 500 req/min for internal services
- Implement using nginx or API gateway

---

## Monitoring Endpoints

### Health Checks
- `GET /health` on all services
- Returns 200 OK when healthy
- Use for load balancer health probes

### Metrics (Future)
- `/metrics` (Prometheus format)
- Request count, latency, error rate
- Service-specific metrics

---

## Examples

### Curl Commands

**Test full chain:**
```bash
curl -X POST http://localhost:8001/emit \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "app_crash",
    "app": "web-api",
    "env": "prod",
    "metadata": {"error_count": 15, "state": "critical"}
  }'
```

**Test malformed JSON:**
```bash
curl -X POST http://localhost:8002/decide \
  -H "Content-Type: application/json" \
  -d '{"invalid json'
```

**Test unauthorized action:**
```bash
curl -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{
    "action": "delete_database",
    "app": "web-api",
    "env": "prod",
    "requested_by": "agent"
  }'
```

### Python Client

```python
import requests

# Emit event
response = requests.post(
    "http://localhost:8001/emit",
    json={
        "event_type": "app_crash",
        "app": "web-api",
        "env": "prod",
        "metadata": {"error_count": 15, "state": "critical"}
    }
)
print(response.json())
```

---

## Service Dependencies

```
Runtime depends on:
- Agent Service (http://localhost:8002)
- Orchestrator Service (http://localhost:8003)

Agent depends on:
- None (stateless)

Orchestrator depends on:
- None (stateless)
```

---

**Version:** 1.0.0  
**Last Updated:** 2026-02-11
