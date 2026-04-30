"""
Office — Main entry point for kantorku.

The Office is to kantorku what Crew is to CrewAI or StateGraph is to LangGraph.
It orchestrates everything: workers, conductor, briefing room, context pool, memory.

Usage:
    # From config file
    office = Office.from_config("kantorku.toml")
    result = await office.run("Buat rate limiter di Rust")

    # Programmatic
    office = Office(
        conductor_model="anthropic/claude-opus-4-6",
    )
    office.configure_provider("anthropic", api_key="sk-...")
    office.hire_worker("coder_backend", model="minimax/minimax-m2-7")
    result = await office.run("Implement authentication")
"""

from __future__ import annotations

import asyncio
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
from kantorku.pool.context_pool import ContextPool
from kantorku.memory.ring1 import Ring1Memory
from kantorku.memory.ring2 import Ring2Memory
from kantorku.memory.ring3 import Ring3Memory
from kantorku.providers.router import ProviderRouter
from kantorku.worker.base import BaseWorker, Task, TaskResult
from kantorku.worker.registry import WorkerRegistry


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
    ) -> None:
        self.config = config or KantorkuConfig(conductor_model=conductor_model)
        self.hooks = hooks or Hooks()

        # Core infrastructure
        self.bus = EventBus()
        self.router = ProviderRouter()

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

        self._initialized = False

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
    ) -> None:
        """
        Register a worker with the office.

        Args:
            worker_id: Unique identifier (e.g. "coder_backend")
            model: LLM model assignment
            squad: Squad membership
            role: Role description
            skill_md: Skill description (injected into system prompt)
            worker_class: Optional custom worker class
        """
        from kantorku.worker.identity import WorkerIdentity

        identity = WorkerIdentity.from_dict({
            "id": worker_id,
            "model": model,
            "squad": squad,
            "role": role,
            "skill_md": skill_md,
        })
        self.registry.register_identity(identity)

        if worker_class:
            self.registry.register_worker_class(worker_id, worker_class)

    async def initialize(self) -> None:
        """
        Initialize all office systems.

        Must be called before any other operations.
        Sets up memory, pool, providers, and worker instances.
        """
        if self._initialized:
            return

        # Configure providers from config
        self.router.configure_from_dict(self.config.providers)

        # Register workers from config
        workers_config = {
            wid: {"model": w.model, "squad": w.squad, "role": w.role}
            for wid, w in self.config.workers.items()
        }
        self.registry.register_from_config(workers_config)

        # Discover workers from workers/ directory
        workers_dir = Path(__file__).parent.parent / "workers"
        if workers_dir.exists():
            self.registry.discover_workers(workers_dir)

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
        )
        # Resolve intake model safely
        intake_worker_cfg = self.config.workers.get("intake")
        intake_model = intake_worker_cfg.model if intake_worker_cfg else "ollama/llama3"
        self.intake = Intake(
            router=self.router,
            bus=self.bus,
            model=intake_model,
        )

        # Start context pool
        # Inject router into pool workers
        for pw in self.pool.instances:
            pw.router = self.router
        await self.pool.start()

        self._initialized = True

    async def chat(
        self,
        session_id: str,
        message: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Chat with the Conductor (Panel 1 flow).

        Yields events: manager_message or contract_ready.
        Multi-turn — call repeatedly until contract_ready appears.

        Args:
            session_id: Unique session identifier
            message: User message

        Yields:
            Event dictionaries
        """
        if not self._initialized:
            await self.initialize()

        # Optional: Run through Intake first
        if self.intake:
            intake_result = await self.intake.parse(message, session_id)
            # Store intake data in session for Conductor to use
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
        """
        Revise the current contract based on client feedback.

        Args:
            session_id: Session identifier
            feedback: Client's revision request

        Yields:
            Event dictionaries
        """
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

        Args:
            session_id: Session identifier

        Returns:
            Complete result with all task outputs
        """
        if not self._initialized:
            await self.initialize()

        contract = self.conductor.get_contract(session_id)
        if not contract:
            return {"error": "No contract found for this session"}

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

        Args:
            message: Task description
            session_id: Optional session ID (auto-generated if not provided)
            auto_accept: If True, auto-accept the contract without asking

        Returns:
            Complete result dictionary
        """
        if not self._initialized:
            await self.initialize()

        session_id = session_id or uuid.uuid4().hex[:12]

        # Chat until contract is ready
        contract_data = None
        async for event in self.chat(session_id, message):
            if event.get("type") == "contract_ready":
                contract_data = event
            elif event.get("type") == "manager_message":
                # If auto_accept, we need to provide more info
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
        Full orchestration: brief → assign → execute → verify → done.
        """
        emitter = EventEmitter(self.bus, session_id)

        # 1. Conductor drafts plan
        plan = await self.conductor.draft_plan(contract)
        await emitter.plan_drafted(from_id="conductor", content=str(plan))

        # 2. Briefing room — workers discuss + prefetch starts
        briefing_result = await self.briefing_room.open(
            contract=contract,
            plan=plan,
            session_id=session_id,
        )
        final_plan = briefing_result.plan

        # 3. Execute tasks based on plan
        execution_order = final_plan.get("execution_order", [t.id for t in contract.todos])
        parallel_groups = final_plan.get("parallel_groups", [execution_order])
        results: dict[str, TaskResult] = {}

        for group in parallel_groups:
            # Execute group in parallel
            group_tasks = []
            for todo_id in group:
                todo = next((t for t in contract.todos if t.id == todo_id), None)
                if not todo:
                    continue

                assigned_to = todo.assigned_to or self._assign_worker(todo, final_plan)
                worker = self.registry.hire(assigned_to) if assigned_to else None

                if worker:
                    task = Task(
                        instruction=todo.description,
                        session_id=session_id,
                        context={
                            "contract": contract.to_dict(),
                            "todo": todo.to_dict(),
                            "assigned_to": assigned_to,
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
                        # Task threw an exception — attempt recovery
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
                        # If task returned failed status, attempt recovery
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

        # Ask Conductor for recovery strategy
        recovery = await self.conductor.recover_from_failure(session_id, task, error)
        strategy = recovery.get("strategy", "retry_same")

        if strategy == "retry_same":
            # Retry with the same worker
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
            # Reassign to a different worker
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
            # Break into subtasks
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

                # Combine subtask results
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
        # Check plan for explicit assignment
        for group in plan.get("parallel_groups", []):
            if todo.id in group:
                # Find relevant worker from plan
                relevant = plan.get("relevant_workers", [])
                if relevant:
                    return relevant[0]

        # Fallback: assign based on description keywords
        desc = todo.description.lower()
        if any(k in desc for k in ["ui", "frontend", "react", "css", "component"]):
            return "coder_frontend"
        if any(k in desc for k in ["api", "websocket", "integration", "mcp", "glue"]):
            return "coder_wiring"
        return "coder_backend"  # Default

    def get_events(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent events for a session."""
        return self.bus.get_history(session_id, limit)

    def get_worker_status(self) -> list[dict[str, Any]]:
        """Get status of all workers."""
        return self.registry.list_workers()

    def get_pool_status(self) -> dict[str, Any]:
        """Get context pool status."""
        return self.pool.get_status()

    async def cleanup_session(self, session_id: str) -> None:
        """Clean up all session resources."""
        await self.conductor.cleanup_session(session_id)
        await self.bus.cleanup_session(session_id)
        await self.ring1.cleanup_session(session_id)

    async def shutdown(self) -> None:
        """Gracefully shut down the office."""
        await self.pool.stop()
        await self.ring1.close()
        await self.ring2.close()
        await self.ring3.close()
