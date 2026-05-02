"""
BaseWorker — Foundation for all kantorku workers.

Every worker (coder, verifier, support) inherits from BaseWorker.
It handles:
- LLM calls via provider abstraction
- Event emission via EventBus
- Context retrieval from Ring 1
- Lifecycle management (idle → thinking → active → done)
"""

from __future__ import annotations

import asyncio
import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Awaitable, Callable

from kantorku.events.bus import EventBus
from kantorku.events.emitter import EventEmitter
from kantorku.worker.identity import WorkerIdentity
from kantorku.providers.router import ProviderRouter


class WorkerStatus(enum.Enum):
    """Worker lifecycle states."""
    IDLE = "idle"
    THINKING = "thinking"
    ACTIVE = "active"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Task:
    """A task assigned to a worker."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    instruction: str = ""
    session_id: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    parent_task_id: str | None = None
    priority: int = 0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "instruction": self.instruction,
            "session_id": self.session_id,
            "context": self.context,
            "parent_task_id": self.parent_task_id,
            "priority": self.priority,
            "created_at": self.created_at,
        }


@dataclass
class TaskResult:
    """Result from a completed task."""

    task_id: str = ""
    worker_id: str = ""
    status: str = "done"  # done | failed | needs_more_context
    output: str = ""
    files: list[str] = field(default_factory=list)
    error: str = ""
    context_query: str = ""  # For reactive context requests
    data: dict[str, Any] = field(default_factory=dict)


class BaseWorker:
    """
    Base class for all kantorku workers.

    Each worker is an INDEPENDENT AGENT with its own API.
    Workers are NOT just LLM wrappers — they have real APIs.

    Example: A design worker uses Gemini API, a debug worker uses Grok API.
    Each worker's API is configured in plugin.json under the "api" section.

    Subclasses override `handle(task)` to implement specific logic.
    The base class provides:
    - LLM calls via self.llm_call() — uses the worker's OWN API config
    - Direct API access via self.api_call() — for custom HTTP requests
    - Event emission via EventBus
    - Context retrieval from Ring 1
    - Lifecycle management (idle → thinking → active → done)

    Usage:
        class DesignerWorker(BaseWorker):
            async def handle(self, task: Task) -> TaskResult:
                # Uses this worker's OWN API (e.g. Gemini)
                response = await self.llm_call("Design a dashboard layout")
                return TaskResult(task_id=task.id, output=response)

        worker = DesignerWorker(identity=identity, router=router, bus=bus)
        result = await worker.execute(task)
    """

    def __init__(
        self,
        identity: WorkerIdentity,
        router: ProviderRouter,
        bus: EventBus,
    ) -> None:
        self.identity = identity
        self.router = router
        self.bus = bus
        self._status = WorkerStatus.IDLE
        self._emitter: EventEmitter | None = None
        self._ring1: Any = None  # Set by Office during initialization
        self._own_provider: Any = None  # Lazy-init'd provider from identity.api

    @property
    def id(self) -> str:
        return self.identity.id

    @property
    def model(self) -> str:
        """Full model string (provider/model) from this worker's OWN API config."""
        return self.identity.model

    @property
    def api(self):
        """This worker's OWN API configuration (WorkerAPI)."""
        return self.identity.api

    @property
    def squad(self) -> str:
        return self.identity.squad

    @property
    def role(self) -> str:
        return self.identity.role

    @property
    def status(self) -> WorkerStatus:
        return self._status

    def set_ring1(self, ring1: Any) -> None:
        """Set reference to Ring 1 memory (called by Office)."""
        self._ring1 = ring1

    def _get_emitter(self, session_id: str) -> EventEmitter:
        """Get or create an EventEmitter for a session."""
        return EventEmitter(self.bus, session_id)

    # Default timeout in seconds for task execution (0 = no timeout)
    DEFAULT_TASK_TIMEOUT: int = 300  # 5 minutes

    async def execute(self, task: Task, timeout: int | None = None) -> TaskResult:
        """
        Execute a task with full lifecycle management.
        Handles status transitions, event emission, and timeout.

        Args:
            task: The task to execute
            timeout: Maximum seconds to wait (0 or None = DEFAULT_TASK_TIMEOUT)

        Returns:
            TaskResult with status, output, and optional files/error
        """
        emitter = self._get_emitter(task.session_id)
        self._status = WorkerStatus.THINKING
        effective_timeout = timeout if timeout else self.DEFAULT_TASK_TIMEOUT

        try:
            # Emit task_started
            await emitter.task_started(from_id=self.id)
            self._status = WorkerStatus.ACTIVE

            # Call subclass implementation with timeout
            if effective_timeout > 0:
                result = await asyncio.wait_for(
                    self.handle(task),
                    timeout=effective_timeout,
                )
            else:
                result = await self.handle(task)

            # Emit appropriate completion event
            if result.status == "done":
                self._status = WorkerStatus.DONE
                await emitter.task_done(from_id=self.id, files=result.files)
            elif result.status == "failed":
                self._status = WorkerStatus.FAILED
                await emitter.task_failed(from_id=self.id, error=result.error)
            elif result.status == "needs_more_context":
                # Worker needs more context — don't mark as done
                self._status = WorkerStatus.THINKING

            result.worker_id = self.id
            result.task_id = task.id
            return result

        except asyncio.TimeoutError:
            self._status = WorkerStatus.FAILED
            error_msg = f"Task timed out after {effective_timeout}s"
            await emitter.task_failed(from_id=self.id, error=error_msg)
            return TaskResult(
                task_id=task.id,
                worker_id=self.id,
                status="failed",
                error=error_msg,
            )

        except Exception as e:
            self._status = WorkerStatus.FAILED
            await emitter.task_failed(from_id=self.id, error=str(e))
            return TaskResult(
                task_id=task.id,
                worker_id=self.id,
                status="failed",
                error=str(e),
            )

    async def handle(self, task: Task) -> TaskResult:
        """
        Override this in subclasses to implement worker logic.

        Returns:
            TaskResult with status, output, and optional files/error.
        """
        raise NotImplementedError(f"Worker {self.id} must implement handle()")

    def _ensure_own_provider(self) -> None:
        """
        Lazily create this worker's OWN provider from its API config.

        If the worker has its own api_key configured (in plugin.json),
        we create a dedicated provider instance just for this worker.
        This means each worker can use a DIFFERENT API key and even
        a DIFFERENT provider than the global router config.
        """
        if self._own_provider is not None:
            return

        from kantorku.worker.identity import WorkerAPI
        api = self.identity.api
        if not api.provider or not api.model:
            return

        # Resolve env vars
        resolved = api.resolve_env_vars()

        # Check if the router already has this provider configured
        # If yes AND the worker doesn't have its own api_key, reuse it
        if not resolved.api_key and api.provider in self.router._providers:
            self._own_provider = self.router._providers[api.provider]
            return

        # Worker has its own API key — create a dedicated provider
        try:
            provider_cls = self.router.PROVIDER_MAP.get(api.provider)
            if provider_cls is None:
                return  # Unknown provider, will fall back to router

            kwargs: dict[str, Any] = {}
            if resolved.api_key:
                kwargs["api_key"] = resolved.api_key
            if resolved.base_url:
                kwargs["base_url"] = resolved.base_url
            kwargs.update(resolved.extra)

            self._own_provider = provider_cls(**kwargs)
        except Exception:
            pass  # Fall back to global router

    async def llm_call(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Make an LLM call using THIS worker's own API configuration.

        Each worker uses its OWN API key and provider. For example:
        - verifier_designer → calls Gemini API with Google key
        - debugger → calls Grok API with xAI key
        - coder_wiring → calls Codex API with OpenAI key

        Falls back to the global provider router if no worker-specific API is set.

        Args:
            prompt: User message content
            system: Optional system prompt (defaults to SKILL.md)
            model: Override model (defaults to worker's API config)
            **kwargs: Additional provider-specific parameters

        Returns:
            The LLM response text
        """
        messages: list[dict[str, str]] = []
        sys = system or self.identity.skill_md
        if sys:
            messages.append({"role": "system", "content": sys})
        messages.append({"role": "user", "content": prompt})

        # Try worker's own provider first
        self._ensure_own_provider()
        if self._own_provider is not None:
            model_name = model or self.identity.api.model or self.model
            # Strip provider prefix if present
            if "/" in model_name:
                model_name = model_name.split("/", 1)[1]
            return await self._own_provider.complete(
                model=model_name,
                messages=messages,
                **kwargs,
            )

        # Fall back to global router
        model_name = model or self.model
        return await self.router.complete(
            model=model_name,
            messages=messages,
            **kwargs,
        )

    async def api_call(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> Any:
        """
        Make a direct HTTP API call using this worker's own API key.

        Use this for non-LLM API calls, like:
        - Image generation APIs (DALL-E, Midjourney, Stable Diffusion)
        - Web search APIs (Tavily, SerpAPI)
        - Code execution APIs (E2B, CodeSandbox)
        - Any REST API

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Full URL to call
            **kwargs: Passed to httpx (json, headers, params, etc.)

        Returns:
            Parsed JSON response or raw text
        """
        import httpx

        headers = kwargs.pop("headers", {})
        resolved = self.identity.api.resolve_env_vars()

        # Auto-inject API key as Bearer token
        if resolved.api_key and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {resolved.api_key}"

        # Auto-inject Content-Type
        if "Content-Type" not in headers and "json" in kwargs:
            headers["Content-Type"] = "application/json"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                headers=headers,
                **kwargs,
            )
            response.raise_for_status()

            try:
                return response.json()
            except Exception:
                return response.text

    async def llm_call_stream(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        session_id: str = "",
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Make a streaming LLM call — yields token chunks.
        Also emits llm_stream_start, llm_stream_chunk, llm_stream_done
        events to the session's EventBus channel.

        Args:
            prompt: User message content
            system: Optional system prompt (defaults to skill_md)
            model: Override model (defaults to worker's assigned model)
            session_id: Session ID for event emission
            **kwargs: Additional provider-specific parameters

        Yields:
            Token chunks as they arrive
        """
        messages: list[dict[str, str]] = []
        sys = system or self.identity.skill_md
        if sys:
            messages.append({"role": "system", "content": sys})
        messages.append({"role": "user", "content": prompt})

        model_name = model or self.model
        emitter = self._get_emitter(session_id) if session_id else None

        if emitter:
            await emitter.llm_stream_start(from_id=self.id, model=model_name)

        full_text_parts: list[str] = []

        async for chunk in self.router.complete_stream(
            model=model_name,
            messages=messages,
            **kwargs,
        ):
            full_text_parts.append(chunk)
            if emitter:
                await emitter.llm_stream_chunk(from_id=self.id, chunk=chunk, model=model_name)
            yield chunk

        if emitter:
            await emitter.llm_stream_done(
                from_id=self.id, model=model_name, full_text="".join(full_text_parts)
            )

    async def llm_call_structured(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make an LLM call and parse the response as structured JSON.
        Falls back to raw text if parsing fails.
        """
        import json

        response = await self.llm_call(prompt, system, model, **kwargs)
        try:
            # Try to extract JSON from response
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {"raw_response": response}

    async def get_context(self, task_id: str) -> dict[str, Any] | None:
        """Get prefetched context from Ring 1 for a task."""
        if self._ring1:
            return await self._ring1.get_context(task_id)
        return None

    async def speak_up(self, task: Task, plan: dict[str, Any]) -> dict[str, Any]:
        """
        Called during BriefingRoom — worker shares concerns or suggestions.
        Override in subclasses for custom briefing behavior.
        """
        prompt = f"""
        Task: {task.instruction}

        Current plan: {plan}

        You are {self.id} ({self.role}).
        Do you have any concerns, questions, or suggestions about this plan?
        Consider your specific expertise and what might be needed.

        Respond with JSON:
        {{
            "has_input": true/false,
            "concern": "your concern or suggestion (if any)",
            "suggestion": "what you'd suggest instead (if any)"
        }}
        """
        result = await self.llm_call_structured(prompt)
        return {
            "worker_id": self.id,
            "has_input": result.get("has_input", False),
            "concern": result.get("concern", ""),
            "suggestion": result.get("suggestion", ""),
        }

    async def receive_dm(self, from_id: str, message: str) -> dict[str, Any]:
        """
        Receive a direct message from another worker.
        Override for custom DM behavior.
        """
        prompt = f"""
        Worker {from_id} sent you a direct message:
        "{message}"

        You are {self.id} ({self.role}).
        Respond appropriately. If this is a blocker, mark it.

        Respond with JSON:
        {{
            "response": "your response",
            "is_blocker": true/false
        }}
        """
        result = await self.llm_call_structured(prompt)
        return {
            "response": result.get("raw_response", str(result)),
            "is_blocker": result.get("is_blocker", False),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "model": self.model,
            "squad": self.squad,
            "role": self.role,
            "status": self._status.value,
            "capabilities": self.identity.capabilities,
        }
