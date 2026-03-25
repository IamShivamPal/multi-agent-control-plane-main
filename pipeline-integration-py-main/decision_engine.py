import logging
import json
import uuid
from typing import Dict, Tuple
from datetime import datetime
import time

from runtime_contract import RuntimeState, Decision, ActionType, SignalType
from action_scope_enforcer import ActionScopeEnforcer
from orchestrator_client import OrchestratorClient
from multi_app_state import MultiAppStateManager

logger = logging.getLogger(__name__)

class DecisionEngine:
    def __init__(self):
        self.action_scope_enforcer = ActionScopeEnforcer()
        self.orchestrator_client = OrchestratorClient()
        self.app_state_manager = MultiAppStateManager()
        self.decision_log = []
        self.false_positive_dampening = {}  # app_id -> {action -> last_time}
    
    def process_runtime_state(self, runtime_state: RuntimeState) -> Dict:
        """
        CANONICAL DECISION PIPELINE
        
        Flow:
        1. Receive runtime state
        2. Normalize payload
        3. Generate decision (rule-based or RL)
        4. Enforce action scope
        5. Relay to orchestrator
        6. Log decision
        """
        
        app_id = runtime_state.app_id
        logger.info(f"=== DECISION PIPELINE START for {app_id} ===")
        
        # Step 1: Validate runtime state
        if not self._validate_runtime_state(runtime_state):
            logger.error(f"Invalid runtime state for {app_id}")
            return {'error': 'invalid_runtime_state', 'app_id': app_id}
        
        # Step 2: Normalize payload (already normalized in RuntimeState)
        normalized_state = runtime_state.to_dict()
        logger.debug(f"Normalized state: {json.dumps(normalized_state, default=str)}")
        
        # Step 3: Generate decision
        decision = self._generate_decision(runtime_state)
        logger.info(f"Decision generated: {decision.action} (confidence: {decision.confidence})")
        
        # Step 4: Enforce action scope
        enforced_decision, enforcement_log = self.action_scope_enforcer.enforce(
            decision, 
            runtime_state.environment
        )
        logger.info(f"Action scope enforcement: {json.dumps(enforcement_log)}")
        
        # Step 5: Relay to orchestrator
        orchestrator_response = self.orchestrator_client.send_decision(enforced_decision.to_dict())
        logger.info(f"Orchestrator response: {json.dumps(orchestrator_response)}")
        
        # Step 6: Log decision
        decision_log_entry = {
            'decision_id': enforced_decision.decision_id,
            'app_id': app_id,
            'action_requested': decision.action,
            'action_emitted': enforced_decision.action,
            'environment': runtime_state.environment,
            'enforcement_log': enforcement_log,
            'orchestrator_acknowledged': orchestrator_response.get('orchestrator_acknowledged'),
            'timestamp': datetime.now().isoformat(),
            'decision_type': enforced_decision.decision_type
        }
        
        self.decision_log.append(decision_log_entry)
        self.app_state_manager.record_decision(app_id, enforced_decision.to_dict())
        
        logger.info(f"=== DECISION PIPELINE END for {app_id} ===")
        
        return decision_log_entry
    
    def _validate_runtime_state(self, state: RuntimeState) -> bool:
        """Validate required fields in runtime state"""
        required_fields = [
            'app_id', 'current_replicas', 'desired_replicas',
            'cpu_usage', 'memory_usage', 'error_rate', 'environment'
        ]
        
        for field in required_fields:
            if not hasattr(state, field):
                logger.error(f"Missing required field: {field}")
                return False
        
        return True
    
    def _generate_decision(self, state: RuntimeState) -> Decision:
        """
        Generate decision using rule-based logic.
        Can be extended with RL logic.
        """
        decision_id = str(uuid.uuid4())
        timestamp = time.time()
        
        # Rule-based decision logic
        action = ActionType.NOOP.value
        reason = "No action needed"
        confidence = 0.5
        decision_type = "rule_based"
        
        # Rule 1: High CPU usage
        if state.cpu_usage > 0.8:
            action = ActionType.SCALE_UP.value
            reason = f"CPU usage high: {state.cpu_usage:.2%}"
            confidence = 0.9
        
        # Rule 2: High memory usage
        elif state.memory_usage > 0.85:
            action = ActionType.SCALE_UP.value
            reason = f"Memory usage high: {state.memory_usage:.2%}"
            confidence = 0.85
        
        # Rule 3: High error rate
        elif state.error_rate > 0.05:
            action = ActionType.RESTART.value
            reason = f"Error rate high: {state.error_rate:.2%}"
            confidence = 0.8
        
        # Rule 4: High latency
        elif state.latency_p99 > 1000:  # ms
            action = ActionType.SCALE_UP.value
            reason = f"P99 latency high: {state.latency_p99:.0f}ms"
            confidence = 0.75
        
        # Rule 5: Low resource usage - scale down
        elif (state.cpu_usage < 0.2 and state.memory_usage < 0.3 and 
              state.current_replicas > state.desired_replicas):
            action = ActionType.SCALE_DOWN.value
            reason = "Low resource usage, scaling down"
            confidence = 0.7
        
        # Check false positive dampening
        if self._should_dampen_decision(state.app_id, action):
            action = ActionType.NOOP.value
            reason = f"Decision dampened to prevent cascading actions"
            confidence = 0.5
        
        return Decision(
            decision_id=decision_id,
            app_id=state.app_id,
            action=action,
            reason=reason,
            confidence=confidence,
            timestamp=timestamp,
            decision_type=decision_type
        )
    
    def _should_dampen_decision(self, app_id: str, action: str) -> bool:
        """
        Prevent aggressive or repeated decisions within short time intervals.
        False-positive dampening.
        """
        if action == ActionType.NOOP.value:
            return False
        
        if app_id not in self.false_positive_dampening:
            self.false_positive_dampening[app_id] = {}
        
        last_time = self.false_positive_dampening[app_id].get(action, 0)
        current_time = time.time()
        
        # Minimum 60 seconds between same actions
        if current_time - last_time < 60:
            logger.warning(f"Dampening {action} for {app_id} - too soon after last action")
            return True
        
        self.false_positive_dampening[app_id][action] = current_time
        return False
    
    def record_feedback(self, decision_id: str, feedback: Dict):
        """Record feedback for learning (DEV only)"""
        # Find decision in log
        decision_log = next(
            (d for d in self.decision_log if d['decision_id'] == decision_id),
            None
        )
        
        if not decision_log:
            logger.error(f"Decision not found: {decision_id}")
            return
        
        app_id = decision_log['app_id']
        self.app_state_manager.record_feedback(app_id, decision_id, feedback)
        
        logger.info(f"Feedback recorded for {decision_id}: {feedback['result_status']}")
    
    def get_decision_logs(self, app_id: str = None, limit: int = 50) -> list:
        """Retrieve decision logs"""
        logs = self.decision_log
        
        if app_id:
            logs = [d for d in logs if d['app_id'] == app_id]
        
        return logs[-limit:]
    
    def get_app_stats(self, app_id: str) -> Dict:
        """Get statistics for an application"""
        return self.app_state_manager.get_app_stats(app_id)
