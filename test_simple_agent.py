#!/usr/bin/env python3
"""Simple test of the agent without Chainlit."""

import asyncio
import os

# Set environment variables
os.environ["LLM_BASE_URL"] = "https://litellm.data.divar.cloud"
os.environ["LLM_AUTH_TOKEN"] = "sk-Jega_JK10vRmLe3q-qQrzA"
os.environ["DB_PASSWORD"] = ""
os.environ["DB_USER"] = "divar"

from law_agent.agent import LawAgent

async def main():
    print("Creating agent...")
    agent = LawAgent(
        model="grok-4-1-fast-reasoning",
        temperature=1.0,
    )

    print("Agent initialized successfully!")
    print(f"Model: {agent.model}")
    print()

    # Simple test question
    query = "قانون بیمه چیست؟"
    print(f"Question: {query}")
    print()

    print("Calling agent.run()...")
    try:
        response = await agent.run(
            user_query=query,
            conversation_history=None,
            conversation_id="test-session",
        )

        print("=" * 80)
        print("RESPONSE:")
        print("=" * 80)
        print(response)
        print("=" * 80)
        print()
        print("SUCCESS!")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
