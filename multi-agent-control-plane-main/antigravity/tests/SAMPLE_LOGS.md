# Sample Logs - Agent Failure Scenarios

## Scenario 1: Agent Connection Error (Service Down)

### Runtime Service Logs

```json
{
  "timestamp": "2026-02-11T15:53:00Z",
  "service": "runtime",
  "event": "event_emitted",
  "event_id": "evt_a1b2c3d4",
  "event_type": "app_crash",
  "app": "web-api",
  "env": "prod",
  "level": "INFO"
}
```

```json
{
  "timestamp": "2026-02-11T15:53:00Z",
  "service": "runtime",
  "event": "calling_agent",
  "event_id": "evt_a1b2c3d4",
  "agent_url": "http://localhost:8002/decide",
  "timeout": 3,
  "level": "INFO"
}
```

```json
{
  "timestamp": "2026-02-11T15:53:01Z",
  "service": "runtime",
  "event": "agent_connection_error",
  "event_id": "evt_a1b2c3d4",
  "error": "HTTPConnectionPool(host='localhost', port=8002): Max retries exceeded",
  "error_type": "ConnectionError",
  "level": "WARNING"
}
```

**Console Log:**
```
WARNING:__main__:[Runtime] Agent unreachable – executing NOOP (connection error)
```

### Client Response (HTTP 200)

```json
{
  "status": "degraded",
  "event_id": "evt_a1b2c3d4",
  "agent_decision": {
    "decision": "noop",
    "reason": "agent_unavailable",
    "confidence": 0.0,
    "metadata": {
      "fallback": "connection_error"
    }
  },
  "orchestrator_result": null,
  "error": "agent_connection_error",
  "fallback": "noop"
}
```

---

## Scenario 2: Agent Timeout (Takes > 3 seconds)

### Runtime Service Logs

```json
{
  "timestamp": "2026-02-11T15:55:00Z",
  "service": "runtime",
  "event": "event_emitted",
  "event_id": "evt_x9y8z7w6",
  "event_type": "health_check",
  "app": "api-service",
  "env": "stage",
  "level": "INFO"
}
```

```json
{
  "timestamp": "2026-02-11T15:55:00Z",
  "service": "runtime",
  "event": "calling_agent",
  "event_id": "evt_x9y8z7w6",
  "agent_url": "http://localhost:8002/decide",
  "timeout": 3,
  "level": "INFO"
}
```

```json
{
  "timestamp": "2026-02-11T15:55:03Z",
  "service": "runtime",
  "event": "agent_timeout",
  "event_id": "evt_x9y8z7w6",
  "error": "Agent timeout after 3s",
  "error_type": "Timeout",
  "level": "WARNING"
}
```

**Console Log:**
```
WARNING:__main__:[Runtime] Agent unreachable – executing NOOP (timeout)
```

### Client Response (HTTP 200)

```json
{
  "status": "degraded",
  "event_id": "evt_x9y8z7w6",
  "agent_decision": {
    "decision": "noop",
    "reason": "agent_unavailable",
    "confidence": 0.0,
    "metadata": {
      "fallback": "timeout"
    }
  },
  "orchestrator_result": null,
  "error": "agent_timeout",
  "fallback": "noop"
}
```

---

## Scenario 3: Agent HTTP Error (500 Internal Server Error)

### Runtime Service Logs

```json
{
  "timestamp": "2026-02-11T15:57:00Z",
  "service": "runtime",
  "event": "event_emitted",
  "event_id": "evt_m5n6p7q8",
  "event_type": "memory_leak",
  "app": "worker",
  "env": "dev",
  "level": "INFO"
}
```

```json
{
  "timestamp": "2026-02-11T15:57:00Z",
  "service": "runtime",
  "event": "calling_agent",
  "event_id": "evt_m5n6p7q8",
  "agent_url": "http://localhost:8002/decide",
  "timeout": 3,
  "level": "INFO"
}
```

```json
{
  "timestamp": "2026-02-11T15:57:01Z",
  "service": "runtime",
  "event": "agent_http_error",
  "event_id": "evt_m5n6p7q8",
  "error": "500 Server Error: Internal Server Error for url: http://localhost:8002/decide",
  "error_type": "HTTPError",
  "status_code": 500,
  "level": "WARNING"
}
```

**Console Log:**
```
WARNING:__main__:[Runtime] Agent unreachable – executing NOOP (HTTP error)
```

### Client Response (HTTP 200)

```json
{
  "status": "degraded",
  "event_id": "evt_m5n6p7q8",
  "agent_decision": {
    "decision": "noop",
    "reason": "agent_unavailable",
    "confidence": 0.0,
    "metadata": {
      "fallback": "http_error"
    }
  },
  "orchestrator_result": null,
  "error": "agent_http_error",
  "fallback": "noop"
}
```

---

## Scenario 4: Successful Flow (Agent Healthy)

### Runtime Service Logs

```json
{
  "timestamp": "2026-02-11T16:00:00Z",
  "service": "runtime",
  "event": "event_emitted",
  "event_id": "evt_s1t2u3v4",
  "event_type": "app_crash",
  "app": "web-api",
  "env": "prod",
  "level": "INFO"
}
```

```json
{
  "timestamp": "2026-02-11T16:00:00Z",
  "service": "runtime",
  "event": "calling_agent",
  "event_id": "evt_s1t2u3v4",
  "agent_url": "http://localhost:8002/decide",
  "timeout": 3,
  "level": "INFO"
}
```

```json
{
  "timestamp": "2026-02-11T16:00:01Z",
  "service": "runtime",
  "event": "agent_response_received",
  "event_id": "evt_s1t2u3v4",
  "decision": "restart",
  "reason": "state_critical",
  "level": "INFO"
}
```

```json
{
  "timestamp": "2026-02-11T16:00:01Z",
  "service": "runtime",
  "event": "calling_orchestrator",
  "event_id": "evt_s1t2u3v4",
  "orchestrator_url": "http://localhost:8003/execute",
  "action": "restart",
  "level": "INFO"
}
```

```json
{
  "timestamp": "2026-02-11T16:00:02Z",
  "service": "runtime",
  "event": "orchestrator_response_received",
  "event_id": "evt_s1t2u3v4",
  "status": "executed",
  "execution_id": "exec_abc123",
  "level": "INFO"
}
```

### Client Response (HTTP 200)

```json
{
  "status": "processed",
  "event_id": "evt_s1t2u3v4",
  "agent_decision": {
    "decision": "restart",
    "reason": "state_critical",
    "confidence": 0.9,
    "metadata": {
      "timestamp": "2026-02-11T16:00:01Z",
      "agent_version": "1.0.0-rityadani-rl",
      "rule_matched": "critical_state",
      "rl_engine": "rityadani"
    }
  },
  "orchestrator_result": {
    "status": "executed",
    "action": "restart",
    "app": "web-api",
    "env": "prod",
    "execution_id": "exec_abc123",
    "demo_mode": false,
    "timestamp": "2026-02-11T16:00:02Z"
  },
  "error": null,
  "fallback": null
}
```

---

## Key Observations

### Hardened Behavior

1. **3-Second Timeout Enforced**
   - Agent calls timeout after exactly 3 seconds
   - No hanging or infinite waits

2. **Comprehensive Exception Handling**
   - `ConnectionError` - Agent service down
   - `Timeout` - Agent too slow
   - `HTTPError` - Agent returned error status
   - `RequestException` - Any other request error
   - `Exception` - Final safety net

3. **Always Returns HTTP 200**
   - Runtime NEVER crashes
   - Client always gets valid JSON
   - Safe NOOP fallback

4. **Clear Logging**
   - Console: `[Runtime] Agent unreachable – executing NOOP`
   - JSON logs include error type and details
   - Easy to diagnose issues

5. **No Infinite Retries**
   - Single attempt only
   - Immediate fallback to NOOP
   - Fast failure recovery

---

## Testing Commands

### Test 1: Kill Agent, Test Degradation

```bash
# Stop Agent service
kill $(lsof -t -i:8002)

# Send event to Runtime
curl -X POST http://localhost:8001/emit \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "app_crash",
    "app": "web-api",
    "env": "prod",
    "metadata": {"state": "critical"}
  }'

# Expected: HTTP 200 with agent_decision.decision = "noop"
```

### Test 2: Run Automated Tests

```bash
cd antigravity/tests
python test_agent_failure.py
```

---

**Status:** Hardened Runtime ready for production  
**Tolerance:** 3-second timeout  
**Fallback:** Safe NOOP, no crashes
