#!/usr/bin/env python3
"""
Stop AgentCore Runtime Session

Terminates an active AgentCore runtime session using the stopRuntimeSession API.
Uses the same environment variables as other client tools for consistency.

Usage:
    python stop_agentcore_session.py [--session-id SESSION_ID]

Environment Variables (same as pty_client.py):
    TOKEN              - JWT Bearer token for authentication (required)
    SESSION_ID         - Session ID to stop (optional, auto-generated from TOKEN if not set)
    AGENTCORE_URL      - Base AgentCore URL WITHOUT /invocations (optional, highest priority)
    AGENT_ARN          - Agent ARN (optional, used if AGENTCORE_URL not set)
    AWS_REGION         - AWS region (optional, defaults to us-west-2, used with AGENT_ARN)

URL Priority (same as pty_client.py):
    1. AGENTCORE_URL (if set) - highest priority
    2. AGENT_ARN (constructs URL using AWS_REGION)
    3. Error if neither is set

Examples:
    # Using AGENTCORE_URL (recommended)
    export TOKEN="your-jwt-token"
    export AGENTCORE_URL="https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/arn%3Aaws%3A..."
    export SESSION_ID="user-123@workspace"
    python stop_agentcore_session.py

    # Using AGENT_ARN (auto-constructs URL)
    export TOKEN="your-jwt-token"
    export AGENT_ARN="arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/my-agent"
    export AWS_REGION="us-west-2"
    python stop_agentcore_session.py

    # Auto-generate SESSION_ID from TOKEN
    export TOKEN="your-jwt-token"
    export AGENTCORE_URL="https://..."
    python stop_agentcore_session.py  # Extracts user_id from TOKEN

    # Override SESSION_ID via command line
    export TOKEN="your-jwt-token"
    export AGENTCORE_URL="https://..."
    python stop_agentcore_session.py --session-id user-123@workspace/my-project
"""

import argparse
import os
import sys
import urllib.parse

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: uv add requests")
    sys.exit(1)


def stop_agentcore_session(
    base_url: str,
    session_id: str,
    bearer_token: str,
    qualifier: str = "DEFAULT"
):
    """
    Stop an AgentCore runtime session.

    Args:
        base_url: Base AgentCore URL (e.g., https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/arn%3A...)
        session_id: Session ID to stop
        bearer_token: JWT Bearer token for authentication
        qualifier: Session qualifier (default: DEFAULT)

    Returns:
        Response JSON if successful

    Raises:
        requests.exceptions.RequestException: If request fails
    """
    # Construct the stopRuntimeSession endpoint
    url = f"{base_url}/stopruntimesession"
    if qualifier:
        url += f"?qualifier={qualifier}"

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id
    }

    print("=" * 80)
    print("🛑 Stopping AgentCore Runtime Session")
    print("=" * 80)
    print(f"Base URL: {base_url}")
    print(f"Session ID: {session_id}")
    print(f"Qualifier: {qualifier}")
    print(f"Endpoint: {url}")
    print()

    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()

        print(f"✅ Session {session_id} stopped successfully")
        print()

        # Display response if any
        try:
            result = response.json()
            print("Response:")
            import json
            print(json.dumps(result, indent=2))
            return result
        except:
            print("Response: (no JSON body)")
            return None

    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e.response.status_code}")
        print()

        if e.response.status_code == 404:
            print("Session not found or already terminated")
            print("This may be normal if the session was already closed.")
        elif e.response.status_code == 403:
            print("Insufficient permissions or invalid token")
            print("Check that your TOKEN is valid and has the correct permissions.")
        elif e.response.status_code == 401:
            print("Authentication failed")
            print("Check that your TOKEN is valid and not expired.")
        else:
            print(f"Unexpected error: {e.response.text}")

        raise

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Stop AgentCore Runtime Session",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--session-id",
        help="Session ID to stop (overrides SESSION_ID env var)"
    )
    parser.add_argument(
        "--qualifier",
        default="DEFAULT",
        help="Session qualifier (default: DEFAULT)"
    )

    args = parser.parse_args()

    # Get environment variables
    bearer_token = os.getenv("TOKEN")
    if not bearer_token:
        print("❌ Error: TOKEN environment variable not set")
        print("   Please set it with: export TOKEN='your-jwt-token'")
        sys.exit(1)

    # Determine base URL with priority: AGENTCORE_URL > AGENT_ARN (same as pty_client.py)
    base_url = None
    if os.getenv("AGENTCORE_URL"):
        base_url = os.getenv("AGENTCORE_URL")
        print(f"✅ Using AGENTCORE_URL: {base_url}")
    elif os.getenv("AGENT_ARN"):
        agent_arn = os.getenv("AGENT_ARN")
        region = os.getenv("AWS_REGION", "us-west-2")
        encoded_arn = urllib.parse.quote(agent_arn, safe='')
        base_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}"
        print(f"✅ Constructed URL from AGENT_ARN")
        print(f"   Region: {region}")
        print(f"   Agent ARN: {agent_arn}")
    else:
        print("❌ Error: Either AGENTCORE_URL or AGENT_ARN environment variable is required")
        print("   Set one of:")
        print("     export AGENTCORE_URL='https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/...'")
        print("     export AGENT_ARN='arn:aws:bedrock-agentcore:...'")
        sys.exit(1)

    print()

    # Get session ID from command line or environment
    session_id = args.session_id or os.getenv("SESSION_ID")

    # If still no session_id, try to extract user_id from JWT and construct it
    if not session_id:
        print("⚠️  SESSION_ID not provided, attempting to extract from TOKEN...")
        try:
            import jwt as pyjwt
            decoded = pyjwt.decode(bearer_token, options={"verify_signature": False})
            user_id = decoded.get("sub")
            if user_id:
                session_id = f"{user_id}@workspace"
                print(f"✅ Auto-generated session_id: {session_id}")
            else:
                print("❌ Error: Could not extract user_id from TOKEN")
                sys.exit(1)
        except ImportError:
            print("❌ Error: PyJWT library not found. Install with: uv add pyjwt")
            print("   Or provide SESSION_ID explicitly")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error: Failed to decode TOKEN: {e}")
            sys.exit(1)

    try:
        stop_agentcore_session(
            base_url=base_url,
            session_id=session_id,
            bearer_token=bearer_token,
            qualifier=args.qualifier
        )
        print()
        print("=" * 80)
        print("🏁 Session stop completed")
        print("=" * 80)

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ Failed to stop session")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
