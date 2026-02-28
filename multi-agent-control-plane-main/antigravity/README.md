# Antigravity - Distributed Multi-Agent System

A distributed multi-agent system with strict microservice architecture, REST-only communication, and comprehensive safety guarantees.

## 🏗 Architecture

```
┌─────────────┐      HTTP      ┌─────────────┐      HTTP      ┌─────────────┐
│   Runtime   │─────────────────▶│    Agent    │─────────────────▶│Orchestrator │
│   Service   │   POST /decide  │   Service   │  POST /execute  │   Service   │
│  (Port 8001)│                 │  (Port 8002)│                 │  (Port 8003)│
└─────────────┘                 └─────────────┘                 └─────────────┘
```

### Service Responsibilities

- **Runtime Service (8001)** - Emits events, orchestrates full flow
- **Agent Service (8002)** - Makes decisions, validates input
- **Orchestrator Service (8003)** - Executes actions, enforces allowlist

## 🚀 Quick Start

### Local Development

#### 1. Start Services Individually

```bash
# Terminal 1: Agent Service
cd services/agent
pip install -r requirements.txt
python main.py

# Terminal 2: Orchestrator Service
cd services/orchestrator
pip install -r requirements.txt
python main.py

# Terminal 3: Runtime Service
cd services/runtime
pip install -r requirements.txt
python main.py
```

#### 2. Or Use Docker Compose

```bash
cd docker
docker-compose up --build
```

### Test the System

```bash
# Test successful flow
curl -X POST http://localhost:8001/emit \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "app_crash",
    "app": "web-api",
    "env": "prod",
    "metadata": {"error_count": 15, "state": "critical"}
  }'

# Run full validation suite
cd tests
bash test_validation.sh
```

## 🛡 Safety Guarantees

### 1. NOOP on Invalid Input
- Malformed JSON → `{"decision": "noop"}`
- Missing required fields → `{"decision": "noop"}`
- Invalid field values → `{"decision": "noop"}`

### 2. Environment Action Allowlist
```
dev:   restart, scale_up, scale_down, deploy, rollback, noop
stage: restart, scale_up, scale_down, noop
prod:  restart, noop
```

### 3. Demo Mode
```bash
# Start orchestrator in demo mode
DEMO_MODE=true python services/orchestrator/main.py
```
All actions simulated, no real execution.

### 4. Graceful Degradation
- Agent down → Runtime returns NOOP fallback
- Orchestrator down → Runtime logs error, doesn't crash
- Network timeout → Safe fallback with logging

## 📊 REST API Reference

### Runtime Service

**POST /emit**
```json
{
  "event_type": "app_crash",
  "app": "web-api",
  "env": "prod",
  "metadata": {"error_count": 15}
}
```

### Agent Service

**POST /decide**
```json
{
  "event_type": "app_crash",
  "app": "web-api",
  "env": "prod",
  "state": "critical",
  "metrics": {"error_count": 15}
}
```

### Orchestrator Service

**POST /execute**
```json
{
  "action": "restart",
  "app": "web-api",
  "env": "prod",
  "requested_by": "agent"
}
```

## 🧪 Validation Tests

| Test | Expected | Command |
|------|----------|---------|
| Full chain | Success | `curl -X POST http://localhost:8001/emit ...` |
| Malformed JSON | NOOP | `curl -X POST http://localhost:8002/decide -d '{"invalid'` |
| Missing field | NOOP | Agent with missing `env` field |
| Unauthorized action | Rejected | `scale_up` in `prod` environment |
| Demo mode | Simulated | `DEMO_MODE=true` → no real execution |

## 📝 Structured Logging

All services log in JSON format:

```json
{
  "timestamp": "2026-02-11T10:30:00Z",
  "service": "agent",
  "event": "decision_made",
  "decision": "restart",
  "reason": "error_count_exceeded",
  "confidence": 0.9
}
```

## 🔒 Key Architectural Rules

1. ❌ No cross-imports between services
2. ❌ No shared local memory
3. ✅ All communication via HTTP REST
4. ✅ Services independently deployable
5. ✅ Graceful degradation on failures

## 📁 Directory Structure

```
antigravity/
├── services/
│   ├── runtime/       # Event emitter
│   ├── agent/         # Decision maker
│   └── orchestrator/  # Action executor
├── docker/
│   └── docker-compose.yml
├── tests/
│   └── test_validation.sh
├── docs/
│   ├── API.md
│   └── ARCHITECTURE.md
└── README.md
```

## 📖 Documentation

- [API Reference](docs/API.md) - Complete REST API documentation
- [Architecture](docs/ARCHITECTURE.md) - System design and principles
- [Deployment](docs/DEPLOYMENT.md) - Production deployment guide

## 🎯 Production Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for:
- Kubernetes configuration
- Environment variables
- Monitoring setup
- Scaling recommendations

## ⚡ Performance

- Request timeout: 5 seconds (configurable)
- JSON logging for observability
- Stateless services for horizontal scaling
- Docker-native for easy deployment

---

**Built with:** FastAPI, Python 3.10+, Docker

**License:** MIT
