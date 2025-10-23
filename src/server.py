#!/usr/bin/env python3
"""
Claude Agent API Server

A stateful API server that wraps the Claude Agent SDK and provides
RESTful endpoints for client applications. Manages multiple concurrent
sessions with full support for conversation history, permission control,
and session lifecycle management.

Key Features:
- Session-based state management
- Permission callback system
- Multi-turn conversation support
- Session history and restoration
- Graceful error handling
"""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    CLINotFoundError,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    TextBlock,
    ToolPermissionContext,
    ToolUseBlock,
    UserMessage,
)

# ============================================================================
# Data Models
# ============================================================================


class CreateSessionRequest(BaseModel):
    """Request to create a new session or resume an existing one."""

    resume_session_id: Optional[str] = None
    system_prompt: Optional[str] = None


class CreateSessionResponse(BaseModel):
    """Response containing new session information."""

    session_id: str
    created_at: str
    status: str


class SendMessageRequest(BaseModel):
    """Request to send a message in a session."""

    message: str


class MessageBlock(BaseModel):
    """Represents a single content block in a message."""

    type: str  # "text", "tool_use", "thinking"
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[dict[str, Any]] = None


class SendMessageResponse(BaseModel):
    """Response containing assistant's reply."""

    messages: list[MessageBlock]
    session_id: str
    cost_usd: Optional[float] = None
    num_turns: Optional[int] = None


class SessionInfo(BaseModel):
    """Information about a session."""

    session_id: str
    created_at: str
    last_activity: str
    status: str
    message_count: int


class ListSessionsResponse(BaseModel):
    """Response containing list of sessions."""

    sessions: list[SessionInfo]


class PermissionRequest(BaseModel):
    """Pending permission request."""

    request_id: str
    tool_name: str
    tool_input: dict[str, Any]
    suggestions: list[dict[str, Any]]


class PermissionResponse(BaseModel):
    """User's response to permission request."""

    request_id: str
    allowed: bool
    apply_suggestions: bool = False


class SessionStatus(BaseModel):
    """Current status of a session."""

    session_id: str
    status: str
    pending_permission: Optional[PermissionRequest] = None


# ============================================================================
# Session Manager
# ============================================================================


class SessionManager:
    """
    Manages multiple concurrent Claude Agent sessions.

    Each session maintains its own SDK client, conversation history,
    and permission state. Supports session creation, restoration,
    and cleanup.
    """

    def __init__(self):
        """Initialize the session manager."""
        self.sessions: dict[str, "AgentSession"] = {}
        self.session_dir = Path.home() / ".claude" / "projects"

    async def create_session(
        self, resume_session_id: Optional[str] = None, system_prompt: Optional[str] = None
    ) -> str:
        """
        Create a new session or resume an existing one.

        Args:
            resume_session_id: Optional session ID to resume
            system_prompt: Optional system prompt override

        Returns:
            The session ID (new or resumed)
        """
        session_id = resume_session_id or str(uuid.uuid4())

        if session_id in self.sessions:
            raise HTTPException(status_code=400, detail="Session already active")

        session = AgentSession(session_id, system_prompt)
        await session.connect(resume_session_id)

        self.sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> "AgentSession":
        """
        Get an active session by ID.

        Args:
            session_id: The session ID

        Returns:
            The AgentSession instance

        Raises:
            HTTPException: If session not found
        """
        if session_id not in self.sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        return self.sessions[session_id]

    async def close_session(self, session_id: str):
        """
        Close and cleanup a session.

        Args:
            session_id: The session ID to close
        """
        if session_id in self.sessions:
            session = self.sessions[session_id]
            await session.disconnect()
            del self.sessions[session_id]

    def list_sessions(self) -> list[SessionInfo]:
        """
        List all active sessions.

        Returns:
            List of SessionInfo objects
        """
        result = []
        for session_id, session in self.sessions.items():
            result.append(
                SessionInfo(
                    session_id=session_id,
                    created_at=session.created_at.isoformat(),
                    last_activity=session.last_activity.isoformat(),
                    status=session.status,
                    message_count=session.message_count,
                )
            )
        return result

    def list_available_sessions(self) -> list[dict[str, Any]]:
        """
        List all available sessions from disk.

        Returns:
            List of session information dictionaries
        """
        sessions = []

        if not self.session_dir.exists():
            return sessions

        # Scan all project directories
        for project_dir in self.session_dir.iterdir():
            if not project_dir.is_dir():
                continue

            for session_file in project_dir.glob("*.jsonl"):
                try:
                    session_id = session_file.stem
                    mtime = session_file.stat().st_mtime
                    modified = datetime.fromtimestamp(mtime)

                    # Read first few lines for preview
                    preview = "No preview"
                    summary = None

                    with open(session_file, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue

                            try:
                                entry = json.loads(line)
                                entry_type = entry.get("type")

                                if entry_type == "summary" and not summary:
                                    summary = entry.get("summary", "")
                                    if summary:
                                        break
                            except json.JSONDecodeError:
                                continue

                    if summary:
                        preview = summary[:100]

                    sessions.append(
                        {
                            "session_id": session_id,
                            "modified": modified.isoformat(),
                            "preview": preview,
                            "project": project_dir.name,
                        }
                    )
                except Exception:
                    continue

        # Sort by modification time
        sessions.sort(key=lambda x: x["modified"], reverse=True)
        return sessions


# ============================================================================
# Agent Session
# ============================================================================


class AgentSession:
    """
    Represents a single Claude Agent session.

    Manages the SDK client, permission callbacks, and conversation state
    for one interactive session.
    """

    def __init__(self, session_id: str, system_prompt: Optional[str] = None):
        """
        Initialize an agent session.

        Args:
            session_id: Unique session identifier
            system_prompt: Optional system prompt override
        """
        self.session_id = session_id
        self.client: Optional[ClaudeSDKClient] = None
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.status = "initializing"
        self.message_count = 0

        # Permission management
        self.pending_permission: Optional[dict[str, Any]] = None
        self.permission_event: Optional[asyncio.Event] = None
        self.permission_result: Optional[Any] = None

        # Session configuration
        self.system_prompt = system_prompt or "You are a helpful AI assistant."

    async def connect(self, resume_session_id: Optional[str] = None):
        """
        Connect the SDK client and initialize the session.

        Args:
            resume_session_id: Optional session ID to resume from
        """
        options_dict = {
            "allowed_tools": ["Read", "Glob", "Grep"],
            "system_prompt": self.system_prompt,
            "max_turns": 0,
            "can_use_tool": self.permission_callback,
            "permission_mode": "default",
        }

        if resume_session_id:
            options_dict["resume"] = resume_session_id

        options = ClaudeAgentOptions(**options_dict)

        try:
            self.client = ClaudeSDKClient(options=options)
            await self.client.connect()
            self.status = "connected"
        except (CLINotFoundError, CLIConnectionError) as e:
            self.status = "error"
            raise HTTPException(status_code=500, detail=f"Failed to connect: {str(e)}")

    async def disconnect(self):
        """Disconnect the SDK client and cleanup."""
        if self.client:
            await self.client.disconnect()
            self.status = "disconnected"

    async def permission_callback(
        self, tool_name: str, input_data: dict, context: ToolPermissionContext
    ) -> PermissionResultAllow | PermissionResultDeny:
        """
        Permission callback for tool usage.

        This method is called by the SDK when a tool needs permission.
        It creates a pending permission request and waits for the client
        to respond via the API.

        Args:
            tool_name: Name of the tool requesting permission
            input_data: Tool input parameters
            context: Permission context with suggestions

        Returns:
            Permission result (allow or deny)
        """
        # Auto-allow read-only operations
        if tool_name in ["Read", "Glob", "Grep"]:
            return PermissionResultAllow()

        # Create permission request
        request_id = str(uuid.uuid4())
        self.pending_permission = {
            "request_id": request_id,
            "tool_name": tool_name,
            "tool_input": input_data,
            "suggestions": [s.__dict__ if hasattr(s, "__dict__") else s for s in context.suggestions],
        }

        # Create event to wait for response
        self.permission_event = asyncio.Event()
        self.permission_result = None

        # Wait for client to respond (with timeout)
        try:
            await asyncio.wait_for(self.permission_event.wait(), timeout=300)  # 5 minute timeout
        except asyncio.TimeoutError:
            self.pending_permission = None
            return PermissionResultDeny(message="Permission request timed out")

        # Get result
        result = self.permission_result
        self.pending_permission = None
        self.permission_event = None
        self.permission_result = None

        return result

    def respond_to_permission(
        self, request_id: str, allowed: bool, apply_suggestions: bool = False
    ):
        """
        Respond to a pending permission request.

        Args:
            request_id: The permission request ID
            allowed: Whether to allow the operation
            apply_suggestions: Whether to apply permission suggestions

        Raises:
            HTTPException: If no matching pending permission
        """
        if not self.pending_permission or self.pending_permission["request_id"] != request_id:
            raise HTTPException(status_code=404, detail="No matching permission request")

        if allowed:
            if apply_suggestions and self.pending_permission["suggestions"]:
                # Apply suggestions by converting them back to PermissionUpdate objects
                from claude_agent_sdk import PermissionUpdate

                suggestions = []
                for s in self.pending_permission["suggestions"]:
                    suggestions.append(PermissionUpdate(**s))

                self.permission_result = PermissionResultAllow(updated_permissions=suggestions)
            else:
                self.permission_result = PermissionResultAllow()
        else:
            self.permission_result = PermissionResultDeny(message="User denied")

        # Signal that response is ready
        if self.permission_event:
            self.permission_event.set()

    async def send_message(self, message: str) -> SendMessageResponse:
        """
        Send a message and get the response.

        Args:
            message: The user's message

        Returns:
            SendMessageResponse with assistant's reply

        Raises:
            HTTPException: If session not connected
        """
        if not self.client or self.status != "connected":
            raise HTTPException(status_code=400, detail="Session not connected")

        self.last_activity = datetime.now()
        self.message_count += 1

        # Send message
        await self.client.query(message)

        # Collect response
        messages = []
        cost_usd = None
        num_turns = None

        async for msg in self.client.receive_response():
            if isinstance(msg, UserMessage):
                # Skip user messages in response
                pass
            elif isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        messages.append(MessageBlock(type="text", content=block.text))
                    elif isinstance(block, ToolUseBlock):
                        messages.append(
                            MessageBlock(
                                type="tool_use",
                                tool_name=block.name,
                                tool_input=block.input,
                            )
                        )
            elif isinstance(msg, ResultMessage):
                cost_usd = msg.total_cost_usd
                num_turns = msg.num_turns

        return SendMessageResponse(
            messages=messages,
            session_id=self.session_id,
            cost_usd=cost_usd,
            num_turns=num_turns,
        )

    def get_status(self) -> SessionStatus:
        """
        Get current session status.

        Returns:
            SessionStatus object
        """
        pending_perm = None
        if self.pending_permission:
            pending_perm = PermissionRequest(**self.pending_permission)

        return SessionStatus(
            session_id=self.session_id,
            status=self.status,
            pending_permission=pending_perm,
        )


# ============================================================================
# FastAPI Application
# ============================================================================

session_manager = SessionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    yield
    # Shutdown - close all sessions
    for session_id in list(session_manager.sessions.keys()):
        await session_manager.close_session(session_id)


app = FastAPI(
    title="Claude Agent API Server",
    description="Stateful API server for Claude Agent SDK",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# API Endpoints
# ============================================================================


@app.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    Create a new session or resume an existing one.

    Args:
        request: Session creation request

    Returns:
        Session information
    """
    session_id = await session_manager.create_session(
        resume_session_id=request.resume_session_id,
        system_prompt=request.system_prompt,
    )

    return CreateSessionResponse(
        session_id=session_id,
        created_at=datetime.now().isoformat(),
        status="connected",
    )


@app.get("/sessions", response_model=ListSessionsResponse)
async def list_sessions():
    """
    List all active sessions.

    Returns:
        List of active sessions
    """
    sessions = session_manager.list_sessions()
    return ListSessionsResponse(sessions=sessions)


@app.get("/sessions/available")
async def list_available_sessions():
    """
    List all available sessions from disk.

    Returns:
        List of available sessions
    """
    sessions = session_manager.list_available_sessions()
    return {"sessions": sessions}


@app.get("/sessions/{session_id}/status", response_model=SessionStatus)
async def get_session_status(session_id: str):
    """
    Get the status of a session.

    Args:
        session_id: The session ID

    Returns:
        Session status including pending permissions
    """
    session = session_manager.get_session(session_id)
    return session.get_status()


@app.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(session_id: str, request: SendMessageRequest):
    """
    Send a message in a session.

    Args:
        session_id: The session ID
        request: Message request

    Returns:
        Assistant's response
    """
    session = session_manager.get_session(session_id)
    return await session.send_message(request.message)


@app.post("/sessions/{session_id}/permissions/respond")
async def respond_to_permission(session_id: str, response: PermissionResponse):
    """
    Respond to a pending permission request.

    Args:
        session_id: The session ID
        response: Permission response

    Returns:
        Success message
    """
    session = session_manager.get_session(session_id)
    session.respond_to_permission(
        request_id=response.request_id,
        allowed=response.allowed,
        apply_suggestions=response.apply_suggestions,
    )
    return {"status": "ok"}


@app.delete("/sessions/{session_id}")
async def close_session(session_id: str):
    """
    Close a session.

    Args:
        session_id: The session ID

    Returns:
        Success message
    """
    await session_manager.close_session(session_id)
    return {"status": "closed"}


@app.post("/invocations")
async def invocations(request: dict[str, Any]):
    """
    Unified invocation endpoint that routes to other API endpoints.

    This endpoint provides a single entry point for all API operations,
    routing requests based on the path and payload parameters.

    Args:
        request: Dictionary containing:
            - path: The API path to invoke (e.g., "/sessions", "/sessions/{id}/messages")
            - method: HTTP method (GET, POST, DELETE) - optional, defaults to POST
            - payload: The request payload (optional)
            - path_params: Path parameters as dict (optional, e.g., {"session_id": "abc"})

    Returns:
        The response from the invoked endpoint

    Examples:
        Create session:
        {
            "path": "/sessions",
            "method": "POST",
            "payload": {"resume_session_id": "optional-id"}
        }

        Send message:
        {
            "path": "/sessions/{session_id}/messages",
            "method": "POST",
            "path_params": {"session_id": "abc123"},
            "payload": {"message": "Hello"}
        }

        Get status:
        {
            "path": "/sessions/{session_id}/status",
            "method": "GET",
            "path_params": {"session_id": "abc123"}
        }
    """
    path = request.get("path")
    method = request.get("method", "POST").upper()
    payload = request.get("payload", {})
    path_params = request.get("path_params", {})

    if not path:
        raise HTTPException(status_code=400, detail="Missing 'path' parameter")

    # Replace path parameters
    resolved_path = path
    for key, value in path_params.items():
        resolved_path = resolved_path.replace(f"{{{key}}}", str(value))

    # Route to appropriate endpoint based on path and method
    try:
        if path == "/sessions" and method == "POST":
            # Create session
            req = CreateSessionRequest(**payload)
            return await create_session(req)

        elif path == "/sessions" and method == "GET":
            # List sessions
            return await list_sessions()

        elif path == "/sessions/available" and method == "GET":
            # List available sessions
            return await list_available_sessions()

        elif path.startswith("/sessions/") and path.endswith("/status") and method == "GET":
            # Get session status
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(status_code=400, detail="Missing session_id in path_params")
            return await get_session_status(session_id)

        elif path.startswith("/sessions/") and path.endswith("/messages") and method == "POST":
            # Send message
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(status_code=400, detail="Missing session_id in path_params")
            req = SendMessageRequest(**payload)
            return await send_message(session_id, req)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/permissions/respond")
            and method == "POST"
        ):
            # Respond to permission
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(status_code=400, detail="Missing session_id in path_params")
            resp = PermissionResponse(**payload)
            return await respond_to_permission(session_id, resp)

        elif path.startswith("/sessions/") and method == "DELETE":
            # Close session
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(status_code=400, detail="Missing session_id in path_params")
            return await close_session(session_id)

        elif path == "/health" and method == "GET":
            # Health check
            return await health_check()

        else:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown path or method: {method} {path}",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invocation error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_sessions": len(session_manager.sessions),
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
