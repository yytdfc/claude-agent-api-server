#!/bin/bash
# Quick test for PTY client

echo "Testing PTY client with server on port 8001..."
echo ""
echo "Running: uv run cli_client/pty_client.py --url http://localhost:8001"
echo ""
echo "Once connected, try these commands:"
echo "  - ls -la"
echo "  - pwd"
echo "  - vim test.txt  (press 'i' to insert, type, then ESC :wq to save)"
echo "  - htop  (if installed, press 'q' to quit)"
echo "  - exit  (to close the terminal)"
echo ""
echo "Press Enter to start..."
read

uv run cli_client/pty_client.py --url http://localhost:8001
