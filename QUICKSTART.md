# Quick Start Guide

Get up and running with the Claude Agent API Server in 5 minutes.

## Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- Claude Code CLI installed: `npm install -g @anthropic-ai/claude-code`

## Installation

### 1. Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

### 2. Install Dependencies

```bash
# From the workspace root (claude-agent-sdk-python)
cd /path/to/claude-agent-sdk-python
uv sync

# This will install both the SDK and api_server dependencies
```

## Running the Server and Client

### Option 1: Using uv (Recommended)

```bash
# Terminal 1: Start the server
cd api_server
uv run src/server.py
```

```bash
# Terminal 2: Start the client
cd api_server
uv run src/client.py
```

### Option 2: Using the Start Script

```bash
# Terminal 1: Start the server
cd api_server
./start.sh
```

```bash
# Terminal 2: Start the client
cd api_server
uv run src/client.py
```

## First Conversation

Once the client is running:

```
👤 You: Hello! What can you help me with?
🤖 Claude: [Claude's response]

👤 You: List files in the current directory
🔧 Using tool: Bash
🤖 Claude: [Results]
```

## Common Commands

- `help` - Show help information
- `sessions` - List available sessions
- `clear` - Start a new session
- `exit` - Exit the program

## Permission Approval

When Claude needs to use a write operation:

```
⚠️  Permission Request
Tool: Bash
Command: ls -la

Allow? [Y/n/d]:
```

- Press `Y` or `Enter` to approve
- Press `n` to deny
- Press `d` to see details
- Press `a` to apply suggestions (if available)

## Testing the API

Run the example and test scripts:

```bash
# Run usage examples
uv run src/example.py

# Run invocations endpoint tests
uv run src/test_invocations.py
```

This will demonstrate:
- Simple conversations
- Session management
- Multi-turn dialogues
- Permission handling
- Unified /invocations endpoint

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Architecture

```
Client (client.py) ←→ HTTP API ←→ Server (server.py) ←→ Claude Agent SDK
```

- **Client**: Lightweight CLI with no SDK dependencies
- **Server**: Stateful API wrapper around the SDK
- **SDK**: Claude Agent SDK for Claude Code

## Troubleshooting

### "Cannot connect to server"

Make sure the server is running:
```bash
curl http://localhost:8000/health
```

### "Claude Code CLI not found"

Install the CLI:
```bash
npm install -g @anthropic-ai/claude-code
```

### Import errors

Make sure all dependencies are installed:
```bash
# From workspace root
uv sync

# Or reinstall if needed
uv sync --reinstall
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore [example.py](example.py) for programmatic usage
- Check out the API docs at http://localhost:8000/docs

## File Structure

```
api_server/
├── src/
│   ├── __init__.py           # Package initialization
│   ├── server.py             # FastAPI server implementation
│   ├── client.py             # Interactive CLI client
│   ├── example.py            # Usage examples
│   ├── test_invocations.py  # Test suite
│   └── main.py               # Entry points
├── pyproject.toml            # Project config (uv managed)
├── uv.lock                   # Dependency lock file
├── .python-version           # Python version specification
├── start.sh                  # Quick start script
├── README.md                 # Full documentation
├── QUICKSTART.md             # This file
└── LICENSE                   # MIT License
```

## Key Features

✅ **Multi-session support** - Run multiple conversations simultaneously
✅ **Permission control** - Approve tool usage interactively
✅ **Session persistence** - Resume previous conversations
✅ **Stateful API** - Server manages all SDK state
✅ **Lightweight client** - No SDK dependencies in client
✅ **RESTful API** - Easy integration with other tools

Happy coding! 🚀
