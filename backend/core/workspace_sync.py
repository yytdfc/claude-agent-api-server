"""
Workspace synchronization utilities for S3.

Provides functions to sync user workspace directories from S3 to local filesystem
using s5cmd for high-performance parallel transfers.
"""

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class WorkspaceSyncError(Exception):
    """Exception raised when workspace sync fails."""
    pass


def check_s5cmd_installed() -> bool:
    """
    Check if s5cmd is installed and available.

    Returns:
        bool: True if s5cmd is installed, False otherwise
    """
    return shutil.which("s5cmd") is not None


async def sync_workspace_from_s3(
    user_id: str,
    bucket_name: str,
    local_base_path: str = "/workspace",
    workspace_name: str = "workspace",
    s3_prefix: str = "user_data",
    dry_run: bool = False,
) -> dict:
    """
    Sync a user's workspace directory from S3 to local filesystem using s5cmd.

    Args:
        user_id: User ID (used as subdirectory under s3_prefix)
        bucket_name: S3 bucket name
        local_base_path: Local base directory for workspaces
        workspace_name: Name of the workspace subdirectory
        s3_prefix: S3 key prefix (default: "user_data")
        dry_run: If True, only simulate the sync without actually transferring files

    Returns:
        dict: Sync result with status, local_path, files_synced, etc.

    Raises:
        WorkspaceSyncError: If sync fails or s5cmd is not installed
    """
    # Check if s5cmd is installed
    if not check_s5cmd_installed():
        raise WorkspaceSyncError(
            "s5cmd is not installed. Please install it: "
            "https://github.com/peak/s5cmd#installation"
        )

    # Build S3 path: s3://bucket/user_data/user_id/workspace/
    s3_path = f"s3://{bucket_name}/{s3_prefix}/{user_id}/{workspace_name}/*"

    # Build local path: /workspace/user_id/
    local_path = Path(local_base_path) / user_id
    local_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Syncing workspace from {s3_path} to {local_path}")

    # Build s5cmd command
    # s5cmd sync downloads files preserving the directory structure
    # --include-etag ensures content integrity checking
    # --no-sign-request can be added if bucket is public
    cmd = [
        "s5cmd",
        "--log", "error",  # Only log errors
        "sync",
    ]

    if dry_run:
        cmd.append("--dry-run")

    cmd.extend([
        s3_path,
        str(local_path) + "/",
    ])

    try:
        # Execute s5cmd
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        # Parse output
        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""

        if process.returncode != 0:
            error_msg = f"s5cmd failed with exit code {process.returncode}: {stderr_text}"
            logger.error(error_msg)
            raise WorkspaceSyncError(error_msg)

        # Count files synced (each line in stdout represents a file operation)
        files_synced = len([line for line in stdout_text.strip().split('\n') if line])

        result = {
            "status": "success",
            "user_id": user_id,
            "s3_path": s3_path,
            "local_path": str(local_path),
            "files_synced": files_synced,
            "dry_run": dry_run,
            "output": stdout_text,
        }

        if dry_run:
            result["message"] = "Dry run completed - no files were actually transferred"
        else:
            result["message"] = f"Successfully synced {files_synced} files from S3"

        logger.info(f"Workspace sync completed: {result['message']}")
        return result

    except asyncio.CancelledError:
        logger.warning("Workspace sync was cancelled")
        raise
    except Exception as e:
        error_msg = f"Failed to sync workspace: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise WorkspaceSyncError(error_msg) from e


async def sync_workspace_to_s3(
    user_id: str,
    bucket_name: str,
    local_base_path: str = "/workspace",
    workspace_name: str = "workspace",
    s3_prefix: str = "user_data",
    dry_run: bool = False,
) -> dict:
    """
    Sync a user's workspace directory from local filesystem to S3 using s5cmd.

    Args:
        user_id: User ID (used as subdirectory under s3_prefix)
        bucket_name: S3 bucket name
        local_base_path: Local base directory for workspaces
        workspace_name: Name of the workspace subdirectory
        s3_prefix: S3 key prefix (default: "user_data")
        dry_run: If True, only simulate the sync without actually transferring files

    Returns:
        dict: Sync result with status, s3_path, files_synced, etc.

    Raises:
        WorkspaceSyncError: If sync fails or s5cmd is not installed
    """
    # Check if s5cmd is installed
    if not check_s5cmd_installed():
        raise WorkspaceSyncError(
            "s5cmd is not installed. Please install it: "
            "https://github.com/peak/s5cmd#installation"
        )

    # Build local path: /workspace/user_id/
    local_path = Path(local_base_path) / user_id

    if not local_path.exists():
        raise WorkspaceSyncError(f"Local workspace does not exist: {local_path}")

    # Build S3 path: s3://bucket/user_data/user_id/workspace/
    s3_path = f"s3://{bucket_name}/{s3_prefix}/{user_id}/{workspace_name}/"

    logger.info(f"Syncing workspace from {local_path} to {s3_path}")

    # Build s5cmd command
    cmd = [
        "s5cmd",
        "--log", "error",
        "sync",
    ]

    if dry_run:
        cmd.append("--dry-run")

    cmd.extend([
        str(local_path) + "/*",
        s3_path,
    ])

    try:
        # Execute s5cmd
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""

        if process.returncode != 0:
            error_msg = f"s5cmd failed with exit code {process.returncode}: {stderr_text}"
            logger.error(error_msg)
            raise WorkspaceSyncError(error_msg)

        # Count files synced
        files_synced = len([line for line in stdout_text.strip().split('\n') if line])

        result = {
            "status": "success",
            "user_id": user_id,
            "local_path": str(local_path),
            "s3_path": s3_path,
            "files_synced": files_synced,
            "dry_run": dry_run,
            "output": stdout_text,
        }

        if dry_run:
            result["message"] = "Dry run completed - no files were actually transferred"
        else:
            result["message"] = f"Successfully synced {files_synced} files to S3"

        logger.info(f"Workspace sync completed: {result['message']}")
        return result

    except asyncio.CancelledError:
        logger.warning("Workspace sync was cancelled")
        raise
    except Exception as e:
        error_msg = f"Failed to sync workspace: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise WorkspaceSyncError(error_msg) from e


async def clone_git_repository(
    user_id: str,
    git_url: str,
    local_base_path: str = "/workspace",
    branch: Optional[str] = None,
    repo_name: Optional[str] = None,
    shallow: bool = False,
) -> dict:
    """
    Clone a Git repository into a user's workspace.

    Args:
        user_id: User ID
        git_url: Git repository URL (https or ssh)
        local_base_path: Local base directory for workspaces
        branch: Specific branch to clone (default: repository default branch)
        repo_name: Custom name for the cloned repository (default: extract from URL)
        shallow: If True, perform shallow clone (--depth=1) for faster cloning

    Returns:
        dict: Clone result with status, local_path, repo info

    Raises:
        WorkspaceSyncError: If clone fails or git is not installed
    """
    # Check if git is installed
    if not shutil.which("git"):
        raise WorkspaceSyncError(
            "git is not installed. Please install git: "
            "https://git-scm.com/downloads"
        )

    # Build local path: /workspace/user_id/
    workspace_path = Path(local_base_path) / user_id
    workspace_path.mkdir(parents=True, exist_ok=True)

    # Extract repository name from URL if not provided
    if not repo_name:
        # Extract from URL: https://github.com/user/repo.git -> repo
        repo_name = git_url.rstrip('/').split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]

    # Full path for the cloned repository
    repo_path = workspace_path / repo_name

    # Check if repository already exists
    if repo_path.exists():
        raise WorkspaceSyncError(
            f"Repository directory already exists: {repo_path}. "
            f"Please remove it first or use a different repo_name."
        )

    logger.info(f"Cloning repository {git_url} to {repo_path}")

    # Build git clone command
    cmd = ["git", "clone"]

    if shallow:
        cmd.extend(["--depth", "1"])

    if branch:
        cmd.extend(["--branch", branch])

    cmd.extend([git_url, str(repo_path)])

    try:
        # Execute git clone
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""

        if process.returncode != 0:
            error_msg = f"git clone failed with exit code {process.returncode}: {stderr_text}"
            logger.error(error_msg)
            raise WorkspaceSyncError(error_msg)

        # Get repository info
        try:
            # Get current branch
            branch_process = await asyncio.create_subprocess_exec(
                "git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            branch_stdout, _ = await branch_process.communicate()
            current_branch = branch_stdout.decode().strip() if branch_stdout else "unknown"

            # Get commit hash
            commit_process = await asyncio.create_subprocess_exec(
                "git", "-C", str(repo_path), "rev-parse", "HEAD",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            commit_stdout, _ = await commit_process.communicate()
            commit_hash = commit_stdout.decode().strip() if commit_stdout else "unknown"

            # Get repository size
            repo_size = sum(f.stat().st_size for f in repo_path.rglob("*") if f.is_file())

        except Exception as e:
            logger.warning(f"Failed to get repository info: {e}")
            current_branch = "unknown"
            commit_hash = "unknown"
            repo_size = 0

        result = {
            "status": "success",
            "user_id": user_id,
            "git_url": git_url,
            "local_path": str(repo_path),
            "workspace_path": str(workspace_path),
            "repo_name": repo_name,
            "branch": current_branch,
            "commit_hash": commit_hash,
            "shallow": shallow,
            "size_bytes": repo_size,
            "size_mb": round(repo_size / (1024 * 1024), 2),
            "message": f"Successfully cloned repository to {repo_path}",
            "output": stdout_text + stderr_text,
        }

        logger.info(f"Repository cloned successfully: {result['message']}")
        return result

    except asyncio.CancelledError:
        logger.warning("Git clone was cancelled")
        # Cleanup partially cloned repository
        if repo_path.exists():
            try:
                shutil.rmtree(repo_path)
            except Exception as e:
                logger.error(f"Failed to cleanup repository: {e}")
        raise
    except Exception as e:
        error_msg = f"Failed to clone repository: {str(e)}"
        logger.error(error_msg, exc_info=True)
        # Cleanup on error
        if repo_path.exists():
            try:
                shutil.rmtree(repo_path)
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup repository: {cleanup_error}")
        raise WorkspaceSyncError(error_msg) from e


def get_workspace_info(user_id: str, local_base_path: str = "/workspace") -> dict:
    """
    Get information about a user's local workspace.

    Args:
        user_id: User ID
        local_base_path: Local base directory for workspaces

    Returns:
        dict: Workspace information including path, size, file count
    """
    local_path = Path(local_base_path) / user_id

    if not local_path.exists():
        return {
            "exists": False,
            "path": str(local_path),
            "message": "Workspace does not exist locally",
        }

    # Calculate workspace size and file count
    total_size = 0
    file_count = 0
    dir_count = 0

    try:
        for item in local_path.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size
                file_count += 1
            elif item.is_dir():
                dir_count += 1
    except Exception as e:
        logger.error(f"Error calculating workspace info: {e}")

    return {
        "exists": True,
        "path": str(local_path),
        "size_bytes": total_size,
        "size_mb": round(total_size / (1024 * 1024), 2),
        "file_count": file_count,
        "dir_count": dir_count,
    }


async def check_s3_directory_exists(
    bucket_name: str,
    s3_prefix: str,
) -> bool:
    """
    Check if a directory exists in S3.

    Args:
        bucket_name: S3 bucket name
        s3_prefix: S3 key prefix to check

    Returns:
        bool: True if directory exists and has objects, False otherwise
    """
    if not check_s5cmd_installed():
        logger.warning("s5cmd not installed, cannot check S3 directory")
        return False

    s3_path = f"s3://{bucket_name}/{s3_prefix}/"

    try:
        # Use s5cmd ls to check if directory has any objects
        process = await asyncio.create_subprocess_exec(
            "s5cmd",
            "--log", "error",
            "ls",
            s3_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode() if stdout else ""

        # If there's any output, directory exists and has objects
        return bool(stdout_text.strip())

    except Exception as e:
        logger.error(f"Failed to check S3 directory: {e}")
        return False


async def sync_claude_dir_from_s3(
    user_id: str,
    bucket_name: str,
    s3_prefix: str = "user_data",
    local_home: Optional[str] = None,
) -> dict:
    """
    Sync .claude directory from S3 to local ~/.claude for a user.

    Args:
        user_id: User ID
        bucket_name: S3 bucket name
        s3_prefix: S3 key prefix (default: "user_data")
        local_home: Local home directory (default: from HOME env var)

    Returns:
        dict: Sync result with status, local_path, files_synced, etc.

    Raises:
        WorkspaceSyncError: If sync fails
    """
    if not check_s5cmd_installed():
        raise WorkspaceSyncError("s5cmd is not installed")

    # Get home directory
    if local_home is None:
        local_home = os.environ.get("HOME", "/root")

    local_claude_dir = Path(local_home) / ".claude"
    s3_path = f"s3://{bucket_name}/{s3_prefix}/{user_id}/.claude/"

    logger.info(f"🔍 Checking if .claude data exists in S3: {s3_path}")

    # Check if S3 directory exists
    s3_exists = await check_s3_directory_exists(
        bucket_name, f"{s3_prefix}/{user_id}/.claude"
    )

    if not s3_exists:
        logger.info(f"⏭️  No .claude data found in S3 for user {user_id}")
        return {
            "status": "skipped",
            "user_id": user_id,
            "s3_path": s3_path,
            "local_path": str(local_claude_dir),
            "message": "No .claude data found in S3",
            "files_synced": 0,
        }

    # Create .claude directory if it doesn't exist
    local_claude_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"⬇️  Syncing .claude from {s3_path} to {local_claude_dir}")

    # Build s5cmd command
    cmd = [
        "s5cmd",
        "--log", "error",
        "sync",
        s3_path + "*",
        str(local_claude_dir) + "/",
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""

        if process.returncode != 0:
            error_msg = f"s5cmd failed: {stderr_text}"
            logger.error(error_msg)
            raise WorkspaceSyncError(error_msg)

        files_synced = len([line for line in stdout_text.strip().split('\n') if line])

        result = {
            "status": "success",
            "user_id": user_id,
            "s3_path": s3_path,
            "local_path": str(local_claude_dir),
            "files_synced": files_synced,
            "message": f"Successfully synced {files_synced} files from S3",
            "output": stdout_text,
        }

        logger.info(f"✅ .claude sync completed: {files_synced} files from S3")
        return result

    except Exception as e:
        error_msg = f"Failed to sync .claude directory: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        raise WorkspaceSyncError(error_msg) from e


async def list_projects_from_s3(
    user_id: str,
    bucket_name: str,
    s3_prefix: str = "user_data",
) -> list[str]:
    """
    List all projects for a user from S3.

    Args:
        user_id: User ID
        bucket_name: S3 bucket name
        s3_prefix: S3 key prefix (default: "user_data")

    Returns:
        List of project names
    """
    if not check_s5cmd_installed():
        logger.warning("s5cmd not installed, cannot list projects")
        return []

    s3_path = f"s3://{bucket_name}/{s3_prefix}/{user_id}/projects/"

    try:
        # Use s5cmd ls to list directories
        process = await asyncio.create_subprocess_exec(
            "s5cmd",
            "--log", "error",
            "ls",
            s3_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode() if stdout else ""

        if not stdout_text.strip():
            logger.info(f"No projects found in S3 for user {user_id}")
            return []

        # Parse s5cmd ls output to extract directory names
        # Format: "DIR s3://bucket/prefix/user_id/projects/project_name/"
        projects = []
        for line in stdout_text.strip().split('\n'):
            if line.strip() and line.startswith("DIR"):
                # Extract project name from path
                path = line.split()[-1].rstrip('/')
                project_name = path.split('/')[-1]
                if project_name:
                    projects.append(project_name)

        logger.info(f"Found {len(projects)} projects for user {user_id}: {projects}")
        return projects

    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        return []


async def sync_project_from_s3(
    user_id: str,
    project_name: str,
    bucket_name: str,
    s3_prefix: str = "user_data",
    local_base_path: str = "/workspace",
) -> dict:
    """
    Sync a project directory from S3 to local workspace.

    Args:
        user_id: User ID
        project_name: Project name
        bucket_name: S3 bucket name
        s3_prefix: S3 key prefix (default: "user_data")
        local_base_path: Local base directory for workspaces (default: "/workspace")

    Returns:
        dict: Sync result with status, local_path, files_synced, etc.

    Raises:
        WorkspaceSyncError: If sync fails
    """
    if not check_s5cmd_installed():
        raise WorkspaceSyncError("s5cmd is not installed")

    # Build paths
    local_project_path = Path(local_base_path) / user_id / project_name
    s3_path = f"s3://{bucket_name}/{s3_prefix}/{user_id}/projects/{project_name}/"

    logger.info(f"🔍 Checking if project exists in S3: {s3_path}")

    # Check if S3 directory exists
    s3_exists = await check_s3_directory_exists(
        bucket_name, f"{s3_prefix}/{user_id}/projects/{project_name}"
    )

    if not s3_exists:
        logger.info(f"⏭️  No project data found in S3 for {user_id}/{project_name}")
        return {
            "status": "skipped",
            "user_id": user_id,
            "project_name": project_name,
            "s3_path": s3_path,
            "local_path": str(local_project_path),
            "message": "No project data found in S3",
            "files_synced": 0,
        }

    # Create project directory if it doesn't exist
    local_project_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"⬇️  Syncing project from {s3_path} to {local_project_path}")

    # Build s5cmd command
    cmd = [
        "s5cmd",
        "--log", "error",
        "sync",
        s3_path + "*",
        str(local_project_path) + "/",
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""

        if process.returncode != 0:
            error_msg = f"s5cmd failed: {stderr_text}"
            logger.error(error_msg)
            raise WorkspaceSyncError(error_msg)

        files_synced = len([line for line in stdout_text.strip().split('\n') if line])

        result = {
            "status": "success",
            "user_id": user_id,
            "project_name": project_name,
            "s3_path": s3_path,
            "local_path": str(local_project_path),
            "files_synced": files_synced,
            "message": f"Successfully synced {files_synced} files from S3",
            "output": stdout_text,
        }

        logger.info(f"✅ Project sync completed: {files_synced} files from S3")
        return result

    except Exception as e:
        error_msg = f"Failed to sync project: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        raise WorkspaceSyncError(error_msg) from e


async def backup_project_to_s3(
    user_id: str,
    project_name: str,
    bucket_name: str,
    s3_prefix: str = "user_data",
    local_base_path: str = "/workspace",
) -> dict:
    """
    Backup a project directory from local workspace to S3.

    Args:
        user_id: User ID
        project_name: Project name
        bucket_name: S3 bucket name
        s3_prefix: S3 key prefix (default: "user_data")
        local_base_path: Local base directory for workspaces (default: "/workspace")

    Returns:
        dict: Backup result with status, s3_path, files_synced, etc.

    Raises:
        WorkspaceSyncError: If backup fails
    """
    if not check_s5cmd_installed():
        raise WorkspaceSyncError("s5cmd is not installed")

    # Build paths
    local_project_path = Path(local_base_path) / user_id / project_name

    if not local_project_path.exists():
        logger.debug(f"⏭️  No local project directory: {local_project_path}")
        return {
            "status": "skipped",
            "user_id": user_id,
            "project_name": project_name,
            "local_path": str(local_project_path),
            "message": "No local project directory to backup",
            "files_synced": 0,
        }

    s3_path = f"s3://{bucket_name}/{s3_prefix}/{user_id}/projects/{project_name}/"

    logger.info(f"⬆️  Backing up project from {local_project_path} to {s3_path}")

    # Build s5cmd command
    cmd = [
        "s5cmd",
        "--log", "error",
        "sync",
        str(local_project_path) + "/*",
        s3_path,
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""

        if process.returncode != 0:
            error_msg = f"s5cmd failed: {stderr_text}"
            logger.error(error_msg)
            raise WorkspaceSyncError(error_msg)

        files_synced = len([line for line in stdout_text.strip().split('\n') if line])

        result = {
            "status": "success",
            "user_id": user_id,
            "project_name": project_name,
            "local_path": str(local_project_path),
            "s3_path": s3_path,
            "files_synced": files_synced,
            "message": f"Successfully backed up {files_synced} files to S3",
            "output": stdout_text,
        }

        logger.info(f"✅ Project backup completed: {files_synced} files to S3")
        return result

    except Exception as e:
        error_msg = f"Failed to backup project: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        raise WorkspaceSyncError(error_msg) from e


async def backup_claude_dir_to_s3(
    user_id: str,
    bucket_name: str,
    s3_prefix: str = "user_data",
    local_home: Optional[str] = None,
) -> dict:
    """
    Backup .claude directory from local ~/.claude to S3.

    Args:
        user_id: User ID
        bucket_name: S3 bucket name
        s3_prefix: S3 key prefix (default: "user_data")
        local_home: Local home directory (default: from HOME env var)

    Returns:
        dict: Backup result with status, s3_path, files_synced, etc.

    Raises:
        WorkspaceSyncError: If backup fails
    """
    if not check_s5cmd_installed():
        raise WorkspaceSyncError("s5cmd is not installed")

    # Get home directory
    if local_home is None:
        local_home = os.environ.get("HOME", "/root")

    local_claude_dir = Path(local_home) / ".claude"

    if not local_claude_dir.exists():
        logger.debug(f"⏭️  No .claude directory found for user {user_id}")
        return {
            "status": "skipped",
            "user_id": user_id,
            "local_path": str(local_claude_dir),
            "message": "No .claude directory to backup",
            "files_synced": 0,
        }

    s3_path = f"s3://{bucket_name}/{s3_prefix}/{user_id}/.claude/"

    logger.info(f"⬆️  Backing up .claude from {local_claude_dir} to {s3_path}")

    # Build s5cmd command
    cmd = [
        "s5cmd",
        "--log", "error",
        "sync",
        str(local_claude_dir) + "/*",
        s3_path,
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""

        if process.returncode != 0:
            error_msg = f"s5cmd failed: {stderr_text}"
            logger.error(error_msg)
            raise WorkspaceSyncError(error_msg)

        files_synced = len([line for line in stdout_text.strip().split('\n') if line])

        result = {
            "status": "success",
            "user_id": user_id,
            "local_path": str(local_claude_dir),
            "s3_path": s3_path,
            "files_synced": files_synced,
            "message": f"Successfully backed up {files_synced} files to S3",
            "output": stdout_text,
        }

        logger.info(f"✅ .claude backup completed: {files_synced} files to S3")
        return result

    except Exception as e:
        error_msg = f"Failed to backup .claude directory: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        raise WorkspaceSyncError(error_msg) from e
