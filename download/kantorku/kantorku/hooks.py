"""
Hooks — Callback system for kantorku.

Provides lifecycle hooks that users can register to inject custom
logic at key points in the orchestration flow.

Hook points:
- on_contract_created: After a contract is drafted
- on_contract_accepted: After client accepts a contract
- on_briefing_opened: When briefing room opens
- on_task_started: When a worker starts a task
- on_task_completed: When a worker completes a task
- on_task_failed: When a worker fails a task
- on_task_recovered: After a failed task is recovered
- on_verification_done: After verification completes
- on_work_done: When all work is complete
- on_error: On any unhandled error

Usage:
    from kantorku.hooks import Hooks, HookType

    hooks = Hooks()

    @hooks.on(HookType.ON_TASK_COMPLETED)
    async def log_completion(event):
        print(f"Task completed: {event['task_id']}")

    @hooks.on(HookType.ON_TASK_FAILED)
    async def on_failure(event):
        await send_alert(event['error'])

    office = Office(hooks=hooks)
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

logger = logging.getLogger("kantorku.hooks")


class HookType(enum.Enum):
    """Available hook points in the kantorku lifecycle."""
    ON_CONTRACT_CREATED = "on_contract_created"
    ON_CONTRACT_ACCEPTED = "on_contract_accepted"
    ON_CONTRACT_REVISED = "on_contract_revised"
    ON_BRIEFING_OPENED = "on_briefing_opened"
    ON_PLAN_DRAFTED = "on_plan_drafted"
    ON_PLAN_REVISED = "on_plan_revised"
    ON_TASK_ASSIGNED = "on_task_assigned"
    ON_TASK_STARTED = "on_task_started"
    ON_TASK_COMPLETED = "on_task_completed"
    ON_TASK_FAILED = "on_task_failed"
    ON_TASK_RECOVERED = "on_task_recovered"
    ON_TASK_TIMEOUT = "on_task_timeout"
    ON_WORKER_SPEAK_UP = "on_worker_speak_up"
    ON_WORKER_DM = "on_worker_dm"
    ON_CONTEXT_FETCHED = "on_context_fetched"
    ON_VERIFICATION_START = "on_verification_start"
    ON_VERIFICATION_DONE = "on_verification_done"
    ON_ERROR_LOGGED = "on_error_logged"
    ON_WORK_DONE = "on_work_done"
    ON_ERROR = "on_error"
    ON_LLM_CALL_START = "on_llm_call_start"
    ON_LLM_CALL_DONE = "on_llm_call_done"
    ON_LLM_STREAM_CHUNK = "on_llm_stream_chunk"


# Type alias for hook callback functions
HookCallback = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass
class HookEntry:
    """A registered hook with optional priority."""
    callback: HookCallback
    priority: int = 0  # Lower = runs first
    name: str = ""


class Hooks:
    """
    Callback/hook system for kantorku lifecycle events.

    Allows users to register async callbacks that fire at specific
    points during the orchestration flow. Hooks run in priority order.

    Usage:
        hooks = Hooks()

        # Decorator registration
        @hooks.on(HookType.ON_TASK_COMPLETED)
        async def my_hook(event):
            print(event)

        # Direct registration with priority
        hooks.register(HookType.ON_ERROR, alert_team, priority=1)

        # Triggering (internal — called by Office/Worker/etc)
        await hooks.trigger(HookType.ON_TASK_COMPLETED, {"task_id": "abc", "status": "done"})
    """

    def __init__(self) -> None:
        self._hooks: dict[HookType, list[HookEntry]] = {}

    def on(self, hook_type: HookType) -> Callable[[HookCallback], HookCallback]:
        """
        Decorator to register a hook callback.

        Usage:
            @hooks.on(HookType.ON_TASK_COMPLETED)
            async def my_callback(event):
                ...
        """
        def decorator(func: HookCallback) -> HookCallback:
            self.register(hook_type, func)
            return func
        return decorator

    def register(
        self,
        hook_type: HookType,
        callback: HookCallback,
        priority: int = 0,
        name: str = "",
    ) -> None:
        """
        Register a hook callback directly.

        Args:
            hook_type: Which lifecycle event to hook into
            callback: Async function that receives event dict
            priority: Execution order (lower runs first)
            name: Optional name for debugging
        """
        if hook_type not in self._hooks:
            self._hooks[hook_type] = []

        entry = HookEntry(
            callback=callback,
            priority=priority,
            name=name or callback.__name__,
        )
        self._hooks[hook_type].append(entry)

        # Keep sorted by priority
        self._hooks[hook_type].sort(key=lambda e: e.priority)

    def unregister(self, hook_type: HookType, callback: HookCallback) -> None:
        """Remove a previously registered hook callback."""
        if hook_type in self._hooks:
            self._hooks[hook_type] = [
                e for e in self._hooks[hook_type] if e.callback != callback
            ]

    async def trigger(self, hook_type: HookType, event: dict[str, Any]) -> None:
        """
        Trigger all callbacks registered for a hook point.

        Callbacks run in priority order. If a callback raises an exception,
        it is logged but does not prevent other callbacks from running.

        Args:
            hook_type: The lifecycle event that occurred
            event: Event data dict passed to all callbacks
        """
        entries = self._hooks.get(hook_type, [])

        for entry in entries:
            try:
                await entry.callback(event)
            except Exception as e:
                logger.error(
                    f"Hook callback '{entry.name}' for {hook_type.value} "
                    f"raised exception: {e}"
                )

    def list_hooks(self) -> dict[str, list[str]]:
        """List all registered hooks (for debugging)."""
        result = {}
        for hook_type, entries in self._hooks.items():
            result[hook_type.value] = [
                f"{e.name} (priority={e.priority})" for e in entries
            ]
        return result

    def clear(self, hook_type: HookType | None = None) -> None:
        """
        Clear registered hooks.

        Args:
            hook_type: If provided, clear only this type. Otherwise clear all.
        """
        if hook_type:
            self._hooks.pop(hook_type, None)
        else:
            self._hooks.clear()
