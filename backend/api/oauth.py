"""
OAuth token management using Bedrock AgentCore Identity.

Provides endpoints to get OAuth2 tokens for external providers like GitHub.
"""

import asyncio
import logging
import os
import shutil
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter()


async def initialize_gh_auth(access_token: str) -> dict:
    """
    Initialize GitHub CLI authentication with access token.

    Uses 'gh auth login --with-token' to set up authentication.

    Args:
        access_token: GitHub OAuth access token

    Returns:
        dict: Result with status and message

    Raises:
        Exception: If gh command fails
    """
    # Check if gh is installed
    if not shutil.which("gh"):
        logger.warning("gh CLI is not installed, skipping authentication setup")
        return {
            "status": "skipped",
            "message": "gh CLI not installed"
        }

    logger.info("Initializing GitHub CLI authentication with access token")

    try:
        # Use gh auth login --with-token
        # Pass token via stdin for security
        process = await asyncio.create_subprocess_exec(
            "gh", "auth", "login", "--with-token",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Send token to stdin and close
        stdout, stderr = await process.communicate(input=access_token.encode())

        if process.returncode == 0:
            logger.info("Successfully initialized GitHub CLI authentication")
            return {
                "status": "success",
                "message": "GitHub CLI authenticated successfully"
            }
        else:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"Failed to initialize GitHub CLI auth: {error_msg}")
            return {
                "status": "failed",
                "message": f"gh auth login failed: {error_msg}"
            }

    except Exception as e:
        logger.error(f"Exception during gh auth setup: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to run gh auth login: {str(e)}"
        }


def get_bedrock_agentcore_client():
    """
    Get Bedrock AgentCore client.

    Returns:
        boto3 client for bedrock-agentcore service
    """
    import os
    region = os.environ.get("AWS_DEFAULT_REGION", "us-west-2")
    return boto3.client("bedrock-agentcore", region_name=region)


@router.post("/oauth/github/token")
async def get_github_oauth_token(request: Request):
    """
    Get GitHub OAuth2 token using Bedrock AgentCore Identity.

    Extracts workload identity token from request headers and exchanges it
    for a GitHub OAuth token using AgentCore's identity federation.

    Headers required:
    - x-amzn-bedrock-agentcore-runtime-workload-accesstoken: Workload identity token
    - authorization: Bearer token containing user_id in 'sub' claim

    API Call:
        Uses client.get_resource_oauth2_token() with:
        - workloadIdentityToken: From request header
        - resourceCredentialProviderName: "github-provider"
        - scopes: ["repo", "read:user"]
        - oauth2Flow: "USER_FEDERATION"
        - sessionUri: user_id from JWT
        - forceAuthentication: True

    Returns:
        dict: OAuth token response with:
            - access_token: GitHub OAuth access token (if available)
            - token_type: "Bearer"
            - authorization_url: URL to complete authorization (if IN_PROGRESS)
            - session_uri: Session identifier
            - session_status: "IN_PROGRESS" | "FAILED" | (success if access_token present)
            - gh_auth: GitHub CLI authentication result (if access_token obtained)
                - status: "success" | "skipped" | "failed" | "error"
                - message: Description of the result

    Side Effects:
        If access_token is obtained, automatically runs 'gh auth login --with-token'
        to initialize GitHub CLI authentication for subsequent gh commands.

    Raises:
        HTTPException: If token exchange fails or headers are missing

    Reference:
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agentcore/client/get_resource_oauth2_token.html
    """
    # Extract workload identity token from headers
    workload_token = request.headers.get("x-amzn-bedrock-agentcore-runtime-workload-accesstoken")
    if not workload_token:
        raise HTTPException(
            status_code=400,
            detail="Missing x-amzn-bedrock-agentcore-runtime-workload-accesstoken header"
        )

    # Extract user_id from Authorization header
    user_id = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        try:
            import jwt
            decoded = jwt.decode(token, options={"verify_signature": False})
            user_id = decoded.get("sub")
        except Exception as e:
            logger.warning(f"Failed to decode JWT token: {e}")

    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="Missing or invalid Authorization header (user_id not found in JWT)"
        )

    logger.info(f"Getting GitHub OAuth token for user: {user_id}")

    # Get OAuth callback URL from environment variable
    oauth_callback_url = os.environ.get("OAUTH_CALLBACK_URL")
    if not oauth_callback_url:
        logger.warning("OAUTH_CALLBACK_URL not set, using default: http://localhost:8080/oauth/callback")
        oauth_callback_url = "http://localhost:8080/oauth/callback"

    logger.info(f"Using OAuth callback URL: {oauth_callback_url}")

    try:
        client = get_bedrock_agentcore_client()

        # Call get_resource_oauth2_token with correct parameter names from AWS API
        response = client.get_resource_oauth2_token(
            workloadIdentityToken=workload_token,
            resourceCredentialProviderName="github-provider",
            scopes=["repo", "read:user"],
            oauth2Flow="USER_FEDERATION",
            resourceOauth2ReturnUrl=oauth_callback_url,
            forceAuthentication=False
        )

        # Extract token information from response
        # Response contains: authorizationUrl, accessToken, sessionUri, sessionStatus
        access_token = response.get("accessToken")
        authorization_url = response.get("authorizationUrl")
        session_uri = response.get("sessionUri")
        session_status = response.get("sessionStatus")

        result = {
            "access_token": access_token,
            "token_type": "Bearer",
            "authorization_url": authorization_url,
            "session_uri": session_uri,
            "session_status": session_status
        }

        # Log appropriate message based on session status
        if session_status == "IN_PROGRESS":
            logger.info(f"GitHub OAuth authorization in progress for user {user_id}, URL: {authorization_url}")
        elif session_status == "FAILED":
            logger.warning(f"GitHub OAuth authorization failed for user {user_id}")
        elif access_token:
            logger.info(f"Successfully obtained GitHub OAuth token for user {user_id}")

            # Initialize GitHub CLI authentication with the token
            gh_auth_result = await initialize_gh_auth(access_token)
            result["gh_auth"] = gh_auth_result

            if gh_auth_result["status"] == "success":
                logger.info(f"GitHub CLI authentication initialized for user {user_id}")
            elif gh_auth_result["status"] == "skipped":
                logger.info(f"GitHub CLI not installed, skipping auth setup for user {user_id}")
            else:
                logger.warning(f"GitHub CLI authentication failed for user {user_id}: {gh_auth_result['message']}")

        return result

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"AWS ClientError getting GitHub OAuth token: {error_code} - {error_message}")

        raise HTTPException(
            status_code=500,
            detail=f"Failed to get GitHub OAuth token: {error_code} - {error_message}"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting GitHub OAuth token: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get GitHub OAuth token: {str(e)}"
        )


@router.get("/oauth/github/callback")
async def github_oauth_callback(request: Request, session_id: str):
    """
    GitHub OAuth callback endpoint for 3-legged OAuth (3LO) flow.

    This endpoint is called by GitHub after user authorization. It receives the
    session_id and completes the OAuth flow by calling AgentCore's
    complete_resource_token_auth API.

    Query Parameters:
        session_id (str): Session identifier from OAuth provider redirect

    Headers required:
        - authorization: Bearer token containing user_id in 'sub' claim

    Returns:
        HTMLResponse: Success page indicating OAuth flow completion

    Raises:
        HTTPException: If session_id is missing or completion fails

    Reference:
        Based on amazon-bedrock-agentcore-samples oauth2_callback_server.py
    """
    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="Missing session_id query parameter"
        )

    # Extract user_id from Authorization header
    user_id = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        try:
            import jwt
            decoded = jwt.decode(token, options={"verify_signature": False})
            user_id = decoded.get("sub")
        except Exception as e:
            logger.warning(f"Failed to decode JWT token: {e}")

    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="Missing or invalid Authorization header (user_id not found in JWT)"
        )

    logger.info(f"Processing GitHub OAuth callback for user: {user_id}, session: {session_id}")

    try:
        client = get_bedrock_agentcore_client()

        # Complete the OAuth flow by calling complete_resource_token_auth
        # This associates the OAuth session with the user and retrieves access tokens
        response = client.complete_resource_token_auth(
            sessionUri=session_id,
            userIdentifier={"userToken": token}
        )

        logger.info(f"Successfully completed OAuth flow for user {user_id}, session {session_id}")

        # Return success HTML page
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>OAuth2 Success</title>
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    font-family: Arial, sans-serif;
                    background-color: #f5f5f5;
                }
                .container {
                    text-align: center;
                    padding: 2rem;
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                }
                h1 {
                    color: #28a745;
                    margin: 0 0 1rem 0;
                }
                p {
                    color: #666;
                    margin: 0;
                }
                .close-btn {
                    margin-top: 1.5rem;
                    padding: 0.5rem 1rem;
                    background-color: #007bff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 1rem;
                }
                .close-btn:hover {
                    background-color: #0056b3;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✓ GitHub Authentication Complete</h1>
                <p>You can now close this window and return to the application.</p>
                <button class="close-btn" onclick="window.close()">Close Window</button>
            </div>
        </body>
        </html>
        """

        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content, status_code=200)

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"AWS ClientError completing OAuth flow: {error_code} - {error_message}")

        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete OAuth flow: {error_code} - {error_message}"
        )
    except Exception as e:
        logger.error(f"Unexpected error completing OAuth flow: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete OAuth flow: {str(e)}"
        )
