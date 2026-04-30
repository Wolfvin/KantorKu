"""
BriefingRoom — Workers discuss before execution.

The BriefingRoom is where the Conductor opens a discussion with
relevant workers about an upcoming task. Workers can:
- Share concerns or suggestions (speak_up)
- Ask clarifying questions
- Suggest alternative approaches
- See what OTHER workers are saying (shared context!)
- Respond to each other's messages

P4 UPGRADE: Multi-round discussion with GroupChannel.
Instead of isolated parallel speak_up, workers now have a REAL
group discussion where everyone can see and respond to each other.

Key changes from v0.3:
- Uses GroupChannel for shared communication
- Multi-round discussion (not just 1 shot)
- Workers can see and respond to each other
- Manager summarizes each round before the next
- Discussion continues until consensus or max rounds reached
- Proactive prefetch still happens simultaneously

Like a real office meeting:
- Everyone sits in the same room
- When someone speaks, everyone hears it
- People can build on each other's ideas
- Manager facilitates and summarizes
- Meeting ends when there's consensus
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from kantorku.events.bus import EventBus
from kantorku.events.emitter import EventEmitter
from kantorku.layers.conductor import Conductor, Contract
from kantorku.layers.group_channel import GroupChannel, MessageType
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
    channel: GroupChannel | None = None
    rounds_completed: int = 0
    consensus_reached: bool = False
    concerns: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)


class BriefingRoom:
    """
    BriefingRoom — where workers discuss the plan before execution.

    P4 FLOW (multi-round, shared context):
    1. Conductor opens briefing, shares plan with the group
    2. Round 1: Workers speak_up (everyone sees each other's messages)
    3. Manager summarizes Round 1, identifies concerns & agreements
    4. Round 2: Workers respond to concerns, refine approach
    5. ... repeat until consensus or max_rounds ...
    6. Manager makes final decision, briefing closes

    The key insight: prefetch starts DURING briefing, not after.
    By the time workers start working, context is already in Ring 1.

    Like a real office meeting, the discussion is NOT one-shot.
    People discuss, align, and iterate until they reach consensus.
    """

    def __init__(
        self,
        conductor: Conductor,
        hub: WorkerHub,
        pool: ContextPool,
        registry: WorkerRegistry,
        bus: EventBus,
        max_rounds: int = 3,
        round_timeout: float = 90.0,
    ) -> None:
        self.conductor = conductor
        self.hub = hub
        self.pool = pool
        self.registry = registry
        self.bus = bus
        self.max_rounds = max_rounds
        self.round_timeout = round_timeout

    async def open(
        self,
        contract: Contract,
        plan: dict[str, Any],
        session_id: str,
    ) -> BriefingResult:
        """
        Open a briefing session for a contract.

        Multi-round discussion where:
        - Workers can see and respond to each other
        - Manager facilitates and summarizes each round
        - Discussion continues until consensus or max_rounds

        Args:
            contract: The accepted contract
            plan: The initial execution plan from Conductor
            session_id: Session identifier

        Returns:
            BriefingResult with (possibly revised) plan, worker inputs,
            and the GroupChannel for continued context
        """
        emitter = EventEmitter(self.bus, session_id)

        # Identify relevant workers
        relevant_workers = plan.get("relevant_workers", [])
        if not relevant_workers:
            # Infer from contract todos
            for todo in contract.todos:
                if todo.assigned_to and todo.assigned_to not in relevant_workers:
                    relevant_workers.append(todo.assigned_to)

        # Create the GroupChannel — the shared communication board
        channel = GroupChannel(
            session_id=session_id,
            bus=self.bus,
            participants=relevant_workers + ["conductor"],
        )

        # 1. Announce briefing
        await emitter.briefing_opened(
            from_id="conductor",
            content=f"Briefing for: {contract.title}",
        )

        # 2. Manager shares the plan with the group
        plan_text = self._format_plan_for_sharing(plan, contract)
        await channel.speak(
            from_id="conductor",
            content=plan_text,
            message_type=MessageType.INFO,
            metadata={"plan": plan},
        )

        # 3. Breakdown todos → immediately trigger prefetch
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

        # 4. Multi-round discussion
        worker_inputs: list[dict[str, Any]] = []
        all_concerns: list[dict[str, Any]] = []
        consensus_reached = False
        rounds_completed = 0

        for round_num in range(1, self.max_rounds + 1):
            channel.start_round()

            # Workers speak in this round
            round_inputs, round_concerns = await self._run_discussion_round(
                channel=channel,
                contract=contract,
                plan=plan,
                round_num=round_num,
                session_id=session_id,
                relevant_workers=relevant_workers,
            )

            worker_inputs.extend(round_inputs)
            all_concerns.extend(round_concerns)
            rounds_completed = round_num

            # Check if we have consensus (no new concerns)
            if not round_concerns:
                consensus_reached = True
                await channel.manager_summary(
                    content=f"Round {round_num}: No new concerns. Team is aligned.",
                    decisions=["Proceed with current plan"],
                )
                break

            # Manager summarizes the round
            summary = await self._manager_summarize_round(
                channel=channel,
                round_num=round_num,
                concerns=round_concerns,
                inputs=round_inputs,
                contract=contract,
            )

            # If not the last round, give workers a chance to respond
            if round_num < self.max_rounds:
                # Revise plan based on concerns if needed
                revised = await self._revise_plan(plan, round_concerns, contract)
                if revised != plan:
                    plan = revised
                    await channel.speak(
                        from_id="conductor",
                        content="I've revised the plan based on our discussion. Here's the updated version:\n" + self._format_plan_for_sharing(plan, contract),
                        message_type=MessageType.INFO,
                    )

            channel.end_round(
                summary=summary,
                decisions=channel.get_decisions(),
            )

        # If we exhausted rounds without consensus, manager decides
        if not consensus_reached:
            await channel.manager_decision(
                content=f"After {self.max_rounds} rounds of discussion, I'm making the final call. We need to proceed with the current plan while noting the remaining concerns.",
                decisions=["Proceed with current plan, noting unresolved concerns"],
            )

        # Emit final plan
        await emitter.plan_drafted(
            from_id="conductor",
            content="Briefing complete. Plan is finalized.",
        )

        return BriefingResult(
            plan=plan,
            worker_inputs=worker_inputs,
            prefetch_tasks=prefetch_tasks,
            channel=channel,
            rounds_completed=rounds_completed,
            consensus_reached=consensus_reached,
            concerns=all_concerns,
            decisions=channel.get_decisions(),
        )

    async def _run_discussion_round(
        self,
        channel: GroupChannel,
        contract: Contract,
        plan: dict[str, Any],
        round_num: int,
        session_id: str,
        relevant_workers: list[str],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Run a single round of discussion.

        In this round, each worker:
        1. Reads the full channel transcript (what others have said)
        2. Speaks their mind (concerns, suggestions, questions)
        3. Can respond to other workers' messages

        Args:
            channel: The GroupChannel for this session
            contract: The contract being discussed
            plan: The current execution plan
            round_num: Which round number this is
            session_id: Session ID
            relevant_workers: Workers participating in this round

        Returns:
            Tuple of (worker_inputs, concerns)
        """
        emitter = EventEmitter(self.bus, session_id)
        worker_inputs: list[dict[str, Any]] = []
        concerns: list[dict[str, Any]] = []

        # Get the transcript so far — this is the SHARED CONTEXT
        transcript = channel.get_transcript_text()

        briefing_task = Task(
            instruction=contract.description,
            session_id=session_id,
            context={"contract": contract.to_dict(), "plan": plan},
        )

        speak_tasks = []
        for worker_id in relevant_workers:
            try:
                worker = self.registry.hire(worker_id)
            except Exception:
                continue

            # Worker speaks with full context of what others have said
            speak_tasks.append(
                self._worker_speak_with_context(
                    worker=worker,
                    worker_id=worker_id,
                    channel=channel,
                    transcript=transcript,
                    contract=contract,
                    plan=plan,
                    round_num=round_num,
                    briefing_task=briefing_task,
                )
            )

        # Wait for all workers to speak (with timeout)
        try:
            voices = await asyncio.wait_for(
                asyncio.gather(*speak_tasks, return_exceptions=True),
                timeout=self.round_timeout,
            )

            for v in voices:
                if isinstance(v, Exception):
                    continue
                worker_inputs.append(v)

                # Post the worker's message to the group channel
                # so ALL other workers can see it
                msg_type = MessageType.SPEAK
                if v.get("concern"):
                    msg_type = MessageType.CONCERN
                    concerns.append(v)
                elif v.get("suggestion"):
                    msg_type = MessageType.SUGGESTION

                await channel.speak(
                    from_id=v["worker_id"],
                    content=v.get("concern") or v.get("suggestion") or v.get("response", ""),
                    message_type=msg_type,
                )

                # Emit event for UI
                if v.get("has_input"):
                    await emitter.worker_speak_up(
                        from_id=v["worker_id"],
                        content=v.get("concern", "") or v.get("suggestion", ""),
                    )

        except asyncio.TimeoutError:
            await channel.speak(
                from_id="conductor",
                content=f"Round {round_num} timed out. Proceeding with what we have.",
                message_type=MessageType.INFO,
            )

        return worker_inputs, concerns

    async def _worker_speak_with_context(
        self,
        worker: Any,
        worker_id: str,
        channel: GroupChannel,
        transcript: str,
        contract: Contract,
        plan: dict[str, Any],
        round_num: int,
        briefing_task: Task,
    ) -> dict[str, Any]:
        """
        Have a worker speak in the briefing, WITH full context
        of what other workers have said.

        This is the key difference from the old speak_up:
        the worker now sees the full group discussion, not just
        the plan in isolation.

        Args:
            worker: The worker instance
            worker_id: The worker's ID
            channel: The GroupChannel
            transcript: Formatted transcript of the discussion so far
            contract: The contract
            plan: Current execution plan
            round_num: Which round this is
            briefing_task: The briefing task object

        Returns:
            Dict with worker's input
        """
        prompt = f"""
You are {worker_id} ({worker.role}).
This is Round {round_num} of our team briefing for: {contract.title}

===== GROUP DISCUSSION SO FAR =====
{transcript}
===================================

Current plan: {plan}

Based on the discussion above and your expertise:
1. Do you have any CONCERNS about the current plan? (especially given what others have said)
2. Do you have any SUGGESTIONS for improvement?
3. Do you AGREE or DISAGREE with anything that was said?
4. Any QUESTIONS for the team?

Respond with JSON:
{{
    "has_input": true/false,
    "concern": "your concern (if any)",
    "suggestion": "your suggestion (if any)",
    "agreement": "what you agree with (if any)",
    "disagreement": "what you disagree with (if any)",
    "question": "your question (if any)",
    "response": "a brief summary of your position"
}}

IMPORTANT: You can see what other team members have said. Build on their ideas
or raise concerns about their suggestions. This is a TEAM discussion, not just
individual feedback to the manager.
"""
        result = await worker.llm_call_structured(prompt)
        return {
            "worker_id": worker_id,
            "has_input": result.get("has_input", False),
            "concern": result.get("concern", ""),
            "suggestion": result.get("suggestion", ""),
            "agreement": result.get("agreement", ""),
            "disagreement": result.get("disagreement", ""),
            "question": result.get("question", ""),
            "response": result.get("response", ""),
        }

    async def _manager_summarize_round(
        self,
        channel: GroupChannel,
        round_num: int,
        concerns: list[dict[str, Any]],
        inputs: list[dict[str, Any]],
        contract: Contract,
    ) -> str:
        """
        Have the manager summarize the round's discussion.

        This is critical for maintaining alignment — the summary
        ensures everyone is on the same page about what was
        discussed and what was decided.
        """
        transcript = channel.get_transcript_text()
        concerns_text = "\n".join(
            f"- [{c['worker_id']}] {c.get('concern', c.get('response', ''))}"
            for c in concerns
        )

        prompt = f"""
You are the Manager facilitating a team briefing for: {contract.title}

Round {round_num} discussion:
{transcript}

Concerns raised:
{concerns_text}

Summarize this round:
1. What are the key points raised?
2. What are the main concerns?
3. What decisions have been made?
4. What needs further discussion?

Be concise but thorough. This summary will be shared with the team.
"""
        response = await self.conductor.router.complete(
            model=self.conductor.model,
            messages=[
                {"role": "system", "content": "You are a project manager summarizing a team meeting."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
        )

        # Post summary to the channel
        decisions = []
        for inp in inputs:
            if inp.get("suggestion") and not inp.get("concern"):
                decisions.append(f"{inp['worker_id']}: {inp['suggestion']}")

        await channel.manager_summary(
            content=response,
            decisions=decisions,
        )

        return response

    def _format_plan_for_sharing(self, plan: dict[str, Any], contract: Contract) -> str:
        """Format the execution plan for sharing in the group channel."""
        import json

        lines = [f"📋 Execution Plan for: {contract.title}"]
        lines.append(f"Description: {contract.description}")
        lines.append("")

        workers = plan.get("relevant_workers", [])
        if workers:
            lines.append(f"Team: {', '.join(workers)}")

        parallel_groups = plan.get("parallel_groups", [])
        if parallel_groups:
            lines.append("\nExecution Order:")
            for i, group in enumerate(parallel_groups):
                if isinstance(group, list):
                    lines.append(f"  Phase {i+1}: {', '.join(group)} (parallel)")
                else:
                    lines.append(f"  Phase {i+1}: {group}")

        todos = contract.todos
        if todos:
            lines.append("\nTasks:")
            for todo in todos:
                assignee = f" → {todo.assigned_to}" if todo.assigned_to else ""
                lines.append(f"  • {todo.description}{assignee}")

        return "\n".join(lines)

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
