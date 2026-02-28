"""
Canonical Decision API Layer

Exposes only:
- POST /api/runtime
- GET  /api/status
- GET  /api/health
- GET  /api/control-plane/apps
- GET  /api/control-plane/health
- GET  /api/control-plane/history/<app_name>
- POST /api/control-plane/override
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import datetime
import json
import os
import sys
import threading

from jsonschema import ValidationError, validate

# Define project root
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from agent_runtime import AgentRuntime
from control_plane.multi_app_control_plane import MultiAppControlPlane
from core.input_validator import InputValidator, ValidationError as InputValidationError

ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
SCHEMA_PATH = os.path.join(root_dir, "runtime_payload_schema.json")

with open(SCHEMA_PATH, "r", encoding="utf-8") as schema_file:
    RUNTIME_SCHEMA = json.load(schema_file)

# One shared runtime instance
agent = AgentRuntime(env=ENVIRONMENT)
control_plane = MultiAppControlPlane(env=ENVIRONMENT)


def start_agent_loop() -> None:
    """Run autonomous loop in background."""
    agent.run()


threading.Thread(target=start_agent_loop, daemon=True).start()

app = Flask(__name__)
CORS(app)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)


def _validate_runtime_payload(payload: dict) -> None:
    """Validate payload against canonical runtime contract."""
    validate(instance=payload, schema=RUNTIME_SCHEMA)


def _event_type_from_contract(payload: dict) -> str:
    """Derive internal event type from canonical runtime contract."""
    state = payload.get("state")
    latency_ms = payload.get("latency_ms", 0)
    errors_last_min = payload.get("errors_last_min", 0)

    if state == "crashed":
        return "crash"

    if state == "degraded" or latency_ms >= 200 or errors_last_min >= 5:
        return "overload"

    return "false_alarm"


def _to_agent_event(payload: dict) -> dict:
    """Map canonical runtime contract to agent runtime event envelope."""
    return {
        "event_id": f"runtime-{datetime.datetime.utcnow().timestamp()}",
        "event_type": _event_type_from_contract(payload),
        "environment": payload["env"],
        "app_id": payload["app"],
        "timestamp": datetime.datetime.utcnow().timestamp(),
        "data": {
            "state": payload["state"],
            "metrics": {
                "latency_ms": payload["latency_ms"],
                "errors_last_min": payload["errors_last_min"],
                "workers": payload["workers"],
            },
        },
    }


@app.route("/api/health", methods=["GET"])
@limiter.limit("100 per minute")
def health_check():
    """Health and liveness endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "canonical-decision-api",
        "environment": ENVIRONMENT,
    }), 200


@app.route("/api/status", methods=["GET"])
@limiter.limit("60 per minute")
def runtime_status():
    """Return current status of the shared runtime instance."""
    try:
        status = agent.get_agent_status()
        return jsonify(status), 200
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/runtime", methods=["POST"])
@limiter.limit("30 per minute")
def runtime_decision():
    """Canonical runtime decision endpoint."""
    payload = request.get_json(silent=True)

    if payload is None:
        return jsonify({
            "status": "error",
            "error": "Request body must be valid JSON",
        }), 400

    # Hardened input validation
    try:
        InputValidator.validate_runtime_payload(payload)
    except InputValidationError as exc:
        return jsonify({
            "status": "error",
            "error": "Input validation failed",
            "details": str(exc),
        }), 400
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": "Runtime payload validation failed",
            "details": str(exc),
        }), 400

    try:
        result = agent.handle_external_event(_to_agent_event(payload))
        return jsonify({
            "status": "success",
            "input": payload,
            "result": result,
        }), 200
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": "Runtime decision failed",
            "details": str(exc),
        }), 500


@app.route("/api/control-plane/apps", methods=["GET"])
@limiter.limit("40 per minute")
def control_plane_apps():
    """List all onboarded apps in the registry."""
    try:
        return jsonify({"status": "success", "apps": control_plane.list_apps()}), 200
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/control-plane/health", methods=["GET"])
@limiter.limit("40 per minute")
def control_plane_health_overview():
    """Health overview dashboard data for all onboarded apps."""
    try:
        return jsonify({"status": "success", "overview": control_plane.get_health_overview()}), 200
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/control-plane/history/<app_name>", methods=["GET"])
@limiter.limit("40 per minute")
def control_plane_history(app_name: str):
    """Decision history timeline for one app."""
    try:
        # Validate app_name
        app_name = InputValidator.validate_app_name(app_name)
        
        # Validate limit parameter
        limit_param = request.args.get("limit", "200")
        limit = InputValidator.validate_limit_param(limit_param)
        
        history = control_plane.get_decision_history(app_name=app_name, limit=limit)
        return jsonify({"status": "success", "app_name": app_name, "timeline": history}), 200
    except InputValidationError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/control-plane/override", methods=["POST"])
@limiter.limit("40 per minute")
def control_plane_override():
    """Manual override panel actions: set or clear temporary per-app freeze."""
    payload = request.get_json(silent=True) or {}

    try:
        app_name, action, duration, reason = InputValidator.validate_control_plane_override_payload(payload)
    except InputValidationError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400

    try:
        if action == "clear_freeze":
            result = control_plane.clear_manual_override(app_name)
        else:
            result = control_plane.set_manual_override(app_name, duration, reason)
        return jsonify({"status": "success", "result": result}), 200
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.getenv("CONTROL_PLANE_PORT", os.getenv("PORT", 7000)))
    app.run(host="0.0.0.0", port=port, debug=False)
