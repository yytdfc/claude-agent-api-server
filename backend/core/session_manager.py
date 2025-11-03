"""
Session Manager.

This module contains the SessionManager class which manages multiple
concurrent Claude Agent sessions, handling creation, restoration,
and cleanup operations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException

from ..models import SessionInfo
from .session import AgentSession


class SessionManager:
    """
    Manages multiple concurrent Claude Agent sessions.

    Each session maintains its own SDK client, conversation history,
    and permission state. Supports session creation, restoration,
    and cleanup.
    """

    def __init__(self):
        """Initialize the session manager."""
        self.sessions: dict[str, AgentSession] = {}
        self.session_dir = Path.home() / ".claude" / "projects"

    async def create_session(
        self,
        resume_session_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        background_model: Optional[str] = None,
        enable_proxy: bool = False,
        server_port: int = 8000,
        cwd: Optional[str] = None,
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
            cwd: Working directory for the session

        Returns:
            The session ID (new or resumed)
        """
        session_id = resume_session_id or str(__import__("uuid").uuid4())

        if session_id in self.sessions:
            raise HTTPException(status_code=400, detail="Session already active")

        session = AgentSession(
            session_id,
            system_prompt,
            model,
            background_model,
            enable_proxy,
            server_port,
            cwd,
        )
        await session.connect(resume_session_id)

        self.sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> AgentSession:
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

    def list_sessions(self, cwd: Optional[str] = None) -> list[SessionInfo]:
        """
        List all active sessions, optionally filtered by cwd.

        Args:
            cwd: Optional working directory to filter by

        Returns:
            List of SessionInfo objects
        """
        result = []
        for session_id, session in self.sessions.items():
            # Filter by cwd if provided
            if cwd and session.cwd != cwd:
                continue

            result.append(
                SessionInfo(
                    session_id=session_id,
                    created_at=session.created_at.isoformat(),
                    last_activity=session.last_activity.isoformat(),
                    status=session.status,
                    message_count=session.message_count,
                    cwd=session.cwd,
                )
            )
        return result

    def list_available_sessions(
        self, cwd: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        List all available sessions from disk, optionally filtered by cwd.

        Args:
            cwd: Optional working directory to filter by

        Returns:
            List of session information dictionaries
        """
        sessions = []

        if not self.session_dir.exists():
            return sessions

        # If cwd is provided, only scan that specific project directory
        if cwd:
            path_key = cwd.replace("/", "-").replace("_", "-")
            project_dirs = [self.session_dir / path_key]
        else:
            # Scan all project directories
            project_dirs = list(self.session_dir.iterdir())

        for project_dir in project_dirs:
            if not project_dir.exists() or not project_dir.is_dir():
                continue

            for session_file in project_dir.glob("*.jsonl"):
                try:
                    session_id = session_file.stem

                    # Skip SDK internal sessions (agent-xxxxxxxx format)
                    # These are created by Claude Agent SDK and not user-visible
                    if session_id.startswith("agent-"):
                        continue

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
