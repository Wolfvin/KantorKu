"""
Protocol — Pydantic models for the kantorku WebSocket protocol.

Type-safe message definitions for both Panel 1 (client ↔ manager)
and Panel 2 (office event stream) WebSocket channels.

Usage:
    from kantorku.protocol import ClientMessage, OfficeEvent

    # Parse incoming client message
    msg = ClientMessage.model_validate_json(raw_json)

    # Create outgoing office event
    event = OfficeEvent(type="task_done", from_id="coder_backend", files=["main.py"])
    await ws.send_text(event.model_dump_json(exclude_none=True))
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── Panel 1: Client ↔ Manager Messages ─────────────────────────────


class UserMessage(BaseModel):
    """Client sends a message to the manager."""
    type: str = "user_message"
    content: str


class ContractAccepted(BaseModel):
    """Client accepts the contract."""
    type: str = "contract_accepted"


class ContractRevision(BaseModel):
    """Client requests a revision to the contract."""
    type: str = "contract_revision"
    feedback: str


class ManagerMessage(BaseModel):
    """Server sends a manager message to the client."""
    type: str = "manager_message"
    content: str
    from_id: str = Field(default="conductor", alias="from")

    model_config = {"populate_by_name": True}


class ContractReady(BaseModel):
    """Server sends a contract for client review."""
    type: str = "contract_ready"
    contract: dict[str, Any]


class WorkStarted(BaseModel):
    """Server notifies client that work has begun."""
    type: str = "work_started"
    session_id: str


class WorkDone(BaseModel):
    """Server sends the final work result to the client."""
    type: str = "work_done"
    result: dict[str, Any]


class ErrorMessage(BaseModel):
    """Error message from server."""
    type: str = "error"
    message: str


# ── Panel 2: Office Event Stream ────────────────────────────────────


class OfficeEvent(BaseModel):
    """
    A typed event from the office event stream.

    All events have a `type` field and optional context fields.
    This provides type safety for WebSocket consumers.
    """
    type: str
    from_id: str | None = Field(default=None, alias="from")
    to_id: str | None = Field(default=None, alias="to")
    content: str | None = None
    session_id: str | None = None
    model: str | None = None
    files: list[str] | None = None
    error: str | None = None
    todos: list[dict[str, Any]] | None = None
    issues: list[str] | None = None
    approved: bool | None = None
    reason: str | None = None
    instance: int | None = None
    query: str | None = None
    for_task: str | None = None
    results: list[dict[str, Any]] | None = None
    worker: str | None = None
    lesson: str | None = None
    chunk: str | None = None
    full_text: str | None = None

    model_config = {"populate_by_name": True}


# ── Event type constants ─────────────────────────────────────────────


class EventType:
    """Constants for all event types in the kantorku protocol."""
    # Lifecycle
    BRIEFING_OPENED = "briefing_opened"
    PLAN_DRAFTED = "plan_drafted"
    PLAN_REVISED = "plan_revised"
    CONTRACT_READY = "contract_ready"
    CONTRACT_ACCEPTED = "contract_accepted"

    # Worker activity
    WORKER_SPEAK_UP = "worker_speak_up"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_DONE = "task_done"
    TASK_FAILED = "task_failed"

    # Peer communication
    WORKER_DM = "worker_dm"
    WORKER_BROADCAST = "worker_broadcast"

    # Context pool
    CONTEXT_FETCH_START = "context_fetch_start"
    CONTEXT_FETCH_DONE = "context_fetch_done"
    CONTEXT_REQUESTED = "context_requested"
    CONTEXT_DELIVERED = "context_delivered"

    # Verification
    VERIFY_DESIGN_START = "verify_design_start"
    VERIFY_DESIGN_DONE = "verify_design_done"
    VERIFY_ENGINEER_START = "verify_engineer_start"
    VERIFY_ENGINEER_DONE = "verify_engineer_done"

    # Learning
    ERROR_LOGGED = "error_logged"
    SKILL_UPDATED = "skill_updated"

    # Conductor <-> Client
    MANAGER_MESSAGE = "manager_message"
    MANAGER_QUESTION = "manager_question"

    # Streaming
    LLM_STREAM_START = "llm_stream_start"
    LLM_STREAM_CHUNK = "llm_stream_chunk"
    LLM_STREAM_DONE = "llm_stream_done"


# ── Message parsing helpers ──────────────────────────────────────────


def parse_client_message(raw: str) -> UserMessage | ContractAccepted | ContractRevision | ErrorMessage:
    """
    Parse an incoming client WebSocket message.

    Args:
        raw: Raw JSON string from client

    Returns:
        Typed message object

    Raises:
        ValueError: If the message type is unknown
    """
    import json

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ErrorMessage(message="Invalid JSON")

    msg_type = data.get("type", "")

    if msg_type == "user_message":
        return UserMessage(content=data.get("content", ""))
    elif msg_type == "contract_accepted":
        return ContractAccepted()
    elif msg_type == "contract_revision":
        return ContractRevision(feedback=data.get("feedback", ""))
    else:
        return ErrorMessage(message=f"Unknown message type: {msg_type}")


def create_office_event(event_dict: dict[str, Any]) -> OfficeEvent:
    """
    Create a typed OfficeEvent from a raw event dict.

    Args:
        event_dict: Raw event dictionary from EventBus

    Returns:
        Typed OfficeEvent
    """
    return OfficeEvent.model_validate(event_dict)
