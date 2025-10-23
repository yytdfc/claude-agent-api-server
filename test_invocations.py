#!/usr/bin/env python3
"""
Test script for the unified /invocations endpoint.

Demonstrates how to use the invocations endpoint to access all
API operations through a single entry point.
"""

import asyncio
import httpx


async def test_invocations():
    """Test all operations through the /invocations endpoint."""
    print("\n" + "=" * 60)
    print("Testing /invocations Unified Endpoint")
    print("=" * 60 + "\n")

    base_url = "http://127.0.0.1:8000"
    invocations_url = f"{base_url}/invocations"

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test 1: Health Check
        print("1. Health Check via invocations")
        print("-" * 40)
        response = await client.post(
            invocations_url,
            json={
                "path": "/health",
                "method": "GET",
            },
        )
        print(f"Response: {response.json()}\n")

        # Test 2: Create Session
        print("2. Create Session via invocations")
        print("-" * 40)
        response = await client.post(
            invocations_url,
            json={
                "path": "/sessions",
                "method": "POST",
                "payload": {},
            },
        )
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"Created session: {session_id[:40]}...\n")

        # Test 3: List Active Sessions
        print("3. List Active Sessions via invocations")
        print("-" * 40)
        response = await client.post(
            invocations_url,
            json={
                "path": "/sessions",
                "method": "GET",
            },
        )
        sessions = response.json()
        print(f"Active sessions: {len(sessions['sessions'])}\n")

        # Test 4: Get Session Status
        print("4. Get Session Status via invocations")
        print("-" * 40)
        response = await client.post(
            invocations_url,
            json={
                "path": "/sessions/{session_id}/status",
                "method": "GET",
                "path_params": {"session_id": session_id},
            },
        )
        status = response.json()
        print(f"Session status: {status['status']}\n")

        # Test 5: Send Message
        print("5. Send Message via invocations")
        print("-" * 40)
        response = await client.post(
            invocations_url,
            json={
                "path": "/sessions/{session_id}/messages",
                "method": "POST",
                "path_params": {"session_id": session_id},
                "payload": {"message": "What is 2 + 2?"},
            },
        )
        result = response.json()
        print("Message sent!")
        print("Assistant response:")
        for msg in result["messages"]:
            if msg["type"] == "text":
                print(f"  {msg['content']}")
        print(f"Cost: ${result.get('cost_usd', 0):.6f}\n")

        # Test 6: List Available Sessions
        print("6. List Available Sessions via invocations")
        print("-" * 40)
        response = await client.post(
            invocations_url,
            json={
                "path": "/sessions/available",
                "method": "GET",
            },
        )
        available = response.json()
        print(f"Available sessions from disk: {len(available['sessions'])}\n")

        # Test 7: Close Session
        print("7. Close Session via invocations")
        print("-" * 40)
        response = await client.post(
            invocations_url,
            json={
                "path": "/sessions/{session_id}",
                "method": "DELETE",
                "path_params": {"session_id": session_id},
            },
        )
        result = response.json()
        print(f"Session closed: {result['status']}\n")

    print("=" * 60)
    print("All tests completed successfully!")
    print("=" * 60 + "\n")


async def test_complete_workflow():
    """Test a complete workflow using only invocations endpoint."""
    print("\n" + "=" * 60)
    print("Complete Workflow Test (invocations only)")
    print("=" * 60 + "\n")

    base_url = "http://127.0.0.1:8000"
    invocations_url = f"{base_url}/invocations"

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create session
        response = await client.post(
            invocations_url,
            json={"path": "/sessions", "method": "POST", "payload": {}},
        )
        session_id = response.json()["session_id"]
        print(f"Created session: {session_id[:40]}...\n")

        # Multi-turn conversation
        messages = [
            "My name is Alice",
            "What is my name?",
            "Calculate 15 * 7",
        ]

        for i, msg in enumerate(messages, 1):
            print(f"[Turn {i}] User: {msg}")

            response = await client.post(
                invocations_url,
                json={
                    "path": "/sessions/{session_id}/messages",
                    "method": "POST",
                    "path_params": {"session_id": session_id},
                    "payload": {"message": msg},
                },
            )
            result = response.json()

            for msg_block in result["messages"]:
                if msg_block["type"] == "text":
                    print(f"[Turn {i}] Claude: {msg_block['content']}")

            print()

        # Close session
        await client.post(
            invocations_url,
            json={
                "path": "/sessions/{session_id}",
                "method": "DELETE",
                "path_params": {"session_id": session_id},
            },
        )
        print("Session closed\n")


async def test_error_handling():
    """Test error handling in invocations endpoint."""
    print("\n" + "=" * 60)
    print("Error Handling Tests")
    print("=" * 60 + "\n")

    base_url = "http://127.0.0.1:8000"
    invocations_url = f"{base_url}/invocations"

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test 1: Missing path
        print("1. Missing path parameter")
        print("-" * 40)
        try:
            response = await client.post(invocations_url, json={"method": "GET"})
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}\n")
        except httpx.HTTPStatusError as e:
            print(f"Error (expected): {e}\n")

        # Test 2: Invalid path
        print("2. Invalid path")
        print("-" * 40)
        try:
            response = await client.post(
                invocations_url,
                json={"path": "/invalid/path", "method": "GET"},
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}\n")
        except httpx.HTTPStatusError as e:
            print(f"Error (expected): {e}\n")

        # Test 3: Invalid session ID
        print("3. Invalid session ID")
        print("-" * 40)
        try:
            response = await client.post(
                invocations_url,
                json={
                    "path": "/sessions/{session_id}/status",
                    "method": "GET",
                    "path_params": {"session_id": "invalid-session-id"},
                },
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}\n")
        except httpx.HTTPStatusError as e:
            print(f"Error (expected): {e}\n")


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Invocations Endpoint Test Suite")
    print("=" * 60)
    print("\nMake sure the server is running:")
    print("  python server.py\n")

    try:
        # Check if server is running
        async with httpx.AsyncClient() as client:
            response = await client.get("http://127.0.0.1:8000/health")
            if response.status_code != 200:
                print("❌ Server is not running or not healthy")
                return
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("\nPlease start the server first:")
        print("  python server.py\n")
        return

    # Run tests
    await test_invocations()
    await test_complete_workflow()
    await test_error_handling()

    print("=" * 60)
    print("All test suites completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
