"""
Unified Invocation Endpoint.

Provides a single entry point for all API operations, routing requests
based on the path and payload parameters.
"""

from typing import Any

from fastapi import APIRouter, HTTPException

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
from .sessions import (
    close_session,
    create_session,
    get_server_info,
    get_session_history,
    list_available_sessions,
    list_sessions,
)

router = APIRouter()


@router.post("/invocations")
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

        elif path == "/health" and method == "GET":
            # Health check - import here to avoid circular dependency
            from ..server import health_check

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
