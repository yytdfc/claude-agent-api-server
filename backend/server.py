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

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    files_router,
    invocations_router,
    messages_router,
    permissions_router,
    sessions_router,
    shell_router,
    terminal_router,
    workspace_router,
)
from .core import SessionManager
from .core.pty_manager import PTYManager
from .proxy import router as proxy_router

# ============================================================================
# Global Session Manager
# ============================================================================

session_manager = SessionManager()
pty_manager = PTYManager()


# ============================================================================
# FastAPI Application
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await pty_manager.start()

    # Start gRPC server if enabled
    import os
    grpc_enabled = os.environ.get('ENABLE_GRPC_SERVER', 'false').lower() == 'true'
    grpc_task = None

    if grpc_enabled:
        from .grpc_server.server import start_grpc_server_background
        grpc_port = int(os.environ.get('GRPC_PORT', '50051'))
        grpc_task = start_grpc_server_background(pty_manager, port=grpc_port)

    yield

    # Shutdown - close all sessions
    for session_id in list(session_manager.sessions.keys()):
        await session_manager.close_session(session_id)
    await pty_manager.stop()

    # Stop gRPC server
    if grpc_task:
        grpc_task.cancel()
        try:
            await grpc_task
        except:
            pass


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
# Register Routers
# ============================================================================

# Session management endpoints
app.include_router(sessions_router, tags=["sessions"])

# Message and status endpoints
app.include_router(messages_router, tags=["messages"])

# Permission endpoints
app.include_router(permissions_router, tags=["permissions"])

# File browser endpoints
app.include_router(files_router, tags=["files"])

# Shell terminal endpoints
app.include_router(shell_router, tags=["shell"])

# PTY terminal endpoints
app.include_router(terminal_router, tags=["terminal"])

# Workspace sync endpoints
app.include_router(workspace_router, tags=["workspace"])

# Unified invocations endpoint
app.include_router(invocations_router, tags=["invocations"])

# LiteLLM proxy endpoint
app.include_router(proxy_router, tags=["proxy"])


# ============================================================================
# Health Check
# ============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_sessions": len(session_manager.sessions),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/ping")
async def ping():
    """Ping endpoint for health monitoring."""
    import time
    return {
        "status": "Healthy",
        "time_of_last_update": int(time.time())
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
