# Quick Start Guide

Get up and running with the Claude Agent API Server in 5 minutes.

## Prerequisites

- Python 3.8 or higher
- Claude Code CLI installed: `npm install -g @anthropic-ai/claude-code`

## Installation

### 1. Install the SDK

```bash
# From the project root directory
cd /path/to/claude-agent-sdk-python
pip install -e .
```

### 2. Install API Server Dependencies

```bash
cd api_server
pip install -r requirements.txt
```

## Running the Server and Client

### Option 1: Using the Start Script (Easiest)

```bash
# Terminal 1: Start the server
./start.sh
```

```bash
# Terminal 2: Start the client
python client.py
```

### Option 2: Manual Start

```bash
# Terminal 1: Start the server
python server.py
```

```bash
# Terminal 2: Start the client
python client.py
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

Run the example script:

```bash
python example.py
```

This will demonstrate:
- Simple conversations
- Session management
- Multi-turn dialogues
- Permission handling

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
pip install -r requirements.txt
pip install -e ..  # Install SDK
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore [example.py](example.py) for programmatic usage
- Check out the API docs at http://localhost:8000/docs

## File Structure

```
api_server/
├── server.py          # FastAPI server implementation
├── client.py          # Interactive CLI client
├── example.py         # Usage examples
├── requirements.txt   # Python dependencies
├── start.sh          # Quick start script
├── README.md         # Full documentation
├── QUICKSTART.md     # This file
└── __init__.py       # Package initialization
```

## Key Features

✅ **Multi-session support** - Run multiple conversations simultaneously
✅ **Permission control** - Approve tool usage interactively
✅ **Session persistence** - Resume previous conversations
✅ **Stateful API** - Server manages all SDK state
✅ **Lightweight client** - No SDK dependencies in client
✅ **RESTful API** - Easy integration with other tools

Happy coding! 🚀
