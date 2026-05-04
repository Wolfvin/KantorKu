"""
Office — Main entry point for kantorku.

The Office is to kantorku what Crew is to CrewAI or StateGraph is to LangGraph.
It orchestrates everything: workers, conductor, briefing room, context pool, memory.

Now includes (v0.3.0):
- CostTracker integration (automatic cost tracking for all LLM calls)
- LLMCache integration (avoid redundant API calls)
- Observability integration (tracing + metrics for all operations)
- Async context manager support (async with Office() as office)
- Structured errors
- Session persistence & crash recovery (P3)
- Persistent task queue with retry & DLQ (P3)
- Middleware pipeline (P3)
- Health monitoring (P3)

Usage:
    # From config file
    office = Office.from_config("kantorku.toml")
    result = await office.run("Buat rate limiter di Rust")

    # Programmatic
    office = Office(conductor_model="anthropic/claude-opus-4-6")
    office.configure_provider("anthropic", api_key="sk-...")
    office.hire_worker("coder_backend", model="minimax/minimax-m2-7")
    result = await office.run("Implement authentication")

    # Async context manager
    async with Office.from_config("kantorku.toml") as office:
        result = await office.run("Build rate limiter")

    # Crash recovery
    office = Office.from_config("kantorku.toml")
    await office.initialize()
    if office.recovery.has_recovery_data():
        await office.restore_from_crash()
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any, AsyncIterator

from kantorku.config.settings import KantorkuConfig
from kantorku.events.bus import EventBus
from kantorku.events.emitter import EventEmitter
from kantorku.hooks import HookType, Hooks
from kantorku.layers.conductor import Conductor, Contract, ContractState, TodoItem
from kantorku.layers.briefing_room import BriefingRoom
from kantorku.layers.worker_hub import WorkerHub
from kantorku.layers.intake import Intake
from kantorku.layers.group_channel import GroupChannel, MessageType
from kantorku.layers.todo_review import TodoReviewPhase, TodoReviewResult
from kantorku.layers.session_transcript import SessionTranscript
from kantorku.pool.context_pool import ContextPool
from kantorku.memory.ring1 import Ring1Memory
from kantorku.memory.ring2 import Ring2Memory
from kantorku.memory.ring3 import Ring3Memory
from kantorku.providers.router import ProviderRouter
from kantorku.providers.circuit_breaker import CircuitBreaker
from kantorku.providers.retry import RetryPolicy
from kantorku.worker.base import BaseWorker, Task, TaskResult
from kantorku.worker.registry import WorkerRegistry
from kantorku.cost import CostTracker
from kantorku.cache import LLMCache
from kantorku.observability import get_tracer, get_metrics
from kantorku.errors import OfficeNotInitializedError, NoContractError

# P3 imports
from kantorku.interface.persistence import CheckpointManager, CrashRecovery, OfficeSnapshot
from kantorku.interface.task_queue import TaskQueue
from kantorku.interface.middleware import MiddlewarePipeline, MiddlewareContext
from kantorku.interface.health import HealthChecker

# P4: Session transcripts (per-session context tracking)
from kantorku.layers.session_transcript import SessionTranscript as _SessionTranscript

logger = logging.getLogger("kantorku.office")


class Office:
    """
    Office — the main entry point for kantorku.

    Orchestrates the complete workflow:
    1. Client message → Conductor understands (Panel 1)
    2. Contract accepted → BriefingRoom opens (Panel 2)
    3. Workers execute with prefetched context
    4. Verifiers check the output
    5. Sentinel logs lessons

    Usage:
        office = Office.from_config("kantorku.toml")
        await office.initialize()

        # Understand client (Panel 1 flow)
        async for event in office.chat("session-1", "Build me a rate limiter"):
            print(event)

        # Accept contract and start work
        result = await office.accept_and_run("session-1")
    """

    def __init__(
        self,
        conductor_model: str = "anthropic/claude-opus-4-6",
        config: KantorkuConfig | None = None,
        hooks: Hooks | None = None,
        enable_cache: bool = True,
        cache_ttl: float = 3600.0,
        enable_cost_tracking: bool = True,
        circuit_breaker: CircuitBreaker | None = None,
        retry_policy: RetryPolicy | None = None,
        # P3: Persistence
        snapshot_dir: str = "data/snapshots",
        auto_checkpoint_interval: int = 10,
        # P3: Task Queue
        enable_task_queue: bool = True,
        task_queue_max_retries: int = 2,
        # P3: Middleware
        middleware: MiddlewarePipeline | None = None,
        # P3: Health
        health_check_interval: int = 30,
    ) -> None:
        self.config = config or KantorkuConfig(conductor_model=conductor_model)
        self.hooks = hooks or Hooks()

        # Core infrastructure
        self.bus = EventBus()

        # Cost tracker
        self._enable_cost_tracking = enable_cost_tracking
        self.cost_tracker = CostTracker() if enable_cost_tracking else None

        # LLM cache
        self._enable_cache = enable_cache
        self.cache = LLMCache(backend="memory", ttl_seconds=cache_ttl) if enable_cache else None

        # Router with integrated cost tracking, cache, circuit breaker
        self.router = ProviderRouter(
            cost_tracker=self.cost_tracker,
            cache=self.cache,
            circuit_breaker=circuit_breaker,
            retry_policy=retry_policy,
        )

        # Observability
        self._tracer = get_tracer()
        self._metrics = get_metrics()

        # Conductor
        self.conductor = Conductor(
            router=self.router,
            bus=self.bus,
            model=self.config.conductor_model,
        )

        # Worker registry
        self.registry = WorkerRegistry(router=self.router, bus=self.bus)

        # Memory
        self.ring1 = Ring1Memory(self.config.memory.ring1_path)
        self.ring2 = Ring2Memory(self.config.memory.ring2_path)
        self.ring3 = Ring3Memory(
            self.config.memory.ring3_path,
            enabled=self.config.memory.ring3_enabled,
        )

        # Context pool (initialized later with router)
        self.pool = ContextPool(
            model=self.config.pool.model,
            size=self.config.pool.instances,
            bus=self.bus,
            ring1=self.ring1,
        )

        # Layers (initialized after registry is populated)
        self.hub: WorkerHub | None = None
        self.briefing_room: BriefingRoom | None = None
        self.intake: Intake | None = None

        # P3: Checkpoint manager for session persistence
        self.checkpoint = CheckpointManager(
            ring1=self.ring1,
            ring2=self.ring2,
            bus=self.bus,
            snapshot_dir=snapshot_dir,
            auto_interval=auto_checkpoint_interval,
        )

        # P3: Crash recovery
        self.recovery = CrashRecovery(
            ring1=self.ring1,
            ring2=self.ring2,
            snapshot_dir=snapshot_dir,
        )

        # P3: Task queue (initialized after ring2 in initialize())
        self._enable_task_queue = enable_task_queue
        self._task_queue_max_retries = task_queue_max_retries
        self._task_queue: TaskQueue | None = None

        # P3: Middleware pipeline
        self._middleware = middleware or MiddlewarePipeline()

        # P3: Health checker (initialized after office is ready)
        self._health: HealthChecker | None = None
        self._health_check_interval = health_check_interval

        # P4: Session transcripts (per-session context tracking)
        self._transcripts: dict[str, SessionTranscript] = {}

        # P4: TodoReviewPhase (initialized after registry in initialize())
        self._todo_review: TodoReviewPhase | None = None

        # P4: GroupChannel per session
        self._channels: dict[str, GroupChannel] = {}

        # P4: BriefingRoom settings
        self._briefing_max_rounds: int = 3
        self._briefing_round_timeout: float = 90.0

        self._initialized = False

    async def __aenter__(self) -> Office:
        """Async context manager entry — auto-initialize."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit — auto-shutdown."""
        await self.shutdown()

    @classmethod
    def from_config(cls, path: str | Path) -> Office:
        """
        Create an Office from a kantorku.toml configuration file.

        Args:
            path: Path to the TOML config file

        Returns:
            Configured Office instance (call await office.initialize() before use)
        """
        config = KantorkuConfig.from_toml(path)
        config.resolve_env_vars()
        return cls(config=config)

    def configure_provider(self, name: str, **kwargs: Any) -> None:
        """Configure an LLM provider."""
        self.router.configure(name, **kwargs)

    def hire_worker(
        self,
        worker_id: str,
        model: str = "",
        squad: str = "",
        role: str = "",
        skill_md: str = "",
        worker_class: type[BaseWorker] | None = None,
        path: str | Path | None = None,
    ) -> None:
        """
        Register a worker with the office (plug-and-play).

        Multiple ways to add a worker:

        1. Simple (model + SKILL.md prompt):
            office.hire_worker("my_bot", model="ollama/llama3", skill_md="You are a helper")

        2. From a directory (auto-discovers plugin.json + SKILL.md + worker.py):
            office.hire_worker("my_bot", path="workers/my_bot/")

        3. With a custom class:
            office.hire_worker("my_bot", model="ollama/llama3", worker_class=MyWorker)

        4. Full config:
            office.hire_worker(
                "translator",
                model="ollama/llama3",
                squad="translation",
                role="Language translator",
                skill_md="You translate text...",
            )
        """
        from kantorku.worker.identity import WorkerIdentity

        # If path is provided, load from directory
        if path:
            identity = WorkerIdentity.from_directory(Path(path))
            # Apply overrides
            if model:
                identity.model = model
            if squad:
                identity.squad = squad
            if role:
                identity.role = role
            if skill_md:
                identity.skill_md = skill_md
        else:
            identity = WorkerIdentity.from_dict({
                "id": worker_id,
                "model": model,
                "squad": squad,
                "role": role,
                "skill_md": skill_md,
            })

        self.registry.register_identity(identity)

        if worker_class:
            self.registry.register_worker_class(worker_id or identity.id, worker_class)

        # If already initialized, auto-hire and set ring1
        if self._initialized:
            wid = worker_id or identity.id
            worker = self.registry.hire(wid)
            if self.ring1:
                worker.set_ring1(self.ring1)

    async def hot_plug_worker(
        self,
        path: str | Path,
        model: str = "",
        squad: str = "",
        role: str = "",
    ) -> BaseWorker:
        """
        Hot-plug a worker at runtime from a directory.

        Drop a folder with plugin.json (+ SKILL.md + worker.py),
        call this, and the worker is immediately available for tasks.
        """
        worker = self.registry.hot_plug(
            path=Path(path),
            model=model,
            squad=squad,
            role=role,
        )

        # Set ring1 if available
        if self.ring1 and self._initialized:
            worker.set_ring1(self.ring1)

        # Trigger hook
        await self.hooks.trigger(HookType.ON_WORKER_HIRED, {
            "worker_id": worker.id,
            "model": worker.model,
            "squad": worker.squad,
        })

        return worker

    async def initialize(self) -> None:
        """
        Initialize all office systems.

        Must be called before any other operations.
        Sets up memory, pool, providers, cache, cost tracker, and worker instances.
        """
        if self._initialized:
            return

        with self._tracer.span("office.initialize"):
            # Configure providers from config
            self.router.configure_from_dict(self.config.providers)

            # Initialize cache
            if self.cache:
                await self.cache.initialize()

            # Register workers from config
            workers_config = {
                wid: {"model": w.model, "squad": w.squad, "role": w.role}
                for wid, w in self.config.workers.items()
            }
            self.registry.discover_from_config(workers_config)

            # Discover workers from multiple directories (plug-and-play)
            discover_dirs = []
            builtin_dir = Path(__file__).parent.parent / "workers"
            if builtin_dir.exists():
                discover_dirs.append(builtin_dir)
            project_workers = Path("workers")
            if project_workers.exists() and project_workers.resolve() != builtin_dir.resolve():
                discover_dirs.append(project_workers)
            if hasattr(self.config, 'workers_dir') and self.config.workers_dir:
                ext_dir = Path(self.config.workers_dir)
                if ext_dir.exists() and ext_dir.resolve() not in [d.resolve() for d in discover_dirs]:
                    discover_dirs.append(ext_dir)

            if discover_dirs:
                self.registry.discover_workers_multi(discover_dirs)

            # Discover workers from pip-installed packages (entry points)
            try:
                self.registry.discover_from_entry_points()
            except Exception:
                pass

            # Initialize memory
            await self.ring1.initialize()
            await self.ring2.initialize()
            await self.ring3.initialize()

            # Set Ring1 on pool
            self.pool.ring1 = self.ring1

            # Set Ring1 on conductor for session persistence
            self.conductor.set_ring1(self.ring1)

            # Set Ring1 on all workers
            for worker_id in self.registry.all_worker_ids:
                worker = self.registry.hire(worker_id)
                worker.set_ring1(self.ring1)

            # Initialize layers
            self.hub = WorkerHub(
                registry=self.registry,
                bus=self.bus,
                conductor=self.conductor,
            )
            self.briefing_room = BriefingRoom(
                conductor=self.conductor,
                hub=self.hub,
                pool=self.pool,
                registry=self.registry,
                bus=self.bus,
                max_rounds=self._briefing_max_rounds,
                round_timeout=self._briefing_round_timeout,
            )
            intake_worker_cfg = self.config.workers.get("intake")
            intake_model = intake_worker_cfg.model if intake_worker_cfg else "ollama/llama3"
            self.intake = Intake(
                router=self.router,
                bus=self.bus,
                model=intake_model,
            )

            # P4: TodoReviewPhase
            self._todo_review = TodoReviewPhase(
                conductor=self.conductor,
                registry=self.registry,
                bus=self.bus,
            )

            # Start context pool
            for pw in self.pool.instances:
                pw.router = self.router
            await self.pool.start()

            # P3: Initialize task queue
            if self._enable_task_queue:
                self._task_queue = TaskQueue(
                    ring2=self.ring2,
                    bus=self.bus,
                    default_max_retries=self._task_queue_max_retries,
                )
                await self._task_queue.start()

            # P3: Initialize health checker
            self._health = HealthChecker(
                office=self,
                check_interval=self._health_check_interval,
            )
            await self._health.start()

            # P3: Initialize checkpoint manager references
            self.checkpoint.ring1 = self.ring1
            self.checkpoint.ring2 = self.ring2
            self.checkpoint.bus = self.bus

            self._initialized = True
            logger.info("kantorku Office initialized (v0.4.0)")

    async def chat(
        self,
        session_id: str,
        message: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Chat with the Conductor (Panel 1 flow).

        Yields events: manager_message or contract_ready.
        Multi-turn — call repeatedly until contract_ready appears.
        """
        if not self._initialized:
            await self.initialize()

        with self._tracer.span(
            "office.chat",
            attributes={"session_id": session_id},
        ):
            # Optional: Run through Intake first
            if self.intake:
                intake_result = await self.intake.parse(message, session_id)
                await self.ring1.store_session(session_id, {
                    "intake": intake_result.to_dict(),
                })

            # Conductor understands client
            async for event in self.conductor.understand_client(session_id, message):
                yield event

    async def revise(
        self,
        session_id: str,
        feedback: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Revise the current contract based on client feedback."""
        async for event in self.conductor.revise_contract(session_id, feedback):
            yield event

    async def accept_and_run(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        """
        Accept the current contract and start work.

        This triggers the full Panel 2 flow:
        briefing → prefetch → assign → execute → verify → done
        """
        if not self._initialized:
            await self.initialize()

        contract = self.conductor.get_contract(session_id)
        if not contract:
            raise NoContractError(session_id)

        with self._tracer.span(
            "office.accept_and_run",
            attributes={"session_id": session_id, "contract_title": contract.title},
        ):
            # Mark as working
            await self.conductor.mark_working(session_id)
            emitter = EventEmitter(self.bus, session_id)
            await emitter.contract_accepted()
            await self.hooks.trigger(HookType.ON_CONTRACT_ACCEPTED, {
                "session_id": session_id, "contract": contract.to_dict()
            })

            # Run the full orchestration
            result = await self._conduct(session_id, contract)

            # Mark as done
            await self.conductor.mark_done(session_id)
            return result

    async def run(
        self,
        message: str,
        session_id: str | None = None,
        auto_accept: bool = False,
    ) -> dict[str, Any]:
        """
        One-shot run — send message, get result.

        This is the simplest API: send a task, get the complete result.
        Automatically handles contract negotiation if auto_accept=True.
        """
        if not self._initialized:
            await self.initialize()

        session_id = session_id or uuid.uuid4().hex[:12]

        with self._tracer.span(
            "office.run",
            attributes={"session_id": session_id},
        ):
            # Chat until contract is ready
            contract_data = None
            async for event in self.chat(session_id, message):
                if event.get("type") == "contract_ready":
                    contract_data = event
                elif event.get("type") == "manager_message":
                    if not auto_accept:
                        return {
                            "status": "clarification_needed",
                            "message": event["content"],
                            "session_id": session_id,
                        }

            if not contract_data:
                return {
                    "status": "no_contract",
                    "message": "Could not generate a contract from this message",
                    "session_id": session_id,
                }

            # Auto-accept and run
            return await self.accept_and_run(session_id)

    async def _conduct(
        self,
        session_id: str,
        contract: Contract,
    ) -> dict[str, Any]:
        """
        Full orchestration with P4 communication flow.

        P4 Flow (like a real office):
        1. Conductor drafts plan
        2. BriefingRoom — multi-round team discussion (shared context!)
        3. TodoReviewPhase — team reviews TODOs before execution
        4. Execute tasks (with workers having full context)
        5. Verify output
        6. Log lessons
        """
        emitter = EventEmitter(self.bus, session_id)

        # P4: Create session transcript for context tracking
        transcript = self._get_or_create_transcript(session_id)
        transcript.set_contract(contract)

        # Record client discussion in transcript
        for msg in contract.client_messages:
            transcript.add_entry(
                phase="client_discussion",
                from_id=msg.get("role", "client"),
                content=msg.get("content", ""),
                entry_type="message",
            )

        # 1. Conductor drafts plan
        plan = await self.conductor.draft_plan(contract)
        await emitter.plan_drafted(from_id="conductor", content=str(plan))
        transcript.add_entry(
            phase="team_briefing",
            from_id="conductor",
            content="Plan drafted for team review",
            entry_type="decision",
        )

        # 2. Briefing room — multi-round team discussion with shared context
        await self.conductor.mark_team_review(session_id)
        briefing_result = await self.briefing_room.open(
            contract=contract,
            plan=plan,
            session_id=session_id,
        )
        final_plan = briefing_result.plan

        # P4: Store the channel for continued context
        if briefing_result.channel:
            self._channels[session_id] = briefing_result.channel
            transcript.set_channel(briefing_result.channel)

        # Record briefing results in transcript
        transcript.add_entry(
            phase="team_briefing",
            from_id="conductor",
            content=f"Briefing complete. {briefing_result.rounds_completed} rounds. "
                    f"Consensus: {briefing_result.consensus_reached}. "
                    f"Concerns: {len(briefing_result.concerns)}",
            entry_type="decision",
            metadata={
                "rounds": briefing_result.rounds_completed,
                "consensus": briefing_result.consensus_reached,
                "decisions": briefing_result.decisions,
            },
        )

        # P4: If team has significant concerns, manager goes back to client
        if briefing_result.concerns and not briefing_result.consensus_reached:
            concerns = briefing_result.concerns
            suggestions = [
                {"worker_id": inp.get("worker_id", ""), "suggestion": inp.get("suggestion", "")}
                for inp in briefing_result.worker_inputs
                if inp.get("suggestion")
            ]

            # Manager brings feedback to client (iterative flow!)
            # Note: In auto_accept mode, we skip this and proceed
            # In interactive mode, client would see this and respond
            transcript.add_entry(
                phase="client_discussion",
                from_id="conductor",
                content=f"Team raised {len(concerns)} concerns. Proceeding with noted concerns for now.",
                entry_type="concern",
                metadata={"concerns": concerns},
            )

        # 3. P4: TodoReviewPhase — team reviews TODOs before execution
        if self._todo_review and briefing_result.channel:
            await self.conductor.mark_todo_review(session_id)
            review_result = await self._todo_review.review(
                contract=contract,
                channel=briefing_result.channel,
                session_id=session_id,
            )

            # Record review in transcript
            transcript.add_entry(
                phase="todo_review",
                from_id="conductor",
                content=f"TODO review complete. Approved: {review_result.approved}. "
                        f"All understood: {review_result.all_understood}. "
                        f"Blockers: {len(review_result.blockers)}",
                entry_type="decision",
                metadata={
                    "approved": review_result.approved,
                    "blockers": review_result.blockers,
                    "reviews": [r.to_dict() for r in review_result.reviews],
                },
            )

            # Refine contract based on team input
            if review_result.refined_todos:
                await self.conductor.refine_contract_with_team_input(
                    session_id=session_id,
                    refined_todos=review_result.refined_todos,
                    review_decisions=review_result.channel.get_decisions() if review_result.channel else [],
                )
                contract = self.conductor.get_contract(session_id) or contract

            # Mark team approval
            if review_result.approved:
                await self.conductor.approve_team(session_id)

        # 4. Execute tasks based on plan — workers now have FULL context
        execution_order = final_plan.get("execution_order", [t.id for t in contract.todos])
        parallel_groups = final_plan.get("parallel_groups", [execution_order])
        results: dict[str, TaskResult] = {}

        for group in parallel_groups:
            group_tasks = []
            for todo_id in group:
                todo = next((t for t in contract.todos if t.id == todo_id), None)
                if not todo:
                    continue

                assigned_to = todo.assigned_to or self._assign_worker(todo, final_plan)
                worker = self.registry.hire(assigned_to) if assigned_to else None

                if worker:
                    # P4: Include session transcript context in the task
                    # so the worker has full awareness of what's been discussed
                    worker_context = transcript.get_context_for_worker(assigned_to)

                    task = Task(
                        instruction=todo.description,
                        session_id=session_id,
                        context={
                            "contract": contract.to_dict(),
                            "todo": todo.to_dict(),
                            "assigned_to": assigned_to,
                            "session_context": worker_context,
                            "team_decisions": transcript.get_decisions(),
                        },
                    )

                    await emitter.task_assigned(
                        from_id="conductor",
                        to_id=assigned_to,
                        content=todo.description,
                    )

                    group_tasks.append((todo_id, assigned_to, worker, task))

            # Run parallel tasks
            if group_tasks:
                parallel_results = await asyncio.gather(
                    *[
                        self._execute_task(todo_id, worker, task, emitter)
                        for todo_id, _, worker, task in group_tasks
                    ],
                    return_exceptions=True,
                )

                for (todo_id, assigned_to, _, task), result in zip(group_tasks, parallel_results):
                    if isinstance(result, Exception):
                        recovered = await self._recover_task(
                            session_id=session_id,
                            todo_id=todo_id,
                            task=task,
                            assigned_to=assigned_to,
                            error=str(result),
                            contract=contract,
                            emitter=emitter,
                        )
                        results[todo_id] = recovered
                    else:
                        results[todo_id] = result
                        if result.status == "failed":
                            recovered = await self._recover_task(
                                session_id=session_id,
                                todo_id=todo_id,
                                task=task,
                                assigned_to=assigned_to,
                                error=result.error,
                                contract=contract,
                                emitter=emitter,
                            )
                            results[todo_id] = recovered

                    # Store in Ring 1
                    await self.ring1.store_task_result(
                        task_id=todo_id,
                        worker_id=assigned_to,
                        session_id=session_id,
                        result=results[todo_id].to_dict() if hasattr(results[todo_id], 'to_dict') else {},
                    )

                    # Log episode in Ring 2
                    await self.ring2.log_episode(
                        session_id=session_id,
                        event_type="task_completed" if results[todo_id].status == "done" else "task_failed",
                        data={
                            "todo_id": todo_id,
                            "worker_id": assigned_to,
                            "status": results[todo_id].status,
                        },
                    )

                    # Trigger hooks
                    if results[todo_id].status == "done":
                        await self.hooks.trigger(HookType.ON_TASK_COMPLETED, {
                            "session_id": session_id,
                            "task_id": todo_id,
                            "worker_id": assigned_to,
                            "result": results[todo_id].to_dict() if hasattr(results[todo_id], 'to_dict') else {},
                        })
                    else:
                        await self.hooks.trigger(HookType.ON_TASK_FAILED, {
                            "session_id": session_id,
                            "task_id": todo_id,
                            "worker_id": assigned_to,
                            "error": results[todo_id].error,
                        })

        # 4. Verification
        verification_needed = final_plan.get("verification_needed", [])
        verification_results = {}

        for verifier_id in verification_needed:
            try:
                verifier = self.registry.hire(verifier_id)
                verify_task = Task(
                    instruction=f"Verify the output for: {contract.title}",
                    session_id=session_id,
                    context={
                        "contract": contract.to_dict(),
                        "results": {k: v.to_dict() if hasattr(v, 'to_dict') else {} for k, v in results.items()},
                    },
                )

                if "designer" in verifier_id:
                    await emitter.verify_design_start()
                else:
                    await emitter.verify_engineer_start()

                verify_result = await verifier.execute(verify_task)
                verification_results[verifier_id] = verify_result

                if "designer" in verifier_id:
                    await emitter.verify_design_done(
                        issues=verify_result.data.get("issues", []),
                        approved=verify_result.status == "done",
                    )
                else:
                    await emitter.verify_engineer_done(
                        issues=verify_result.data.get("issues", []),
                        approved=verify_result.status == "done",
                    )

            except Exception as e:
                verification_results[verifier_id] = TaskResult(
                    status="failed",
                    error=str(e),
                )

        # 5. Sentinel logs lessons
        failed_tasks = [r for r in results.values() if r.status == "failed"]
        for failed in failed_tasks:
            await emitter.error_logged(lesson=f"Task failed: {failed.error}")
            await self.ring2.log_lesson(
                source="sentinel",
                lesson=failed.error,
                category="task_failure",
            )

        return {
            "session_id": session_id,
            "contract": contract.to_dict(),
            "results": {k: v.to_dict() if hasattr(v, 'to_dict') else {} for k, v in results.items()},
            "verification": {k: v.to_dict() if hasattr(v, 'to_dict') else {} for k, v in verification_results.items()},
            # P4: Include communication metadata
            "briefing": {
                "rounds_completed": briefing_result.rounds_completed,
                "consensus_reached": briefing_result.consensus_reached,
                "concerns_count": len(briefing_result.concerns),
                "decisions": briefing_result.decisions,
            },
            "transcript_summary": transcript.get_summary(),
        }

    async def _execute_task(
        self,
        todo_id: str,
        worker: BaseWorker,
        task: Task,
        emitter: EventEmitter,
    ) -> TaskResult:
        """Execute a single task with a worker."""
        return await worker.execute(task)

    async def _recover_task(
        self,
        session_id: str,
        todo_id: str,
        task: Task,
        assigned_to: str,
        error: str,
        contract: Contract,
        emitter: EventEmitter,
        max_retries: int = 1,
    ) -> TaskResult:
        """
        Attempt to recover from a failed task using Conductor's recovery strategy.

        Strategies: retry_same, reassign, simplify, abort.
        Only retries once to avoid infinite loops.
        """
        await emitter.error_logged(lesson=f"Task {todo_id} failed: {error}. Attempting recovery...")

        recovery = await self.conductor.recover_from_failure(session_id, task, error)
        strategy = recovery.get("strategy", "retry_same")

        if strategy == "retry_same":
            try:
                worker = self.registry.hire(assigned_to)
                await emitter.task_assigned(
                    from_id="conductor",
                    to_id=assigned_to,
                    content=f"[RETRY] {task.instruction}",
                )
                result = await worker.execute(task)
                if result.status == "done":
                    return result
            except Exception as e:
                return TaskResult(
                    task_id=todo_id,
                    worker_id=assigned_to,
                    status="failed",
                    error=f"Retry failed: {e}",
                )

        elif strategy == "reassign":
            new_worker_id = recovery.get("new_worker", "")
            if new_worker_id and new_worker_id in self.registry.all_worker_ids:
                try:
                    worker = self.registry.hire(new_worker_id)
                    await emitter.task_assigned(
                        from_id="conductor",
                        to_id=new_worker_id,
                        content=f"[REASSIGNED] {task.instruction}",
                    )
                    result = await worker.execute(task)
                    return result
                except Exception as e:
                    return TaskResult(
                        task_id=todo_id,
                        worker_id=new_worker_id,
                        status="failed",
                        error=f"Reassign failed: {e}",
                    )

        elif strategy == "simplify":
            subtasks = recovery.get("subtasks", [])
            if subtasks:
                sub_results = []
                for i, sub_desc in enumerate(subtasks):
                    sub_task = Task(
                        instruction=sub_desc,
                        session_id=session_id,
                        context={
                            "contract": contract.to_dict(),
                            "parent_todo": todo_id,
                            "subtask_index": i,
                        },
                    )
                    try:
                        worker = self.registry.hire(assigned_to)
                        result = await worker.execute(sub_task)
                        sub_results.append(result)
                    except Exception:
                        sub_results.append(TaskResult(
                            task_id=f"{todo_id}_sub_{i}",
                            worker_id=assigned_to,
                            status="failed",
                            error="Subtask failed",
                        ))

                all_done = all(r.status == "done" for r in sub_results)
                combined_output = "\n".join(r.output for r in sub_results if r.output)
                return TaskResult(
                    task_id=todo_id,
                    worker_id=assigned_to,
                    status="done" if all_done else "failed",
                    output=combined_output,
                    error="" if all_done else "Some subtasks failed",
                )

        # strategy == "abort" or fallback
        return TaskResult(
            task_id=todo_id,
            worker_id=assigned_to,
            status="failed",
            error=f"Task aborted: {recovery.get('reason', error)}",
        )

    def _assign_worker(self, todo: TodoItem, plan: dict[str, Any]) -> str:
        """Determine which worker should handle a todo."""
        for group in plan.get("parallel_groups", []):
            if todo.id in group:
                relevant = plan.get("relevant_workers", [])
                if relevant:
                    return relevant[0]

        desc = todo.description.lower()
        if any(k in desc for k in ["ui", "frontend", "react", "css", "component"]):
            return "coder_frontend"
        if any(k in desc for k in ["api", "websocket", "integration", "mcp", "glue"]):
            return "coder_wiring"
        return "coder_backend"

    def get_events(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent events for a session."""
        return self.bus.get_history(session_id, limit)

    def get_worker_status(self) -> list[dict[str, Any]]:
        """Get status of all workers."""
        return self.registry.list_workers()

    def get_pool_status(self) -> dict[str, Any]:
        """Get context pool status."""
        return self.pool.get_status()

    def get_cost_report(self) -> dict[str, Any]:
        """Get cost report for all LLM calls."""
        if self.cost_tracker:
            return self.cost_tracker.get_report()
        return {}

    def get_circuit_breaker_status(self) -> dict[str, Any]:
        """Get circuit breaker status for all providers."""
        return self.router.get_circuit_breaker_status()

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get observability metrics summary."""
        return self._metrics.get_summary()

    def get_observability_spans(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent tracing spans."""
        return self._tracer.get_spans(limit)

    # ── P3: Persistence & Recovery ─────────────────────────────────

    async def checkpoint_session(self, session_id: str) -> str | None:
        """Manually checkpoint a session."""
        session = self.conductor._sessions.get(session_id)
        if not session:
            return None

        contract = session.get("contract")
        contract_dict = contract.to_dict() if contract and hasattr(contract, 'to_dict') else {}
        contract_state = session.get("state")
        state_value = contract_state.value if hasattr(contract_state, 'value') else str(contract_state)

        return await self.checkpoint.save_session(
            session_id=session_id,
            contract=contract_dict,
            contract_state=state_value,
            client_messages=contract.client_messages if contract and hasattr(contract, 'client_messages') else [],
            manager_messages=contract.manager_messages if contract and hasattr(contract, 'manager_messages') else [],
            cost_usd=self.cost_tracker.get_session_cost(session_id) if self.cost_tracker else 0.0,
        )

    async def restore_from_crash(self) -> bool:
        """
        Restore office state from the last crash recovery snapshot.

        Returns True if recovery was successful.
        """
        snapshot = await self.recovery.try_recover()
        if not snapshot:
            logger.info("No recovery data found — starting fresh")
            return False

        # Restore sessions
        for session_id, session_snap in snapshot.sessions.items():
            if session_snap.contract_state in ("working", "contract_presented"):
                logger.info(f"Restoring session {session_id} (state: {session_snap.contract_state})")
                # Store restored session in Ring1
                await self.ring1.store_session(session_id, session_snap.to_dict())

        logger.info(f"Crash recovery completed: {len(snapshot.sessions)} sessions restored")
        return True

    # ── P3: Task Queue ─────────────────────────────────────────────

    async def enqueue_task(
        self,
        instruction: str,
        session_id: str = "",
        assigned_to: str = "",
        priority: int = 0,
        **kwargs: Any,
    ) -> str | None:
        """Enqueue a task to the persistent task queue."""
        if not self._task_queue:
            return None
        return await self._task_queue.enqueue(
            instruction=instruction,
            session_id=session_id,
            assigned_to=assigned_to,
            priority=priority,
            **kwargs,
        )

    def get_task_queue_stats(self) -> dict[str, Any]:
        """Get task queue statistics."""
        if not self._task_queue:
            return {"enabled": False}
        return self._task_queue.get_stats()

    def get_dead_letter_queue(self) -> list[dict[str, Any]]:
        """Get dead letter queue entries."""
        if not self._task_queue:
            return []
        return [e.to_dict() for e in self._task_queue.get_dead_letter_queue()]

    # ── P3: Health ─────────────────────────────────────────────────

    @property
    def health(self) -> HealthChecker | None:
        """Access the health checker."""
        return self._health

    # ── P4: Communication & Context ─────────────────────────────────

    def _get_or_create_transcript(self, session_id: str) -> SessionTranscript:
        """Get or create a SessionTranscript for a session."""
        if session_id not in self._transcripts:
            self._transcripts[session_id] = SessionTranscript(session_id=session_id)
        return self._transcripts[session_id]

    def get_channel(self, session_id: str) -> GroupChannel | None:
        """Get the GroupChannel for a session (P4)."""
        return self._channels.get(session_id)

    def get_transcript(self, session_id: str) -> SessionTranscript | None:
        """Get the SessionTranscript for a session (P4)."""
        return self._transcripts.get(session_id)

    def get_session_context(self, session_id: str, worker_id: str = "") -> str:
        """
        Get the full session context (P4).

        Workers can use this to understand what has happened
        in the session, like reading meeting minutes.

        Args:
            session_id: The session ID
            worker_id: Optional worker ID for personalized context

        Returns:
            Formatted context text
        """
        transcript = self._transcripts.get(session_id)
        if not transcript:
            return "(No context available yet)"

        if worker_id:
            return transcript.get_context_for_worker(worker_id)
        return transcript.get_summary()

    async def cleanup_session(self, session_id: str) -> None:
        """Clean up all session resources."""
        await self.conductor.cleanup_session(session_id)
        await self.bus.cleanup_session(session_id)
        await self.ring1.cleanup_session(session_id)
        # P4: Clean up transcript and channel
        self._transcripts.pop(session_id, None)
        self._channels.pop(session_id, None)

    async def shutdown(self) -> None:
        """Gracefully shut down the office."""
        # P3: Save office snapshot before shutdown
        if self._initialized and self.checkpoint:
            try:
                await self.checkpoint.save_office_snapshot(self)
                logger.info("Office snapshot saved before shutdown")
            except Exception as e:
                logger.warning(f"Failed to save office snapshot: {e}")

        # P3: Stop health checker
        if self._health:
            await self._health.stop()

        # P3: Stop task queue
        if self._task_queue:
            await self._task_queue.stop()

        await self.pool.stop()
        if self.cache:
            await self.cache.close()
        await self.ring1.close()
        await self.ring2.close()
        await self.ring3.close()
