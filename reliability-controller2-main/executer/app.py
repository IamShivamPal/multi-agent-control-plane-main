from flask import Flask, request, jsonify
import uuid
import json
import logging
from datetime import datetime, timedelta
import subprocess
import os

app = Flask(__name__)

# ---------------- CONFIG ----------------
EXECUTION_MODE = os.getenv("EXECUTION_MODE", "docker")  # docker | kubernetes

logging.basicConfig(
    filename="executer.log",
    level=logging.INFO,
    format='%(message)s'
)

VALID_ACTIONS = ["restart", "scale_up", "scale_down", "noop"]

cooldowns = {}
COOLDOWN_TIME = 10  # seconds


# ---------------- LOGGER ----------------
def log_event(event_type, service_id, action, result):
    log = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type,
        "service_id": service_id,
        "action": action,
        "result": result,
        "mode": EXECUTION_MODE
    }
    logging.info(json.dumps(log))


# ---------------- VERIFY ----------------
def verify_deployment(service_id):
    try:
        if EXECUTION_MODE == "kubernetes":
            result = subprocess.run(
                ["kubectl", "get", "pods"],
                capture_output=True,
                text=True
            )
            return service_id in result.stdout

        elif EXECUTION_MODE == "docker":
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True
            )
            return service_id in result.stdout

        return False
    except:
        return False


# ---------------- EXECUTION ----------------
def execute_real_action(service_id, action):
    try:
        # -------- KUBERNETES --------
        if EXECUTION_MODE == "kubernetes":

            if action == "restart":
                cmd = ["kubectl", "rollout", "restart", f"deployment/{service_id}"]

            elif action == "scale_up":
                cmd = ["kubectl", "scale", f"deployment/{service_id}", "--replicas=2"]

            elif action == "scale_down":
                cmd = ["kubectl", "scale", f"deployment/{service_id}", "--replicas=1"]

            else:
                return "noop"

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return f"K8S_ERROR: {result.stderr.strip()}"

            return result.stdout.strip()

        # -------- DOCKER --------
        elif EXECUTION_MODE == "docker":

            if action == "restart":
                cmd = ["docker", "restart", service_id]

            elif action == "scale_up":
                return f"DOCKER_SCALE_UP simulated for {service_id}"

            elif action == "scale_down":
                return f"DOCKER_SCALE_DOWN simulated for {service_id}"

            else:
                return "noop"

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return f"DOCKER_ERROR: {result.stderr.strip()}"

            return result.stdout.strip()

        # -------- FALLBACK --------
        else:
            return "UNKNOWN_EXECUTION_MODE"

    except Exception as e:
        return f"EXCEPTION: {str(e)}"


# ---------------- EXECUTE API ----------------
@app.route("/execute-action", methods=["POST"])
def execute_action():
    data = request.get_json()

    service_id = data.get("service_id")
    action = data.get("action")

    execution_id = str(uuid.uuid4())

    log_event("ACTION_RECEIVED", service_id, action, "incoming")

    # VALIDATION
    if action not in VALID_ACTIONS:
        log_event("ACTION_REJECTED", service_id, action, "invalid")

        return jsonify({
            "execution_id": execution_id,
            "status": "failed",
            "action": action,
            "reason": "invalid action",
            "verified": False
        }), 400

    # COOLDOWN
    now = datetime.utcnow()
    if service_id in cooldowns and now < cooldowns[service_id]:
        log_event("ACTION_BLOCKED", service_id, action, "cooldown")

        return jsonify({
            "execution_id": execution_id,
            "status": "blocked",
            "action": action,
            "reason": "cooldown active",
            "verified": False
        }), 429

    cooldowns[service_id] = now + timedelta(seconds=COOLDOWN_TIME)

    log_event("ACTION_ACCEPTED", service_id, action, "valid")

    # EXECUTION
    result = execute_real_action(service_id, action)

    status = "executed" if "ERROR" not in result and "EXCEPTION" not in result else "failed"

    log_event("ACTION_EXECUTED", service_id, action, result)

    # VERIFICATION
    verified = verify_deployment(service_id)

    log_event("VERIFICATION", service_id, action, "success" if verified else "failed")

    return jsonify({
        "execution_id": execution_id,
        "status": status,
        "action": action,
        "reason": result,
        "verified": verified
    })


# ---------------- HEALTH ----------------
@app.route("/health")
def health():
    return jsonify({"status": "healthy", "mode": EXECUTION_MODE})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)