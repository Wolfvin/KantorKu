"""
BriefingRoom — Workers discuss before execution.

The BriefingRoom is where the Conductor opens a discussion with
relevant workers about an upcoming task. Workers can:
- Share concerns or suggestions (speak_up)
- Ask clarifying questions
- Suggest alternative approaches

Key feature: Proactive prefetch — as each todo is broken down,
the Context Pool immediately starts fetching context for it.
Briefing and prefetch happen simultaneously, not sequentially.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from kantorku.events.bus import EventBus
from kantorku.events.emitter import EventEmitter
from kantorku.layers.conductor import Conductor, Contract
from kantorku.layers.worker_hub import WorkerHub
from kantorku.pool.context_pool import ContextPool
from kantorku.worker.base import Task
from kantorku.worker.registry import WorkerRegistry


@dataclass
class BriefingResult:
    """Result of a briefing session."""

    plan: dict[str, Any] = field(default_factory=dict)
    worker_inputs: list[dict[str, Any]] = field(default_factory=list)
    prefetch_tasks: list[asyncio.Task] = field(default_factory=list)


class BriefingRoom:
    """
    BriefingRoom — where workers discuss the plan before execution.

    Flow:
    1. Conductor drafts initial plan
    2. Each todo triggers a proactive prefetch (async, non-blocking)
    3. Workers speak_up in parallel with their concerns
    4. Conductor revises plan if needed

    The key insight: prefetch starts DURING briefing, not after.
    By the time workers start working, context is already in Ring 1.
    """

    def __init__(
        self,
        conductor: Conductor,
        hub: WorkerHub,
        pool: ContextPool,
        registry: WorkerRegistry,
        bus: EventBus,
    ) -> None:
        self.conductor = conductor
        self.hub = hub
        self.pool = pool
        self.registry = registry
        self.bus = bus

    async def open(
        self,
        contract: Contract,
        plan: dict[str, Any],
        session_id: str,
    ) -> BriefingResult:
        """
        Open a briefing session for a contract.

        Args:
            contract: The accepted contract
            plan: The initial execution plan from Conductor
            session_id: Session identifier

        Returns:
            BriefingResult with (possibly revised) plan and worker inputs
        """
        emitter = EventEmitter(self.bus, session_id)

        # 1. Announce briefing
        await emitter.briefing_opened(
            from_id="conductor",
            content=f"Briefing for: {contract.title}",
        )

        # 2. Breakdown todos → immediately trigger prefetch
        prefetch_tasks: list[asyncio.Task] = []
        for todo in contract.todos:
            # Emit each todo
            await emitter.briefing_opened(
                from_id="conductor",
                content=todo.description,
            )

            # Start prefetch — non-blocking, runs in background
            query = plan.get("prefetch_queries", {}).get(todo.id, todo.description)
            task = asyncio.create_task(
                self.pool.prefetch(
                    task_id=todo.id,
                    query=query,
                    session_id=session_id,
                )
            )
            prefetch_tasks.append(task)

        # 3. Workers speak_up — parallel
        relevant_workers = plan.get("relevant_workers", [])
        worker_inputs: list[dict[str, Any]] = []

        if relevant_workers:
            # Create a task for briefing
            briefing_task = Task(
                instruction=contract.description,
                session_id=session_id,
                context={"contract": contract.to_dict(), "plan": plan},
            )

            speak_tasks = []
            for worker_id in relevant_workers:
                worker = self.registry.hire(worker_id)
                speak_tasks.append(
                    worker.speak_up(briefing_task, plan)
                )

            # Wait for all workers to speak (with timeout)
            try:
                voices = await asyncio.wait_for(
                    asyncio.gather(*speak_tasks, return_exceptions=True),
                    timeout=60.0,
                )

                for v in voices:
                    if isinstance(v, Exception):
                        continue
                    worker_inputs.append(v)
                    if v.get("has_input"):
                        await emitter.worker_speak_up(
                            from_id=v["worker_id"],
                            content=v.get("concern", ""),
                        )
            except asyncio.TimeoutError:
                await emitter.briefing_opened(
                    from_id="conductor",
                    content="Briefing timeout — proceeding with current plan",
                )

        # 4. Conductor revises plan if there are concerns
        concerns = [v for v in worker_inputs if v.get("has_input")]
        final_plan = plan

        if concerns:
            await emitter.plan_revised(
                from_id="conductor",
                content="Revising plan based on team input",
                reason="Worker concerns raised during briefing",
            )

            # Have conductor revise the plan
            revised = await self._revise_plan(plan, concerns, contract)
            final_plan = revised

            await emitter.plan_drafted(
                from_id="conductor",
                content="Revised plan ready",
            )

        return BriefingResult(
            plan=final_plan,
            worker_inputs=worker_inputs,
            prefetch_tasks=prefetch_tasks,
        )

    async def _revise_plan(
        self,
        plan: dict[str, Any],
        concerns: list[dict[str, Any]],
        contract: Contract,
    ) -> dict[str, Any]:
        """Have the Conductor revise the plan based on worker concerns."""
        import json

        concerns_text = json.dumps(concerns, indent=2)

        prompt = f"""
        Original plan:
        {json.dumps(plan, indent=2)}

        Worker concerns:
        {concerns_text}

        Contract: {contract.title}
        Description: {contract.description}

        Revise the plan to address worker concerns.
        Respond with the complete revised plan in the same JSON format.
        """
        result = await self.conductor.router.complete(
            model=self.conductor.model,
            messages=[
                {"role": "system", "content": "You are the Conductor. Revise the execution plan."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
        )

        try:
            text = result.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return plan  # Fall back to original
