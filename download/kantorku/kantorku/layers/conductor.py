"""
Conductor — CEO of the kantorku office.

The Conductor is the orchestrator:
- Understands client messages (multi-turn clarification)
- Drafts contracts (structured todo lists)
- Conducts work (briefing → assign → verify → done)
- Recovers from failures

It uses the conductor_model (Claude Opus by default) for decision-making.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator

from kantorku.providers.router import ProviderRouter
from kantorku.events.bus import EventBus
from kantorku.events.emitter import EventEmitter
from kantorku.worker.base import Task


class ContractState(Enum):
    """State machine for Panel 1 (client ↔ manager interaction)."""
    IDLE = "idle"
    MANAGER_THINKING = "manager_thinking"
    CLARIFYING = "clarifying"
    CONTRACT_PRESENTED = "contract_presented"
    WORKING = "working"
    DONE = "done"


@dataclass
class TodoItem:
    """A single todo item in a contract."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    description: str = ""
    assigned_to: str = ""
    status: str = "pending"  # pending | in_progress | done | failed
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "status": self.status,
            "depends_on": self.depends_on,
        }


@dataclass
class Contract:
    """
    A contract between client and office.

    Contains the structured todo list that the client agrees to.
    After acceptance, the Conductor orchestrates execution.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    session_id: str = ""
    title: str = ""
    description: str = ""
    todos: list[TodoItem] = field(default_factory=list)
    state: ContractState = ContractState.IDLE
    client_messages: list[dict[str, str]] = field(default_factory=list)
    manager_messages: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "title": self.title,
            "description": self.description,
            "todos": [t.to_dict() for t in self.todos],
            "state": self.state.value,
        }


SYSTEM_PROMPT_UNDERSTAND = """You are the Manager (Conductor) of kantorku — a digital office.

Your job is to understand what the client wants. You can:
1. Ask clarifying questions if the request is ambiguous
2. Draft a contract when you have enough information

A contract should be specific and actionable. Break it into clear todo items.
Each todo should be something a specific worker can execute.

When you're ready to present a contract, respond with JSON:
```json
{
  "type": "contract",
  "title": "...",
  "description": "...",
  "todos": [
    {"description": "...", "assigned_to": "suggested_worker_id"},
    ...
  ]
}
```

When you need clarification, respond normally (not JSON).
Be professional but friendly. You're the bridge between client and team.
"""

SYSTEM_PROMPT_CONDUCT = """You are the Conductor (CEO) of kantorku — orchestrating the team.

You have access to:
- BriefingRoom: Discuss plan with workers before execution
- WorkerHub: Direct message workers, get status
- ContextPool: Prefetch context for tasks
- Worker Registry: Hire and assign workers

Your orchestration flow:
1. Open briefing with relevant workers
2. Listen to worker concerns, revise plan if needed
3. Assign tasks to workers (can be parallel)
4. Monitor progress, handle blockers
5. Run verification after coding
6. Log lessons learned

Decision framework:
- Which workers are needed for this task?
- What context should be prefetched?
- Can tasks run in parallel?
- What verification is needed?

Always be decisive. If a worker hits a blocker, either resolve it
or reassign. The goal is to deliver quality output efficiently.
"""


class Conductor:
    """
    Conductor — the CEO of kantorku.

    Handles two main flows:
    1. understand_client(): Multi-turn chat → contract (Panel 1)
    2. conduct(): Orchestrate work after contract acceptance (Panel 2)

    Usage:
        conductor = Conductor(router=router, bus=bus, model="anthropic/claude-opus-4-6")

        # Panel 1 flow
        async for event in conductor.understand_client(session_id, "Buat rate limiter"):
            await ws.send_json(event)

        # Panel 2 flow (after contract accepted)
        await conductor.conduct(session_id, contract)
    """

    def __init__(
        self,
        router: ProviderRouter,
        bus: EventBus,
        model: str = "anthropic/claude-opus-4-6",
    ) -> None:
        self.router = router
        self.bus = bus
        self.model = model
        self._sessions: dict[str, dict[str, Any]] = {}

    def _get_or_create_session(self, session_id: str) -> dict[str, Any]:
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "contract": Contract(session_id=session_id),
                "state": ContractState.IDLE,
                "messages": [],
            }
        return self._sessions[session_id]

    async def understand_client(
        self,
        session_id: str,
        message: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Process a client message in the understanding phase.
        Yields events for Panel 1 (manager messages or contract).

        This handles multi-turn clarification until a contract is ready.
        """
        session = self._get_or_create_session(session_id)
        contract = session["contract"]
        emitter = EventEmitter(self.bus, session_id)

        # Update state
        session["state"] = ContractState.MANAGER_THINKING

        # Build conversation history
        contract.client_messages.append({"role": "user", "content": message})

        messages = [{"role": "system", "content": SYSTEM_PROMPT_UNDERSTAND}]
        for msg in contract.client_messages:
            messages.append(msg)
        for msg in contract.manager_messages:
            messages.append(msg)

        # Call conductor LLM
        response = await self.router.complete(
            model=self.model,
            messages=messages,
            temperature=0.7,
        )

        # Check if response contains a contract
        contract_data = self._try_parse_contract(response)

        if contract_data:
            # Contract is ready!
            session["state"] = ContractState.CONTRACT_PRESENTED
            contract.title = contract_data.get("title", "")
            contract.description = contract_data.get("description", "")

            for todo_data in contract_data.get("todos", []):
                contract.todos.append(TodoItem(
                    description=todo_data.get("description", ""),
                    assigned_to=todo_data.get("assigned_to", ""),
                ))

            yield {"type": "contract_ready", "contract": contract.to_dict()}
            await emitter.contract_ready(todos=[t.to_dict() for t in contract.todos])
        else:
            # Clarification needed
            session["state"] = ContractState.CLARIFYING
            contract.manager_messages.append({"role": "assistant", "content": response})

            yield {"type": "manager_message", "content": response}
            await emitter.manager_message(content=response)

    async def revise_contract(
        self,
        session_id: str,
        feedback: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Revise a contract based on client feedback.
        """
        session = self._get_or_create_session(session_id)
        contract = session["contract"]
        emitter = EventEmitter(self.bus, session_id)

        session["state"] = ContractState.MANAGER_THINKING
        contract.client_messages.append({
            "role": "user",
            "content": f"[REVISION REQUEST] {feedback}",
        })

        messages = [{"role": "system", "content": SYSTEM_PROMPT_UNDERSTAND}]
        for msg in contract.client_messages:
            messages.append(msg)
        for msg in contract.manager_messages:
            messages.append(msg)

        response = await self.router.complete(
            model=self.model,
            messages=messages,
            temperature=0.7,
        )

        # Try to parse revised contract
        contract_data = self._try_parse_contract(response)

        if contract_data:
            # Revised contract ready
            session["state"] = ContractState.CONTRACT_PRESENTED
            contract.title = contract_data.get("title", contract.title)
            contract.description = contract_data.get("description", contract.description)
            contract.todos = []
            for todo_data in contract_data.get("todos", []):
                contract.todos.append(TodoItem(
                    description=todo_data.get("description", ""),
                    assigned_to=todo_data.get("assigned_to", ""),
                ))

            yield {"type": "contract_ready", "contract": contract.to_dict()}
            await emitter.contract_ready(todos=[t.to_dict() for t in contract.todos])
        else:
            session["state"] = ContractState.CLARIFYING
            contract.manager_messages.append({"role": "assistant", "content": response})
            yield {"type": "manager_message", "content": response}
            await emitter.manager_message(content=response)

    def get_contract(self, session_id: str) -> Contract | None:
        """Get the current contract for a session."""
        session = self._sessions.get(session_id)
        return session["contract"] if session else None

    def get_state(self, session_id: str) -> ContractState:
        """Get the current state for a session."""
        session = self._sessions.get(session_id)
        return session["state"] if session else ContractState.IDLE

    def mark_working(self, session_id: str) -> None:
        """Mark session as WORKING after contract acceptance."""
        session = self._sessions.get(session_id)
        if session:
            session["state"] = ContractState.WORKING

    def mark_done(self, session_id: str) -> None:
        """Mark session as DONE after all work complete."""
        session = self._sessions.get(session_id)
        if session:
            session["state"] = ContractState.DONE

    async def draft_plan(self, contract: Contract) -> dict[str, Any]:
        """
        Draft an execution plan from a contract.
        Determines which workers are needed and what to prefetch.
        """
        prompt = f"""
        Contract: {contract.title}
        Description: {contract.description}

        Todos:
        {json.dumps([t.to_dict() for t in contract.todos], indent=2)}

        Create an execution plan:
        1. Which workers are needed?
        2. What context should be prefetched for each todo?
        3. Which todos can run in parallel?
        4. What verification is needed?

        Respond with JSON:
        {{
            "relevant_workers": ["worker_id", ...],
            "prefetch_queries": {{"todo_id": "query", ...}},
            "parallel_groups": [["todo_id1", "todo_id2"], ...],
            "verification_needed": ["verifier_designer", "verifier_engineer"],
            "execution_order": ["todo_id", ...]
        }}
        """
        result = await self.router.complete(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_CONDUCT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
        )

        try:
            text = result.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {
                "relevant_workers": [t.assigned_to for t in contract.todos if t.assigned_to],
                "prefetch_queries": {t.id: t.description for t in contract.todos},
                "parallel_groups": [[t.id for t in contract.todos]],
                "verification_needed": ["verifier_engineer"],
                "execution_order": [t.id for t in contract.todos],
            }

    async def recover_from_failure(
        self,
        session_id: str,
        failed_task: Task,
        error: str,
    ) -> dict[str, Any]:
        """
        Handle a task failure. Decide whether to retry, reassign, or abort.
        """
        prompt = f"""
        Task failed:
        - Task: {failed_task.instruction}
        - Worker: {failed_task.context.get("assigned_to", "unknown")}
        - Error: {error}

        Decide recovery strategy:
        1. retry_same — Same worker tries again with adjusted approach
        2. reassign — Give to a different worker
        3. simplify — Break into smaller subtasks
        4. abort — Cannot complete, notify client

        Respond with JSON:
        {{
            "strategy": "retry_same|reassign|simplify|abort",
            "reason": "...",
            "new_worker": "worker_id (if reassign)",
            "subtasks": ["..."] (if simplify)
        }}
        """
        result = await self.router.complete(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_CONDUCT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        try:
            text = result.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {"strategy": "retry_same", "reason": "Default retry"}

    def _try_parse_contract(self, text: str) -> dict[str, Any] | None:
        """Try to extract contract JSON from LLM response."""
        try:
            # Look for JSON block
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
            else:
                json_str = text.strip()

            data = json.loads(json_str)
            if data.get("type") == "contract" and "todos" in data:
                return data
        except (json.JSONDecodeError, IndexError):
            pass
        return None

    async def notify_blocker(
        self,
        from_id: str,
        to_id: str,
        details: dict[str, Any],
        session_id: str = "",
    ) -> None:
        """
        Handle a blocker reported via WorkerHub DM.
        The Conductor decides whether to intervene, reassign, or escalate.
        """
        emitter = EventEmitter(self.bus, session_id) if session_id else None

        if emitter:
            await emitter.worker_broadcast(
                from_id="conductor",
                content=f"Blocker reported: {from_id} ↔ {to_id}: {details.get('response', '')}",
            )

        # Decide recovery strategy
        # In a full implementation, this would use the LLM to decide
        # For now, log the blocker for manual intervention
        strategy = details.get("response", "Unknown blocker")

        if emitter:
            await emitter.manager_message(
                content=f"Blocker detected: {strategy}. Conductor reviewing."
            )

    async def cleanup_session(self, session_id: str) -> None:
        """Clean up session data."""
        self._sessions.pop(session_id, None)
