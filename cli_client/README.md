# CLI Clients

This directory contains CLI clients for interacting with the Claude Agent API Server.

## Available Clients

### 1. AgentClient (`client.py`)

Full-featured Python client for the Claude Agent SDK API.

**Features:**
- Session management (create, resume, close)
- Message sending and receiving
- Permission handling
- Async/await support
- Direct and Invocations API modes

**Usage:**
```python
from cli_client import AgentClient

client = AgentClient(base_url="http://127.0.0.1:8000")
session = await client.create_session()
response = await client.send_message(session["session_id"], "Hello!")
```

### 2. Shell Client (`shell_client.py`)

Interactive shell terminal client using invocations API with httpx streaming.

**Features:**
- Interactive command-line shell
- Streaming command output (real-time display)
- Working directory management
- cd command support
- Uses invocations API mode
- httpx for HTTP streaming

**Usage:**
```bash
# Basic usage
python cli_client/shell_client.py

# Specify server URL
python cli_client/shell_client.py --url http://localhost:8000

# Set initial working directory
python cli_client/shell_client.py --cwd /workspace

# Make it executable
chmod +x cli_client/shell_client.py
./cli_client/shell_client.py
```

**Commands:**
- Type any shell command and press Enter
- `cd <path>` - Change directory
- `exit` or `quit` - Exit the shell
- `Ctrl+C` - Interrupt current command

**Example Session:**
```
$ ./cli_client/shell_client.py
Shell CLI Client
Connected to: http://127.0.0.1:8000
Working directory: /workspace

/workspace $ ls
file1.txt  file2.py  folder/

/workspace $ cd folder

/workspace/folder $ pwd
/workspace/folder

/workspace/folder $ exit
Goodbye!
```

## Requirements

- Python 3.8+
- httpx (for shell_client.py)
- aiohttp (for client.py)

Install dependencies:
```bash
pip install httpx aiohttp
```

## API Modes

Both clients support invocations API mode, where all requests are routed through a single `/invocations` endpoint. The shell client exclusively uses invocations mode for all operations.

## Server Logs

When using invocations mode, the server logs each forwarded request:
```
🔀 Invocation → POST /shell/execute
🔀 Invocation → GET /shell/cwd
```
