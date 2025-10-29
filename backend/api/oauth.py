"""
OAuth token management using Bedrock AgentCore Identity.

Provides endpoints to get OAuth2 tokens for external providers like GitHub.
"""

import logging
import os
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter()


def get_bedrock_agentcore_client():
    """
    Get Bedrock AgentCore client.

    Returns:
        boto3 client for bedrock-agentcore service
    """
    return boto3.client("bedrock-agentcore")


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

    try:
        client = get_bedrock_agentcore_client()

        # Call get_resource_oauth2_token with correct parameter names from AWS API
        response = client.get_resource_oauth2_token(
            workloadIdentityToken=workload_token,
            resourceCredentialProviderName="github-provider",
            scopes=["repo", "read:user"],
            oauth2Flow="USER_FEDERATION",
            sessionUri=user_id,  # Use user_id as session URI
            forceAuthentication=True
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
