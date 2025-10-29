"""
Unified Invocation Endpoint.

Provides a single entry point for all API operations, routing requests
based on the path and payload parameters.
"""

import jwt
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request

from ..models import (
    CreateSessionRequest,
    PermissionResponse,
    SendMessageRequest,
    SetModelRequest,
    SetPermissionModeRequest,
)
from .messages import (
    get_session_status,
    interrupt_session,
    send_message,
    set_model,
    set_permission_mode,
)
from .permissions import respond_to_permission
from .files import get_file_info, list_files, save_file, SaveFileRequest
from .shell import execute_command, get_current_directory, set_current_directory, ShellExecuteRequest
from .terminal import (
    create_session as create_terminal_session,
    get_session_output,
    send_input,
    resize_session,
    close_session as close_terminal_session,
    get_session_status as get_terminal_status,
    list_sessions as list_terminal_sessions,
    CreateSessionRequest as TerminalCreateRequest,
    InputRequest,
    ResizeRequest
)
from .sessions import (
    close_session,
    create_session,
    get_server_info,
    get_session_history,
    list_available_sessions,
    list_sessions,
)

router = APIRouter()


def parse_session_and_user_from_headers(request: Request) -> tuple[Optional[str], Optional[str]]:
    """
    Parse agentcore_session_id and user_id from request headers.

    Args:
        request: FastAPI Request object

    Returns:
        Tuple of (agentcore_session_id, user_id)
    """
    agentcore_session_id = None
    user_id = None

    # Extract agentcore_session_id from X-Amzn-Bedrock-AgentCore-Runtime-Session-Id header
    # FastAPI headers are case-insensitive, but we try common variations
    agentcore_session_id = request.headers.get("x-amzn-bedrock-agentcore-runtime-session-id")

    # Extract and decode JWT token from Authorization header (case-insensitive)
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()  # Remove "Bearer " prefix and whitespace
        try:
            # Decode JWT without verification (for extracting sub claim)
            # In production, you should verify the token signature
            decoded = jwt.decode(token, options={"verify_signature": False})
            user_id = decoded.get("sub")
        except jwt.DecodeError:
            # Token decode failed, user_id remains None
            pass
        except Exception:
            # Any other error, user_id remains None
            pass

    return agentcore_session_id, user_id


@router.post("/invocations")
async def invocations(http_request: Request, request: dict[str, Any]):
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
    # Parse agentcore_session_id and user_id from headers
    agentcore_session_id, user_id = parse_session_and_user_from_headers(http_request)

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

    # Log the invocation with session and user info
    log_parts = [f"🔀 Invocation → {method} {resolved_path}"]
    if agentcore_session_id:
        log_parts.append(f"agentcore_session_id={agentcore_session_id}")
    if user_id:
        log_parts.append(f"user_id={user_id}")
    print(" | ".join(log_parts))

    # Route to appropriate endpoint based on path and method
    try:
        if path == "/sessions" and method == "POST":
            # Create session
            req = CreateSessionRequest(**payload)
            return await create_session(req)

        elif path == "/sessions" and method == "GET":
            # List sessions
            cwd = payload.get("cwd") if payload else None
            return await list_sessions(cwd)

        elif path == "/sessions/available" and method == "GET":
            # List available sessions
            cwd = payload.get("cwd") if payload else None
            return await list_available_sessions(cwd)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/status")
            and method == "GET"
        ):
            # Get session status
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            return await get_session_status(session_id)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/messages")
            and method == "POST"
        ):
            # Send message
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
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
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            resp = PermissionResponse(**payload)
            return await respond_to_permission(session_id, resp)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/model")
            and method == "POST"
        ):
            # Set model
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            req = SetModelRequest(**payload)
            return await set_model(session_id, req)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/interrupt")
            and method == "POST"
        ):
            # Interrupt session
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            return await interrupt_session(session_id)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/permission_mode")
            and method == "POST"
        ):
            # Set permission mode
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            req = SetPermissionModeRequest(**payload)
            return await set_permission_mode(session_id, req)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/server_info")
            and method == "GET"
        ):
            # Get server info
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            return await get_server_info(session_id)

        elif (
            path.startswith("/sessions/")
            and path.endswith("/history")
            and method == "GET"
        ):
            # Get session history
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            cwd = payload.get("cwd") if payload else None
            return await get_session_history(session_id, cwd)

        elif path.startswith("/sessions/") and method == "DELETE":
            # Close session
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            return await close_session(session_id)

        elif path == "/files" and method == "GET":
            # List files
            file_path = payload.get("path", ".")
            return await list_files(path=file_path)

        elif path == "/files/info" and method == "GET":
            # Get file info
            file_path = payload.get("path")
            if not file_path:
                raise HTTPException(status_code=400, detail="Missing 'path' in payload")
            return await get_file_info(path=file_path)

        elif path == "/files/save" and method == "POST":
            # Save file
            req = SaveFileRequest(**payload)
            return await save_file(req)

        elif path == "/shell/execute" and method == "POST":
            # Execute shell command (returns streaming response)
            req = ShellExecuteRequest(**payload)
            return await execute_command(req)

        elif path == "/shell/cwd" and method == "GET":
            # Get current working directory
            return await get_current_directory()

        elif path == "/shell/cwd" and method == "POST":
            # Set current working directory
            cwd = payload.get("cwd")
            if not cwd:
                raise HTTPException(status_code=400, detail="Missing 'cwd' in payload")
            return await set_current_directory(cwd)

        elif path == "/terminal/sessions" and method == "POST":
            # Create terminal session
            req = TerminalCreateRequest(**payload)
            return await create_terminal_session(req)

        elif path == "/terminal/sessions" and method == "GET":
            # List terminal sessions
            return await list_terminal_sessions()

        elif (
            path.startswith("/terminal/sessions/")
            and "/output" in path
            and method == "GET"
        ):
            # Get terminal output
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            seq = payload.get("seq", 0) if payload else 0
            return await get_session_output(session_id, seq)

        elif (
            path.startswith("/terminal/sessions/")
            and path.endswith("/input")
            and method == "POST"
        ):
            # Send terminal input
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            req = InputRequest(**payload)
            return await send_input(session_id, req)

        elif (
            path.startswith("/terminal/sessions/")
            and path.endswith("/resize")
            and method == "POST"
        ):
            # Resize terminal
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            req = ResizeRequest(**payload)
            return await resize_session(session_id, req)

        elif (
            path.startswith("/terminal/sessions/")
            and path.endswith("/status")
            and method == "GET"
        ):
            # Get terminal status
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            return await get_terminal_status(session_id)

        elif (
            path.startswith("/terminal/sessions/")
            and not path.endswith("/input")
            and not path.endswith("/resize")
            and not path.endswith("/status")
            and "/output" not in path
            and method == "DELETE"
        ):
            # Close terminal session
            session_id = path_params.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=400, detail="Missing session_id in path_params"
                )
            return await close_terminal_session(session_id)

        elif path == "/health" and method == "GET":
            # Health check - import here to avoid circular dependency
            from ..server import health_check

            return await health_check()

        elif path == "/ping" and method == "GET":
            # Ping endpoint - import here to avoid circular dependency
            from ..server import ping

            return await ping()

        else:
            error_msg = f"Unknown path or method: {method} {path}"
            print(f"❌ Invocation Error (404): {error_msg} | path_params={path_params} | payload_keys={list(payload.keys()) if payload else []}")
            raise HTTPException(
                status_code=404,
                detail=error_msg,
            )

    except HTTPException as e:
        # Log HTTPException details
        if e.status_code == 404:
            print(f"❌ Invocation HTTPException (404): {e.detail}")
        elif e.status_code >= 400:
            print(f"❌ Invocation HTTPException ({e.status_code}): {e.detail}")
        raise
    except Exception as e:
        error_detail = f"Invocation error: {str(e)}"
        print(f"❌ Invocation Exception (500): {error_detail} | path={path} | method={method}")
        raise HTTPException(status_code=500, detail=error_detail)
