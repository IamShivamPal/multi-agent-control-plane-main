"""
Orchestrator Service - Action Executor
Port: 8003
Responsibility: Execute actions with strict allowlist enforcement and demo mode
"""

from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import json
from datetime import datetime
import os
import uuid

# Configure JSON logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Orchestrator Service", version="1.0.0")

# Demo mode configuration
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Action allowlist per environment
ALLOWED_ACTIONS = {
    "dev": ["restart", "scale_up", "scale_down", "deploy", "rollback", "noop"],
    "stage": ["restart", "scale_up", "scale_down", "noop"],
    "prod": ["restart", "noop"]
}

# Models
class ExecutionRequest(BaseModel):
    action: str
    app: str
    env: str
    requested_by: str
    decision_metadata: Optional[Dict[str, Any]] = {}

class ExecutionResponse(BaseModel):
    status: str
    action: str
    app: str
    env: str
    execution_id: str
    demo_mode: bool
    timestamp: str
    reason: Optional[str] = None
    message: Optional[str] = None
    allowed_actions: Optional[List[str]] = None

def log_structured(event: str, **kwargs):
    """Log in structured JSON format"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "orchestrator",
        "event": event,
        **kwargs
    }
    logger.info(json.dumps(log_entry))

def create_error_response(status: str, reason: str, action: str = None, app: str = None, env: str = None) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "status": status,
        "reason": reason,
        "action": action or "unknown",
        "app": app or "unknown",
        "env": env or "unknown",
        "execution_id": f"err_{uuid.uuid4().hex[:8]}",
        "demo_mode": DEMO_MODE,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

def validate_execution_request(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate execution request
    Returns error response if invalid, None if valid
    """
    # Check for empty payload
    if not data or len(data) == 0:
        log_structured(
            "validation_failed",
            reason="empty_payload",
            level="WARNING"
        )
        return create_error_response("rejected", "empty_payload")
    
    # Check required fields
    required_fields = ["action", "app", "env", "requested_by"]
    missing_fields = [f for f in required_fields if f not in data]
    
    if missing_fields:
        log_structured(
            "validation_failed",
            reason=f"missing_field_{missing_fields[0]}",
            missing_fields=missing_fields,
            level="WARNING"
        )
        return create_error_response(
            "rejected",
            f"missing_required_field_{missing_fields[0]}",
            data.get("action"),
            data.get("app"),
            data.get("env")
        )
    
    # Validate data types
    if not isinstance(data["action"], str) or not data["action"].strip():
        log_structured(
            "validation_failed",
            reason="invalid_action_type",
            level="WARNING"
        )
        return create_error_response("rejected", "action_must_be_non_empty_string", None, data.get("app"), data.get("env"))
    
    if not isinstance(data["app"], str) or not data["app"].strip():
        log_structured(
            "validation_failed",
            reason="invalid_app_type",
            level="WARNING"
        )
        return create_error_response("rejected", "app_must_be_non_empty_string", data.get("action"), None, data.get("env"))
    
    if not isinstance(data["env"], str) or not data["env"].strip():
        log_structured(
            "validation_failed",
            reason="invalid_env_type",
            level="WARNING"
        )
        return create_error_response("rejected", "env_must_be_non_empty_string", data.get("action"), data.get("app"), None)
    
    return None  # Validation passed

def is_action_allowed(action: str, env: str) -> bool:
    """Check if action is in allowlist for environment"""
    allowed = ALLOWED_ACTIONS.get(env, [])
    return action in allowed

def execute_real_action(action: str, app: str, env: str) -> Dict[str, Any]:
    """
    Execute real action (placeholder implementation)
    
    In production, this would:
    - Call Kubernetes API
    - Trigger CI/CD pipeline
    - Execute infrastructure changes
    """
    log_structured(
        "real_action_executing",
        action=action,
        app=app,
        env=env,
        level="INFO"
    )
    
    # Placeholder: Simulate execution
    # In real system, this would have actual implementation
    return {
        "execution_status": "success",
        "details": f"Executed {action} on {app} in {env}"
    }

def simulate_action(action: str, app: str, env: str) -> Dict[str, Any]:
    """Simulate action in demo mode"""
    log_structured(
        "demo_mode_simulation",
        action=action,
        app=app,
        env=env,
        message="DEMO MODE – action simulated",
        level="INFO"
    )
    
    return {
        "simulation_status": "success",
        "details": f"Simulated {action} on {app} in {env}"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "orchestrator",
        "version": "1.0.0",
        "demo_mode": DEMO_MODE
    }

@app.post("/execute")
async def execute_action(request: Request):
    """
    Execute action with strict safety enforcement
    
    Safety guarantees:
    - Validates all input fields
    - Rejects actions not in allowlist
    - Respects demo mode
    - Logs all execution attempts
    - Never crashes on invalid input
    """
    from json import JSONDecodeError
    
    # Handle malformed JSON
    try:
        data = await request.json()
    except JSONDecodeError as e:
        log_structured(
            "malformed_json",
            error=str(e),
            level="WARNING"
        )
        return create_error_response("rejected", "malformed_json")
    except Exception as e:
        log_structured(
            "json_parse_error",
            error=str(e),
            error_type=type(e).__name__,
            level="WARNING"
        )
        return create_error_response("rejected", "invalid_json")
    
    # Validate input
    validation_error = validate_execution_request(data)
    if validation_error:
        return validation_error
    
    execution_id = f"exec_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    log_structured(
        "execution_request_received",
        execution_id=execution_id,
        action=data["action"],
        app=data["app"],
        env=data["env"],
        requested_by=data["requested_by"],
        demo_mode=DEMO_MODE,
        level="INFO"
    )
    
    # Check action allowlist
    if not is_action_allowed(data["action"], data["env"]):
        allowed = ALLOWED_ACTIONS.get(data["env"], [])
        
        log_structured(
            "action_rejected",
            execution_id=execution_id,
            action=data["action"],
            env=data["env"],
            reason="action_out_of_scope",
            allowed_actions=allowed,
            level="WARNING"
        )
        
        return {
            "status": "rejected",
            "action": data["action"],
            "app": data["app"],
            "env": data["env"],
            "execution_id": execution_id,
            "demo_mode": DEMO_MODE,
            "timestamp": timestamp,
            "reason": "action_out_of_scope",
            "allowed_actions": allowed
        }
    
    # Execute based on demo mode
    if DEMO_MODE:
        simulate_action(data["action"], data["app"], data["env"])
        
        log_structured(
            "action_simulated",
            execution_id=execution_id,
            action=data["action"],
            app=data["app"],
            env=data["env"],
            level="INFO"
        )
        
        return {
            "status": "simulated",
            "action": data["action"],
            "app": data["app"],
            "env": data["env"],
            "execution_id": execution_id,
            "demo_mode": True,
            "timestamp": timestamp,
            "message": "DEMO MODE – action simulated"
        }
    else:
        execute_real_action(data["action"], data["app"], data["env"])
        
        log_structured(
            "action_executed",
            execution_id=execution_id,
            action=data["action"],
            app=data["app"],
            env=data["env"],
            level="INFO"
        )
        
        return {
            "status": "executed",
            "action": data["action"],
            "app": data["app"],
            "env": data["env"],
            "execution_id": execution_id,
            "demo_mode": False,
            "timestamp": timestamp
        }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler"""
    log_structured(
        "unexpected_error",
        error=str(exc),
        error_type=type(exc).__name__,
        level="ERROR"
    )
    return {
        "status": "error",
        "reason": "internal_error",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

if __name__ == "__main__":
    import uvicorn
    log_structured(
        "service_starting",
        port=8003,
        demo_mode=DEMO_MODE,
        level="INFO"
    )
    uvicorn.run(app, host="0.0.0.0", port=8003)
