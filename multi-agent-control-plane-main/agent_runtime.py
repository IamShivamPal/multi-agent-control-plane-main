#!/usr/bin/env python3
"""
Agent Runtime - Autonomous AI Agent Core
Main entry point for the multi-agent CI/CD system operating as an autonomous AI agent.

Agent Loop: sense → validate → decide → enforce → act → observe → explain
State Machine: idle → observing → validating → deciding → enforcing → acting → observing_results → explaining → idle
"""

import argparse
import os
import signal
import sys
import time
import uuid
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Core agent modules
from core.agent_state import AgentState, AgentStateManager
from core.agent_logger import AgentLogger
from core.agent_memory import AgentMemory
from core.perception import PerceptionLayer
from core.perception_adapters import (
    RuntimeEventAdapter,
    HealthSignalAdapter,
    OnboardingInputAdapter,
    SystemAlertAdapter
)
from core.self_restraint import SelfRestraint
# ADD THIS IMPORT AT TOP WITH OTHER CORE MODULES
from core.action_governance import ActionGovernance
from core.proof_logger import write_proof, ProofEvents


# Existing system modules
from core.env_config import EnvironmentConfig
from core.runtime_rl_pipe import get_rl_pipe
from core.rl_orchestrator_safe import get_safe_executor
from core.decision_arbitrator import DecisionArbitrator
from auto_scaler import AutoScaler
from agents.multi_deploy_agent import MultiDeployAgent
from core.redis_event_bus import RedisEventBus
from core.event_bus import EventBus
from agents.issue_detector import IssueDetector
from agents.uptime_monitor import UptimeMonitor
from core.runtime_event_validator import RuntimeEventValidator



class AgentRuntime:
    """Autonomous AI Agent Runtime with explicit sense-validate-decide-enforce-act-observe-explain loop."""
    
    def __init__(self, env: str = 'dev', agent_id: Optional[str] = None, loop_interval: float = 5.0):
        """Initialize agent runtime.
        
        Args:
            env: Environment (dev/stage/prod)
            agent_id: Unique agent identifier (auto-generated if None)
            loop_interval: Loop cycle interval in seconds
        """
        # Normalize environment aliases for internal consistency
        if env == 'staging':
            env = 'stage'

        # Initialize production logging first
        if env == 'prod':
            from core.prod_logging import configure_production_logging
            configure_production_logging(level='INFO', format_style='text')
        
        self.agent_id = agent_id or f"agent-{uuid.uuid4().hex[:8]}"
        self.env = env
        self.loop_interval = loop_interval

        self.governance = ActionGovernance(env=self.env)
        # Agent identity
        
        
        # Agent metadata
        self.start_time = datetime.utcnow()
        self.version = "1.0.0"
        self.loop_count = 0
        
        # State management (Recover from last state if possible)
        state_file = Path("logs/agent") / f"agent_state_{self.agent_id}.json"
        if state_file.exists():
            try:
                self.state_manager = AgentStateManager.load_from_file(str(state_file), self.agent_id)
            except Exception:
                self.state_manager = AgentStateManager(self.agent_id)
        else:
            self.state_manager = AgentStateManager(self.agent_id)
        
        # Logging
        from core.agent_logger import AgentLogger
        self.logger = AgentLogger(self.agent_id)
        
        # Memory (Recover from last snapshot if possible)
        memory_file = Path("logs/agent") / f"memory_snapshot_{self.agent_id}.json"
        self.memory = AgentMemory(
            max_decisions=50,
            max_states_per_app=10,
            agent_id=self.agent_id
        )
        if memory_file.exists():
            try:
                self.memory.from_json(str(memory_file))
            except Exception:
                pass # Start with fresh memory if load fails
        
        # Perception layer
        self.perception_layer = PerceptionLayer(self.agent_id)
        
        # Self-restraint module (intentional self-blocking)
        self.self_restraint = SelfRestraint(
            min_confidence=0.6,
            max_instability_score=75,
            max_recent_failures=5
        )
        
        # Environment configuration
        self.env_config = EnvironmentConfig(env)
        
        # System components
        self._initialize_components()
        
        # Execution lock for sync operations
        import threading
        self._loop_lock = threading.Lock()
        
        # Shutdown flag
        self._shutdown_requested = False
        
        # FIX 5: External visibility - track last decision and block reason
        self._last_decision = None
        self._last_block_reason = None
        self._last_block_type = None
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Log initialization
        self.logger.info(
            f"Agent initialized: id={self.agent_id}, env={env}, version={self.version}",
            agent_state=self.state_manager.current_state.value
        )
        self.logger.log_autonomous_operation(
            "agent_initialization",
            {
                "agent_id": self.agent_id,
                "environment": env,
                "version": self.version,
                "loop_interval": loop_interval
            },
            self.state_manager.current_state.value
        )
    
    def _initialize_components(self):
        """Initialize system components."""
        self.logger.info("Initializing system components", agent_state=self.state_manager.current_state.value)
        
        # RL Pipeline
        self.rl_pipe = get_rl_pipe(self.env)
        
        # Safe Executor
        self.safe_executor = get_safe_executor(self.env)
        
        # Event Bus (try Redis, fallback to local)
        try:
            self.event_bus = RedisEventBus(env=self.env)
            self.logger.info("Redis event bus initialized", agent_state=self.state_manager.current_state.value)
        except Exception as e:
            self.logger.warning(
                f"Redis unavailable, using local event bus: {e}",
                agent_state=self.state_manager.current_state.value
            )
            self.event_bus = EventBus()
        
        # Uptime Monitor
        uptime_log_file = self.env_config.get_log_path("uptime_log.csv")
        self.uptime_monitor = UptimeMonitor(timeline_file=uptime_log_file)
        
        # Event Validator
        self.event_validator = RuntimeEventValidator()
        
        # Auto-Scaler & Multi-Deploy Agent (for sensing and rule-based advice)
        self.auto_scaler = AutoScaler(self.env)
        disable_workers = os.getenv("PRAVAH_DISABLE_DEPLOY_WORKERS", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if disable_workers:
            self.auto_scaler.multi_agent = None
        else:
            self.auto_scaler.multi_agent = MultiDeployAgent(self.env, workers=3)
            self.auto_scaler.multi_agent.start_workers()
        
        # Decision Arbitrator
        self.arbitrator = DecisionArbitrator(self.env)
        
        # Issue Detector (will be initialized when needed)
        self.issue_detector = None
        
        # Initialize perception adapters
        self._initialize_perception_adapters()
        
        self.logger.info("All components initialized", agent_state=self.state_manager.current_state.value)
    
    def _initialize_perception_adapters(self):
        """Initialize and register perception adapters."""
        # Runtime events from event bus
        runtime_adapter = RuntimeEventAdapter(self.event_bus)
        self.perception_layer.register_adapter(runtime_adapter)
        
        # Health signals from uptime monitor
        health_adapter = HealthSignalAdapter(self.uptime_monitor)
        self.perception_layer.register_adapter(health_adapter)
        
        # Onboarding input
        self.onboarding_adapter = OnboardingInputAdapter()
        self.perception_layer.register_adapter(self.onboarding_adapter)
        
        # System alerts
        self.alert_adapter = SystemAlertAdapter()
        self.perception_layer.register_adapter(self.alert_adapter)
        
        self.logger.info(
            f"Perception adapters initialized: {len(self.perception_layer.perception_adapters)} adapters",
            agent_state=self.state_manager.current_state.value
        )
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        self.logger.info(
            f"Shutdown signal received: {signum}",
            agent_state=self.state_manager.current_state.value
        )
        self._shutdown_requested = True
    
    def run(self):
        """Run the agent loop continuously."""
        self.logger.info(
            f"Agent runtime starting continuous operation",
            agent_state=self.state_manager.current_state.value
        )
        
        self.logger.log_autonomous_operation(
            "continuous_operation_start",
            {
                "proof": "no_manual_triggers_required",
                "loop_interval": self.loop_interval,
                "autonomous": True
            },
            self.state_manager.current_state.value
        )
        
        try:
            while not self._shutdown_requested:
                with self._loop_lock:
                    self._execute_agent_loop()
                    
                    # Return to idle while still holding the lock (Atomic Cycle)
                    if self.state_manager.current_state != AgentState.IDLE:
                        self.state_manager.transition_to(AgentState.IDLE, "loop_complete")
                
                self.loop_count += 1
                
                # Heartbeat
                uptime = (datetime.utcnow() - self.start_time).total_seconds()
                self.logger.log_heartbeat(self.state_manager.current_state.value, uptime)
                
                time.sleep(self.loop_interval)
        
        except Exception as e:
            self.logger.log_error(
                "agent_loop_error",
                str(e),
                self.state_manager.current_state.value,
                {"exception_type": type(e).__name__}
            )
            raise
        
        finally:
            self._shutdown()
    
    def _execute_agent_loop(self, manual_observation: Optional[Dict[str, Any]] = None):
        """Execute one iteration of the agent loop: sense → validate → decide → enforce → act → observe → explain.
        
        Args:
            manual_observation: Optional external event data to bypass sensing.
        """
        
        # SENSE (Observing)
        if manual_observation:
            observation = manual_observation
            # Only transition to OBSERVING if we are IDLE (atomicity check)
            if self.state_manager.current_state == AgentState.IDLE:
                self.state_manager.transition_to(AgentState.OBSERVING, "manual_event_received")
        else:
            observation = self._sense()
        
        if not observation:
            # No events to process, stay idle
            return
        
        # VALIDATE
        validation_result = self._validate(observation)
        
        if not validation_result['valid']:
            # Invalid data, log and return to idle
            self.logger.log_observation(
                "validation_failed",
                validation_result,
                self.state_manager.current_state.value
            )
            return
        
        # DECIDE
        decision = self._decide(validation_result['validated_data'])
        
        # ENFORCE
        enforcement_result = self._enforce(decision)
        
        if not enforcement_result['allowed']:
            # Action not allowed, log and return to idle
            self.logger.log_observation(
                "action_refused",
                enforcement_result,
                self.state_manager.current_state.value
            )
            return
        
        # FIX 4: Skip ACT phase if status is 'observe' (signal conflict)
        safe_action = enforcement_result.get('safe_action', {})
        execution_result = safe_action.get('execution_result', {})
        
        if execution_result.get('status') == 'observe':
            # Observe-only mode: skip acting, just observe
            self.logger.log_autonomous_operation(
                "observe_only_mode",
                {"reason": execution_result.get('reason', 'signal_conflict')},
                self.state_manager.current_state.value
            )
            # Transition directly to OBSERVING_RESULTS, skip ACT
            observation_result = self._observe({'status': 'observe_mode', 'action': safe_action})
            self._explain(safe_action, {'status': 'observe_mode'}, observation_result)
            return
        
        # ACT
        action_result = self._act(enforcement_result['safe_action'])
        
        # OBSERVE
        observation_result = self._observe(action_result)
        
        # EXPLAIN
        self._explain(decision, action_result, observation_result)
    
    def handle_external_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Force the agent to process a specific external event synchronously.
        Respects the FSM lifecycle and uses the execution lock.
        """
        with self._loop_lock:
            # Skip if agent is shutting down
            if self._shutdown_requested:
                raise RuntimeError("Agent is shutting down")
                
            # Perform single shot loop
            try:
                self._execute_agent_loop(manual_observation=event_data)
            finally:
                # Always return to IDLE after manual cycle
                if self.state_manager.current_state != AgentState.IDLE:
                    self.state_manager.transition_to(AgentState.IDLE, "manual_loop_complete")
            
            # Return the last decision result (stored during _execute_agent_loop via _explain)
            if not self._last_decision:
                return {
                    "status": "error", 
                    "message": "Cycle complete but no decision was explained (partial loop)",
                    "decision": {"action_name": "noop", "source": "fsm_early_exit", "confidence": 0.0}
                }
            return self._last_decision
    
    def _sense(self) -> Optional[Dict[str, Any]]:
        """SENSE: Observe environment for events/changes using perception layer.
        
        Returns:
            Observed data or None if nothing to process
        """
        self.state_manager.transition_to(AgentState.OBSERVING, "sensing_environment")
        self.logger.log_state_transition(
            AgentState.IDLE.value,
            AgentState.OBSERVING.value,
            "sensing_environment"
        )
        
        try:
            # Use perception layer to aggregate all perceptions
            perceptions = self.perception_layer.perceive()
            
            if perceptions:
                # Get highest priority perception
                perception = self.perception_layer.get_highest_priority_perception(perceptions)
                
                self.logger.log_observation(
                    "perception_detected",
                    {
                        "perception_type": perception.type,
                        "priority": perception.priority,
                        "source": perception.source,
                        "data": perception.data
                    },
                    self.state_manager.current_state.value
                )
                
                # RETURN 1: Found a perception event
                return perception.data
            
            # SIDEBAR: Internal Agent Sensors (e.g. Scaling Queue)
            if self.auto_scaler and self.auto_scaler.multi_agent:
                queue_depth = self.auto_scaler.multi_agent.work_queue.qsize()
                
                # If queue is high, synthesize a internal event
                if queue_depth > 5:
                     return {
                         "event_type": "high_queue", 
                         "queue_depth": queue_depth, 
                         "timestamp": datetime.utcnow().isoformat(),
                         "source": "internal_sensor"
                     }

            # RETURN 2: Nothing detected, Agent remains Idle
            return None

        except Exception as e:
            self.logger.log_error("sense_error", str(e), self.state_manager.current_state.value)
            self.state_manager.transition_to(AgentState.BLOCKED, f"sense_error: {e}")
            return None
    
    def _validate(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """VALIDATE: Validate observed data.
        
        Args:
            observation: Observed data
            
        Returns:
            Validation result with 'valid' flag and 'validated_data'
        """
        self.state_manager.transition_to(AgentState.VALIDATING, "validating_observation")
        self.logger.log_state_transition(
            AgentState.OBSERVING.value,
            AgentState.VALIDATING.value,
            "validating_observation"
        )
        
        try:
            # Use existing validation
            from core.runtime_event_validator import validate_and_log_payload
            
            is_valid, validated_data, error_msg = validate_and_log_payload(
                observation,
                "AGENT_SENSE"
            )
            
            result = {
                'valid': is_valid,
                'validated_data': validated_data if is_valid else observation,
                'error_message': error_msg
            }
            
            self.logger.log_observation(
                "validation_result",
                result,
                self.state_manager.current_state.value
            )
            
            return result
        
        except Exception as e:
            self.logger.log_error(
                "validation_error",
                str(e),
                self.state_manager.current_state.value
            )
            return {'valid': False, 'error_message': str(e)}
    
    def _decide(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """DECIDE: Make decision using memory-influenced logic.
        
        Memory actively influences decisions through:
        1. Pre-decision override checks (failures, repetition, instability)
        2. Memory signals passed to decision logic
        3. Logged memory influence on every decision
        
        Args:
            validated_data: Validated observation data
            
        Returns:
            Decision with action recommendation and memory influence
        """
        self.state_manager.transition_to(AgentState.DECIDING, "making_decision")
        self.logger.log_state_transition(
            AgentState.VALIDATING.value,
            AgentState.DECIDING.value,
            "making_decision"
        )
        
        try:
            # Extract entity ID for memory context
            app_id = validated_data.get('app_id', None)
            
            # STEP 1: Check if memory suggests overriding the decision
            override_check = self.memory.should_override_decision(
                entity_id=app_id,
                failure_threshold=3,
                repetition_threshold=3
            )
            
            memory_signals = override_check['memory_signals']
            
            # Log memory signals being used
            self.logger.info(
                f"Memory signals extracted: failures={memory_signals['recent_failures']}, "
                f"repeated={memory_signals['repeated_actions']}, "
                f"instability={memory_signals['instability_score']}",
                agent_state=self.state_manager.current_state.value
            )
            
            # STEP 2: Apply memory override if triggered
            if override_check['override_applied']:
                decision = {
                    'rl_action': 0,  # NOOP
                    'override_applied': True,
                    'override_decision': override_check['override_decision'],
                    'override_reason': override_check['override_reason'],
                    'timestamp': datetime.utcnow().isoformat(),
                    'input_data': validated_data,
                    'memory_signals_used': {
                        'recent_failures': memory_signals['recent_failures'],
                        'recent_actions': memory_signals['recent_actions'],
                        'repeated_actions': memory_signals['repeated_actions'],
                        'instability_score': memory_signals['instability_score'],
                        'last_action_outcome': memory_signals['last_action_outcome'],
                        'override_applied': True
                    },
                    'execution_result': {
                        'status': 'refused',
                        'reason': override_check['override_reason']
                    }
                }
                
                self.logger.log_decision(
                    "memory_override_decision",
                    decision,
                    self.state_manager.current_state.value
                )
                
                # Remember this memory-overridden decision
                self.memory.remember_decision(
                    decision_type="memory_override",
                    decision_data=decision,
                    outcome="refused",
                    context=validated_data
                )
                
                return decision
            
            # STEP 3: Check self-restraint rules (intentional self-blocking)
            restraint_check = self.self_restraint.evaluate_block(
                decision_data=None,  # No decision made yet
                memory_signals=memory_signals,
                health_signals=validated_data.get('health', None)
            )
            
            if restraint_check.should_block:
                # Transition to BLOCKED state (self-imposed)
                self.state_manager.transition_to(AgentState.BLOCKED, restraint_check.reason)
                
                decision = {
                    'action_name': 'noop',
                    'source': 'self_restraint',
                    'confidence': 1.0,
                    'rl_action': 0,  # NOOP
                    'self_blocked': True,
                    'block_reason': restraint_check.reason,
                    'block_details': restraint_check.details,
                    'self_imposed': True,
                    'timestamp': datetime.utcnow().isoformat(),
                    'input_data': validated_data,
                    'memory_signals_used': {
                        'recent_failures': memory_signals['recent_failures'],
                        'repeated_actions': memory_signals['repeated_actions'],
                        'instability_score': memory_signals['instability_score']
                    },
                    'execution_result': {
                        'status': 'blocked',
                        'reason': restraint_check.reason
                    }
                }
                
                self.logger.info(
                    f"SELF-BLOCKED: {restraint_check.reason} - {restraint_check.details}",
                    agent_state="blocked"
                )
                
                self.logger.log_decision(
                    "self_restraint_block",
                    decision,
                    "blocked"
                )
                
                # Remember this self-blocked decision
                self.memory.remember_decision(
                    decision_type="self_blocked",
                    decision_data=decision,
                    outcome="blocked",
                    context=validated_data
                )
                
                return decision

            # STEP 4: EVENT-POLICY MAPPING (Deterministic closed-loop behavior)
            if self.env == 'prod':
                event_policy_action_map = {
                    'crash': 'restart',
                    'critical_system_failure': 'restart',
                    'overload': 'noop',
                    'false_alarm': 'noop'
                }
            else:
                event_policy_action_map = {
                    'crash': 'restart',
                    'overload': 'scale_up',
                    'false_alarm': 'noop'
                }
            event_type = validated_data.get('event_type')
            policy_action = event_policy_action_map.get(event_type)

            if policy_action is not None:
                action_map_rev = {"noop": 0, "restart": 1, "scale_up": 2, "scale_down": 3, "rollback": 4}
                decision = {
                    'rl_action': action_map_rev.get(policy_action, 0),
                    'action_name': policy_action,
                    'source': 'runtime_event_policy',
                    'reason': f'event_policy:{event_type}',
                    'confidence': 1.0,
                    'execution_result': {},
                    'timestamp': datetime.utcnow().isoformat(),
                    'input_data': validated_data,
                    'override_applied': False,
                    'memory_signals_used': memory_signals
                }

                self._last_decision = decision['action_name']
                self._last_block_reason = decision['reason']
                self._last_block_type = None

                self.logger.log_decision(
                    "event_policy_decision",
                    decision,
                    self.state_manager.current_state.value
                )

                write_proof(ProofEvents.RL_DECISION, {
                    'env': self.env,
                    'event_type': event_type,
                    'decision_str': decision.get('action_name', 'noop'),
                    'source': decision.get('source', 'unknown'),
                    'confidence': decision.get('confidence', 1.0),
                    'status': 'decided'
                })

                self.memory.remember_decision(
                    decision_type="event_policy_decision",
                    decision_data=decision,
                    outcome="pending",
                    context=validated_data
                )

                return decision
            
            # STEP 5: GATHER SUGGESTIONS (Ownership Boundary Gap 7)
            # The Agent Runtime is the orchestrator. RL and Rules are advisors.
            
            # Advisor 1: RL Brain (Stateless, Suggester)
            rl_suggestion = self.rl_pipe.get_decision(
                event_data=validated_data,
                agent_state=self.state_manager.current_state.value,
                memory_context=memory_signals
            )
            
            # Advisor 2: AutoScaler Rules (Heuristic Suggester)
            queue_depth = 0
            if self.auto_scaler and self.auto_scaler.multi_agent:
                queue_depth = self.auto_scaler.multi_agent.work_queue.qsize()
            
            rule_recommendation = self.auto_scaler.get_recommendation(queue_depth)

            # STEP 6: ARBITRATE BETWEEN ADVISORS
            arbitrated_result = self.arbitrator.arbitrate(
                rl_decision=rl_suggestion,
                rule_decision=rule_recommendation,
                context={
                    'env': self.env,
                    'queue_depth': queue_depth,
                    'app_id': validated_data.get('app_id'),
                    'event_type': validated_data.get('event_type')
                }
            )
            
            # STEP 7: FINALIZE DECISION
            decision = {
                'rl_action': 0, # Placeholder
                'action_name': arbitrated_result['action'],
                'source': arbitrated_result['source'],
                'reason': arbitrated_result['reason'],
                'confidence': arbitrated_result['confidence'],
                'execution_result': {}, # Not executed yet
                'timestamp': datetime.utcnow().isoformat(),
                'input_data': validated_data,
                'override_applied': False,
                'memory_signals_used': memory_signals
            }
            
            # Update last decision for visibility
            self._last_decision = decision['action_name']
            self._last_block_reason = decision['reason']
            self._last_block_type = None
            
            self.logger.log_decision(
                "arbitrated_decision",
                decision,
                self.state_manager.current_state.value
            )
            
            # PROOF LOGGING (Required for Dashboard Gap 5)
            write_proof(ProofEvents.RL_DECISION, {
                'env': self.env,
                'event_type': validated_data.get('event_type', 'unknown'),
                'decision_str': decision.get('action_name', 'noop'),
                'source': decision.get('source', 'unknown'),
                'confidence': decision.get('confidence', 1.0),
                'status': 'decided'
            })
            
            # Prepare for enforcement loop
            action_map_rev = {"noop": 0, "restart": 1, "scale_up": 2, "scale_down": 3, "rollback": 4}
            decision['rl_action'] = action_map_rev.get(decision['action_name'], 0)
            
            # The Agent is the ultimate decision maker.
            # It can choose to block its own decision based on self-restraint rules.
            
            # STEP 8: SELF-RESTRAINT SAFETY GATE (Gap 7 Ownership)
            # The Agent checks its own uncertainty before proceeding.
            confidence = decision.get("confidence", 1.0)

            uncertainty_check = self.self_restraint.check_uncertainty(
                decision_data={"confidence": confidence},
                uncertainty_threshold=0.4
            )

            if uncertainty_check.should_block:
                decision["action_name"] = "noop"
                decision["rl_action"] = 0
                decision["source"] = "self_restraint"
                decision["reason"] = "uncertainty_too_high"
                
                self.logger.log_decision("uncertainty_block", decision, "blocked")

                self.memory.remember_decision(
                    decision_type="uncertainty_block",
                    decision_data=decision,
                    outcome="blocked",
                    context=validated_data
                )
                
                return decision

            # STEP 9: CONFLICT CHECK (Stability Gate)
            conflict_check = self.self_restraint.should_observe_instead_of_act(
                health_signals=validated_data.get("health"),
                memory_signals=memory_signals
            )

            if conflict_check.should_block:

                self.memory.remember_decision(
                    decision_type="conflict_observe",
                    decision_data=decision,
                    outcome="blocked",
                    context=validated_data
                )
                
                # Track for external visibility
                self._last_decision = "observe"
                self._last_block_reason = "signal_conflict"
                self._last_block_type = "self_restraint"
                
                return decision  # CRITICAL: Return to prevent further execution






















            
            # Remember this decision
            outcome = "pending"
            if decision.get('execution_result'):
                if decision['execution_result'].get('status') == 'refused':
                    outcome = "refused"
                elif decision['execution_result'].get('status') == 'success':
                    outcome = "success"
            
            self.memory.remember_decision(
                decision_type="rl_decision",
                decision_data=decision,
                outcome=outcome,
                context=validated_data
            )
            
            return decision
        
        except Exception as e:
            self.logger.log_error(
                "decision_error",
                str(e),
                self.state_manager.current_state.value
            )
            # Default to NOOP on error
            return {'rl_action': 0, 'error': str(e)}


    def _map_rl_action_to_name(self, rl_action: int) -> str:
        return {
            0: "noop",
            1: "restart",
            2: "scale_up",
            3: "scale_down",
            4: "rollback"
        }.get(rl_action, "noop")

    
    def _enforce(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """ENFORCE: Apply governance and safety checks.
        
        Args:
            decision: Decision from decide phase
            
        Returns:
            Enforcement result with 'allowed' flag and 'safe_action'
        """
        self.state_manager.transition_to(AgentState.ENFORCING, "governance_enforcement")
        self.logger.log_state_transition(
            AgentState.DECIDING.value,
            AgentState.ENFORCING.value,
            "governance_enforcement"
        )
        
        try:
            rl_action = decision.get("rl_action", 0)
            action_name = self._map_rl_action_to_name(rl_action)
            execution = decision.get("execution_result") or {}

            context = {
                "app_name": decision.get("input_data", {}).get("app_id"),
                "confidence": decision.get("confidence", 1.0)  # Use decision confidence
            }

            governance_result = self.governance.evaluate_action(
                action=action_name,
                context=context,
                source="agent_runtime"
            )

            if governance_result.should_block:
                # FIX 3: Transition agent state to BLOCKED
                self._last_block_reason = governance_result.reason
                self._last_block_type = getattr(governance_result, 'block_type', 'governance')
                self.state_manager.transition_to(AgentState.BLOCKED, self._last_block_reason)
                
                block_payload = governance_result.to_dict()
                
                # DAY 1 FIX: Add cooldown timing for memory visibility
                if hasattr(governance_result, 'next_allowed_time') and governance_result.next_allowed_time:
                    block_payload['cooldown_until'] = governance_result.next_allowed_time.isoformat()

                self.logger.log_autonomous_operation(
                    "governance_block",
                    block_payload,
                    AgentState.BLOCKED.value
                )

                self.memory.remember_decision(
                    decision_type="governance_block",
                    decision_data=block_payload,
                    outcome="blocked",
                    context=context
                )
                
                # Track for external visibility
                self._last_decision = "noop"
                self._last_block_reason = governance_result.reason
                self._last_block_type = "governance"

                return {
                    "allowed": False,
                    "reason": governance_result.reason,
                    "block_type": "governance",
                    "safe_action": {"action": "noop"}
                }

            if execution.get("status") == "refused":
                return {"allowed": False, "reason": execution.get("reason")}

            return {"allowed": True, "safe_action": decision}

        except Exception as e:
            self.logger.log_error(
                "governance_enforcement_error",
                str(e),
                self.state_manager.current_state.value
            )
            return {"allowed": False, "reason": str(e)}

    
    def _act(self, safe_action: Dict[str, Any]) -> Dict[str, Any]:
        """ACT: Execute validated safe action through the Safe Orchestrator.
        
        Args:
            safe_action: Safe action from enforce phase
            
        Returns:
            Action result
        """
        self.state_manager.transition_to(AgentState.ACTING, "executing_action")
        self.logger.log_state_transition(
            AgentState.ENFORCING.value,
            AgentState.ACTING.value,
            "executing_action"
        )
        
        try:
            # CENTRALIZED EXECUTION: Call the Safe Orchestrator
            rl_action_int = safe_action.get('rl_action', 0)
            input_data = safe_action.get('input_data', {})
            context = {
                'app_name': input_data.get('app_id', 'unknown'),
                'event_type': input_data.get('event_type', 'manual'),
                'trigger_metrics': input_data.get('metrics', {}),
                'replicas': input_data.get('workers', 1),
                'max_replicas': 5,
                'min_replicas': 1
            }
            
            # Execute through safety gates
            execution_result = self.safe_executor.validate_and_execute(
                action_index=rl_action_int,
                context=context,
                source='rl_decision_layer' # Mark source for demo_mode gate
            )

            feedback_result = self.rl_pipe.send_execution_feedback(
                decision=safe_action,
                execution_result=execution_result,
                context=context
            )
            
            self.logger.log_action(
                "execute_safe_action",
                {
                    "action": safe_action.get('action_name'),
                    "result": execution_result,
                    "feedback_delivery": feedback_result.get('delivery', {})
                },
                self.state_manager.current_state.value
            )

            try:
                from control_plane.multi_app_control_plane import MultiAppControlPlane
                MultiAppControlPlane(env=self.env).append_decision_history({
                    'env': self.env,
                    'app_name': context.get('app_name', 'unknown'),
                    'event_type': context.get('event_type', 'unknown'),
                    'decision_action': safe_action.get('action_name'),
                    'decision_source': safe_action.get('source'),
                    'confidence': safe_action.get('confidence'),
                    'executed_action': execution_result.get('action_executed'),
                    'execution_success': execution_result.get('success'),
                    'status': 'executed' if execution_result.get('success') else 'refused',
                    'reason': execution_result.get('reason') or execution_result.get('error')
                })
            except Exception:
                pass
            
            return {
                'status': 'executed' if execution_result.get('success') else 'refused',
                'action': safe_action,
                'execution_details': execution_result,
                'execution_feedback': feedback_result,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            self.logger.log_error(
                "action_error",
                str(e),
                self.state_manager.current_state.value
            )
            return {'status': 'failed', 'error': str(e)}
    
    def _observe(self, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """OBSERVE: Monitor action results and remember app state.
        
        Args:
            action_result: Result from act phase
            
        Returns:
            Observation of results
        """
        self.state_manager.transition_to(AgentState.OBSERVING_RESULTS, "observing_results")
        self.logger.log_state_transition(
            AgentState.ACTING.value,
            AgentState.OBSERVING_RESULTS.value,
            "observing_results"
        )
        
        try:
            # Observe system state after action
            action_data = action_result.get('action', {})
            app_id = action_data.get('input_data', {}).get('app_id', 'unknown')
            
            observation = {
                'action_status': action_result.get('status'),
                'timestamp': datetime.utcnow().isoformat(),
                'system_stable': action_result.get('status') == 'executed',
                'app_id': app_id
            }
            
            # Remember app state in memory
            if app_id != 'unknown':
                self.memory.remember_app_state(
                    app_id=app_id,
                    status='active' if observation['system_stable'] else 'unstable',
                    health={'last_action': action_result.get('status')},
                    recent_events=[
                        f"action_{action_result.get('status')}",
                        f"loop_{self.loop_count}"
                    ],
                    metrics={'timestamp': observation['timestamp']}
                )
            
            self.logger.log_observation(
                "action_result",
                observation,
                self.state_manager.current_state.value
            )
            
            return observation
        
        except Exception as e:
            self.logger.log_error(
                "observation_error",
                str(e),
                self.state_manager.current_state.value
            )
            return {'error': str(e)}
    
    def _explain(self, decision: Dict[str, Any], action_result: Dict[str, Any], observation: Dict[str, Any]):
        """EXPLAIN: Log and explain decision and results.
        
        Args:
            decision: Decision made
            action_result: Action result
            observation: Observation of results
        """
        self.state_manager.transition_to(AgentState.EXPLAINING, "explaining_decision")
        self.logger.log_state_transition(
            AgentState.OBSERVING_RESULTS.value,
            AgentState.EXPLAINING.value,
            "explaining_decision"
        )
        
        try:
            explanation = {
                'loop_count': self.loop_count,
                'decision': decision,
                'action_result': action_result,
                'observation': observation,
                'conclusion': self._generate_conclusion(decision, action_result, observation)
            }
            
            self.logger.log_autonomous_operation(
                "loop_complete_with_explanation",
                explanation,
                self.state_manager.current_state.value
            )
            
            self.logger.info(
                f"Loop {self.loop_count} complete: {explanation['conclusion']}",
                agent_state=self.state_manager.current_state.value
            )
            
            # Store for synchronous retrieval
            self._last_decision = explanation
        
        except Exception as e:
            self.logger.log_error(
                "explanation_error",
                str(e),
                self.state_manager.current_state.value
            )
    
    def _generate_conclusion(self, decision: Dict[str, Any], action_result: Dict[str, Any], observation: Dict[str, Any]) -> str:
        """Generate human-readable conclusion.
        
        Args:
            decision: Decision made
            action_result: Action result
            observation: Observation of results
            
        Returns:
            Conclusion string
        """
        action = decision.get('rl_action', 0)
        status = action_result.get('status', 'unknown')
        stable = observation.get('system_stable', False)
        
        if status == 'executed' and stable:
            return f"Successfully executed action {action}, system stable"
        elif status == 'executed':
            return f"Executed action {action}, monitoring for stability"
        else:
            return f"Action {action} {status}"
    
    def _shutdown(self):
        """Perform graceful shutdown."""
        self.logger.info(
            "Agent runtime shutting down",
            agent_state=self.state_manager.current_state.value
        )
        
        try:
            self.state_manager.transition_to(AgentState.SHUTTING_DOWN, "shutdown_requested")
            self.logger.log_state_transition(
                self.state_manager.current_state.value,
                AgentState.SHUTTING_DOWN.value,
                "shutdown_requested"
            )
        except ValueError:
            # Already in a state that can't transition to shutdown
            pass
        
        # Save state
        state_file = Path("logs/agent") / f"agent_state_{self.agent_id}.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_manager.save_to_file(str(state_file))
        
        # Save memory snapshot
        memory_file = Path("logs/agent") / f"memory_snapshot_{self.agent_id}.json"
        self.memory.to_json(str(memory_file))
        
        # Get memory stats for final log
        memory_stats = self.memory.get_memory_stats()
        
        # Log final stats
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        self.logger.log_autonomous_operation(
            "shutdown_complete",
            {
                "uptime_seconds": uptime,
                "loop_count": self.loop_count,
                "memory_stats": memory_stats,
                "proof": "autonomous_operation_verified"
            },
            AgentState.SHUTTING_DOWN.value
        )
        
        self.logger.info(
            f"Agent shutdown complete: uptime={uptime:.1f}s, loops={self.loop_count}, "
            f"decisions={memory_stats['decision_count']}, apps={memory_stats['app_count']}",
            agent_state=AgentState.SHUTTING_DOWN.value
        )

    def get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status for external visibility.
        
        Returns:
            Dict containing agent state, last decision, and block information
        """
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        # Calculate metrics from memory
        stats = self.memory.get_memory_stats()
        total = stats.get("total_decisions_seen", 0)
        
        # Calculate rates (avoid division by zero)
        success_rate = "100%" if total == 0 else f"{(self.memory.get_memory_context().get('recent_successes', 0) / max(1, min(total, 50))) * 100:.0f}%"
        
        # Safety rate calculation
        safety_context = self.memory.get_memory_context()
        fails = safety_context.get('recent_failures', 0)
        safety_rate = "100%" if total == 0 else f"{((max(1, min(total, 50)) - fails) / max(1, min(total, 50))) * 100:.0f}%"

        autonomy_decisions_enabled = bool(self.env_config.get('autonomy_decisions_enabled', True))
        autonomy_learning_enabled = bool(self.env_config.get('autonomy_learning_enabled', self.env == 'dev'))
        env_freeze_enabled = os.getenv('EMERGENCY_FREEZE_ENABLED')
        env_freeze_reason = os.getenv('EMERGENCY_FREEZE_REASON')
        emergency_freeze_enabled = (
            str(env_freeze_enabled).lower() == 'true'
            if env_freeze_enabled is not None
            else bool(self.env_config.get('emergency_freeze_enabled', False))
        )
        emergency_freeze_reason = (
            (env_freeze_reason or '').strip()
            if env_freeze_reason is not None
            else self.env_config.get('emergency_freeze_reason', '')
        )

        autonomy_level = 'CUSTOM'
        autonomy_badge = '⚙️ CUSTOM'
        autonomy_color = 'neutral'

        if self.env == 'dev' and autonomy_decisions_enabled and autonomy_learning_enabled:
            autonomy_level = 'DEV_FULL_AUTONOMY'
            autonomy_badge = '🟢 DEV FULL'
            autonomy_color = 'green'
        elif self.env == 'stage' and autonomy_decisions_enabled and not autonomy_learning_enabled:
            autonomy_level = 'STAGE_DECISIONS_ONLY'
            autonomy_badge = '🟡 STAGE DECISIONS'
            autonomy_color = 'amber'
        elif self.env == 'prod' and autonomy_decisions_enabled and not autonomy_learning_enabled:
            autonomy_level = 'PROD_FROZEN'
            autonomy_badge = '🧊 PROD FROZEN'
            autonomy_color = 'blue'

        if emergency_freeze_enabled:
            autonomy_level = 'EMERGENCY_FREEZE'
            autonomy_badge = '🔴 EMERGENCY FREEZE'
            autonomy_color = 'red'

        status = {
            "agent_id": self.agent_id,
            "state": self.state_manager.current_state.value,
            "last_decision": self._last_decision,
            "last_block_reason": self._last_block_reason,
            "block_type": self._last_block_type,
            "loop_count": self.loop_count,
            "uptime": int(uptime),
            "uptime_seconds": int(uptime),
            "memory_stats": stats,
            "metrics": {
                "success_rate": success_rate,
                "safety_rate": safety_rate,
                "avg_response_time": "40ms" # TODO: Wire to real latency tracking
            },
            "env": self.env,
            "version": self.version,
            "timestamp": datetime.utcnow().isoformat(),
            "autonomy": {
                "level": autonomy_level,
                "badge": autonomy_badge,
                "color": autonomy_color,
                "decisions_enabled": autonomy_decisions_enabled,
                "learning_enabled": autonomy_learning_enabled,
                "emergency_freeze_enabled": emergency_freeze_enabled,
                "emergency_freeze_reason": emergency_freeze_reason
            }
        }
        
        # Add explanation if blocked
        if self._last_block_reason:
            explanations = {
                "uncertainty_too_high": "Agent refused action due to low confidence",
                "signal_conflict": "Agent entered observe-only mode due to conflicting signals",
                "cooldown_active": "Action blocked by cooldown timer",
                "repetition_suppressed": "Action blocked due to repetition limit",
                "eligibility_failed": "Action not eligible for current environment"
            }
            status["explanation"] = explanations.get(
                self._last_block_reason,
                f"Action blocked: {self._last_block_reason}"
            )
        
        return status


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Autonomous AI Agent Runtime")
    parser.add_argument("--env", type=str, choices=['dev', 'stage', 'staging', 'prod'], default='dev',
                       help='Environment to run in (default: dev)')
    parser.add_argument("--agent-id", type=str, help='Agent ID (auto-generated if not provided)')
    parser.add_argument("--loop-interval", type=float, default=5.0,
                       help='Loop interval in seconds (default: 5.0)')
    parser.add_argument("--version", action="store_true", help='Show version and exit')
    
    args = parser.parse_args()
    
    if args.version:
        print("Agent Runtime v1.0.0")
        sys.exit(0)
    
    # Create and run agent
    agent = AgentRuntime(
        env=args.env,
        agent_id=args.agent_id,
        loop_interval=args.loop_interval
    )
    
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║             AUTONOMOUS AI AGENT RUNTIME v1.0.0                   ║
╚══════════════════════════════════════════════════════════════════╝

Agent ID:       {agent.agent_id}
Environment:    {args.env}
Loop Interval:  {args.loop_interval}s
Start Time:     {agent.start_time.isoformat()}

Agent Loop: sense → validate → decide → enforce → act → observe → explain

Press Ctrl+C for graceful shutdown
""")
    
    agent.run()


if __name__ == "__main__":
    main()
