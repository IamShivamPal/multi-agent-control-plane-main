import logging
import json
from typing import Dict, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class OrchestratorClient:
    def __init__(self, orchestrator_endpoint: str = "http://localhost:8080"):
        self.orchestrator_endpoint = orchestrator_endpoint
        self.decision_callbacks = []
        self.acknowledgements = {}
    
    def send_decision(self, decision: Dict) -> Dict:
        """
        Send decision to orchestrator.
        In production, this would make HTTP call to orchestrator.
        For now, simulating with local callback.
        """
        decision_id = decision.get('decision_id')
        app_id = decision.get('app_id')
        action = decision.get('action')
        
        callback_payload = {
            'decision_id': decision_id,
            'app_id': app_id,
            'action': action,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        # Simulate orchestrator acknowledgement
        try:
            ack = self._simulate_orchestrator_call(callback_payload)
            self.acknowledgements[decision_id] = ack
            
            log_entry = {
                'decision_id': decision_id,
                'app_id': app_id,
                'decision': action,
                'orchestrator_acknowledged': ack['acknowledged'],
                'ack_timestamp': ack['timestamp'],
                'ack_message': ack.get('message', '')
            }
            
            logger.info(f"Decision sent to orchestrator: {json.dumps(log_entry)}")
            return log_entry
        except Exception as e:
            logger.error(f"Failed to send decision {decision_id}: {str(e)}")
            return {
                'decision_id': decision_id,
                'app_id': app_id,
                'decision': action,
                'orchestrator_acknowledged': False,
                'error': str(e)
            }
    
    def _simulate_orchestrator_call(self, payload: Dict) -> Dict:
        """Simulate orchestrator response"""
        import time
        return {
            'acknowledged': True,
            'timestamp': datetime.now().isoformat(),
            'message': f"Action {payload['action']} scheduled for {payload['app_id']}",
            'execution_id': str(uuid.uuid4())
        }
    
    def get_acknowledgement(self, decision_id: str) -> Optional[Dict]:
        """Retrieve acknowledgement for a decision"""
        return self.acknowledgements.get(decision_id)
    
    def register_callback(self, callback_func):
        """Register callback for decision execution"""
        self.decision_callbacks.append(callback_func)
    
    def notify_callbacks(self, decision: Dict):
        """Notify all registered callbacks"""
        for callback in self.decision_callbacks:
            try:
                callback(decision)
            except Exception as e:
                logger.error(f"Callback execution failed: {str(e)}")
