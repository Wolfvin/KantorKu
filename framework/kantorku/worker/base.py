"""
BaseWorker — Foundation for all kantorku workers.

Every worker (coder, verifier, support) inherits from BaseWorker.
It handles:
- LLM calls via provider abstraction (with AutoTune + STM integration)
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
from typing import Any, AsyncIterator, Awaitable, Callable, Protocol, runtime_checkable

from kantorku.events.bus import EventBus
from kantorku.events.emitter import EventEmitter
from kantorku.worker.identity import WorkerIdentity
from kantorku.providers.router import ProviderRouter


# ── Protocol classes for type-safe dependency injection ─────────────


@runtime_checkable
class Ring1Protocol(Protocol):
    """Protocol for Ring1 memory — provides context storage and retrieval."""

    async def get_context(self, task_id: str) -> dict[str, Any] | None: ...
    async def store_context(self, task_id: str, context: dict[str, Any]) -> None: ...


@runtime_checkable
class ProviderProtocol(Protocol):
    """Protocol for LLM providers — supports complete, stream, and usage."""

    async def complete(self, model: str, messages: list[dict[str, str]], **kwargs: Any) -> str: ...
    async def complete_stream(self, model: str, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[str]: ...
    async def complete_with_usage(self, model: str, messages: list[dict[str, str]], **kwargs: Any) -> tuple[str, dict[str, Any]]: ...


@runtime_checkable
class AutoTuneProtocol(Protocol):
    """Protocol for AutoTune engine — context-adaptive sampling."""

    def analyze(self, text: str, history: list[str] | list[dict[str, str]] | None = None, strategy: str | None = None, worker_id: str = "") -> Any: ...
    def filter_params_for_provider(self, params: Any, provider: str) -> dict[str, Any]: ...


@runtime_checkable
class STMProtocol(Protocol):
    """Protocol for STM engine — semantic transformation of output."""

    def transform(self, text: str, modules: list[Any] | None = None) -> Any: ...


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
      with AutoTune (adaptive sampling) + STM (output normalization)
      + per-session conversation memory (history injection)
    - Direct API access via self.api_call() — for custom HTTP requests
    - Event emission via EventBus
    - Context retrieval from Ring 1
    - Lifecycle management (idle → thinking → active → done)

    Conversation Memory:
    Workers remember their own exchanges within a session via _conv_history.
    Each llm_call() injects previous messages for that session, so the LLM
    sees its own prior work. This is separate from task.context (which
    carries cross-worker session state) and Ring1 (which carries
    prefetched codebase context).

    Usage:
        class DesignerWorker(BaseWorker):
            async def handle(self, task: Task) -> TaskResult:
                # Uses this worker's OWN API (e.g. Gemini)
                response = await self.llm_call("Design a dashboard layout",
                                               session_id=task.session_id)
                return TaskResult(task_id=task.id, output=response)

        worker = DesignerWorker(identity=identity, router=router, bus=bus)
        result = await worker.execute(task)
    """

    # Maximum messages per session conversation history (10 exchanges = 20 msgs)
    MAX_CONVERSATION_HISTORY: int = 20

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
        self._ring1: Ring1Protocol | None = None  # Set by Office during initialization
        self._own_provider: ProviderProtocol | None = None  # Lazy-init'd provider from identity.api

        # AutoTune — context-adaptive sampling (initialized lazily on first use)
        self._autotune: AutoTuneProtocol | None = None  # AutoTune instance, lazy-init'd

        # STM — Semantic Transformation Modules (initialized lazily on first use)
        self._stm: STMProtocol | None = None  # STMEngine instance, lazy-init'd

        # Per-session conversation memory
        # Key: session_id, Value: list of {"role": "user"|"assistant", "content": ...}
        # Workers remember their own exchanges within a session so the LLM
        # sees what it did previously (Fix 2 — worker conversation memory)
        self._conv_history: dict[str, list[dict[str, str]]] = {}
        self._current_session_id: str = ""  # Set by execute() before handle()

        # Worker personality — when to speak, when to stay quiet
        # Loaded from plugin.json "personality" section
        from kantorku.worker.personality import WorkerPersonality
        personality_config = identity.plugin_data.get("personality", {})
        self.personality = WorkerPersonality(personality_config)

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

    def set_ring1(self, ring1: Ring1Protocol) -> None:
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

            # Set current session so llm_call() can track conversation history
            self._current_session_id = task.session_id

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

    def _ensure_autotune(self) -> None:
        """Lazily initialize AutoTune engine for this worker."""
        if self._autotune is not None:
            return
        try:
            from kantorku.redteam.autotune import AutoTune
            self._autotune = AutoTune(worker_id=self.id)
        except ImportError:
            pass  # AutoTune not available

    def _ensure_stm(self) -> None:
        """Lazily initialize STM engine for this worker."""
        if self._stm is not None:
            return
        try:
            from kantorku.redteam.stm import STMEngine
            self._stm = STMEngine()
        except ImportError:
            pass  # STM not available

    def _get_history_texts(self) -> list[dict[str, str]]:
        """Get recent conversation history for AutoTune context analysis."""
        if self._ring1:
            try:
                # Ring1.get_history returns list[dict[str, str]]
                # We'll call this synchronously since DuckDB is sync
                # In practice, Office should set _history_cache
                pass
            except Exception:
                pass
        return []

    async def llm_call(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        session_id: str = "",
        **kwargs: Any,
    ) -> str:
        """
        Make an LLM call using THIS worker's own API configuration.

        Each worker uses its OWN API key and provider. For example:
        - verifier_designer → calls Gemini API with Google key
        - debugger → calls DeepSeek API with DeepSeek key
        - coder_wiring → calls Google API with Google key

        Pipeline:
        1. Build messages (system + conversation history + current prompt)
        2. AutoTune → select optimal temperature/params (if not overridden)
        3. Call provider → get raw LLM response
        4. Store exchange in conversation history (per-session memory)
        5. STM → normalize output (strip hedging/preambles), unless disabled

        Falls back to the global provider router if no worker-specific API is set.

        Args:
            prompt: User message content
            system: Optional system prompt (defaults to SKILL.md)
            model: Override model (defaults to worker's API config)
            session_id: Session ID for conversation memory injection.
                        Falls back to self._current_session_id (set by execute()).
            **kwargs: Additional provider-specific parameters

        Returns:
            The LLM response text (STM-transformed if enabled)
        """
        # Resolve session ID — explicit param takes priority, then _current_session_id
        sid = session_id or self._current_session_id

        # Build messages: system → conversation history → current prompt
        messages: list[dict[str, str]] = []
        sys = system or self.identity.skill_md
        if sys:
            messages.append({"role": "system", "content": sys})

        # Inject conversation history for this session
        # Workers remember their own exchanges so the LLM sees what it did before
        if sid and sid in self._conv_history:
            messages.extend(self._conv_history[sid])

        messages.append({"role": "user", "content": prompt})

        # AutoTune — select optimal sampling params if not manually set
        if "temperature" not in kwargs:
            self._ensure_autotune()
            if self._autotune is not None:
                try:
                    history_texts = self._get_history_texts()
                    result = self._autotune.analyze(
                        text=prompt,
                        history=history_texts or None,
                        worker_id=self.id,
                    )
                    # Apply only provider-supported parameters
                    provider_name = self.identity.api.provider
                    filtered = self._autotune.filter_params_for_provider(
                        result.params, provider_name
                    )
                    kwargs.update(filtered)
                except Exception:
                    pass  # AutoTune failure is non-fatal

        # Try worker's own provider first, fall back to global router on failure
        self._ensure_own_provider()
        response: str | None = None
        model_name = model or self.model
        if self._own_provider is not None:
            own_model = self.identity.api.model or self.model
            # Strip provider prefix if present
            if "/" in own_model:
                own_model = own_model.split("/", 1)[1]
            try:
                response = await self._own_provider.complete(
                    model=own_model,
                    messages=messages,
                    **kwargs,
                )
            except Exception:
                # Own provider failed — fall back to global router
                response = None

        if response is None:
            # Fall back to global router
            model_name = model or self.model
            response = await self.router.complete(
                model=model_name,
                messages=messages,
                **kwargs,
            )

        # Store exchange in conversation history (raw, before STM)
        # This lets the LLM see its own prior work on subsequent calls
        if sid:
            if sid not in self._conv_history:
                self._conv_history[sid] = []
            self._conv_history[sid].append({"role": "user", "content": prompt})
            self._conv_history[sid].append({"role": "assistant", "content": response})
            # Trim to max history — keep most recent exchanges
            if len(self._conv_history[sid]) > self.MAX_CONVERSATION_HISTORY:
                self._conv_history[sid] = self._conv_history[sid][-self.MAX_CONVERSATION_HISTORY:]

        # STM — normalize worker output (strip hedging/preambles)
        # Skip for conductor (needs to stay conversational with client)
        stm_enabled = self.identity.plugin_data.get("stm_enabled", True)
        if stm_enabled:
            self._ensure_stm()
            if self._stm is not None:
                try:
                    transformed = self._stm.transform(response)
                    return transformed.transformed
                except Exception:
                    pass  # STM failure is non-fatal — return raw response

        return response

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

        Uses worker's own provider (like llm_call), falls back to router.
        Injects conversation history for the session, just like llm_call().

        Args:
            prompt: User message content
            system: Optional system prompt (defaults to skill_md)
            model: Override model (defaults to worker's assigned model)
            session_id: Session ID for event emission + conversation memory
            **kwargs: Additional provider-specific parameters

        Yields:
            Token chunks as they arrive
        """
        # Resolve session ID for conversation memory
        sid = session_id or self._current_session_id

        messages: list[dict[str, str]] = []
        sys = system or self.identity.skill_md
        if sys:
            messages.append({"role": "system", "content": sys})

        # Inject conversation history (same as llm_call)
        if sid and sid in self._conv_history:
            messages.extend(self._conv_history[sid])

        messages.append({"role": "user", "content": prompt})

        # AutoTune — select optimal sampling params for streaming too
        if "temperature" not in kwargs:
            self._ensure_autotune()
            if self._autotune is not None:
                try:
                    history_texts = self._get_history_texts()
                    result = self._autotune.analyze(
                        text=prompt,
                        history=history_texts or None,
                        worker_id=self.id,
                    )
                    provider_name = self.identity.api.provider
                    filtered = self._autotune.filter_params_for_provider(
                        result.params, provider_name
                    )
                    kwargs.update(filtered)
                except Exception:
                    pass  # AutoTune failure is non-fatal

        model_name = model or self.model
        emitter = self._get_emitter(session_id) if session_id else None

        if emitter:
            await emitter.llm_stream_start(from_id=self.id, model=model_name)

        full_text_parts: list[str] = []

        # Try worker's own provider first (consistent with llm_call)
        self._ensure_own_provider()
        if self._own_provider is not None:
            stripped_model = model_name
            if "/" in stripped_model:
                stripped_model = stripped_model.split("/", 1)[1]
            try:
                async for chunk in self._own_provider.complete_stream(
                    model=stripped_model,
                    messages=messages,
                    **kwargs,
                ):
                    full_text_parts.append(chunk)
                    if emitter:
                        await emitter.llm_stream_chunk(from_id=self.id, chunk=chunk, model=model_name)
                    yield chunk
            except AttributeError:
                # Own provider doesn't support streaming — fall back to router
                pass
            else:
                # Store exchange in conversation history (same as llm_call)
                full_response = "".join(full_text_parts)
                if sid:
                    if sid not in self._conv_history:
                        self._conv_history[sid] = []
                    self._conv_history[sid].append({"role": "user", "content": prompt})
                    self._conv_history[sid].append({"role": "assistant", "content": full_response})
                    if len(self._conv_history[sid]) > self.MAX_CONVERSATION_HISTORY:
                        self._conv_history[sid] = self._conv_history[sid][-self.MAX_CONVERSATION_HISTORY:]

                if emitter:
                    await emitter.llm_stream_done(
                        from_id=self.id, model=model_name, full_text=full_response
                    )
                return

        # Fall back to global router for streaming
        async for chunk in self.router.complete_stream(
            model=model_name,
            messages=messages,
            **kwargs,
        ):
            full_text_parts.append(chunk)
            if emitter:
                await emitter.llm_stream_chunk(from_id=self.id, chunk=chunk, model=model_name)
            yield chunk

        # Store exchange in conversation history (same as llm_call)
        full_response = "".join(full_text_parts)
        if sid:
            if sid not in self._conv_history:
                self._conv_history[sid] = []
            self._conv_history[sid].append({"role": "user", "content": prompt})
            self._conv_history[sid].append({"role": "assistant", "content": full_response})
            if len(self._conv_history[sid]) > self.MAX_CONVERSATION_HISTORY:
                self._conv_history[sid] = self._conv_history[sid][-self.MAX_CONVERSATION_HISTORY:]

        if emitter:
            await emitter.llm_stream_done(
                from_id=self.id, model=model_name, full_text=full_response
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

        Supports session_id in kwargs for conversation memory (passed to llm_call).
        """
        import json

        # Extract session_id from kwargs to pass explicitly to llm_call
        session_id = kwargs.pop("session_id", "")

        response = await self.llm_call(
            prompt, system, model, session_id=session_id, **kwargs
        )
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

        This is the BASE implementation. BriefingRoom may bypass this and
        call llm_call_structured() directly with a custom prompt that includes
        the full group transcript (via _worker_speak_with_context).

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

    async def receive_broadcast(self, from_id: str, message: str) -> dict[str, Any]:
        """
        Receive a broadcast message from another worker or the hub.

        Called by WorkerHub.broadcast() — every active worker gets the
        same message. Override in subclasses for custom broadcast behavior.

        Args:
            from_id: ID of the worker that sent the broadcast
            message: Broadcast message content

        Returns:
            Dict with optional response and blocker status
        """
        prompt = f"""
        Worker {from_id} broadcast a message to the team:
        "{message}"

        You are {self.id} ({self.role}).
        If this affects your work, respond. Otherwise, acknowledge briefly.

        Respond with JSON:
        {{
            "response": "your response or acknowledgment",
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

    # ── Context & Memory Helpers ──────────────────────────────────────

    def _build_context_section(self, task: Task) -> str:
        """
        Build formatted context section from task.context for prompt injection.

        Extracts and formats key context fields that the Office prepares:
        - session_context: what happened so far in this session
        - team_decisions: decisions from the briefing room
        - results: output from previous workers
        - contract: the original contract details
        - Any other keys

        Workers should include this in their prompts so the LLM knows
        what happened in the session before this task arrived.

        Args:
            task: The task with context dict from Office/Conductor

        Returns:
            Formatted string ready to inject into a prompt, or "" if no context
        """
        if not task.context:
            return ""

        parts: list[str] = []

        # Session context — what happened so far in this session
        session_ctx = task.context.get("session_context", "")
        if session_ctx:
            parts.append(f"Session context (what happened so far):\n{session_ctx}")

        # Team decisions from briefing room
        team_decisions = task.context.get("team_decisions", [])
        if team_decisions:
            if isinstance(team_decisions, list):
                decisions_text = "\n".join(f"- {d}" for d in team_decisions)
            else:
                decisions_text = str(team_decisions)
            parts.append(f"Team decisions:\n{decisions_text}")

        # Results from previous workers (if present)
        results = task.context.get("results", "")
        if results:
            if isinstance(results, dict):
                parts.append(f"Previous worker results:\n{results}")
            else:
                parts.append(f"Previous worker results:\n{results}")

        # Contract details (if present)
        contract = task.context.get("contract", "")
        if contract:
            if isinstance(contract, dict):
                title = contract.get("title", "Unknown")
                parts.append(f"Contract: {title}")
            else:
                parts.append(f"Contract: {contract}")

        # Notebook context (shared persistent knowledge from ProjectNotebook)
        notebook = task.context.get("notebook", "")
        if notebook:
            parts.append(str(notebook))

        # Other context keys not yet handled
        handled_keys = {"session_context", "team_decisions", "results", "contract", "notebook"}
        other = {k: v for k, v in task.context.items() if k not in handled_keys}
        if other:
            for k, v in other.items():
                parts.append(f"{k}: {v}")

        return "\n\n".join(parts)

    def clear_conversation(self, session_id: str = "") -> None:
        """
        Clear conversation history for a session (or all sessions).

        Call this when a session ends or on /reset.

        Args:
            session_id: Specific session to clear, or "" to clear all
        """
        if session_id:
            self._conv_history.pop(session_id, None)
        else:
            self._conv_history.clear()

    def get_conversation_summary(self, session_id: str = "") -> str:
        """
        Get a text summary of conversation history for context injection.

        Useful for workers that want to include their own history as part
        of a larger prompt, without relying on automatic llm_call() injection.

        Args:
            session_id: Session to summarize, or "" for current session

        Returns:
            Formatted summary string, or "" if no history
        """
        sid = session_id or self._current_session_id
        if not sid or sid not in self._conv_history:
            return ""
        history = self._conv_history[sid]
        if not history:
            return ""
        parts: list[str] = []
        for msg in history:
            role = msg["role"].capitalize()
            content = msg["content"]
            # Truncate long messages to keep summary manageable
            if len(content) > 300:
                content = content[:297] + "..."
            parts.append(f"{role}: {content}")
        return "\n".join(parts)

    async def consider_speaking(
        self,
        channel: Any,
        context: dict[str, Any],
        session_id: str,
    ) -> bool:
        """
        Worker decides whether to speak up in an ExecutionChannel.

        Called by Office when an event occurs that might be relevant
        to all workers. The worker uses its personality config to
        decide if it should speak, then uses the LLM to evaluate
        whether it has something valuable to add.

        Args:
            channel: ExecutionChannel to speak on
            context: Situation info (trigger, topic, active_workers, etc.)
            session_id: Current session ID

        Returns:
            True if the worker spoke, False if it stayed quiet
        """
        from kantorku.layers.group_channel import MessageType

        # Step 1: Personality filter — should this worker even consider speaking?
        if not self.personality.should_speak(context):
            return False  # Stay quiet

        # Step 2: LLM evaluation — does this worker have something valuable to say?
        channel_text = ""
        if hasattr(channel, 'get_transcript_text'):
            channel_text = channel.get_transcript_text()

        prompt = f"""Situation: {context.get('situation', '')}
Current discussion:
{channel_text[-1500:] if channel_text else '(No discussion yet)'}

You are {self.id} ({self.role}).
Your expertise: {', '.join(self.identity.capabilities[:5])}

Do you have something IMPORTANT to add? Do not speak if you have nothing of value.

Respond with JSON:
{{
    "should_speak": true/false,
    "confidence": 0.0-1.0,
    "message": "what you want to say (if should_speak=true)",
    "message_type": "concern/suggestion/question/info/agreement"
}}"""

        result = await self.llm_call_structured(
            prompt, session_id=session_id
        )

        # Step 3: Confidence threshold — don't speak if not confident enough
        should_speak = result.get("should_speak", False)
        confidence = result.get("confidence", 0.0)
        message = result.get("message", "")
        msg_type_str = result.get("message_type", "speak")

        if not should_speak or confidence < self.personality.confidence_threshold:
            return False  # Not confident enough — stay quiet

        if not message:
            return False  # Nothing to say — stay quiet

        # Step 4: Speak — map message_type string to MessageType enum
        type_map = {
            "concern": MessageType.CONCERN,
            "suggestion": MessageType.SUGGESTION,
            "question": MessageType.QUESTION,
            "info": MessageType.INFO,
            "agreement": MessageType.AGREEMENT,
            "disagreement": MessageType.DISAGREEMENT,
        }
        msg_type = type_map.get(msg_type_str.lower(), MessageType.SPEAK)

        await channel.speak(
            from_id=self.id,
            content=message,
            message_type=msg_type,
        )
        return True
