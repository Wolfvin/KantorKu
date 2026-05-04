"""
Example: Plug-and-Play Custom Workers in kantorku

This example shows all the ways to add custom workers:
1. From a directory (auto-discovers plugin.json + SKILL.md + worker.py)
2. Programmatic (with code)
3. Hot-plug at runtime
4. CLI command
"""

import asyncio
from pathlib import Path
from kantorku import Office, BaseWorker, Task, TaskResult, Hooks, HookType


# ─────────────────────────────────────────────────
#  Method 1: From a directory (plug-and-play)
# ─────────────────────────────────────────────────

async def example_from_directory():
    """Add a worker by pointing to its directory."""
    office = Office()
    office.configure_provider("ollama", base_url="http://localhost:11434")

    # Hire a worker from a directory — auto-discovers everything
    office.hire_worker(
        "translator",
        path="examples/custom_worker/translator/",
    )

    await office.initialize()
    print(f"Workers: {office.get_worker_status()}")
    await office.shutdown()


# ─────────────────────────────────────────────────
#  Method 2: Programmatic (with custom class)
# ─────────────────────────────────────────────────

class CodeReviewer(BaseWorker):
    """Custom worker defined entirely in code."""

    async def handle(self, task: Task) -> TaskResult:
        prompt = f"""Review this code and provide feedback:

{task.instruction}

Focus on: correctness, style, performance, security.
Respond with a structured review."""

        result = await self.llm_call_structured(prompt)
        return TaskResult(
            task_id=task.id,
            status="done",
            output=result.get("review", str(result)),
            data=result,
        )


async def example_programmatic():
    """Add a worker programmatically with a custom class."""
    office = Office()
    office.configure_provider("ollama", base_url="http://localhost:11434")

    # Add a custom worker class directly
    office.hire_worker(
        "code_reviewer",
        model="ollama/llama3",
        squad="verification",
        role="Code review specialist",
        skill_md="You are a code reviewer. Analyze code for bugs, style issues, and improvements.",
        worker_class=CodeReviewer,
    )

    await office.initialize()
    print(f"Workers: {office.get_worker_status()}")
    await office.shutdown()


# ─────────────────────────────────────────────────
#  Method 3: Hot-plug at runtime
# ─────────────────────────────────────────────────

async def example_hot_plug():
    """Hot-plug a worker at runtime (after initialization)."""
    office = Office()
    office.configure_provider("ollama", base_url="http://localhost:11434")

    await office.initialize()
    print(f"Before hot-plug: {len(office.get_worker_status())} workers")

    # Hot-plug a worker from a directory at runtime
    worker = await office.hot_plug_worker(
        "examples/custom_worker/translator/",
        model="ollama/llama3",
    )

    print(f"After hot-plug: {len(office.get_worker_status())} workers")
    print(f"Hot-plugged worker: {worker.id} (model={worker.model})")

    # The worker is immediately available
    task = Task(
        instruction="Hello, how are you?",
        session_id="test-session",
        context={"target_language": "Indonesian"},
    )
    result = await worker.execute(task)
    print(f"Translation result: {result.output[:100]}...")

    await office.shutdown()


# ─────────────────────────────────────────────────
#  Method 4: With hooks for worker events
# ─────────────────────────────────────────────────

async def example_with_hooks():
    """Add workers with lifecycle hooks."""
    hooks = Hooks()

    @hooks.on(HookType.ON_WORKER_HIRED)
    async def on_worker_hired(event):
        print(f"Worker hired: {event['worker_id']} (model={event['model']})")

    @hooks.on(HookType.ON_TASK_COMPLETED)
    async def on_task_done(event):
        print(f"Task completed: {event.get('task_id', 'unknown')}")

    office = Office(hooks=hooks)
    office.configure_provider("ollama", base_url="http://localhost:11434")

    office.hire_worker(
        "my_bot",
        model="ollama/llama3",
        skill_md="You are a helpful assistant.",
    )

    await office.initialize()
    await office.shutdown()


# ─────────────────────────────────────────────────
#  CLI usage (run from terminal)
# ─────────────────────────────────────────────────

CLI_EXAMPLES = """
# Create a new worker (generates plugin.json + SKILL.md + worker.py)
kantorku worker create my_translator --squad translation --model "ollama/llama3"

# Validate a worker directory
kantorku worker validate workers/my_translator/

# Add an existing worker directory
kantorku worker add workers/my_translator/

# List all available workers
kantorku worker list

# Run with custom worker
kantorku run "Translate this to Indonesian" --config kantorku.toml
"""


if __name__ == "__main__":
    print("=" * 60)
    print("kantorku — Plug-and-Play Worker Examples")
    print("=" * 60)
    print()
    print("Available examples:")
    print("  1. From directory (auto-discover)")
    print("  2. Programmatic (custom class)")
    print("  3. Hot-plug at runtime")
    print("  4. With lifecycle hooks")
    print()
    print("CLI usage:")
    print(CLI_EXAMPLES)
    print()
    print("Uncomment one of the examples below to run:")

    # Uncomment to run:
    # asyncio.run(example_from_directory())
    # asyncio.run(example_programmatic())
    # asyncio.run(example_hot_plug())
    # asyncio.run(example_with_hooks())
