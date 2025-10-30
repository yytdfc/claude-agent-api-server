#!/usr/bin/env python3
"""Test script to understand how SDK resume works."""

import asyncio
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async def test_resume():
    """Test resuming a session."""
    session_id = "24ddf2eb-835f-4833-bb63-9060119bd42c"
    cwd = "/Users/cfu/git/300_autocode/test_claude"

    print(f"Testing resume with:")
    print(f"  session_id: {session_id}")
    print(f"  cwd: {cwd}")

    options = ClaudeAgentOptions(
        resume=session_id,
        cwd=cwd,
        max_turns=0
    )

    try:
        client = ClaudeSDKClient(options=options)
        await client.connect()
        print("✅ Successfully resumed session!")
        await client.disconnect()
    except Exception as e:
        print(f"❌ Failed to resume: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_resume())
