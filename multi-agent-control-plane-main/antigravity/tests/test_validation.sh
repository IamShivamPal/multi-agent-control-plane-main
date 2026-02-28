#!/bin/bash
# Test validation criteria for Antigravity system

echo "======================================"
echo "ANTIGRAVITY SYSTEM VALIDATION TESTS"
echo "======================================"
echo ""

# Colors
GREEN='\033[0.32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Successful Full Chain
echo "Test 1: Successful Full Chain Execution"
echo "----------------------------------------"
response=$(curl -s -X POST http://localhost:8001/emit \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "app_crash",
    "app": "web-api",
    "env": "prod",
    "metadata": {"error_count": 15, "state": "critical"}
  }')

echo "Response: $response"
if echo "$response" | grep -q '"status":"processed"'; then
  echo -e "${GREEN}✅ PASSED${NC}"
else
  echo -e "${RED}❌ FAILED${NC}"
fi
echo ""

# Test 2: Malformed JSON → NOOP
echo "Test 2: Malformed JSON → Agent Returns NOOP"
echo "--------------------------------------------"
response=$(curl -s -X POST http://localhost:8002/decide \
  -H "Content-Type: application/json" \
  -d '{"invalid json')

echo "Response: $response"
if echo "$response" | grep -q '"decision":"noop"'; then
  echo -e "${GREEN}✅ PASSED${NC}"
else
  echo -e "${RED}❌ FAILED${NC}"
fi
echo ""

# Test 3: Missing Required Field → NOOP
echo "Test 3: Missing Required Field → Agent Returns NOOP"
echo "----------------------------------------------------"
response=$(curl -s -X POST http://localhost:8002/decide \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "app_crash",
    "app": "web-api",
    "state": "critical"
  }')

echo "Response: $response"
if echo "$response" | grep -q '"decision":"noop"' && echo "$response" | grep -q 'missing.*env'; then
  echo -e "${GREEN}✅ PASSED${NC}"
else
  echo -e "${RED}❌ FAILED${NC}"
fi
echo ""

# Test 4: Unauthorized Action → Orchestrator Rejects
echo "Test 4: Unauthorized Action → Orchestrator Rejects"
echo "---------------------------------------------------"
response=$(curl -s -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{
    "action": "delete_database",
    "app": "web-api",
    "env": "prod",
    "requested_by": "agent"
  }')

echo "Response: $response"
if echo "$response" | grep -q '"status":"rejected"' && echo "$response" | grep -q 'action_out_of_scope'; then
  echo -e "${GREEN}✅ PASSED${NC}"
else
  echo -e "${RED}❌ FAILED${NC}"
fi
echo ""

# Test 5: scale_up in prod → Rejected
echo "Test 5: scale_up in prod → Rejected"
echo "------------------------------------"
response=$(curl -s -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{
    "action": "scale_up",
    "app": "web-api",
    "env": "prod",
    "requested_by": "agent"
  }')

echo "Response: $response"
if echo "$response" | grep -q '"status":"rejected"'; then
  echo -e "${GREEN}✅ PASSED${NC}"
else
  echo -e "${RED}❌ FAILED${NC}"
fi
echo ""

# Test 6: Health Checks
echo "Test 6: Health Checks for All Services"
echo "---------------------------------------"
runtime_health=$(curl -s http://localhost:8001/health | grep -q '"status":"healthy"' && echo "OK" || echo "FAIL")
agent_health=$(curl -s http://localhost:8002/health | grep -q '"status":"healthy"' && echo "OK" || echo "FAIL")
orchestrator_health=$(curl -s http://localhost:8003/health | grep -q '"status":"healthy"' && echo "OK" || echo "FAIL")

echo "Runtime: $runtime_health"
echo "Agent: $agent_health"
echo "Orchestrator: $orchestrator_health"

if [ "$runtime_health" == "OK" ] && [ "$agent_health" == "OK" ] && [ "$orchestrator_health" == "OK" ]; then
  echo -e "${GREEN}✅ PASSED${NC}"
else
  echo -e "${RED}❌ FAILED${NC}"
fi
echo ""

echo "======================================"
echo "VALIDATION COMPLETE"
echo "======================================"
