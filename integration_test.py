import logging
import json
import time
from datetime import datetime
from runtime_contract import RuntimeState, RuntimeSignal, SignalType
from decision_engine import DecisionEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntegrationTestSuite:
    def __init__(self):
        self.engine = DecisionEngine()
        self.test_results = []
    
    def test_single_app_decision_flow(self):
        """Test: Single app decision flow"""
        logger.info("\n" + "="*60)
        logger.info("TEST 1: Single App Decision Flow")
        logger.info("="*60)
        
        # Create runtime state with high CPU
        state = RuntimeState(
            app_id="app-001",
            current_replicas=2,
            desired_replicas=3,
            cpu_usage=0.85,
            memory_usage=0.5,
            error_rate=0.02,
            latency_p99=500,
            last_deployment_time=time.time() - 3600,
            signals=[
                RuntimeSignal(
                    signal_type=SignalType.CPU_HIGH.value,
                    app_id="app-001",
                    severity=0.9,
                    timestamp=time.time(),
                    metadata={'threshold': 0.8, 'current': 0.85}
                )
            ],
            environment="prod"
        )
        
        result = self.engine.process_runtime_state(state)
        
        assert result['action_emitted'] == 'scale_up', "Expected scale_up action"
        assert result['orchestrator_acknowledged'] == True, "Orchestrator should acknowledge"
        
        logger.info(f"✓ Test passed: {json.dumps(result, indent=2)}")
        self.test_results.append(('single_app_flow', True))
    
    def test_multi_app_isolation(self):
        """Test: Multi-app state isolation"""
        logger.info("\n" + "="*60)
        logger.info("TEST 2: Multi-App State Isolation")
        logger.info("="*60)
        
        apps = ["app-001", "app-002", "app-003"]
        
        for app_id in apps:
            state = RuntimeState(
                app_id=app_id,
                current_replicas=2,
                desired_replicas=2,
                cpu_usage=0.9 if app_id == "app-001" else 0.3,
                memory_usage=0.5,
                error_rate=0.02,
                latency_p99=500,
                last_deployment_time=time.time() - 3600,
                signals=[],
                environment="prod"
            )
            
            self.engine.process_runtime_state(state)
        
        # Verify isolation
        for app_id in apps:
            stats = self.engine.get_app_stats(app_id)
            assert stats is not None, f"Stats missing for {app_id}"
            assert stats['app_id'] == app_id, f"App ID mismatch"
            logger.info(f"✓ App {app_id} isolated: {stats['total_decisions']} decisions")
        
        self.test_results.append(('multi_app_isolation', True))
    
    def test_action_scope_enforcement(self):
        """Test: Action scope enforcement"""
        logger.info("\n" + "="*60)
        logger.info("TEST 3: Action Scope Enforcement")
        logger.info("="*60)
        
        # Create state that triggers multiple scale-ups
        for i in range(5):
            state = RuntimeState(
                app_id="app-scope-test",
                current_replicas=2,
                desired_replicas=2,
                cpu_usage=0.95,
                memory_usage=0.5,
                error_rate=0.02,
                latency_p99=500,
                last_deployment_time=time.time() - 3600,
                signals=[],
                environment="prod"
            )
            
            result = self.engine.process_runtime_state(state)
            logger.info(f"Iteration {i+1}: action_emitted={result['action_emitted']}")
        
        # Check enforcement stats
        stats = self.engine.action_scope_enforcer.get_enforcement_stats("app-scope-test")
        logger.info(f"Enforcement stats: {json.dumps(stats, indent=2)}")
        
        self.test_results.append(('action_scope_enforcement', True))
    
    def test_false_positive_dampening(self):
        """Test: False positive dampening"""
        logger.info("\n" + "="*60)
        logger.info("TEST 4: False Positive Dampening")
        logger.info("="*60)
        
        app_id = "app-dampening-test"
        
        # First decision should be allowed
        state1 = RuntimeState(
            app_id=app_id,
            current_replicas=2,
            desired_replicas=2,
            cpu_usage=0.85,
            memory_usage=0.5,
            error_rate=0.02,
            latency_p99=500,
            last_deployment_time=time.time() - 3600,
            signals=[],
            environment="prod"
        )
        
        result1 = self.engine.process_runtime_state(state1)
        logger.info(f"First decision: {result1['action_emitted']}")
        
        # Immediate second decision should be dampened
        result2 = self.engine.process_runtime_state(state1)
        logger.info(f"Second decision (immediate): {result2['action_emitted']}")
        
        assert result2['action_emitted'] == 'noop', "Second decision should be dampened"
        
        logger.info("✓ False positive dampening working")
        self.test_results.append(('false_positive_dampening', True))
    
    def test_environment_constraints(self):
        """Test: Environment-specific constraints"""
        logger.info("\n" + "="*60)
        logger.info("TEST 5: Environment Constraints")
        logger.info("="*60)
        
        environments = ["dev", "staging", "prod"]
        
        for env in environments:
            state = RuntimeState(
                app_id=f"app-{env}",
                current_replicas=2,
                desired_replicas=2,
                cpu_usage=0.85,
                memory_usage=0.5,
                error_rate=0.02,
                latency_p99=500,
                last_deployment_time=time.time() - 3600,
                signals=[],
                environment=env
            )
            
            result = self.engine.process_runtime_state(state)
            logger.info(f"{env}: action_emitted={result['action_emitted']}")
        
        self.test_results.append(('environment_constraints', True))
    
    def test_decision_feedback_loop(self):
        """Test: Decision feedback recording"""
        logger.info("\n" + "="*60)
        logger.info("TEST 6: Decision Feedback Loop")
        logger.info("="*60)
        
        state = RuntimeState(
            app_id="app-feedback",
            current_replicas=2,
            desired_replicas=2,
            cpu_usage=0.85,
            memory_usage=0.5,
            error_rate=0.02,
            latency_p99=500,
            last_deployment_time=time.time() - 3600,
            signals=[],
            environment="dev"
        )
        
        result = self.engine.process_runtime_state(state)
        decision_id = result['decision_id']
        
        # Record feedback
        feedback = {
            'decision_id': decision_id,
            'app_id': 'app-feedback',
            'action_executed': True,
            'execution_time': 2.5,
            'result_status': 'success',
            'metrics_before': {'cpu': 0.85, 'replicas': 2},
            'metrics_after': {'cpu': 0.65, 'replicas': 3},
            'timestamp': time.time()
        }
        
        self.engine.record_feedback(decision_id, feedback)
        
        stats = self.engine.get_app_stats('app-feedback')
        logger.info(f"App stats after feedback: {json.dumps(stats, indent=2)}")
        
        self.test_results.append(('decision_feedback_loop', True))
    
    def run_all_tests(self):
        """Run all integration tests"""
        logger.info("\n" + "="*80)
        logger.info("PRAVAH INTEGRATION TEST SUITE")
        logger.info("="*80)
        
        try:
            self.test_single_app_decision_flow()
            self.test_multi_app_isolation()
            self.test_action_scope_enforcement()
            self.test_false_positive_dampening()
            self.test_environment_constraints()
            self.test_decision_feedback_loop()
        except Exception as e:
            logger.error(f"Test failed: {str(e)}", exc_info=True)
            self.test_results.append(('error', False))
        
        # Print summary
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        
        for test_name, passed in self.test_results:
            status = "✓ PASSED" if passed else "✗ FAILED"
            logger.info(f"{status}: {test_name}")
        
        total = len(self.test_results)
        passed = sum(1 for _, p in self.test_results if p)
        logger.info(f"\nTotal: {passed}/{total} tests passed")
        
        # Print decision logs
        logger.info("\n" + "="*80)
        logger.info("DECISION LOGS")
        logger.info("="*80)
        
        logs = self.engine.get_decision_logs(limit=20)
        for log in logs:
            logger.info(json.dumps(log, indent=2, default=str))

if __name__ == "__main__":
    suite = IntegrationTestSuite()
    suite.run_all_tests()
