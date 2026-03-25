import logging
from typing import Dict, List, Optional
from collections import defaultdict
import time

logger = logging.getLogger(__name__)

class MultiAppStateManager:
    def __init__(self, memory_cap_per_app: int = 1000):
        self.memory_cap_per_app = memory_cap_per_app
        self.app_states = {}  # app_id -> AppState
        self.decision_history = defaultdict(list)  # app_id -> [decisions]
        self.rl_state = defaultdict(dict)  # app_id -> RL state
        self.last_cleanup = time.time()
    
    def get_or_create_app_state(self, app_id: str) -> Dict:
        """Get or create state for an application"""
        if app_id not in self.app_states:
            self.app_states[app_id] = {
                'app_id': app_id,
                'created_at': time.time(),
                'last_decision': None,
                'decision_count': 0,
                'failed_decisions': 0,
                'successful_decisions': 0
            }
            logger.info(f"Created new app state for {app_id}")
        
        return self.app_states[app_id]
    
    def record_decision(self, app_id: str, decision: Dict):
        """Record a decision for an application"""
        self.get_or_create_app_state(app_id)
        
        decision_record = {
            'decision_id': decision.get('decision_id'),
            'action': decision.get('action'),
            'timestamp': time.time(),
            'confidence': decision.get('confidence', 0),
            'decision_type': decision.get('decision_type', 'unknown')
        }
        
        self.decision_history[app_id].append(decision_record)
        self.app_states[app_id]['last_decision'] = decision_record
        self.app_states[app_id]['decision_count'] += 1
        
        # Enforce memory cap
        if len(self.decision_history[app_id]) > self.memory_cap_per_app:
            removed = self.decision_history[app_id].pop(0)
            logger.debug(f"Removed old decision for {app_id}: {removed['decision_id']}")
    
    def update_rl_state(self, app_id: str, state_update: Dict):
        """Update RL state for an application"""
        self.get_or_create_app_state(app_id)
        self.rl_state[app_id].update(state_update)
        logger.debug(f"Updated RL state for {app_id}")
    
    def get_rl_state(self, app_id: str) -> Dict:
        """Get RL state for an application"""
        return self.rl_state.get(app_id, {})
    
    def get_decision_history(self, app_id: str, limit: int = 10) -> List[Dict]:
        """Get recent decision history for an application"""
        history = self.decision_history.get(app_id, [])
        return history[-limit:]
    
    def record_feedback(self, app_id: str, decision_id: str, feedback: Dict):
        """Record feedback for a decision"""
        self.get_or_create_app_state(app_id)
        
        if feedback.get('result_status') == 'success':
            self.app_states[app_id]['successful_decisions'] += 1
        else:
            self.app_states[app_id]['failed_decisions'] += 1
        
        logger.info(f"Recorded feedback for {app_id}/{decision_id}: {feedback['result_status']}")
    
    def get_app_stats(self, app_id: str) -> Dict:
        """Get statistics for an application"""
        if app_id not in self.app_states:
            return None
        
        state = self.app_states[app_id]
        history = self.decision_history.get(app_id, [])
        
        return {
            'app_id': app_id,
            'created_at': state['created_at'],
            'total_decisions': state['decision_count'],
            'successful_decisions': state['successful_decisions'],
            'failed_decisions': state['failed_decisions'],
            'recent_decisions': len(history),
            'last_decision': state['last_decision']
        }
    
    def cleanup_stale_apps(self, stale_threshold_hours: int = 24):
        """Remove stale application states"""
        current_time = time.time()
        stale_threshold = stale_threshold_hours * 3600
        
        stale_apps = []
        for app_id, state in self.app_states.items():
            if current_time - state['created_at'] > stale_threshold:
                stale_apps.append(app_id)
        
        for app_id in stale_apps:
            del self.app_states[app_id]
            del self.decision_history[app_id]
            del self.rl_state[app_id]
            logger.info(f"Cleaned up stale app state: {app_id}")
        
        self.last_cleanup = current_time
        return len(stale_apps)
    
    def get_all_apps_stats(self) -> List[Dict]:
        """Get statistics for all applications"""
        return [self.get_app_stats(app_id) for app_id in self.app_states.keys()]
