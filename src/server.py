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
    invocations_router,
    messages_router,
    permissions_router,
    sessions_router,
)
from .core import SessionManager
from .proxy import router as proxy_router

# ============================================================================
# Global Session Manager
# ============================================================================

session_manager = SessionManager()


# ============================================================================
# FastAPI Application
# ============================================================================


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
# Register Routers
# ============================================================================

# Session management endpoints
app.include_router(sessions_router, tags=["sessions"])

# Message and status endpoints
app.include_router(messages_router, tags=["messages"])

# Permission endpoints
app.include_router(permissions_router, tags=["permissions"])

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


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
