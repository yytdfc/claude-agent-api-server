"""
Message and Status Endpoints.

Provides REST API endpoints for sending messages to sessions,
checking session status, and managing session models.
"""


from fastapi import APIRouter

from ..core import SessionManager
from ..models import (
    SendMessageRequest,
    SendMessageResponse,
    SessionStatus,
    SetModelRequest,
    SetPermissionModeRequest,
)

router = APIRouter()


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    from ..server import session_manager

    return session_manager


@router.get("/sessions/{session_id}/status", response_model=SessionStatus)
async def get_session_status(session_id: str):
    """
    Get the status of a session.

    Args:
        session_id: The session ID

    Returns:
        Session status including pending permissions
    """
    manager = get_session_manager()
    session = manager.get_session(session_id)
    return session.get_status()


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(session_id: str, request: SendMessageRequest):
    """
    Send a message in a session.

    Args:
        session_id: The session ID
        request: Message request

    Returns:
        Assistant's response
    """
    manager = get_session_manager()
    session = manager.get_session(session_id)
    return await session.send_message(request.message)


@router.post("/sessions/{session_id}/model")
async def set_model(session_id: str, request: SetModelRequest):
    """
    Change the model for a session.

    Args:
        session_id: The session ID
        request: Model change request

    Returns:
        Success message with new model
    """
    manager = get_session_manager()
    session = manager.get_session(session_id)
    await session.set_model(request.model)
    return {"status": "ok", "model": request.model}


@router.post("/sessions/{session_id}/interrupt")
async def interrupt_session(session_id: str):
    """
    Interrupt the current operation in a session.

    Args:
        session_id: The session ID

    Returns:
        Success message
    """
    manager = get_session_manager()
    session = manager.get_session(session_id)
    await session.interrupt()
    return {"status": "interrupted"}


@router.post("/sessions/{session_id}/permission_mode")
async def set_permission_mode(session_id: str, request: SetPermissionModeRequest):
    """
    Change the permission mode for a session.

    Args:
        session_id: The session ID
        request: Permission mode change request

    Returns:
        Success message with new mode
    """
    manager = get_session_manager()
    session = manager.get_session(session_id)
    await session.set_permission_mode(request.mode)
    return {"status": "ok", "mode": request.mode}
