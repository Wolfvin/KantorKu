"""
Example 1: Basic Usage — Create an office and run a task.

The simplest way to use kantorku: create an Office, configure providers,
and run a task.

Usage:
    python examples/01_basic_usage.py
"""

import asyncio
from kantorku import Office, Hooks, HookType


async def main():
    # Create office with default settings
    office = Office(conductor_model="ollama/llama3")

    # Configure provider (using Ollama for local/free usage)
    office.configure_provider("ollama", base_url="http://localhost:11434")

    # Hire workers
    office.hire_worker(
        "coder_backend",
        model="ollama/llama3",
        squad="coding",
        role="Backend developer",
    )
    office.hire_worker(
        "intake",
        model="ollama/llama3",
        squad="translation",
        role="Message parser",
    )
    office.hire_worker(
        "narrator",
        model="ollama/llama3",
        squad="translation",
        role="Output formatter",
    )

    # Initialize all systems
    await office.initialize()

    # Run a one-shot task (auto-accepts the contract)
    result = await office.run(
        "Write a Python function to calculate fibonacci numbers with memoization",
        auto_accept=True,
    )

    print("=" * 60)
    print("RESULT:")
    print("=" * 60)
    import json
    print(json.dumps(result, indent=2, default=str))

    # Clean up
    await office.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
