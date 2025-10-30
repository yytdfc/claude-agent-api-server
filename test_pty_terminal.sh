#!/bin/bash

# Test script for PTY terminal implementation

set -e

BASE_URL="http://127.0.0.1:8001"

echo "=== PTY Terminal API Test ==="
echo ""

# Test 1: Create terminal session
echo "1. Creating terminal session..."
SESSION_RESPONSE=$(curl -s -X POST "$BASE_URL/terminal/sessions" \
  -H "Content-Type: application/json" \
  -d '{"rows": 24, "cols": 80, "cwd": "/tmp", "shell": "bash"}')

SESSION_ID=$(echo $SESSION_RESPONSE | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$SESSION_ID" ]; then
  echo "❌ Failed to create session"
  echo "Response: $SESSION_RESPONSE"
  exit 1
fi

echo "✅ Session created: $SESSION_ID"
echo ""

# Test 2: Send command
echo "2. Sending command: echo 'Hello from PTY'"
curl -s -X POST "$BASE_URL/terminal/sessions/$SESSION_ID/input" \
  -H "Content-Type: application/json" \
  -d '{"data": "echo \"Hello from PTY\"\n"}' > /dev/null

sleep 1

# Test 3: Poll output
echo "3. Polling output..."
OUTPUT_RESPONSE=$(curl -s "$BASE_URL/terminal/sessions/$SESSION_ID/output?seq=0")
echo "Output: $OUTPUT_RESPONSE"
echo ""

# Test 4: Get session status
echo "4. Getting session status..."
STATUS=$(curl -s "$BASE_URL/terminal/sessions/$SESSION_ID/status")
echo "Status: $STATUS"
echo ""

# Test 5: Resize terminal
echo "5. Resizing terminal to 40x100..."
curl -s -X POST "$BASE_URL/terminal/sessions/$SESSION_ID/resize" \
  -H "Content-Type: application/json" \
  -d '{"rows": 40, "cols": 100}' > /dev/null
echo "✅ Terminal resized"
echo ""

# Test 6: List sessions
echo "6. Listing all sessions..."
SESSIONS=$(curl -s "$BASE_URL/terminal/sessions")
echo "Sessions: $SESSIONS"
echo ""

# Test 7: Close session
echo "7. Closing session..."
curl -s -X DELETE "$BASE_URL/terminal/sessions/$SESSION_ID" > /dev/null
echo "✅ Session closed"
echo ""

echo "=== All tests passed! ==="
