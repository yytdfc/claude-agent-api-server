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
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
    model: Optional[str] = None  # e.g., "claude-3-5-sonnet-20241022"
    background_model: Optional[str] = None  # Background model for agents (sets ANTHROPIC_DEFAULT_HAIKU_MODEL)
    enable_proxy: bool = False  # Enable LiteLLM proxy mode


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
    current_model: Optional[str] = None


class SetModelRequest(BaseModel):
    """Request to change the model for a session."""

    model: Optional[str] = None  # None means use default model


class SetPermissionModeRequest(BaseModel):
    """Request to change the permission mode for a session."""

    mode: str  # "default", "acceptEdits", "plan", "bypassPermissions"


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
        self,
        resume_session_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        background_model: Optional[str] = None,
        enable_proxy: bool = False,
        server_port: int = 8000,
    ) -> str:
        """
        Create a new session or resume an existing one.

        Args:
            resume_session_id: Optional session ID to resume
            system_prompt: Optional system prompt override
            model: Optional model name override
            background_model: Optional background model for agents
            enable_proxy: Enable LiteLLM proxy mode
            server_port: Server port for proxy mode

        Returns:
            The session ID (new or resumed)
        """
        session_id = resume_session_id or str(uuid.uuid4())

        if session_id in self.sessions:
            raise HTTPException(status_code=400, detail="Session already active")

        session = AgentSession(session_id, system_prompt, model, background_model, enable_proxy, server_port)
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

    def __init__(
        self,
        session_id: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        background_model: Optional[str] = None,
        enable_proxy: bool = False,
        server_port: int = 8000,
    ):
        """
        Initialize an agent session.

        Args:
            session_id: Unique session identifier
            system_prompt: Optional system prompt override
            model: Optional model name (defaults to ANTHROPIC_MODEL env var)
            background_model: Optional background model for agents
            enable_proxy: Enable LiteLLM proxy mode (sets ANTHROPIC_BASE_URL)
            server_port: Server port for proxy mode (default: 8000)
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
        # Model: use provided, or env var, or None (SDK default)
        self.model = model or os.environ.get("ANTHROPIC_MODEL")
        self.background_model = background_model  # Background model for agents
        self.current_model = self.model  # Track current model for status

        # Proxy configuration
        self.enable_proxy = enable_proxy
        self.server_port = server_port

        # Server info cache
        self.server_info: Optional[dict[str, Any]] = None

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

        if self.model:
            options_dict["model"] = self.model

        # Build environment variables
        env_vars = {}

        # Enable proxy mode by setting ANTHROPIC_BASE_URL
        if self.enable_proxy:
            env_vars["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{self.server_port}"
            # Disable Bedrock when using proxy mode
            env_vars["CLAUDE_CODE_USE_BEDROCK"] = "0"
            # Add placeholder API key (not actually used, just a placeholder)
            env_vars["ANTHROPIC_API_KEY"] = "placeholder"

            # If a background model is specified, set it as the default Haiku model for agents
            if self.background_model:
                env_vars["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = self.background_model

        # Add env vars if any were set
        if env_vars:
            options_dict["env"] = env_vars

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

    async def set_model(self, model: Optional[str]):
        """
        Change the model for this session.

        Args:
            model: Model name to use (None for default)

        Raises:
            HTTPException: If session not connected or SDK call fails
        """
        if not self.client or self.status != "connected":
            raise HTTPException(status_code=400, detail="Session not connected")

        try:
            await self.client.set_model(model)
            self.current_model = model
            self.model = model  # Update tracked model for consistency
            self.last_activity = datetime.now()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to set model: {str(e)}")

    async def interrupt(self):
        """
        Interrupt the current operation.

        Raises:
            HTTPException: If session not connected or SDK call fails
        """
        if not self.client or self.status != "connected":
            raise HTTPException(status_code=400, detail="Session not connected")

        try:
            await self.client.interrupt()
            self.last_activity = datetime.now()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to interrupt: {str(e)}")

    async def set_permission_mode(self, mode: str):
        """
        Change the permission mode for this session.

        Args:
            mode: Permission mode ("default", "acceptEdits", "plan", "bypassPermissions")

        Raises:
            HTTPException: If session not connected or SDK call fails
        """
        if not self.client or self.status != "connected":
            raise HTTPException(status_code=400, detail="Session not connected")

        try:
            await self.client.set_permission_mode(mode)
            self.last_activity = datetime.now()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to set permission mode: {str(e)}")

    async def get_server_info(self) -> dict[str, Any]:
        """
        Get server initialization info.

        Returns:
            Dictionary with server info (commands, output styles, etc.)

        Raises:
            HTTPException: If session not connected or info not available
        """
        if not self.client or self.status != "connected":
            raise HTTPException(status_code=400, detail="Session not connected")

        try:
            # Cache server info if not already cached
            if self.server_info is None:
                self.server_info = await self.client.get_server_info()

            if self.server_info is None:
                # Return empty dict if not available
                return {}

            return self.server_info
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get server info: {str(e)}")

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
            current_model=self.current_model,
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

# Add CORS middleware to allow web client access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
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
        model=request.model,
        background_model=request.background_model,
        enable_proxy=request.enable_proxy,
        server_port=8000,  # Using hardcoded port from uvicorn.run
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


@app.post("/sessions/{session_id}/model")
async def set_model(session_id: str, request: SetModelRequest):
    """
    Change the model for a session.

    Args:
        session_id: The session ID
        request: Model change request

    Returns:
        Success message with new model
    """
    session = session_manager.get_session(session_id)
    await session.set_model(request.model)
    return {"status": "ok", "model": request.model}


@app.post("/sessions/{session_id}/interrupt")
async def interrupt_session(session_id: str):
    """
    Interrupt the current operation in a session.

    Args:
        session_id: The session ID

    Returns:
        Success message
    """
    session = session_manager.get_session(session_id)
    await session.interrupt()
    return {"status": "interrupted"}


@app.post("/sessions/{session_id}/permission_mode")
async def set_permission_mode(session_id: str, request: SetPermissionModeRequest):
    """
    Change the permission mode for a session.

    Args:
        session_id: The session ID
        request: Permission mode change request

    Returns:
        Success message with new mode
    """
    session = session_manager.get_session(session_id)
    await session.set_permission_mode(request.mode)
    return {"status": "ok", "mode": request.mode}


@app.get("/sessions/{session_id}/server_info")
async def get_server_info(session_id: str):
    """
    Get server initialization info for a session.

    Args:
        session_id: The session ID

    Returns:
        Server info dictionary with commands, output styles, etc.
    """
    session = session_manager.get_session(session_id)
    info = await session.get_server_info()
    return info


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

        elif path.startswith("/sessions/") and path.endswith("/model") and method == "POST":
            # Set model
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(status_code=400, detail="Missing session_id in path_params")
            req = SetModelRequest(**payload)
            return await set_model(session_id, req)

        elif path.startswith("/sessions/") and path.endswith("/interrupt") and method == "POST":
            # Interrupt session
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(status_code=400, detail="Missing session_id in path_params")
            return await interrupt_session(session_id)

        elif path.startswith("/sessions/") and path.endswith("/permission_mode") and method == "POST":
            # Set permission mode
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(status_code=400, detail="Missing session_id in path_params")
            req = SetPermissionModeRequest(**payload)
            return await set_permission_mode(session_id, req)

        elif path.startswith("/sessions/") and path.endswith("/server_info") and method == "GET":
            # Get server info
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(status_code=400, detail="Missing session_id in path_params")
            return await get_server_info(session_id)

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
# LiteLLM Proxy Endpoint
# ============================================================================


def remove_cache_control(obj: Any) -> Any:
    """
    Recursively remove all cache_control fields from a data structure.

    This is needed for non-Claude models that don't support prompt caching.

    Args:
        obj: The object to process (dict, list, or primitive)

    Returns:
        The object with all cache_control fields removed
    """
    if isinstance(obj, dict):
        # Create a new dict without cache_control
        return {k: remove_cache_control(v) for k, v in obj.items() if k != "cache_control"}
    elif isinstance(obj, list):
        # Process each item in the list
        return [remove_cache_control(item) for item in obj]
    else:
        # Return primitives as-is
        return obj


@app.post("/v1/messages")
async def litellm_messages_proxy(request: Request):
    """
    LiteLLM proxy endpoint for Anthropic-compatible messages API.

    This endpoint forwards requests to LiteLLM for model inference,
    allowing the SDK client to use this server as ANTHROPIC_BASE_URL.

    Supports:
    - Streaming responses
    - Multiple model providers via LiteLLM
    - Compatible with Anthropic Messages API format
    - Automatic removal of cache_control for non-Claude models
    """
    try:
        # Try to import litellm
        try:
            import litellm
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="LiteLLM is not installed. Install with: pip install litellm",
            )

        body = await request.json()

        # Check if model is a Claude model
        model = body.get("model", "")
        is_claude_model = "claude" in model.lower()

        # Remove cache_control if not a Claude model
        if not is_claude_model:
            body = remove_cache_control(body)

        # Check if streaming is requested
        is_streaming = body.get("stream", False)

        if is_streaming:
            # Streaming response
            async def generate_stream():
                try:
                    # Forward to LiteLLM with streaming
                    response = await litellm.acompletion(**body)

                    async for chunk in response:
                        # Forward raw chunk in SSE format
                        if hasattr(chunk, "model_dump_json"):
                            # Pydantic model
                            yield f"data: {chunk.model_dump_json()}\n\n"
                        elif hasattr(chunk, "json"):
                            # Dict-like with json method
                            yield f"data: {chunk.json()}\n\n"
                        else:
                            # Plain dict
                            yield f"data: {json.dumps(chunk)}\n\n"

                except Exception as e:
                    error_data = {
                        "error": {"message": str(e), "type": type(e).__name__}
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
            )
        else:
            # Non-streaming response
            try:
                response = await litellm.acompletion(**body)

                # Convert response to dict
                if hasattr(response, "model_dump"):
                    return response.model_dump()
                elif hasattr(response, "dict"):
                    return response.dict()
                else:
                    return response

            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail={"error": {"message": str(e), "type": type(e).__name__}},
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": str(e), "type": type(e).__name__}},
        )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
