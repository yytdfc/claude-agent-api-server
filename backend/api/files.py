"""
File Browser Endpoints.

Provides REST API endpoints for browsing files and directories.
"""

import os
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


class FileItem(BaseModel):
    """A file or directory item."""
    name: str
    path: str
    is_directory: bool
    size: Optional[int] = None
    modified: Optional[float] = None


class ListFilesResponse(BaseModel):
    """Response for listing files."""
    path: str
    items: List[FileItem]


router = APIRouter()


@router.get("/files", response_model=ListFilesResponse)
async def list_files(path: str = Query(default=".")):
    """
    List files and directories at the given path.

    Args:
        path: Directory path to list (default: current directory)

    Returns:
        List of files and directories
    """
    try:
        # Resolve the path
        target_path = Path(path).expanduser().resolve()

        # Security check: prevent directory traversal attacks
        # Allow any absolute path or relative path
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")

        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

        # List directory contents
        items = []
        try:
            for entry in sorted(target_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                try:
                    stat = entry.stat()
                    items.append(FileItem(
                        name=entry.name,
                        path=str(entry),
                        is_directory=entry.is_dir(),
                        size=stat.st_size if entry.is_file() else None,
                        modified=stat.st_mtime
                    ))
                except (PermissionError, OSError):
                    # Skip files we can't access
                    continue
        except PermissionError:
            raise HTTPException(status_code=403, detail="Permission denied")

        return ListFilesResponse(
            path=str(target_path),
            items=items
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")
