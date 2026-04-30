"""
Example 3: Hooks and Streaming — Monitor and customize the orchestration.

Shows how to use the hook system for monitoring, logging, and
custom behavior injection at key lifecycle points.

Usage:
    python examples/03_hooks_and_streaming.py
"""

import asyncio
import time
from kantorku import Office, Hooks, HookType


async def main():
    # Create hooks for monitoring
    hooks = Hooks()
    start_times: dict[str, float] = {}

    @hooks.on(HookType.ON_CONTRACT_ACCEPTED)
    async def on_contract_accepted(event):
        print(f"\n{'='*50}")
        print(f"CONTRACT ACCEPTED — Session: {event.get('session_id', '?')}")
        contract = event.get("contract", {})
        print(f"  Title: {contract.get('title', 'N/A')}")
        print(f"  Todos: {len(contract.get('todos', []))}")
        print(f"{'='*50}\n")

    @hooks.on(HookType.ON_TASK_STARTED)
    async def on_task_started(event):
        task_id = event.get("task_id", "?")
        start_times[task_id] = time.time()
        print(f"  [START] {task_id}")

    @hooks.on(HookType.ON_TASK_COMPLETED)
    async def on_task_completed(event):
        task_id = event.get("task_id", "?")
        duration = time.time() - start_times.get(task_id, time.time())
        worker = event.get("worker_id", "?")
        print(f"  [DONE]  {task_id} by {worker} ({duration:.2f}s)")

    @hooks.on(HookType.ON_TASK_FAILED)
    async def on_task_failed(event):
        task_id = event.get("task_id", "?")
        error = event.get("error", "Unknown")
        print(f"  [FAIL]  {task_id}: {error}")

    @hooks.on(HookType.ON_WORK_DONE)
    async def on_work_done(event):
        print(f"\nAll work completed for session: {event.get('session_id', '?')}")

    # Create office with hooks
    office = Office(conductor_model="ollama/llama3", hooks=hooks)
    office.configure_provider("ollama", base_url="http://localhost:11434")

    office.hire_worker("coder_backend", model="ollama/llama3", squad="coding", role="Backend")
    office.hire_worker("intake", model="ollama/llama3", squad="translation", role="Parser")
    office.hire_worker("narrator", model="ollama/llama3", squad="translation", role="Formatter")

    await office.initialize()

    result = await office.run(
        "Create a simple REST API endpoint in FastAPI that returns the current time",
        auto_accept=True,
    )

    print("\n--- Hook Debug ---")
    print(f"Registered hooks: {hooks.list_hooks()}")

    await office.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
