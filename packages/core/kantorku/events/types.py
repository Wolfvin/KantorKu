"""
Event type constants for KantorKu.

Single source of truth for all event type strings used across the system.
These define the "contract" between backend and any client (TUI, GUI, API).
"""

# ── Event Type Strings ────────────────────────────────────────────────

# Briefing events
EVENT_BRIEFING_OPENED = "briefing_opened"
EVENT_PLAN_DRAFTED = "plan_drafted"
EVENT_PLAN_REVISED = "plan_revised"
EVENT_REVISION_REQUESTED = "revision_requested"
EVENT_MANAGER_BRAINSTORMING = "manager_brainstorming"

# Worker communication events
EVENT_WORKER_SPEAK_UP = "worker_speak_up"
EVENT_WORKER_DM = "worker_dm"
EVENT_WORKER_BROADCAST = "worker_broadcast"

# Task lifecycle events
EVENT_TASK_ASSIGNED = "task_assigned"
EVENT_TASK_STARTED = "task_started"
EVENT_TASK_DONE = "task_done"
EVENT_TASK_FAILED = "task_failed"
EVENT_TASK_RECOVERED = "task_recovered"
EVENT_TASK_TIMEOUT = "task_timeout"

# Context pool events
EVENT_CONTEXT_FETCH_START = "context_fetch_start"
EVENT_CONTEXT_FETCH_DONE = "context_fetch_done"

# Verification events
EVENT_VERIFY_DESIGN_START = "verify_design_start"
EVENT_VERIFY_DESIGN_DONE = "verify_design_done"
EVENT_VERIFY_ENGINEER_START = "verify_engineer_start"
EVENT_VERIFY_ENGINEER_DONE = "verify_engineer_done"

# System events
EVENT_ERROR_LOGGED = "error_logged"
EVENT_SKILL_UPDATED = "skill_updated"

# LLM streaming events
EVENT_LLM_STREAM_START = "llm_stream_start"
EVENT_LLM_STREAM_CHUNK = "llm_stream_chunk"
EVENT_LLM_STREAM_DONE = "llm_stream_done"

# Contract events
EVENT_CONTRACT_ACCEPTED = "contract_accepted"

# Delegation events
EVENT_DELEGATION_REQUEST = "delegation_request"
EVENT_DELEGATION_RESULT = "delegation_result"

# Persistence events
EVENT_CHECKPOINT_SAVED = "checkpoint_saved"
EVENT_CRASH_RECOVERED = "crash_recovered"

# Circuit breaker / rate limit events
EVENT_CIRCUIT_OPEN = "circuit_open"
EVENT_CIRCUIT_CLOSED = "circuit_closed"
EVENT_RATE_LIMIT_HIT = "rate_limit_hit"
EVENT_COST_WARNING = "cost_warning"

# Worker lifecycle events
EVENT_WORKER_HIRED = "worker_hired"
EVENT_WORKER_FIRED = "worker_fired"

# Middleware events
EVENT_MIDDLEWARE_BEFORE = "middleware_before"
EVENT_MIDDLEWARE_AFTER = "middleware_after"

# ── Event Category Sets ────────────────────────────────────────────────

BRIEFING_EVENTS = {
    EVENT_BRIEFING_OPENED, EVENT_PLAN_DRAFTED, EVENT_PLAN_REVISED,
    EVENT_WORKER_SPEAK_UP, EVENT_MANAGER_BRAINSTORMING,
}

DAG_EVENTS = {
    EVENT_TASK_ASSIGNED, EVENT_TASK_DONE, EVENT_TASK_FAILED,
}

FILTER_CATEGORIES: dict[str, set[str]] = {
    "tasks": {
        EVENT_TASK_ASSIGNED, EVENT_TASK_STARTED, EVENT_TASK_DONE,
        EVENT_TASK_FAILED, EVENT_TASK_RECOVERED, EVENT_TASK_TIMEOUT,
    },
    "briefing": {
        EVENT_BRIEFING_OPENED, EVENT_PLAN_DRAFTED, EVENT_PLAN_REVISED,
        EVENT_WORKER_SPEAK_UP, EVENT_WORKER_DM, EVENT_WORKER_BROADCAST,
    },
    "errors": {
        EVENT_ERROR_LOGGED, EVENT_CIRCUIT_OPEN, EVENT_RATE_LIMIT_HIT, EVENT_COST_WARNING,
    },
    "llm": {
        EVENT_LLM_STREAM_START, EVENT_LLM_STREAM_CHUNK, EVENT_LLM_STREAM_DONE,
    },
}

# ── Phase Map ────────────────────────────────────────────────────────

PHASE_MAP: dict[str, str] = {
    EVENT_BRIEFING_OPENED: "briefing",
    EVENT_PLAN_DRAFTED: "briefing",
    EVENT_WORKER_SPEAK_UP: "briefing",
    EVENT_CONTRACT_ACCEPTED: "execution",
    EVENT_TASK_ASSIGNED: "execution",
    EVENT_TASK_STARTED: "execution",
    EVENT_TASK_DONE: "execution",
    EVENT_TASK_FAILED: "execution",
    EVENT_VERIFY_DESIGN_START: "verification",
    EVENT_VERIFY_ENGINEER_START: "verification",
    EVENT_REVISION_REQUESTED: "briefing",
    EVENT_MANAGER_BRAINSTORMING: "briefing",
}
