from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
import json

class SignalType(Enum):
    CPU_HIGH = "cpu_high"
    MEMORY_HIGH = "memory_high"
    LATENCY_HIGH = "latency_high"
    ERROR_RATE_HIGH = "error_rate_high"
    DEPLOYMENT_FAILED = "deployment_failed"
    HEALTH_CHECK_FAILED = "health_check_failed"

class ActionType(Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    RESTART = "restart"
    ROLLBACK = "rollback"
    NOOP = "noop"

@dataclass
class RuntimeSignal:
    signal_type: str
    app_id: str
    severity: float  # 0-1
    timestamp: float
    metadata: Dict[str, Any]
    
    def to_dict(self):
        return asdict(self)

@dataclass
class RuntimeState:
    app_id: str
    current_replicas: int
    desired_replicas: int
    cpu_usage: float
    memory_usage: float
    error_rate: float
    latency_p99: float
    last_deployment_time: float
    signals: List[RuntimeSignal]
    environment: str  # dev, staging, prod
    
    def to_dict(self):
        return {
            'app_id': self.app_id,
            'current_replicas': self.current_replicas,
            'desired_replicas': self.desired_replicas,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'error_rate': self.error_rate,
            'latency_p99': self.latency_p99,
            'last_deployment_time': self.last_deployment_time,
            'signals': [s.to_dict() for s in self.signals],
            'environment': self.environment
        }

@dataclass
class Decision:
    decision_id: str
    app_id: str
    action: str
    reason: str
    confidence: float
    timestamp: float
    decision_type: str  # 'rule_based' or 'rl_assisted'
    
    def to_dict(self):
        return asdict(self)

@dataclass
class DecisionFeedback:
    decision_id: str
    app_id: str
    action_executed: bool
    execution_time: float
    result_status: str  # 'success', 'failed', 'partial'
    metrics_before: Dict[str, float]
    metrics_after: Dict[str, float]
    timestamp: float
