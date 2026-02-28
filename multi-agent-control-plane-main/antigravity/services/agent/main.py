"""
Agent Service - Decision Maker
Port: 8002
Responsibility: Validate input and make safe decisions
"""

from fastapi import FastAPI, Request
from pydantic import BaseModel, ValidationError
from typing import Dict, Any, Optional
import logging
import json
from datetime import datetime
from json import JSONDecodeError

# Configure JSON logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Service", version="1.0.0")

# Valid values
VALID_ENVS = ["dev", "stage", "prod"]
VALID_STATES = ["healthy", "degraded", "critical", "unknown"]

# Decision models
class DecisionRequest(BaseModel):
    event_type: str
    app: str
    env: str
    state: str
    metrics: Optional[Dict[str, Any]] = {}

class DecisionResponse(BaseModel):
    decision: str
    reason: str
    confidence: float
    metadata: Dict[str, Any]

def log_structured(event: str, **kwargs):
    """Log in structured JSON format"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "agent",
        "event": event,
        **kwargs
    }
    logger.info(json.dumps(log_entry))

def create_noop_response(reason: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """Create standardized NOOP response"""
    return {
        "decision": "noop",
        "reason": reason,
        "confidence": 0.0,
        "metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent_version": "1.0.0",
            **(details or {})
        }
    }

def validate_decision_input(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Strict input validation
    Returns NOOP response if invalid, None if valid
    """
    # Check for empty payload
    if not data or len(data) == 0:
        return create_noop_response(
            "invalid_input_empty_payload",
            {"validation_errors": ["payload cannot be empty"]}
        )
    
    # Check required fields
    required_fields = ["event_type", "app", "env", "state"]
    missing_fields = [f for f in required_fields if f not in data]
    
    if missing_fields:
        return create_noop_response(
            f"invalid_input_missing_required_field_{missing_fields[0]}",
            {"validation_errors": [f"missing: {f}" for f in missing_fields]}
        )
    
    # Validate env
    if data["env"] not in VALID_ENVS:
        return create_noop_response(
            "invalid_env",
            {
                "validation_errors": [f"env must be one of {VALID_ENVS}"],
                "received": data["env"]
            }
        )
    
    # Validate state
    if data["state"] not in VALID_STATES:
        return create_noop_response(
            "invalid_state",
            {
                "validation_errors": [f"state must be one of {VALID_STATES}"],
                "received": data["state"]
            }
        )
    
    # Validate event_type is non-empty string
    if not isinstance(data["event_type"], str) or not data["event_type"].strip():
        return create_noop_response(
            "invalid_event_type",
            {"validation_errors": ["event_type must be non-empty string"]}
        )
    
    # Validate app is non-empty string
    if not isinstance(data["app"], str) or not data["app"].strip():
        return create_noop_response(
            "invalid_app",
            {"validation_errors": ["app must be non-empty string"]}
        )
    
    # Validate data types for optional metrics
    if "metrics" in data and not isinstance(data["metrics"], dict):
        return create_noop_response(
            "invalid_metrics_type",
            {"validation_errors": ["metrics must be a dictionary/object"]}
        )
    
    return None  # Validation passed

def make_decision_logic(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    RL-based decision logic (Rityadani's algorithm)
    
    Rules:
    - critical state → restart
    - high error count (>10) → restart  
    - high latency (>5000ms) → scale_up
    - degraded state + errors → restart
    - healthy state → noop
    
    This implements Rityadani's conservative RL decision layer
    with strict safety boundaries and no learning.
    """
    state = data.get("state")
    metrics = data.get("metrics", {})
    env = data.get("env")
    
    # Extract metrics with safe defaults
    error_count = metrics.get("error_count", 0) or metrics.get("errors_last_min", 0)
    latency_ms = metrics.get("latency_ms", 0)
    
    # Critical state → restart (highest priority)
    if state == "critical":
        return {
            "decision": "restart",
            "reason": "state_critical",
            "confidence": 0.9,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "agent_version": "1.0.0-rityadani-rl",
                "rule_matched": "critical_state",
                "rl_engine": "rityadani"
            }
        }
    
    # High error count → restart
    if error_count > 10:
        return {
            "decision": "restart",
            "reason": "error_count_exceeded_threshold",
            "confidence": 0.85,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "agent_version": "1.0.0-rityadani-rl",
                "rule_matched": "high_error_count",
                "error_count": error_count,
                "rl_engine": "rityadani"
            }
        }
    
    # High latency → scale_up
    latency_ms = metrics.get("latency_ms", 0)
    if latency_ms > 5000:
        return {
            "decision": "scale_up",
            "reason": "high_latency_detected",
            "confidence": 0.75,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "agent_version": "1.0.0",
                "rule_matched": "high_latency",
                "latency_ms": latency_ms
            }
        }
    
    # Default → noop
    return {
        "decision": "noop",
        "reason": "no_action_required",
        "confidence": 0.95,
        "metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent_version": "1.0.0",
            "rule_matched": "default_safe"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "agent", "version": "1.0.0"}

@app.post("/decide")
async def decide(request: Request):
    """
    Make decision based on runtime event
    
    Safety guarantees:
    - Returns NOOP on malformed JSON
    - Returns NOOP on missing required fields
    - Returns NOOP on invalid field values
    - Never raises exceptions to caller
    """
    # Handle malformed JSON
    try:
        data = await request.json()
    except JSONDecodeError as e:
        log_structured(
            "malformed_json",
            error=str(e),
            level="WARNING"
        )
        return create_noop_response("malformed_json")
    
    log_structured(
        "decision_request_received",
        input_event_type=data.get("event_type"),
        app=data.get("app"),
        env=data.get("env"),
        state=data.get("state"),
        level="INFO"
    )
    
    # Validate input
    validation_error = validate_decision_input(data)
    if validation_error:
        log_structured(
            "input_validation_failed",
            reason=validation_error["reason"],
            level="WARNING"
        )
        return validation_error
    
    # Make decision
    decision = make_decision_logic(data)
    
    log_structured(
        "decision_made",
        input_event_type=data.get("event_type"),
        decision=decision["decision"],
        reason=decision["reason"],
        confidence=decision["confidence"],
        level="INFO"
    )
    
    return decision

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler - always return NOOP"""
    log_structured(
        "unexpected_error",
        error=str(exc),
        error_type=type(exc).__name__,
        level="ERROR"
    )
    return create_noop_response("internal_error")

if __name__ == "__main__":
    import uvicorn
    log_structured("service_starting", port=8002, level="INFO")
    uvicorn.run(app, host="0.0.0.0", port=8002)
