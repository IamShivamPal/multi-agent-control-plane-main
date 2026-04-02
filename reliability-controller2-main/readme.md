Monitoring + Execution Control Loop System
Overview
This project implements a production-style control loop system consisting of:
Monitoring Layer → Detects system health and issues
Decision Layer → (external) decides actions based on runtime payload
Execution Layer → Executes actions and verifies results
The system follows:
Detect → Emit → Decide → Execute → Verify

Architecture
Monitor Service → Runtime Payload → Decision Engine → Executer Service → Infrastructure

Components:
Monitor Service
Collects real metrics using psutil
Detects issues (CPU spike, crash, etc.)
Emits structured data
Executer Service
Accepts actions (restart, scale_up, scale_down)
Executes actions (Docker / Kubernetes)
Verifies execution
Logs all events

Features
 Real system metrics (CPU, memory)
 Structured schema (no drift)
 Deterministic behavior
 Cooldown protection (prevents repeated actions)
 Validation of actions
 Execution verification
 Structured JSON logging
 Supports Docker + Kubernetes
 Failure-safe (no crashes)

API Endpoints
1. /metrics
Returns system metrics and issue detection.
{
  "service_id": "web1",
  "timestamp": "UTC",
  "status": "healthy | degraded | critical",
  "metrics": {
    "cpu": float,
    "memory": float,
    "error_rate": float,
    "uptime": int
  },
  "issue_detected": boolean,
  "issue_type": "cpu_spike | crash | none",
  "recommended_action": "restart | scale_up | noop"
}


2. /internal/runtime-payload
Used by decision engine.
{
  "app_id": "monitor-service",
  "cpu_usage": float,
  "memory_usage": float,
  "error_rate": float,
  "health_score": float,
  "environment": "dev | stage | prod"
}


3. /execute-action
Executes actions.
Request:
{
  "service_id": "web1",
  "action": "restart"
}

Response:
{
  "execution_id": "...",
  "status": "executed | failed | blocked",
  "action": "restart",
  "reason": "...",
  "verified": true/false
}


Docker Setup
Build Images
docker build -t rayyandevopss/monitor-service:latest .
docker build -t rayyandevopss/executer-service:latest .

Run Containers
docker run -d -p 5004:5004 rayyandevopss/monitor-service
docker run -d -p 5003:5003 rayyandevopss/executer-service


Kubernetes Setup
Apply Deployment
kubectl apply -f k8s/

Restart Deployment
kubectl rollout restart deployment monitor
kubectl rollout restart deployment executer


Environment Configuration

The system supports dual execution modes:

Mode	      Behavior
docker	    Uses Docker commands
kubernetes	Uses kubectl commands

Set using environment variable:
EXECUTION_MODE=docker

OR
env:
- name: EXECUTION_MODE
  value: "kubernetes"


Logging (Observability)
Logs are structured JSON and include:
timestamp
service_id
action
result
Example:
{
  "timestamp": "...",
  "event": "ACTION_EXECUTED",
  "service_id": "web1",
  "action": "restart",
  "result": "success"
}


Failure Handling
The system handles failures safely:
Invalid actions → rejected
Rapid actions → blocked (cooldown)
Infrastructure failure → logged + returned
No crashes
Example failure:
{
  "status": "failed",
  "reason": "DOCKER_ERROR: daemon not running",
  "verified": false
}


Full Control Loop
1. Monitor detects issue
2. Runtime payload generated
3. Decision engine selects action
4. Executer receives action
5. Action executed (Docker/K8s)
6. Verification performed
7. Logs recorded


Testing Scenarios
✅ Normal operation (healthy)
✅ Service crash detection
✅ Invalid action rejection
✅ Cooldown enforcement
✅ Execution failure handling

Key Highlights
Deterministic system design
Production-style control loop
Environment-agnostic execution
Observability-first approach
Failure-safe architecture

Conclusion
This system demonstrates a fully functional monitoring + execution loop capable of:
Detecting issues
Executing corrective actions
Handling failures safely
Providing verifiable logs

Status: ✅ Production-Ready Control Loop Component


