#!/bin/bash
# Quick start script for Claude Agent API Server

echo "=========================================="
echo "Claude Agent API Server - Quick Start"
echo "=========================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check if in correct directory
if [ ! -f "server.py" ]; then
    echo "❌ Please run this script from the api_server directory"
    exit 1
fi

# Check if dependencies are installed
echo "Checking dependencies..."
python3 -c "import fastapi, uvicorn, httpx" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Dependencies not found. Installing..."
    pip install -r requirements.txt
fi

# Check if SDK is installed
python3 -c "import claude_agent_sdk" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Claude Agent SDK not found. Installing from parent directory..."
    pip install -e ..
fi

echo ""
echo "✅ All dependencies are ready"
echo ""
echo "Starting server on http://127.0.0.1:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

# Start the server
python3 server.py
