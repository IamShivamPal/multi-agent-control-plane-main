"""
Action Governance Module
Implements action eligibility, cooldowns, and repetition suppression.

The agent uses this module to determine when NOT to act, enforcing:
1. Action eligibility rules (prerequisites, allowlists)
2. Cooldown periods (minimum time between repeated actions)
3. Repetition suppression (prevent action loops)
"""

import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from collections import deque
from enum import Enum


class GovernanceReason(Enum):
    """Reasons for governance blocking."""
    COOLDOWN_ACTIVE = "cooldown_active"
    REPETITION_LIMIT_EXCEEDED = "repetition_limit_exceeded"
    ACTION_NOT_ELIGIBLE = "action_not_eligible"
    PREREQUISITE_NOT_MET = "prerequisite_not_met"


@dataclass
class GovernanceDecision:
    """Represents an action governance decision."""
    should_block: bool
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'should_block': self.should_block,
            'governance_reason': self.reason,
            'governance_details': self.details
        }


@dataclass
class ActionRecord:
    """Record of an action execution."""
    action: str
    timestamp: float
    context: Dict[str, Any]


class ActionGovernance:
    """Action governance system for autonomous agents.
    
    Enforces rules about when actions should NOT be executed:
    - Cooldowns: Minimum time between repeated actions
    - Repetition: Prevent action loops
    - Eligibility: Action prerequisites and allowlists
    """
    
    # Default cooldown periods (in seconds) for each action
    DEFAULT_COOLDOWNS = {
        'restart': 60,      # 1 minute between restarts
        'scale_up': 120,    # 2 minutes between scale-ups
        'scale_down': 120,  # 2 minutes between scale-downs
        'rollback': 300,    # 5 minutes between rollbacks
        'noop': 0,          # No cooldown for noop
    }
    
    # Repetition limits: max occurrences within time window
    DEFAULT_REPETITION_LIMIT = 3
    DEFAULT_REPETITION_WINDOW = 300  # 5 minutes
    
    def __init__(
        self,
        env: str = 'dev',
        cooldown_periods: Optional[Dict[str, int]] = None,
        repetition_limit: int = DEFAULT_REPETITION_LIMIT,
        repetition_window: int = DEFAULT_REPETITION_WINDOW
    ):
        """Initialize action governance.
        
        Args:
            env: Environment name (dev, stage, prod)
            cooldown_periods: Custom cooldown periods per action
            repetition_limit: Max identical actions within window
            repetition_window: Time window for repetition check (seconds)
        """
        self.env = env
        self.cooldown_periods = cooldown_periods or self.DEFAULT_COOLDOWNS
        self.repetition_limit = repetition_limit
        self.repetition_window = repetition_window
        
        # Track last execution time for each action
        self._last_execution: Dict[str, float] = {}
        
        # Track action history (sliding window)
        self._action_history: deque = deque(maxlen=100)
        
        # Environment-specific eligibility rules
        self._eligibility_rules = {
            'prod': ['noop', 'restart'],  # Production frozen mode: noop-first, restart only
            'stage': ['restart', 'noop', 'scale_up', 'scale_down'],  # Stage: safe actions
            'dev': ['restart', 'scale_up', 'noop', 'scale_down', 'rollback']  # Dev: all actions
        }
    
    def evaluate_action(
        self,
        action: str,
        context: Dict[str, Any],
        source: Optional[str] = None
    ) -> GovernanceDecision:
        """Evaluate whether action should be allowed.
        
        Checks in priority order:
        1. Action eligibility
        2. Cooldown enforcement
        3. Repetition suppression
        
        Args:
            action: Action name to evaluate
            context: Action context
            source: Source identifier
            
        Returns:
            GovernanceDecision indicating allow/block
        """
        current_time = time.time()
        
        # Rule 1: Check action eligibility
        decision = self._check_eligibility(action, context)
        if decision.should_block:
            return decision
        
        # Rule 2: Check cooldown
        decision = self._check_cooldown(action, current_time)
        if decision.should_block:
            return decision
        
        # Rule 3: Check repetition
        decision = self._check_repetition(action, current_time)
        if decision.should_block:
            return decision
        
        # All checks passed - record action and allow
        self._record_action(action, current_time, context)
        return GovernanceDecision(should_block=False)
    
    def _check_eligibility(
        self,
        action: str,
        context: Dict[str, Any]
    ) -> GovernanceDecision:
        """Check if action is eligible for execution.
        
        Args:
            action: Action name
            context: Action context
            
        Returns:
            GovernanceDecision
        """
        allowed_actions = self._eligibility_rules.get(self.env, ['noop'])
        
        if action not in allowed_actions:
            return GovernanceDecision(
                should_block=True,
                reason=GovernanceReason.ACTION_NOT_ELIGIBLE.value,
                details={
                    'action': action,
                    'env': self.env,
                    'allowed_actions': allowed_actions,
                    'message': f'Action {action} not eligible in {self.env} environment'
                }
            )
        
        # Check prerequisites (e.g., app must exist to be restarted)
        prerequisite_check = self._check_prerequisites(action, context)
        if prerequisite_check.should_block:
            return prerequisite_check
        
        return GovernanceDecision(should_block=False)
    
    def _check_prerequisites(
        self,
        action: str,
        context: Dict[str, Any]
    ) -> GovernanceDecision:
        """Check action-specific prerequisites.
        
        Args:
            action: Action name
            context: Action context
            
        Returns:
            GovernanceDecision
        """
        # For restart/scale actions, app should exist
        if action in ['restart', 'scale_up', 'scale_down']:
            app_name = context.get('app_name')
            if not app_name:
                return GovernanceDecision(
                    should_block=True,
                    reason=GovernanceReason.PREREQUISITE_NOT_MET.value,
                    details={
                        'action': action,
                        'missing_prerequisite': 'app_name',
                        'message': f'Action {action} requires app_name in context'
                    }
                )
        
        # For rollback, previous version should exist
        if action == 'rollback':
            has_previous = context.get('has_previous_version', True)
            if not has_previous:
                return GovernanceDecision(
                    should_block=True,
                    reason=GovernanceReason.PREREQUISITE_NOT_MET.value,
                    details={
                        'action': action,
                        'missing_prerequisite': 'previous_version',
                        'message': 'Cannot rollback without previous version'
                    }
                )
        
        return GovernanceDecision(should_block=False)
    
    def _check_cooldown(
        self,
        action: str,
        current_time: float
    ) -> GovernanceDecision:
        """Check if action is on cooldown.
        
        Args:
            action: Action name
            current_time: Current timestamp
            
        Returns:
            GovernanceDecision
        """
        cooldown_period = self.cooldown_periods.get(action, 0)
        
        if cooldown_period == 0:
            return GovernanceDecision(should_block=False)
        
        last_execution = self._last_execution.get(action)
        
        if last_execution:
            time_since_last = current_time - last_execution
            if time_since_last < cooldown_period:
                time_remaining = cooldown_period - time_since_last
                return GovernanceDecision(
                    should_block=True,
                    reason=GovernanceReason.COOLDOWN_ACTIVE.value,
                    details={
                        'action': action,
                        'last_execution': last_execution,
                        'cooldown_period': f'{cooldown_period}s',
                        'time_since_last': f'{time_since_last:.1f}s',
                        'time_remaining': f'{time_remaining:.1f}s',
                        'message': f'Action {action} on cooldown for {time_remaining:.1f}s'
                    }
                )
        
        return GovernanceDecision(should_block=False)
    
    def _check_repetition(
        self,
        action: str,
        current_time: float
    ) -> GovernanceDecision:
        """Check if action is being repeated too frequently.
        
        Args:
            action: Action name
            current_time: Current timestamp
            
        Returns:
            GovernanceDecision
        """
        # Get recent actions within the repetition window
        cutoff_time = current_time - self.repetition_window
        recent_actions = [
            record for record in self._action_history
            if record.timestamp > cutoff_time and record.action == action
        ]
        
        if len(recent_actions) >= self.repetition_limit:
            return GovernanceDecision(
                should_block=True,
                reason=GovernanceReason.REPETITION_LIMIT_EXCEEDED.value,
                details={
                    'action': action,
                    'action_history': [r.action for r in recent_actions],
                    'window': f'{self.repetition_window}s',
                    'limit': self.repetition_limit,
                    'actual': len(recent_actions),
                    'message': f'Action {action} repeated {len(recent_actions)} times in {self.repetition_window}s (limit: {self.repetition_limit})'
                }
            )
        
        return GovernanceDecision(should_block=False)
    
    def _record_action(
        self,
        action: str,
        timestamp: float,
        context: Dict[str, Any]
    ):
        """Record action execution.
        
        Args:
            action: Action name
            timestamp: Execution timestamp
            context: Action context
        """
        # Update last execution time
        self._last_execution[action] = timestamp
        
        # Add to history
        record = ActionRecord(
            action=action,
            timestamp=timestamp,
            context=context
        )
        self._action_history.append(record)
    
    def get_action_history(
        self,
        action: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent action history.
        
        Args:
            action: Filter by action name (None for all)
            limit: Max number of records
            
        Returns:
            List of action records
        """
        history = list(self._action_history)
        
        if action:
            history = [r for r in history if r.action == action]
        
        # Return most recent first
        history.reverse()
        history = history[:limit]
        
        return [
            {
                'action': r.action,
                'timestamp': r.timestamp,
                'context': r.context
            }
            for r in history
        ]
    
    def reset(self):
        """Reset governance state (useful for testing)."""
        self._last_execution.clear()
        self._action_history.clear()
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration.
        
        Returns:
            Configuration dictionary
        """
        return {
            'env': self.env,
            'cooldown_periods': self.cooldown_periods,
            'repetition_limit': self.repetition_limit,
            'repetition_window': self.repetition_window,
            'eligibility_rules': self._eligibility_rules.get(self.env, [])
        }


def get_governance(env: str = 'dev') -> ActionGovernance:
    """Get action governance instance.
    
    Args:
        env: Environment name
        
    Returns:
        ActionGovernance instance
    """
    return ActionGovernance(env=env)
