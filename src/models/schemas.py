"""
Pydantic models for request/response validation.

Contains all the data models used by the API endpoints for
request validation, response serialization, and documentation.
"""

from typing import Any, Optional

from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    """Request to create a new session or resume an existing one."""

    resume_session_id: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None  # e.g., "claude-3-5-sonnet-20241022"
    background_model: Optional[
        str
    ] = None  # Background model for agents (sets ANTHROPIC_DEFAULT_HAIKU_MODEL)
    enable_proxy: bool = False  # Enable LiteLLM proxy mode
    cwd: Optional[str] = None  # Working directory for the session


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
    cwd: Optional[str] = None


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
