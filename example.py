#!/usr/bin/env python3
"""
Example usage of the Claude Agent API Server

Demonstrates programmatic usage of the API without the interactive client.
Useful for testing, automation, or building custom integrations.
"""

import asyncio
import httpx


async def example_simple_conversation():
    """Simple example: Create session and send a message."""
    print("\n" + "=" * 60)
    print("Example 1: Simple Conversation")
    print("=" * 60 + "\n")

    async with httpx.AsyncClient() as client:
        # Check server health
        response = await client.get("http://127.0.0.1:8000/health")
        print(f"Server health: {response.json()}\n")

        # Create a new session
        response = await client.post("http://127.0.0.1:8000/sessions", json={})
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"Created session: {session_id}\n")

        # Send a message
        response = await client.post(
            f"http://127.0.0.1:8000/sessions/{session_id}/messages",
            json={"message": "What is 2 + 2?"},
        )
        result = response.json()

        print("Assistant response:")
        for msg in result["messages"]:
            if msg["type"] == "text":
                print(f"  {msg['content']}")

        print(f"\nCost: ${result.get('cost_usd', 0):.6f}")

        # Close session
        await client.delete(f"http://127.0.0.1:8000/sessions/{session_id}")
        print(f"\nSession closed\n")


async def example_list_sessions():
    """Example: List active and available sessions."""
    print("\n" + "=" * 60)
    print("Example 2: List Sessions")
    print("=" * 60 + "\n")

    async with httpx.AsyncClient() as client:
        # List active sessions
        response = await client.get("http://127.0.0.1:8000/sessions")
        active = response.json()
        print(f"Active sessions: {len(active['sessions'])}")
        for session in active["sessions"]:
            print(f"  - {session['session_id'][:40]}... ({session['status']})")

        print()

        # List available sessions from disk
        response = await client.get("http://127.0.0.1:8000/sessions/available")
        available = response.json()
        print(f"Available sessions: {len(available['sessions'])}")
        for session in available["sessions"][:5]:  # Show first 5
            print(f"  - {session['session_id'][:40]}...")
            print(f"    Modified: {session['modified']}")
            print(f"    Preview: {session['preview'][:60]}...")

        print()


async def example_resume_session():
    """Example: Resume an existing session."""
    print("\n" + "=" * 60)
    print("Example 3: Resume Session")
    print("=" * 60 + "\n")

    async with httpx.AsyncClient() as client:
        # Get available sessions
        response = await client.get("http://127.0.0.1:8000/sessions/available")
        available = response.json()["sessions"]

        if not available:
            print("No sessions available to resume\n")
            return

        # Resume the most recent session
        session_to_resume = available[0]["session_id"]
        print(f"Resuming session: {session_to_resume[:40]}...\n")

        response = await client.post(
            "http://127.0.0.1:8000/sessions",
            json={"resume_session_id": session_to_resume},
        )
        session_data = response.json()
        session_id = session_data["session_id"]

        print(f"Resumed as: {session_id}\n")

        # Send a follow-up message
        response = await client.post(
            f"http://127.0.0.1:8000/sessions/{session_id}/messages",
            json={"message": "Continue our previous conversation"},
        )
        result = response.json()

        print("Assistant response:")
        for msg in result["messages"]:
            if msg["type"] == "text":
                print(f"  {msg['content']}")

        print()

        # Close session
        await client.delete(f"http://127.0.0.1:8000/sessions/{session_id}")
        print("Session closed\n")


async def example_multi_turn_conversation():
    """Example: Multi-turn conversation in one session."""
    print("\n" + "=" * 60)
    print("Example 4: Multi-turn Conversation")
    print("=" * 60 + "\n")

    async with httpx.AsyncClient() as client:
        # Create session
        response = await client.post("http://127.0.0.1:8000/sessions", json={})
        session_id = response.json()["session_id"]
        print(f"Session: {session_id[:40]}...\n")

        # Multiple messages
        messages = [
            "My name is Alice",
            "What is my name?",
            "What is the capital of France?",
        ]

        for i, msg in enumerate(messages, 1):
            print(f"[Turn {i}] User: {msg}")

            response = await client.post(
                f"http://127.0.0.1:8000/sessions/{session_id}/messages",
                json={"message": msg},
            )
            result = response.json()

            for msg_block in result["messages"]:
                if msg_block["type"] == "text":
                    print(f"[Turn {i}] Claude: {msg_block['content']}")

            print()

        # Close session
        await client.delete(f"http://127.0.0.1:8000/sessions/{session_id}")
        print("Session closed\n")


async def example_permission_handling():
    """Example: Demonstrating permission handling (manual approval needed)."""
    print("\n" + "=" * 60)
    print("Example 5: Permission Handling")
    print("=" * 60 + "\n")
    print("NOTE: This example requires manual approval in another terminal")
    print("      using the interactive client or API calls.\n")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create session
        response = await client.post("http://127.0.0.1:8000/sessions", json={})
        session_id = response.json()["session_id"]
        print(f"Session: {session_id[:40]}...\n")

        # Send message that will require permission
        print("Asking Claude to create a file (requires permission)...")

        # Start the message in background
        async def send_message():
            response = await client.post(
                f"http://127.0.0.1:8000/sessions/{session_id}/messages",
                json={"message": "Create a test.txt file with 'Hello World'"},
            )
            return response.json()

        message_task = asyncio.create_task(send_message())

        # Poll for permission request
        print("Waiting for permission request...")
        pending_permission = None

        for _ in range(10):  # Poll for up to 5 seconds
            await asyncio.sleep(0.5)

            response = await client.get(f"http://127.0.0.1:8000/sessions/{session_id}/status")
            status = response.json()

            if status.get("pending_permission"):
                pending_permission = status["pending_permission"]
                print(f"\nPermission request detected:")
                print(f"  Tool: {pending_permission['tool_name']}")
                print(f"  Request ID: {pending_permission['request_id']}")
                break

        if pending_permission:
            print("\n⚠️  In a real application, you would:")
            print("  1. Show this to the user")
            print("  2. Get their approval")
            print("  3. Send approval via POST to /sessions/{session_id}/permissions/respond")
            print("\nFor this example, we'll auto-approve after 2 seconds...\n")

            await asyncio.sleep(2)

            # Auto-approve (normally user would approve)
            await client.post(
                f"http://127.0.0.1:8000/sessions/{session_id}/permissions/respond",
                json={
                    "request_id": pending_permission["request_id"],
                    "allowed": True,
                    "apply_suggestions": False,
                },
            )
            print("Permission approved!\n")

        # Get result
        result = await message_task
        print("Assistant response:")
        for msg in result["messages"]:
            if msg["type"] == "text":
                print(f"  {msg['content']}")

        # Close session
        await client.delete(f"http://127.0.0.1:8000/sessions/{session_id}")
        print("\nSession closed\n")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Claude Agent API Server - Examples")
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

    # Run examples
    await example_simple_conversation()
    await example_list_sessions()
    # await example_resume_session()  # Uncomment if you have sessions to resume
    await example_multi_turn_conversation()
    # await example_permission_handling()  # Uncomment to test permission flow

    print("=" * 60)
    print("Examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
