"""
Runtime Service - Event Emitter
Port: 8001
Responsibility: Emit events and orchestrate full flow
"""

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ValidationError
from typing import Dict, Any, Optional
import requests
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

app = FastAPI(title="Runtime Service", version="1.0.0")

# Service URLs from environment
AGENT_URL = os.getenv("AGENT_URL", "http://localhost:8002")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8003")
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "3"))  # Hardened: 3-second max timeout
ORCHESTRATOR_TIMEOUT = int(os.getenv("ORCHESTRATOR_TIMEOUT", "3"))

#Models
class RuntimeEvent(BaseModel):
    event_type: str
    app: str
    env: str
    metadata: Optional[Dict[str, Any]] = {}

class EventResponse(BaseModel):
    status: str
    event_id: str
    agent_decision: Optional[Dict[str, Any]] = None
    orchestrator_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    fallback: Optional[str] = None

def log_structured(event: str, **kwargs):
    """Log in structured JSON format"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "runtime",
        "event": event,
        **kwargs
    }
    logger.info(json.dumps(log_entry))

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "runtime", "version": "1.0.0"}

@app.post("/emit", response_model=EventResponse)
async def emit_event(event: RuntimeEvent):
    """
    Emit runtime event and orchestrate full decision → execution flow
    
    Graceful degradation:
    - If Agent down → fallback to NOOP
    - If Orchestrator down → log error but don't crash
    """
    event_id = f"evt_{uuid.uuid4().hex[:8]}"
    
    log_structured(
        "event_emitted",
        event_id=event_id,
        event_type=event.event_type,
        app=event.app,
        env=event.env,
        level="INFO"
    )
    
    # Step 1: Call Agent for decision (HARDENED)
    agent_decision = None
    try:
        agent_payload = {
            "event_type": event.event_type,
            "app": event.app,
            "env": event.env,
            "state": event.metadata.get("state", "unknown"),
            "metrics": event.metadata
        }
        
        log_structured(
            "calling_agent",
            event_id=event_id,
            agent_url=f"{AGENT_URL}/decide",
            timeout=AGENT_TIMEOUT,
            level="INFO"
        )
        
        # Hardened REST call with 3-second timeout
        response = requests.post(
            f"{AGENT_URL}/decide",
            json=agent_payload,
            timeout=AGENT_TIMEOUT  # Max 3 seconds
        )
        response.raise_for_status()
        agent_decision = response.json()
        
        log_structured(
            "agent_response_received",
            event_id=event_id,
            decision=agent_decision.get("decision"),
            reason=agent_decision.get("reason"),
            level="INFO"
        )
        
    except requests.Timeout as e:
        # Timeout after 3 seconds
        log_structured(
            "agent_timeout",
            event_id=event_id,
            error=f"Agent timeout after {AGENT_TIMEOUT}s",
            error_type="Timeout",
            level="WARNING"
        )
        logger.warning(f"[Runtime] Agent unreachable – executing NOOP (timeout)")
        
        # Return safe NOOP fallback with 200 OK
        return EventResponse(
            status="degraded",
            event_id=event_id,
            agent_decision={
                "decision": "noop",
                "reason": "agent_unavailable",
                "confidence": 0.0,
                "metadata": {"fallback": "timeout"}
            },
            error="agent_timeout",
            fallback="noop"
        )
        
    except requests.ConnectionError as e:
        # Agent service not running or unreachable
        log_structured(
            "agent_connection_error",
            event_id=event_id,
            error=str(e),
            error_type="ConnectionError",
            level="WARNING"
        )
        logger.warning(f"[Runtime] Agent unreachable – executing NOOP (connection error)")
        
        # Return safe NOOP fallback with 200 OK
        return EventResponse(
            status="degraded",
            event_id=event_id,
            agent_decision={
                "decision": "noop",
                "reason": "agent_unavailable",
                "confidence": 0.0,
                "metadata": {"fallback": "connection_error"}
            },
            error="agent_connection_error",
            fallback="noop"
        )
        
    except requests.HTTPError as e:
        # Agent returned 4xx or 5xx error
        log_structured(
            "agent_http_error",
            event_id=event_id,
            error=str(e),
            error_type="HTTPError",
            status_code=e.response.status_code if e.response else None,
            level="WARNING"
        )
        logger.warning(f"[Runtime] Agent unreachable – executing NOOP (HTTP error)")
        
        # Return safe NOOP fallback with 200 OK
        return EventResponse(
            status="degraded",
            event_id=event_id,
            agent_decision={
                "decision": "noop",
                "reason": "agent_unavailable",
                "confidence": 0.0,
                "metadata": {"fallback": "http_error"}
            },
            error="agent_http_error",
            fallback="noop"
        )
        
    except requests.RequestException as e:
        # Catch-all for any other requests exceptions
        log_structured(
            "agent_request_exception",
            event_id=event_id,
            error=str(e),
            error_type=type(e).__name__,
            level="WARNING"
        )
        logger.warning(f"[Runtime] Agent unreachable – executing NOOP (request exception)")
        
        # Return safe NOOP fallback with 200 OK
        return EventResponse(
            status="degraded",
            event_id=event_id,
            agent_decision={
                "decision": "noop",
                "reason": "agent_unavailable",
                "confidence": 0.0,
                "metadata": {"fallback": "request_exception"}
            },
            error="agent_unavailable",
            fallback="noop"
        )
        
    except Exception as e:
        # Final safety net for any unexpected errors
        log_structured(
            "agent_unexpected_error",
            event_id=event_id,
            error=str(e),
            error_type=type(e).__name__,
            level="ERROR"
        )
        logger.error(f"[Runtime] Agent unreachable – executing NOOP (unexpected error)")
        
        # Return safe NOOP fallback with 200 OK
        return EventResponse(
            status="degraded",
            event_id=event_id,
            agent_decision={
                "decision": "noop",
                "reason": "agent_unavailable",
                "confidence": 0.0,
                "metadata": {"fallback": "unexpected_error"}
            },
            error="agent_unexpected_error",
            fallback="noop"
        )
    
    # Step 2: Call Orchestrator for execution
    orchestrator_result = None
    if agent_decision:
        try:
            orchestrator_payload = {
                "action": agent_decision.get("decision"),
                "app": event.app,
                "env": event.env,
                "requested_by": "agent",
                "decision_metadata": {
                    "confidence": agent_decision.get("confidence", 0.0),
                    "reason": agent_decision.get("reason")
                }
            }
            
            log_structured(
                "calling_orchestrator",
                event_id=event_id,
                orchestrator_url=f"{ORCHESTRATOR_URL}/execute",
                action=orchestrator_payload["action"],
                level="INFO"
            )
            
            response = requests.post(
                f"{ORCHESTRATOR_URL}/execute",
                json=orchestrator_payload,
                timeout=ORCHESTRATOR_TIMEOUT
            )
            response.raise_for_status()
            orchestrator_result = response.json()
            
            log_structured(
                "orchestrator_response_received",
                event_id=event_id,
                status=orchestrator_result.get("status"),
                execution_id=orchestrator_result.get("execution_id"),
                level="INFO"
            )
            
        except (requests.RequestException, requests.Timeout) as e:
            log_structured(
                "orchestrator_unavailable",
                event_id=event_id,
                error=str(e),
                level="ERROR"
            )
            # Log error but don't crash
            orchestrator_result = {
                "status": "failed",
                "reason": "orchestrator_unavailable"
            }
    
    # Return full chain result
    return EventResponse(
        status="processed",
        event_id=event_id,
        agent_decision=agent_decision,
        orchestrator_result=orchestrator_result
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors gracefully"""
    log_structured(
        "validation_error",
        errors=exc.errors(),
        level="ERROR"
    )
    return {"status": "error", "reason": "invalid_request", "details": exc.errors()}

if __name__ == "__main__":
    import uvicorn
    log_structured("service_starting", port=8001, level="INFO")
    uvicorn.run(app, host="0.0.0.0", port=8001)
