"""API endpoint routers."""

from .files import router as files_router
from .invocations import router as invocations_router
from .messages import router as messages_router
from .oauth import router as oauth_router
from .permissions import router as permissions_router
from .sessions import router as sessions_router
from .shell import router as shell_router
from .terminal import router as terminal_router
from .workspace import router as workspace_router

__all__ = [
    "sessions_router",
    "messages_router",
    "permissions_router",
    "invocations_router",
    "files_router",
    "shell_router",
    "terminal_router",
    "workspace_router",
    "oauth_router",
]
