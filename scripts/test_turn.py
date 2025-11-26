#!/usr/bin/env python3
"""
Test Turn Execution Script
Usage: python scripts/test_turn.py [session_id]

Tries to initialize the TurnOrchestrator and execute a turn.
"""
import asyncio
import os
import sys

# Add app directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.session_manager import get_session_manager
from app.services.turn_orchestrator import get_turn_orchestrator


async def main():
    print("Initializing services...")
    try:
        session_manager = get_session_manager()
        _orchestrator = get_turn_orchestrator(session_manager)
        print("Services initialized.")

        # We can't easily run a full turn without a valid session and credentials,
        # but we can check if the orchestrator initializes correctly.

        from app.services.turn_orchestrator import get_singleton_runner

        print("Initializing singleton runner...")
        _runner = get_singleton_runner()
        print("Singleton runner initialized.")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
