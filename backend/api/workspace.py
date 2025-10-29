"""
Workspace management endpoints.

Provides API endpoints for initializing and syncing user workspaces with S3.
"""

import logging
import os

from fastapi import APIRouter, HTTPException

from ..core.workspace_sync import (
    WorkspaceSyncError,
    clone_git_repository,
    get_workspace_info,
    sync_workspace_from_s3,
    sync_workspace_to_s3,
)
from ..models.schemas import (
    CloneGitRepositoryRequest,
    CloneGitRepositoryResponse,
    InitWorkspaceRequest,
    InitWorkspaceResponse,
    SyncWorkspaceToS3Request,
    SyncWorkspaceToS3Response,
    WorkspaceInfoResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Get S3 bucket from environment
S3_BUCKET = os.getenv("S3_WORKSPACE_BUCKET")
S3_PREFIX = os.getenv("S3_WORKSPACE_PREFIX", "user_data")
LOCAL_BASE_PATH = os.getenv("WORKSPACE_BASE_PATH", "/workspace")


@router.post("/workspace/init", response_model=InitWorkspaceResponse)
async def init_workspace(request: InitWorkspaceRequest):
    """
    Initialize a user's workspace by syncing from S3.

    Downloads the user's workspace directory from S3 to local filesystem
    using s5cmd for high-performance parallel transfers.

    Environment Variables:
    - S3_WORKSPACE_BUCKET: S3 bucket name (required)
    - S3_WORKSPACE_PREFIX: S3 key prefix (default: "user_data")
    - WORKSPACE_BASE_PATH: Local base directory (default: "/workspace")

    S3 Path Format: s3://{bucket}/{prefix}/{user_id}/{workspace_name}/
    Local Path Format: {base_path}/{user_id}/

    Args:
        request: InitWorkspaceRequest containing user_id, workspace_name, dry_run

    Returns:
        InitWorkspaceResponse with sync status and details

    Raises:
        HTTPException: If S3 bucket not configured or sync fails
    """
    if not S3_BUCKET:
        raise HTTPException(
            status_code=500,
            detail="S3_WORKSPACE_BUCKET environment variable not configured"
        )

    logger.info(f"Initializing workspace for user: {request.user_id}")

    try:
        result = await sync_workspace_from_s3(
            user_id=request.user_id,
            bucket_name=S3_BUCKET,
            local_base_path=LOCAL_BASE_PATH,
            workspace_name=request.workspace_name,
            s3_prefix=S3_PREFIX,
            dry_run=request.dry_run,
        )

        return InitWorkspaceResponse(**result)

    except WorkspaceSyncError as e:
        logger.error(f"Workspace init failed for user {request.user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during workspace init: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Workspace initialization failed: {str(e)}")


@router.post("/workspace/sync-to-s3", response_model=SyncWorkspaceToS3Response)
async def sync_to_s3(request: SyncWorkspaceToS3Request):
    """
    Sync a user's local workspace back to S3.

    Uploads the user's local workspace directory to S3 using s5cmd
    for high-performance parallel transfers.

    Environment Variables:
    - S3_WORKSPACE_BUCKET: S3 bucket name (required)
    - S3_WORKSPACE_PREFIX: S3 key prefix (default: "user_data")
    - WORKSPACE_BASE_PATH: Local base directory (default: "/workspace")

    Args:
        request: SyncWorkspaceToS3Request containing user_id, workspace_name, dry_run

    Returns:
        SyncWorkspaceToS3Response with sync status and details

    Raises:
        HTTPException: If S3 bucket not configured or sync fails
    """
    if not S3_BUCKET:
        raise HTTPException(
            status_code=500,
            detail="S3_WORKSPACE_BUCKET environment variable not configured"
        )

    logger.info(f"Syncing workspace to S3 for user: {request.user_id}")

    try:
        result = await sync_workspace_to_s3(
            user_id=request.user_id,
            bucket_name=S3_BUCKET,
            local_base_path=LOCAL_BASE_PATH,
            workspace_name=request.workspace_name,
            s3_prefix=S3_PREFIX,
            dry_run=request.dry_run,
        )

        return SyncWorkspaceToS3Response(**result)

    except WorkspaceSyncError as e:
        logger.error(f"Workspace sync to S3 failed for user {request.user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during workspace sync: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Workspace sync failed: {str(e)}")


@router.get("/workspace/info/{user_id}", response_model=WorkspaceInfoResponse)
async def workspace_info(user_id: str):
    """
    Get information about a user's local workspace.

    Returns details about the workspace including path, size, and file count.

    Environment Variables:
    - WORKSPACE_BASE_PATH: Local base directory (default: "/workspace")

    Args:
        user_id: User ID

    Returns:
        WorkspaceInfoResponse with workspace details
    """
    logger.info(f"Getting workspace info for user: {user_id}")

    try:
        info = get_workspace_info(user_id, LOCAL_BASE_PATH)
        return WorkspaceInfoResponse(**info)

    except Exception as e:
        logger.error(f"Error getting workspace info: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get workspace info: {str(e)}")


@router.post("/workspace/clone-git", response_model=CloneGitRepositoryResponse)
async def clone_git(request: CloneGitRepositoryRequest):
    """
    Clone a Git repository into a user's workspace.

    Downloads a Git repository to the user's workspace directory.
    Supports both HTTPS and SSH URLs, branch selection, and shallow cloning.

    Environment Variables:
    - WORKSPACE_BASE_PATH: Local base directory (default: "/workspace")

    Repository Path: {base_path}/{user_id}/{repo_name}/

    Args:
        request: CloneGitRepositoryRequest containing user_id, git_url, and options

    Returns:
        CloneGitRepositoryResponse with clone status and repository details

    Raises:
        HTTPException: If git is not installed or clone fails
    """
    logger.info(f"Cloning repository {request.git_url} for user: {request.user_id}")

    try:
        result = await clone_git_repository(
            user_id=request.user_id,
            git_url=request.git_url,
            local_base_path=LOCAL_BASE_PATH,
            branch=request.branch,
            repo_name=request.repo_name,
            shallow=request.shallow,
        )

        return CloneGitRepositoryResponse(**result)

    except WorkspaceSyncError as e:
        logger.error(f"Git clone failed for user {request.user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during git clone: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Git clone failed: {str(e)}")
