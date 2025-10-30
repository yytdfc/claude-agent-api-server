#!/usr/bin/env python3
"""
Temporary test script for GitHub OAuth authentication.

Tests the /oauth/github/token endpoint by simulating a web client request.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx


async def test_github_oauth():
    """Test GitHub OAuth token endpoint."""

    # Configuration - use same environment variables as pty_client.py
    # AGENTCORE_URL can be used instead of SERVER_URL for consistency
    server_url = os.getenv("AGENTCORE_URL") or os.getenv("SERVER_URL", "http://127.0.0.1:8000")

    # Get environment variables (TOKEN is required, others are optional)
    jwt_token = os.getenv("TOKEN")
    if not jwt_token:
        print("❌ Error: TOKEN environment variable not set")
        print("   Please set it with: export TOKEN='your-jwt-token'")
        return

    workload_token = os.getenv("WORKLOAD_IDENTITY_TOKEN")
    session_id = os.getenv("SESSION_ID")

    # Extract user_id from JWT token (optional, just for display)
    user_id = "unknown"
    try:
        import jwt as pyjwt
        decoded = pyjwt.decode(jwt_token, options={"verify_signature": False})
        user_id = decoded.get("sub", "unknown")
    except:
        pass

    # Use session_id from env, or construct from user_id
    if not session_id:
        session_id = f"{user_id}@workspace"

    print("=" * 80)
    print("🧪 Testing GitHub OAuth Authentication")
    print("=" * 80)
    print(f"Server URL: {server_url}")
    print(f"User ID: {user_id}")
    print(f"Session ID: {session_id}")
    print(f"JWT Token: {jwt_token[:30]}..." if len(jwt_token) > 30 else jwt_token)
    if workload_token:
        print(f"Workload Token: {workload_token[:20]}..." if len(workload_token) > 20 else workload_token)
    else:
        print("Workload Token: (not set)")
    print()

    # Prepare headers - only add if variables are set
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt_token}",
    }

    # Add optional headers if environment variables are set
    if session_id:
        headers["X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"] = session_id
    if workload_token:
        headers["X-Amzn-Bedrock-AgentCore-Runtime-Workload-AccessToken"] = workload_token

    print("📤 Request Headers:")
    for key, value in headers.items():
        if "token" in key.lower() or key == "Authorization":
            display_value = value[:30] + "..." if len(value) > 30 else value
        else:
            display_value = value
        print(f"   {key}: {display_value}")
    print()

    # Test with invocations endpoint
    print("🔀 Testing via /invocations endpoint...")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Call invocations endpoint
            response = await client.post(
                f"{server_url}/invocations",
                headers=headers,
                json={
                    "path": "/oauth/github/token",
                    "method": "POST"
                }
            )

            print(f"📥 Response Status: {response.status_code}")
            print()

            if response.status_code == 200:
                result = response.json()
                print("✅ Success! Response:")
                print(json.dumps(result, indent=2))
                print()

                # Analyze response
                if result.get("access_token"):
                    print("🎉 Access token obtained!")
                    print(f"   Token (first 20 chars): {result['access_token'][:20]}...")

                    if result.get("gh_auth"):
                        gh_status = result["gh_auth"].get("status")
                        gh_message = result["gh_auth"].get("message")

                        if gh_status == "success":
                            print(f"   ✅ GitHub CLI authenticated: {gh_message}")
                        elif gh_status == "skipped":
                            print(f"   ⚠️  GitHub CLI not installed: {gh_message}")
                        else:
                            print(f"   ❌ GitHub CLI auth failed: {gh_message}")

                elif result.get("authorization_url"):
                    print("🔗 Authorization required!")
                    print(f"   Please open this URL in your browser:")
                    print(f"   {result['authorization_url']}")
                    print()
                    print(f"   Session URI: {result.get('session_uri')}")
                    print(f"   Session Status: {result.get('session_status')}")

                elif result.get("session_status") == "FAILED":
                    print("❌ Authorization failed")
                    print(f"   Session Status: {result.get('session_status')}")

                else:
                    print("⚠️  Unexpected response format")

            else:
                print(f"❌ Request failed with status {response.status_code}")
                try:
                    error = response.json()
                    print("Error details:")
                    print(json.dumps(error, indent=2))
                except:
                    print("Response text:")
                    print(response.text)

        except httpx.TimeoutException:
            print("❌ Request timed out")
        except httpx.ConnectError:
            print(f"❌ Could not connect to server at {server_url}")
            print("   Make sure the server is running")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 80)
    print("🏁 Test completed")
    print("=" * 80)


async def test_direct_endpoint():
    """Test GitHub OAuth token endpoint directly (not through invocations)."""

    # Configuration - use same environment variables as pty_client.py
    server_url = os.getenv("AGENTCORE_URL") or os.getenv("SERVER_URL", "http://127.0.0.1:8000")

    # Get environment variables (TOKEN is required, others are optional)
    jwt_token = os.getenv("TOKEN")
    if not jwt_token:
        print("❌ Error: TOKEN environment variable not set")
        print("   Please set it with: export TOKEN='your-jwt-token'")
        return

    workload_token = os.getenv("WORKLOAD_IDENTITY_TOKEN")
    session_id = os.getenv("SESSION_ID")

    # Extract user_id from JWT token (optional, just for display)
    user_id = "unknown"
    try:
        import jwt as pyjwt
        decoded = pyjwt.decode(jwt_token, options={"verify_signature": False})
        user_id = decoded.get("sub", "unknown")
    except:
        pass

    # Use session_id from env, or construct from user_id
    if not session_id:
        session_id = f"{user_id}@workspace"

    print("=" * 80)
    print("🧪 Testing GitHub OAuth Authentication (Direct Endpoint)")
    print("=" * 80)
    print(f"Server URL: {server_url}")
    print(f"User ID: {user_id}")
    print(f"Session ID: {session_id}")
    if workload_token:
        print(f"Workload Token: {workload_token[:20]}..." if len(workload_token) > 20 else workload_token)
    else:
        print("Workload Token: (not set)")
    print()

    # Prepare headers - only add if variables are set
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt_token}",
    }

    # Add optional headers if environment variables are set
    if workload_token:
        headers["X-Amzn-Bedrock-AgentCore-Runtime-Workload-AccessToken"] = workload_token

    print("📤 Request Headers:")
    for key, value in headers.items():
        if "token" in key.lower() or key == "Authorization":
            display_value = value[:30] + "..." if len(value) > 30 else value
        else:
            display_value = value
        print(f"   {key}: {display_value}")
    print()

    print("🔀 Testing direct /oauth/github/token endpoint...")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{server_url}/oauth/github/token",
                headers=headers
            )

            print(f"📥 Response Status: {response.status_code}")
            print()

            if response.status_code == 200:
                result = response.json()
                print("✅ Success! Response:")
                print(json.dumps(result, indent=2))
            else:
                print(f"❌ Request failed with status {response.status_code}")
                try:
                    error = response.json()
                    print("Error details:")
                    print(json.dumps(error, indent=2))
                except:
                    print("Response text:")
                    print(response.text)

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test GitHub OAuth authentication")
    parser.add_argument(
        "--mode",
        choices=["invocations", "direct", "both"],
        default="invocations",
        help="Test mode: invocations (via /invocations), direct (direct endpoint), or both"
    )
    args = parser.parse_args()

    if args.mode == "invocations":
        asyncio.run(test_github_oauth())
    elif args.mode == "direct":
        asyncio.run(test_direct_endpoint())
    else:  # both
        asyncio.run(test_github_oauth())
        print("\n" * 2)
        asyncio.run(test_direct_endpoint())
