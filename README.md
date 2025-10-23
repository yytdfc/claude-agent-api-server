# Claude Agent API Server

A client-server architecture for the Claude Agent SDK that separates the SDK logic into a stateful API server and provides a lightweight command-line client.

## Architecture

```
┌─────────────────┐         HTTP/REST API        ┌──────────────────┐
│                 │ ◄─────────────────────────── │                  │
│   API Server    │                              │  CLI Client      │
│   (server.py)   │ ─────────────────────────► │  (client.py)     │
│                 │                              │                  │
└────────┬────────┘                              └──────────────────┘
         │
         │ Uses SDK
         │
         ▼
┌─────────────────┐
│  Claude Agent   │
│      SDK        │
└─────────────────┘
```

### Components

1. **API Server (`server.py`)**
   - Wraps the Claude Agent SDK
   - Manages multiple concurrent sessions
   - Handles permission callbacks
   - Provides RESTful API endpoints
   - Stateful session management

2. **CLI Client (`client.py`)**
   - Lightweight command-line interface
   - No SDK dependencies
   - Communicates with server via HTTP
   - Interactive permission approval
   - Session management commands

## Features

### API Server
- ✅ Multi-session support with unique session IDs
- ✅ Stateful conversation management
- ✅ Permission callback system
- ✅ Session restoration from disk
- ✅ Graceful shutdown and cleanup
- ✅ Health check endpoints
- ✅ Async/await throughout

### CLI Client
- ✅ Interactive command-line interface
- ✅ Colored output for better readability
- ✅ Session management (create, resume, list)
- ✅ Permission approval workflow
- ✅ Command shortcuts (exit, clear, sessions, help)
- ✅ Background permission checking
- ✅ Error handling and recovery

## Installation

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer

### Installing uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

### Setup

This project uses `uv` for dependency management and is configured as a workspace member.

```bash
# Install all dependencies (from parent directory)
cd /path/to/claude-agent-sdk-python
uv sync

# Or install just for api_server
cd api_server
uv sync
```

The project structure uses a `src/` layout:
```
api_server/
├── src/
│   ├── __init__.py
│   ├── server.py          # FastAPI server
│   ├── client.py          # CLI client
│   ├── example.py         # Usage examples
│   ├── test_invocations.py # Tests
│   └── main.py            # Entry points
├── pyproject.toml         # Project config (uv managed)
├── uv.lock               # Lock file
└── README.md
```

### Dependencies

All dependencies are managed via `pyproject.toml`:
- `claude-agent-sdk` (workspace dependency)
- `fastapi>=0.119.1`
- `uvicorn` (auto-installed with FastAPI)
- `httpx` (auto-installed with FastAPI)

## Usage

### Starting the Server

```bash
# Using uv (recommended)
uv run src/server.py

# Or use the start script
./start.sh

# Or with uvicorn directly for development
uv run uvicorn src.server:app --host 127.0.0.1 --port 8000 --reload
```

The server will start on `http://127.0.0.1:8000` by default.

### Using the Client

```bash
# Start the interactive client
uv run src/client.py

# With custom server URL
uv run src/client.py --server http://localhost:8000
```

### Interactive Commands

Once the client is running, you can use these commands:

- **Regular conversation**: Just type your message
- **`exit` or `quit`**: Exit the program
- **`clear`**: Start a new session
- **`sessions`**: List all available sessions
- **`help`**: Show help information

### Permission Workflow

When Claude needs to use a write tool (Write, Edit, Bash), you'll be prompted:

```
⚠️  Permission Request
Tool: Bash
Command: ls -la

Allow? [Y/n/a(apply suggestions)/d(details)]:
```

Options:
- **Y/yes/Enter**: Allow this operation
- **n/no**: Deny this operation
- **a**: Apply system suggestions (e.g., switch to acceptEdits mode)
- **d**: Show detailed information about the request

## API Endpoints

### Unified Invocations Endpoint

The `/invocations` endpoint provides a single entry point for all API operations.

#### POST /invocations

```http
POST /invocations
Content-Type: application/json

{
  "path": "/sessions/{session_id}/messages",
  "method": "POST",
  "path_params": {"session_id": "abc123"},
  "payload": {"message": "Hello"}
}
```

**Request Parameters:**
- `path` (required): The API path to invoke (e.g., "/sessions", "/sessions/{id}/messages")
- `method` (optional): HTTP method (GET, POST, DELETE) - defaults to POST
- `payload` (optional): The request payload for the target endpoint
- `path_params` (optional): Dictionary of path parameters (e.g., {"session_id": "abc"})

**Examples:**

Create session:
```json
{
  "path": "/sessions",
  "method": "POST",
  "payload": {"resume_session_id": "optional-id"}
}
```

Send message:
```json
{
  "path": "/sessions/{session_id}/messages",
  "method": "POST",
  "path_params": {"session_id": "abc123"},
  "payload": {"message": "What is 2+2?"}
}
```

Get status:
```json
{
  "path": "/sessions/{session_id}/status",
  "method": "GET",
  "path_params": {"session_id": "abc123"}
}
```

Close session:
```json
{
  "path": "/sessions/{session_id}",
  "method": "DELETE",
  "path_params": {"session_id": "abc123"}
}
```

**Testing:**
```bash
# Run the test suite
python test_invocations.py

# Or test with curl
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/health",
    "method": "GET"
  }'
```

### Session Management

#### Create Session
```http
POST /sessions
Content-Type: application/json

{
  "resume_session_id": "optional-session-id",
  "system_prompt": "Optional custom system prompt"
}
```

Response:
```json
{
  "session_id": "uuid-here",
  "created_at": "2024-01-01T00:00:00",
  "status": "connected"
}
```

#### List Active Sessions
```http
GET /sessions
```

Response:
```json
{
  "sessions": [
    {
      "session_id": "uuid-here",
      "created_at": "2024-01-01T00:00:00",
      "last_activity": "2024-01-01T00:05:00",
      "status": "connected",
      "message_count": 5
    }
  ]
}
```

#### List Available Sessions (from disk)
```http
GET /sessions/available
```

Response:
```json
{
  "sessions": [
    {
      "session_id": "session-id-here",
      "modified": "2024-01-01T00:00:00",
      "preview": "Session preview...",
      "project": "project-name"
    }
  ]
}
```

#### Get Session Status
```http
GET /sessions/{session_id}/status
```

Response:
```json
{
  "session_id": "uuid-here",
  "status": "connected",
  "pending_permission": {
    "request_id": "perm-uuid",
    "tool_name": "Bash",
    "tool_input": {"command": "ls -la"},
    "suggestions": []
  }
}
```

#### Close Session
```http
DELETE /sessions/{session_id}
```

### Messages

#### Send Message
```http
POST /sessions/{session_id}/messages
Content-Type: application/json

{
  "message": "Your message here"
}
```

Response:
```json
{
  "messages": [
    {
      "type": "text",
      "content": "Claude's response here"
    },
    {
      "type": "tool_use",
      "tool_name": "Read",
      "tool_input": {"file_path": "/path/to/file"}
    }
  ],
  "session_id": "uuid-here",
  "cost_usd": 0.001234,
  "num_turns": 3
}
```

### Permissions

#### Respond to Permission Request
```http
POST /sessions/{session_id}/permissions/respond
Content-Type: application/json

{
  "request_id": "perm-uuid",
  "allowed": true,
  "apply_suggestions": false
}
```

### Health Check

```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "active_sessions": 2,
  "timestamp": "2024-01-01T00:00:00"
}
```

## Architecture Details

### Session Lifecycle

1. **Creation**: Client sends POST to `/sessions`
2. **Connection**: Server creates SDK client and connects
3. **Messages**: Client sends messages, receives responses
4. **Permissions**: Background polling for permission requests
5. **Closure**: Client sends DELETE to close session
6. **Cleanup**: Server disconnects SDK client and removes session

### Permission Flow

```
┌──────────┐                  ┌──────────┐                  ┌──────────┐
│  Client  │                  │  Server  │                  │   SDK    │
└────┬─────┘                  └────┬─────┘                  └────┬─────┘
     │                             │                             │
     │  1. Send message            │                             │
     ├────────────────────────────►│                             │
     │                             │  2. Process message         │
     │                             ├────────────────────────────►│
     │                             │                             │
     │                             │  3. Tool needs permission   │
     │                             │◄────────────────────────────┤
     │                             │     (callback invoked)      │
     │                             │                             │
     │  4. Poll for status         │                             │
     ├────────────────────────────►│                             │
     │  5. Pending permission      │                             │
     │◄────────────────────────────┤                             │
     │                             │                             │
     │  6. User approves           │                             │
     ├────────────────────────────►│                             │
     │                             │  7. Return permission       │
     │                             ├────────────────────────────►│
     │                             │                             │
     │                             │  8. Tool executes           │
     │                             │◄────────────────────────────┤
     │                             │                             │
     │  9. Get response            │                             │
     │◄────────────────────────────┤                             │
     │                             │                             │
```

### State Management

The server maintains session state in memory:

- **SessionManager**: Global singleton managing all sessions
- **AgentSession**: Individual session with SDK client
- **Permission State**: Pending permission requests with async events

Sessions are automatically cleaned up on:
- Client-initiated closure (DELETE request)
- Server shutdown (graceful cleanup)
- Permission timeout (5 minutes)

## Error Handling

### Client Errors
- Connection failures: Displays error and instructions
- Invalid input: Prompts for valid input
- Server errors: Shows error message and continues

### Server Errors
- SDK connection failures: Returns 500 error
- Invalid session ID: Returns 404 error
- Permission timeout: Auto-denies and returns error

## Development

### Running Tests

```bash
# Start server in one terminal
uv run src/server.py

# In another terminal, run tests
uv run src/test_invocations.py

# Or test with curl
curl http://localhost:8000/health

# Run examples
uv run src/example.py
```

### API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Code Quality

```bash
# Format code
uv run ruff format src/

# Check linting
uv run ruff check src/

# Type checking (if mypy is added)
uv run mypy src/
```

### Extending the API

To add new endpoints:

1. Define Pydantic models for request/response in `src/server.py`
2. Add endpoint function to `src/server.py`
3. Update `APIClient` in `src/client.py`
4. Add client command/feature as needed
5. Update `/invocations` routing if necessary

## Troubleshooting

### Server won't start
- Check if port 8000 is already in use
- Verify all dependencies are installed: `uv sync`
- Check Claude CLI is installed: `npx @anthropic-ai/claude-code --version`
- Try running with: `uv run src/server.py`

### Client can't connect
- Verify server is running: `curl http://localhost:8000/health`
- Check firewall settings
- Verify correct server URL
- Ensure uv environment is activated

### Permission requests hang
- Check server logs for errors
- Verify client is polling for permissions
- Check network connectivity

### uv sync fails
- Ensure you're in the workspace root or api_server directory
- Check Python version: `python --version` (requires 3.12+)
- Try: `uv sync --reinstall`

## License

Same as the parent Claude Agent SDK project.

## Contributing

Contributions welcome! Please ensure:
- Code follows existing style (English comments, type hints)
- All endpoints have proper error handling
- Documentation is updated
