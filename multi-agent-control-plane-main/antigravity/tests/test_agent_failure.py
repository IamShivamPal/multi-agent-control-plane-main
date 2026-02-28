"""
Agent Failure Simulation Test
Tests Runtime service graceful degradation when Agent is unavailable
"""

import requests
import json
import time
import sys

# Colors for output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
NC = '\033[0m'  # No Color

RUNTIME_URL = "http://localhost:8001"

def print_test(name):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")

def print_result(passed, message=""):
    if passed:
        print(f"{GREEN}✅ PASSED{NC} {message}")
    else:
        print(f"{RED}❌ FAILED{NC} {message}")
    return passed

def test_agent_unavailable():
    """
    Test Runtime behavior when Agent service is down.
    
    Prerequisites: 
    - Runtime service running on 8001
    - Agent service NOT running (killed)
    - Orchestrator service running on 8003
    """
    print_test("Agent Unavailable - Runtime Graceful Degradation")
    
    print("\nSending event to Runtime while Agent is DOWN...")
    
    event_payload = {
        "event_type": "app_crash",
        "app": "web-api",
        "env": "prod",
        "metadata": {
            "error_count": 15,
            "state": "critical"
        }
    }
    
    print(f"Event Payload: {json.dumps(event_payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{RUNTIME_URL}/emit",
            json=event_payload,
            timeout=10
        )
        
        print(f"\nRuntime Response Status: {response.status_code}")
        
        # Check that Runtime didn't crash and returned 200
        if response.status_code != 200:
            return print_result(False, f"Expected 200, got {response.status_code}")
        
        print(f"{GREEN}✅ Runtime returned 200 OK (didn't crash){NC}")
        
        response_data = response.json()
        print(f"\nResponse Body:")
        print(json.dumps(response_data, indent=2))
        
        # Verify response structure
        checks = []
        
        # Check status is degraded
        if response_data.get("status") == "degraded":
            print(f"{GREEN}✅ Status: degraded{NC}")
            checks.append(True)
        else:
            print(f"{RED}❌ Status: {response_data.get('status')} (expected 'degraded'){NC}")
            checks.append(False)
        
        # Check fallback is noop
        if response_data.get("fallback") == "noop":
            print(f"{GREEN}✅ Fallback: noop{NC}")
            checks.append(True)
        else:
            print(f"{RED}❌ Fallback: {response_data.get('fallback')} (expected 'noop'){NC}")
            checks.append(False)
        
        # Check agent_decision has noop
        agent_decision = response_data.get("agent_decision", {})
        if agent_decision.get("decision") == "noop":
            print(f"{GREEN}✅ Agent Decision: noop{NC}")
            checks.append(True)
        else:
            print(f"{RED}❌ Agent Decision: {agent_decision.get('decision')}{NC}")
            checks.append(False)
        
        if agent_decision.get("reason") == "agent_unavailable":
            print(f"{GREEN}✅ Reason: agent_unavailable{NC}")
            checks.append(True)
        else:
            print(f"{RED}❌ Reason: {agent_decision.get('reason')}{NC}")
            checks.append(False)
        
        # Check error field
        if "agent" in response_data.get("error", "").lower():
            print(f"{GREEN}✅ Error field present: {response_data.get('error')}{NC}")
            checks.append(True)
        else:
            print(f"{RED}❌ Error field: {response_data.get('error')}{NC}")
            checks.append(False)
        
        # Final result
        all_passed = all(checks)
        print(f"\n{'='*60}")
        if all_passed:
            print(f"{GREEN}✅ ALL CHECKS PASSED{NC}")
            print(f"\nRuntime successfully:")
            print(f"  - Did NOT crash")
            print(f"  - Returned HTTP 200")
            print(f"  - Returned safe JSON")
            print(f"  - Executed NOOP fallback")
            print(f"  - Logged agent unavailable")
        else:
            print(f"{RED}❌ SOME CHECKS FAILED{NC}")
        
        return all_passed
        
    except requests.Timeout:
        print(f"{RED}❌ Runtime timed out (shouldn't happen){NC}")
        return False
    except requests.ConnectionError:
        print(f"{RED}❌ Runtime service not running on {RUNTIME_URL}{NC}")
        return False
    except Exception as e:
        print(f"{RED}❌ Unexpected error: {e}{NC}")
        return False

def test_agent_timeout():
    """
    Test Runtime behavior when Agent times out (takes > 3 seconds)
    
    This requires a special Agent configuration or mock that delays responses.
    """
    print_test("Agent Timeout - 3 Second Limit")
    
    print("\nNote: This test requires Agent to be configured with artificial delays.")
    print("If Agent responds normally, this test will show normal flow.")
    
    event_payload = {
        "event_type": "slow_test",
        "app": "test-app",
        "env": "dev",
        "metadata": {
            "state": "healthy"
        }
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{RUNTIME_URL}/emit",
            json=event_payload,
            timeout=10
        )
        elapsed = time.time() - start_time
        
        print(f"\nResponse received in {elapsed:.2f}s")
        
        if elapsed > 3.5:
            # Agent likely timed out
            response_data = response.json()
            if response_data.get("fallback") == "noop":
                return print_result(True, f"Agent timeout handled (took {elapsed:.2f}s)")
            else:
                return print_result(False, "Agent timeout not handled correctly")
        else:
            print(f"{YELLOW}⚠️  Agent responded within timeout ({elapsed:.2f}s < 3s){NC}")
            print("This is normal behavior - Agent is healthy.")
            return True
            
    except Exception as e:
        print(f"{RED}❌ Error: {e}{NC}")
        return False

def main():
    print("\n" + "="*60)
    print("RUNTIME AGENT FAILURE TOLERANCE TESTS")
    print("="*60)
    
    print("\n📋 Prerequisites:")
    print("  1. ✅ Runtime service running on port 8001")
    print("  2. ❌ Agent service NOT running (kill it!)")
    print("  3. ✅ Orchestrator service running on port 8003")
    
    print("\n⚠️  Please ensure Agent service (port 8002) is STOPPED")
    input("Press Enter when Agent is stopped...")
    
    # Check Runtime is up
    try:
        health = requests.get(f"{RUNTIME_URL}/health", timeout=2)
        if health.status_code == 200:
            print(f"{GREEN}✅ Runtime service is healthy{NC}")
        else:
            print(f"{RED}❌ Runtime service health check failed{NC}")
            sys.exit(1)
    except:
        print(f"{RED}❌ Runtime service not reachable on {RUNTIME_URL}{NC}")
        sys.exit(1)
    
    # Check Agent is down
    try:
        requests.get("http://localhost:8002/health", timeout=1)
        print(f"{YELLOW}⚠️  WARNING: Agent service appears to be running!{NC}")
        print("Please stop Agent service for this test.")
        cont = input("Continue anyway? (y/N): ")
        if cont.lower() != 'y':
            sys.exit(0)
    except:
        print(f"{GREEN}✅ Agent service is down (as expected){NC}")
    
    # Run tests
    results = []
    results.append(test_agent_unavailable())
    # results.append(test_agent_timeout())  # Optional
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print(f"{GREEN}✅ ALL TESTS PASSED{NC}")
        sys.exit(0)
    else:
        print(f"{RED}❌ SOME TESTS FAILED{NC}")
        sys.exit(1)

if __name__ == "__main__":
    main()
