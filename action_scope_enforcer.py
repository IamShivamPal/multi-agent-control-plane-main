import logging
from typing import Dict, Tuple
from runtime_contract import ActionType, Decision

logger = logging.getLogger(__name__)

class ActionScopeEnforcer:
    def __init__(self):
        self.action_limits = {
            'dev': {
                'scale_up': {'max_replicas': 5, 'rate_limit_per_hour': 10},
                'scale_down': {'min_replicas': 1, 'rate_limit_per_hour': 10},
                'restart': {'rate_limit_per_hour': 20},
                'rollback': {'rate_limit_per_hour': 5}
            },
            'staging': {
                'scale_up': {'max_replicas': 10, 'rate_limit_per_hour': 5},
                'scale_down': {'min_replicas': 2, 'rate_limit_per_hour': 5},
                'restart': {'rate_limit_per_hour': 10},
                'rollback': {'rate_limit_per_hour': 3}
            },
            'prod': {
                'scale_up': {'max_replicas': 50, 'rate_limit_per_hour': 2},
                'scale_down': {'min_replicas': 3, 'rate_limit_per_hour': 1},
                'restart': {'rate_limit_per_hour': 2},
                'rollback': {'rate_limit_per_hour': 1}
            }
        }
        self.action_history = {}  # app_id -> [(action, timestamp), ...]
    
    def enforce(self, decision: Decision, environment: str) -> Tuple[Decision, Dict]:
        """
        Enforce action scope on decision.
        Returns: (modified_decision, enforcement_log)
        """
        enforcement_log = {
            'action_requested': decision.action,
            'environment': environment,
            'action_allowed': True,
            'action_emitted': decision.action,
            'reason': 'allowed'
        }
        
        # Check if action is valid for environment
        if decision.action not in self.action_limits.get(environment, {}):
            enforcement_log['action_allowed'] = False
            enforcement_log['action_emitted'] = ActionType.NOOP.value
            enforcement_log['reason'] = f'action {decision.action} not allowed in {environment}'
            decision.action = ActionType.NOOP.value
            logger.warning(f"Action {enforcement_log['action_requested']} blocked: {enforcement_log['reason']}")
            return decision, enforcement_log
        
        # Check rate limits
        app_id = decision.app_id
        if not self._check_rate_limit(app_id, decision.action, environment):
            enforcement_log['action_allowed'] = False
            enforcement_log['action_emitted'] = ActionType.NOOP.value
            enforcement_log['reason'] = f'rate limit exceeded for {decision.action}'
            decision.action = ActionType.NOOP.value
            logger.warning(f"Action {enforcement_log['action_requested']} rate limited: {enforcement_log['reason']}")
            return decision, enforcement_log
        
        # Record action
        if app_id not in self.action_history:
            self.action_history[app_id] = []
        
        import time
        self.action_history[app_id].append((decision.action, time.time()))
        
        logger.info(f"Action {decision.action} allowed for {app_id} in {environment}")
        return decision, enforcement_log
    
    def _check_rate_limit(self, app_id: str, action: str, environment: str) -> bool:
        """Check if action is within rate limits"""
        import time
        current_time = time.time()
        hour_ago = current_time - 3600
        
        if app_id not in self.action_history:
            return True
        
        recent_actions = [
            (act, ts) for act, ts in self.action_history[app_id]
            if ts > hour_ago and act == action
        ]
        
        limit = self.action_limits[environment][action]['rate_limit_per_hour']
        return len(recent_actions) < limit
    
    def get_enforcement_stats(self, app_id: str) -> Dict:
        """Get enforcement statistics for an app"""
        if app_id not in self.action_history:
            return {'app_id': app_id, 'total_actions': 0, 'actions': {}}
        
        import time
        current_time = time.time()
        hour_ago = current_time - 3600
        
        recent = [
            act for act, ts in self.action_history[app_id]
            if ts > hour_ago
        ]
        
        action_counts = {}
        for action in recent:
            action_counts[action] = action_counts.get(action, 0) + 1
        
        return {
            'app_id': app_id,
            'total_actions_last_hour': len(recent),
            'actions': action_counts
        }
