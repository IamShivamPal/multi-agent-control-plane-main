"""
JSON Validation Test Suite
Tests strict validation across all Antigravity services
"""

import requests
import json

# Service URLs
AGENT_URL = "http://localhost:8002"
ORCHESTRATOR_URL = "http://localhost:8003"

def print_test(service, test_name):
    print(f"\n{'='*70}")
    print(f"{service.upper()} - {test_name}")
    print(f"{'='*70}")

def test_service(service_name, url, payload, expected_status=200):
    """Generic test function"""
    print(f"\nPayload: {json.dumps(payload) if not isinstance(payload, str) else payload}")
    
    try:
        if isinstance(payload, str):
            # Send raw string (malformed JSON test)
            response = requests.post(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
        else:
            response = requests.post(url, json=payload, timeout=5)
        
        print(f"Status Code: {response.status_code}")
        
        # Check that we never get 500
        if response.status_code == 500:
            print("❌ FAILED: Got 500 Internal Server Error (should never happen!)")
            return False
        
        # Check expected status
        if response.status_code != expected_status:
            print(f"⚠️  Got {response.status_code}, expected {expected_status}")
        
        # Parse and display response
        try:
            response_data = response.json()
            print(f"Response: {json.dumps(response_data, indent=2)}")
            return response_data
        except:
            print(f"Response (text): {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_agent_validation():
    """Test Agent service validation"""
    
    # Test 1: Malformed JSON
    print_test("Agent", "Malformed JSON")
    result = test_service("agent", f"{AGENT_URL}/decide", '{"invalid json')
    if result and result.get("decision") == "noop" and result.get("reason") == "malformed_json":
        print("✅ PASS: Returns NOOP for malformed JSON")
    else:
        print("❌ FAIL: Did not return NOOP for malformed JSON")
    
    # Test 2: Empty Payload
    print_test("Agent", "Empty Payload")
    result = test_service("agent", f"{AGENT_URL}/decide", {})
    if result and result.get("decision") == "noop" and "empty_payload" in result.get("reason", ""):
        print("✅ PASS: Returns NOOP for empty payload")
    else:
        print("❌ FAIL: Did not return NOOP for empty payload")
    
    # Test 3: Missing Required Field (env)
    print_test("Agent", "Missing Required Field - env")
    result = test_service("agent", f"{AGENT_URL}/decide", {
        "event_type": "test",
        "app": "web-api",
        "state": "healthy"
    })
    if result and result.get("decision") == "noop" and "missing_required_field_env" in result.get("reason", ""):
        print("✅ PASS: Returns NOOP for missing 'env' field")
    else:
        print("❌ FAIL: Did not return NOOP for missing field")
    
    # Test 4: Wrong Data Type (env as number)
    print_test("Agent", "Wrong Data Type - env as number")
    result = test_service("agent", f"{AGENT_URL}/decide", {
        "event_type": "test",
        "app": "web-api",
        "env": 123,  # Should be string
        "state": "healthy"
    })
    if result and result.get("decision") == "noop":
        print("✅ PASS: Returns NOOP for wrong data type")
    else:
        print("❌ FAIL: Did not return NOOP for wrong data type")
    
    # Test 5: Invalid Enum Value (env)
    print_test("Agent", "Invalid Enum Value - env")
    result = test_service("agent", f"{AGENT_URL}/decide", {
        "event_type": "test",
        "app": "web-api",
        "env": "invalid-env",  # Valid values: dev, stage, prod
        "state": "healthy"
    })
    if result and result.get("decision") == "noop" and "invalid_env" in result.get("reason", ""):
        print("✅ PASS: Returns NOOP for invalid enum value")
    else:
        print("❌ FAIL: Did not return NOOP for invalid enum")
    
    # Test 6: Empty String Field
    print_test("Agent", "Empty String - app")
    result = test_service("agent", f"{AGENT_URL}/decide", {
        "event_type": "test",
        "app": "",  # Empty string
        "env": "prod",
        "state": "healthy"
    })
    if result and result.get("decision") == "noop" and "invalid_app" in result.get("reason", ""):
        print("✅ PASS: Returns NOOP for empty string")
    else:
        print("❌ FAIL: Did not return NOOP for empty string")
    
    # Test 7: Metrics wrong type
    print_test("Agent", "Wrong Type - metrics")
    result = test_service("agent", f"{AGENT_URL}/decide", {
        "event_type": "test",
        "app": "web-api",
        "env": "prod",
        "state": "healthy",
        "metrics": "not a dict"  # Should be dict
    })
    if result and result.get("decision") == "noop":
        print("✅ PASS: Returns NOOP for wrong metrics type")
    else:
        print("❌ FAIL: Did not return NOOP for wrong metrics type")
    
    # Test 8: Valid Payload (should work)
    print_test("Agent", "Valid Payload")
    result = test_service("agent", f"{AGENT_URL}/decide", {
        "event_type": "test",
        "app": "web-api",
        "env": "prod",
        "state": "healthy"
    })
    if result and result.get("decision") is not None:
        print(f"✅ PASS: Returns valid decision: {result.get('decision')}")
    else:
        print("❌ FAIL: Did not return valid decision")

def test_orchestrator_validation():
    """Test Orchestrator service validation"""
    
    # Test 1: Malformed JSON
    print_test("Orchestrator", "Malformed JSON")
    result = test_service("orchestrator", f"{ORCHESTRATOR_URL}/execute", '{"malformed')
    if result and result.get("status") == "rejected" and result.get("reason") == "malformed_json":
        print("✅ PASS: Returns rejected for malformed JSON")
    else:
        print("❌ FAIL: Did not reject malformed JSON")
    
    # Test 2: Empty Payload
    print_test("Orchestrator", "Empty Payload")
    result = test_service("orchestrator", f"{ORCHESTRATOR_URL}/execute", {})
    if result and result.get("status") == "rejected" and "empty_payload" in result.get("reason", ""):
        print("✅ PASS: Returns rejected for empty payload")
    else:
        print("❌ FAIL: Did not reject empty payload")
    
    # Test 3: Missing Required Field (action)
    print_test("Orchestrator", "Missing Required Field - action")
    result = test_service("orchestrator", f"{ORCHESTRATOR_URL}/execute", {
        "app": "web-api",
        "env": "prod",
        "requested_by": "test"
    })
    if result and result.get("status") == "rejected" and "missing_required_field_action" in result.get("reason", ""):
        print("✅ PASS: Returns rejected for missing 'action' field")
    else:
        print("❌ FAIL: Did not reject missing field")
    
    # Test 4: Wrong Data Type (action as number)
    print_test("Orchestrator", "Wrong Data Type - action as number")
    result = test_service("orchestrator", f"{ORCHESTRATOR_URL}/execute", {
        "action": 123,  # Should be string
        "app": "web-api",
        "env": "prod",
        "requested_by": "test"
    })
    if result and result.get("status") == "rejected":
        print("✅ PASS: Returns rejected for wrong data type")
    else:
        print("❌ FAIL: Did not reject wrong data type")
    
    # Test 5: Empty String Field
    print_test("Orchestrator", "Empty String - app")
    result = test_service("orchestrator", f"{ORCHESTRATOR_URL}/execute", {
        "action": "restart",
        "app": "",  # Empty string
        "env": "prod",
        "requested_by": "test"
    })
    if result and result.get("status") == "rejected" and "app_must_be_non_empty_string" in result.get("reason", ""):
        print("✅ PASS: Returns rejected for empty string")
    else:
        print("❌ FAIL: Did not reject empty string")
    
    # Test 6: Valid Payload (should work)
    print_test("Orchestrator", "Valid Payload")
    result = test_service("orchestrator", f"{ORCHESTRATOR_URL}/execute", {
        "action": "restart",
        "app": "web-api",
        "env": "prod",
        "requested_by": "test"
    })
    if result and result.get("status") in ["executed", "simulated"]:
        print(f"✅ PASS: Returns valid status: {result.get('status')}")
    else:
        print("❌ FAIL: Did not execute/simulate properly")

def main():
    print("\n" + "="*70)
    print("ANTIGRAVITY JSON VALIDATION TEST SUITE")
    print("="*70)
    print("\nTesting strict JSON validation across all services")
    print("Expectation: No service should ever return HTTP 500")
    print("\n")
    
    # Check services are running
    try:
        agent_health = requests.get(f"{AGENT_URL}/health", timeout=2)
        if agent_health.status_code == 200:
            print("✅ Agent service is running")
        else:
            print(f"⚠️  Agent service returned {agent_health.status_code}")
    except:
        print("❌ Agent service not reachable - please start it first")
        return
    
    try:
        orch_health = requests.get(f"{ORCHESTRATOR_URL}/health", timeout=2)
        if orch_health.status_code == 200:
            print("✅ Orchestrator service is running")
        else:
            print(f"⚠️  Orchestrator service returned {orch_health.status_code}")
    except:
        print("❌ Orchestrator service not reachable - please start it first")
        return
    
    print("\n" + "="*70)
    print("RUNNING TESTS")
    print("="*70)
    
    # Run tests
    test_agent_validation()
    test_orchestrator_validation()
    
    print("\n" + "="*70)
    print("TEST SUITE COMPLETE")
    print("="*70)
    print("\n✅ All tests completed - review results above")
    print("❗ Key: No service should ever return HTTP 500")

if __name__ == "__main__":
    main()
