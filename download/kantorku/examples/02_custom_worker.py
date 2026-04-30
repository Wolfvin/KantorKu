"""
Example 2: Custom Worker — Create your own worker type.

Shows how to subclass BaseWorker to create a specialized worker
with custom behavior, context handling, and output format.

Usage:
    python examples/02_custom_worker.py
"""

import asyncio
from kantorku import Office, BaseWorker, Task, TaskResult, Hooks, HookType


class CodeReviewer(BaseWorker):
    """
    A custom worker that reviews code and provides feedback.
    Demonstrates how to create specialized workers.
    """

    async def handle(self, task: Task) -> TaskResult:
        # 1. Get prefetched context if available
        context = await self.get_context(task.id)

        # 2. Build a specialized prompt
        code_to_review = task.instruction

        prompt = f"""Review the following code and provide:
1. Security issues (if any)
2. Performance concerns
3. Style/best practice violations
4. Suggested improvements

Code:
{code_to_review}

{'Context from codebase: ' + str(context) if context else 'No additional context available.'}
"""

        # 3. Make LLM call
        response = await self.llm_call(prompt)

        # 4. Return structured result
        return TaskResult(
            task_id=task.id,
            status="done",
            output=response,
            files=[],
            data={"review_type": "security_and_performance"},
        )


async def main():
    office = Office(conductor_model="ollama/llama3")
    office.configure_provider("ollama", base_url="http://localhost:11434")

    # Hire standard workers
    office.hire_worker("intake", model="ollama/llama3", squad="translation", role="Parser")
    office.hire_worker("narrator", model="ollama/llama3", squad="translation", role="Formatter")

    # Hire our custom worker by passing the class
    office.hire_worker(
        "code_reviewer",
        model="ollama/llama3",
        squad="review",
        role="Security and performance code reviewer",
        worker_class=CodeReviewer,
    )

    await office.initialize()

    # Run with hooks to see what's happening
    hooks = Hooks()

    @hooks.on(HookType.ON_TASK_COMPLETED)
    async def log_completion(event):
        print(f"  [HOOK] Task completed: {event.get('task_id', '?')} by {event.get('worker_id', '?')}")

    @hooks.on(HookType.ON_TASK_FAILED)
    async def log_failure(event):
        print(f"  [HOOK] Task FAILED: {event.get('task_id', '?')} - {event.get('error', '?')}")

    result = await office.run(
        "Review this code: def add(a, b): return a + b",
        auto_accept=True,
    )

    print("\nResult:")
    import json
    print(json.dumps(result, indent=2, default=str))

    await office.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
