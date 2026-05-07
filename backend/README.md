# Pravah Decision Brain Backend (FastAPI)

Stateless, deterministic Decision Brain API designed for the Pravah Dashboard.

## Principles

- Stateless service
- Deterministic decision logic
- No database
- No infrastructure side effects
- Environment-safe action constraints (`DEV`, `STAGE`, `PROD`)
- Demo-frozen mode enabled

## Stack

- Python 3.11+
- FastAPI
- Pydantic v2
- Uvicorn

## Project structure

```text
backend/
  app/
    main.py
    config.py
    schemas.py
    decision_engine.py
    __init__.py
  requirements.txt
  run.py
```

## API contract

### `GET /health`

```json
{
  "status": "healthy",
  "demo_frozen": true,
  "stateless": true,
  "success_rate": 1.0
}
```

### `GET /action-scope`

```json
{
  "DEV": ["noop", "scale_up", "scale_down", "restart"],
  "STAGE": ["noop", "scale_up", "scale_down"],
  "PROD": ["noop", "restart"]
}
```

### `POST /decision`

Request:

```json
{
  "environment": "DEV",
  "event_type": "HIGH_CPU",
  "cpu": 85,
  "memory": 50
}
```

Response shape:

```json
{
  "decision_id": "uuid",
  "environment": "DEV",
  "selected_action": "scale_up",
  "reason": "CPU above threshold",
  "confidence": 0.91,
  "timestamp": "ISO-8601"
}
```

### `GET /recent-activity`

Returns the latest 10 in-memory decisions.

### `GET /decision-summary`

Returns aggregate summary values for the Pravah Dashboard.

### `GET /live-dashboard`

Returns the full payload for Pravah Dashboard sections.

## Decision rules

- If `cpu > 80` -> `scale_up` (if allowed)
- If `cpu < 30` -> `scale_down` (if allowed)
- If `memory > 85` -> `scale_up` (if allowed)
- Otherwise -> `noop`

Environment constraints are always enforced (`PROD` never auto-scales).

## Run locally

1. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

2. Start server (runs on port 7999 by default):

```bash
python backend/run.py
```

3. Verify connectivity:

- `http://localhost:7999/live-dashboard`
- `http://localhost:7999/docs`
