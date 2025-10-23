#!/bin/bash
# Quick start script for Claude Agent API Server

echo "=========================================="
echo "Claude Agent API Server - Quick Start"
echo "=========================================="
echo ""

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed"
    echo "💡 Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if in correct directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Please run this script from the api_server directory"
    exit 1
fi

# Check if src/server.py exists
if [ ! -f "src/server.py" ]; then
    echo "❌ src/server.py not found"
    exit 1
fi

# Ensure dependencies are installed
echo "Checking dependencies..."
uv sync --quiet 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Running uv sync to install dependencies..."
    uv sync
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
uv run src/server.py
