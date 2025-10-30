#!/bin/bash
# Direct test of terminal API endpoints

SERVER_URL="http://localhost:8001"

echo "=== Testing Terminal API ==="
echo ""
echo "Step 1: Create terminal session"
CREATE_RESPONSE=$(curl -s -X POST "$SERVER_URL/invocations" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/terminal/sessions",
    "method": "POST",
    "payload": {
      "rows": 24,
      "cols": 80,
      "cwd": "/workspace",
      "shell": "bash"
    }
  }')

echo "$CREATE_RESPONSE" | jq .

SESSION_ID=$(echo "$CREATE_RESPONSE" | jq -r '.session_id')
echo ""
echo "Session ID: $SESSION_ID"

if [ "$SESSION_ID" = "null" ] || [ -z "$SESSION_ID" ]; then
  echo "Failed to create session"
  exit 1
fi

echo ""
echo "Step 2: Wait for initial output..."
sleep 1

echo ""
echo "Step 3: Get terminal output (seq=0)"
OUTPUT_RESPONSE=$(curl -s -X POST "$SERVER_URL/invocations" \
  -H "Content-Type: application/json" \
  -d "{
    \"path\": \"/terminal/sessions/{session_id}/output\",
    \"method\": \"GET\",
    \"path_params\": {\"session_id\": \"$SESSION_ID\"},
    \"payload\": {\"seq\": 0}
  }")

echo "$OUTPUT_RESPONSE" | jq .

echo ""
echo "Step 4: Send input 'ls -la\\n'"
INPUT_RESPONSE=$(curl -s -X POST "$SERVER_URL/invocations" \
  -H "Content-Type: application/json" \
  -d "{
    \"path\": \"/terminal/sessions/{session_id}/input\",
    \"method\": \"POST\",
    \"path_params\": {\"session_id\": \"$SESSION_ID\"},
    \"payload\": {\"data\": \"ls -la\\n\"}
  }")

echo "$INPUT_RESPONSE" | jq .

echo ""
echo "Step 5: Wait for command output..."
sleep 1

echo ""
echo "Step 6: Get terminal output again"
OUTPUT_RESPONSE2=$(curl -s -X POST "$SERVER_URL/invocations" \
  -H "Content-Type: application/json" \
  -d "{
    \"path\": \"/terminal/sessions/{session_id}/output\",
    \"method\": \"GET\",
    \"path_params\": {\"session_id\": \"$SESSION_ID\"},
    \"payload\": {\"seq\": 0}
  }")

echo "$OUTPUT_RESPONSE2" | jq .

echo ""
echo "Step 7: Close session"
CLOSE_RESPONSE=$(curl -s -X POST "$SERVER_URL/invocations" \
  -H "Content-Type: application/json" \
  -d "{
    \"path\": \"/terminal/sessions/{session_id}\",
    \"method\": \"DELETE\",
    \"path_params\": {\"session_id\": \"$SESSION_ID\"}
  }")

echo "$CLOSE_RESPONSE" | jq .

echo ""
echo "=== Test Complete ==="
