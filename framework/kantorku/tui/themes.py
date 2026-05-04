"""
Themes — Color themes and style constants for the KantorKu TUI.

Provides complete styling for ALL framework features:
- KANTORKU_THEMES: Named theme dict (5 built-in themes)
- KANTORKU_THEME: Alias to KANTORKU_THEMES["office"] for backward compat
- get_theme(): Get a theme by name
- list_themes(): List available theme names
- SQUAD_COLORS: Per-squad color mapping
- STATUS_ICONS: Unicode icons for worker/task/queue/contract states
- STATUS_COLORS: Color names for status states
- EVENT_STYLES: (color, label) tuples for event type rendering
- CONTRACT_STATE_COLORS: Colors for contract/conductor states
- SEVERITY_COLORS: Colors for alert severity levels
- PANEL_BORDER_COLORS: Border colors for all panels
- ERROR_COLORS: Colors for structured error types
- REDTEAM_STYLES: Styles for redteam features
- MIDDLEWARE_COLORS: Colors for middleware pipeline stages
- TASK_STATE_ICONS: Icons for task queue states
"""

# ── Named Themes ────────────────────────────────────────────────────

KANTORKU_THEMES: dict[str, dict[str, str]] = {
    "office": {
        "primary": "#00d4aa",
        "secondary": "#7c3aed",
        "accent": "#f59e0b",
        "success": "#10b981",
        "error": "#ef4444",
        "warning": "#f59e0b",
        "info": "#3b82f6",
        "muted": "#6b7280",
        "background": "#0f172a",
        "surface": "#1e293b",
        "text": "#f1f5f9",
    },
    "midnight": {
        "primary": "#06b6d4",
        "secondary": "#8b5cf6",
        "accent": "#f97316",
        "success": "#10b981",
        "error": "#ef4444",
        "warning": "#f59e0b",
        "info": "#3b82f6",
        "muted": "#6b7280",
        "background": "#0a0a0a",
        "surface": "#171717",
        "text": "#f1f5f9",
    },
    "terminal": {
        "primary": "#00ff00",
        "secondary": "#00cc00",
        "accent": "#ffff00",
        "success": "#00ff00",
        "error": "#ff4444",
        "warning": "#ffff00",
        "info": "#00cc00",
        "muted": "#008800",
        "background": "#000000",
        "surface": "#0a0a0a",
        "text": "#00ff00",
    },
    "cyberpunk": {
        "primary": "#ff00ff",
        "secondary": "#00ffff",
        "accent": "#ffff00",
        "success": "#00ff88",
        "error": "#ff0055",
        "warning": "#ff8800",
        "info": "#00ffff",
        "muted": "#885588",
        "background": "#0d0221",
        "surface": "#150535",
        "text": "#ff88ff",
    },
    "forest": {
        "primary": "#22c55e",
        "secondary": "#059669",
        "accent": "#f59e0b",
        "success": "#22c55e",
        "error": "#dc2626",
        "warning": "#f59e0b",
        "info": "#0ea5e9",
        "muted": "#4d7c4d",
        "background": "#0f1a0f",
        "surface": "#1a2e1a",
        "text": "#d4f0d4",
    },
}

# Backward compatibility — alias to default theme
KANTORKU_THEME = KANTORKU_THEMES["office"]

# Default theme name
DEFAULT_THEME = "office"


def get_theme(name: str) -> dict[str, str]:
    """Get a theme dict by name. Falls back to DEFAULT_THEME if not found."""
    return KANTORKU_THEMES.get(name, KANTORKU_THEMES[DEFAULT_THEME])


def list_themes() -> list[str]:
    """List all available theme names."""
    return list(KANTORKU_THEMES.keys())


# Squad color mapping
SQUAD_COLORS = {
    "coding": "cyan",
    "verification": "magenta",
    "support": "yellow",
    "translation": "blue",
}

# Worker/task status icons
STATUS_ICONS = {
    "idle": "\u25cb",        # ○
    "thinking": "\u25d0",    # ◐
    "active": "\u25cf",      # ●
    "done": "\u2713",        # ✓
    "failed": "\u2717",      # ✗
    "pending": "\u25cb",     # ○
    "in_progress": "\u25d0", # ◐
}

# Status color mapping
STATUS_COLORS = {
    "idle": "dim",
    "thinking": "yellow",
    "active": "green bold",
    "done": "green",
    "failed": "red bold",
    "pending": "dim",
    "in_progress": "yellow",
    "unknown": "dim",
}

# Task queue state icons
TASK_STATE_ICONS = {
    "pending": "\u25cb",           # ○
    "queued": "\u25cb",            # ○
    "in_progress": "\u25d0",       # ◐
    "completed": "\u2713",         # ✓
    "failed": "\u2717",            # ✗
    "retrying": "\u21bb",          # ↻
    "cancelled": "\u2298",         # ⊘
    "dead_letter": "\u2620",       # ☠
}

TASK_STATE_COLORS = {
    "pending": "dim",
    "queued": "cyan",
    "in_progress": "yellow",
    "completed": "green",
    "failed": "red bold",
    "retrying": "yellow",
    "cancelled": "dim",
    "dead_letter": "red bold",
}

# Event type styling
EVENT_STYLES = {
    "briefing_opened": ("magenta", "briefing"),
    "plan_drafted": ("blue", "plan"),
    "contract_ready": ("green bold", "contract"),
    "contract_accepted": ("green", "accepted"),
    "contract_revised": ("yellow", "revised"),
    "task_assigned": ("cyan", "assigned"),
    "task_started": ("yellow", "started"),
    "task_done": ("green bold", "done"),
    "task_failed": ("red bold", "failed"),
    "task_recovered": ("green", "recovered"),
    "task_timeout": ("red", "timeout"),
    "worker_speak_up": ("magenta", "speak_up"),
    "worker_dm": ("dim", "dm"),
    "worker_broadcast": ("cyan", "broadcast"),
    "worker_hired": ("green bold", "hired"),
    "worker_fired": ("red bold", "fired"),
    "context_fetch_start": ("dim", "fetch"),
    "context_fetch_done": ("dim", "fetched"),
    "verify_design_start": ("magenta", "v_design"),
    "verify_design_done": ("magenta", "v_design"),
    "verify_engineer_start": ("magenta", "v_engineer"),
    "verify_engineer_done": ("magenta", "v_engineer"),
    "error_logged": ("red", "error"),
    "manager_message": ("green bold", "manager"),
    "manager_question": ("yellow bold", "question"),
    "llm_call_start": ("dim", "llm_start"),
    "llm_call_done": ("dim", "llm_done"),
    "llm_stream_start": ("dim", "stream"),
    "llm_stream_chunk": ("dim", "chunk"),
    "llm_stream_done": ("dim", "stream_done"),
    "work_started": ("green bold", "work"),
    "work_done": ("green bold", "complete"),
    "briefing_message": ("magenta", "briefing"),
    "delegation_request": ("cyan", "delegate"),
    "delegation_result": ("cyan", "delegated"),
    "checkpoint_saved": ("green", "checkpoint"),
    "crash_recovered": ("yellow bold", "recovered"),
    "circuit_open": ("red bold", "circuit_open"),
    "circuit_closed": ("green", "circuit_closed"),
    "rate_limit_hit": ("yellow", "rate_limit"),
    "middleware_before": ("blue", "mw_before"),
    "middleware_after": ("blue", "mw_after"),
    "cost_warning": ("yellow bold", "cost_warn"),
    # v0.7.0 revision events
    "revision_requested": ("yellow bold", "revision"),
    "manager_brainstorming": ("cyan bold", "brainstorm"),
}

# Contract/conductor state colors (all 11 states from Conductor)
CONTRACT_STATE_COLORS = {
    "idle": "dim",
    "manager_thinking": "yellow",
    "clarifying": "yellow",
    "contract_presented": "cyan",
    "awaiting_revision": "yellow bold",
    "team_review": "magenta",
    "todo_review": "blue",
    "client_feedback": "yellow",
    "working": "green bold",
    "verifying": "magenta",
    "accepted": "green bold",
    "done": "green",
    "failed": "red",
    "drafting": "yellow",
    "proposed": "cyan",
    "negotiating": "yellow",
}

# Alert severity colors
SEVERITY_COLORS = {
    "info": "blue",
    "warning": "yellow",
    "critical": "red bold",
}

# Structured error type colors
ERROR_COLORS = {
    "KantorkuError": "red",
    "ProviderError": "red",
    "ProviderTimeoutError": "yellow",
    "ProviderRateLimitError": "yellow",
    "ProviderAuthError": "red bold",
    "ProviderCircuitOpenError": "red bold",
    "AllProvidersFailedError": "red bold",
    "WorkerError": "red",
    "WorkerTimeoutError": "yellow",
    "WorkerNotReadyError": "yellow",
    "OfficeError": "red",
    "OfficeNotInitializedError": "red bold",
    "ContractError": "yellow",
    "NoContractError": "yellow",
    "ConfigError": "red",
    "WorkerNotFoundError": "yellow",
    "DAGCycleError": "red bold",
}

# Middleware stage colors
MIDDLEWARE_COLORS = {
    "LoggingMiddleware": "blue",
    "AuthMiddleware": "red",
    "RateLimitMiddleware": "yellow",
    "CostGuardMiddleware": "magenta",
    "AuditMiddleware": "cyan",
    "TimeoutMiddleware": "yellow",
    "RetryMiddleware": "green",
    "CachingMiddleware": "cyan",
}

# Redteam feature styles
REDTEAM_STYLES = {
    "parseltongue": "magenta bold",
    "autotune": "cyan",
    "stm": "yellow",
    "classify": "red",
    "godmode": "red bold",
    "scoring": "green",
}

# Harm category colors (for classify)
HARM_COLORS = {
    "benign": "green",
    "low_risk": "cyan",
    "medium_risk": "yellow",
    "high_risk": "red",
    "critical": "red bold",
}

# Panel border colors — built from KANTORKU_THEME for backward compat
# (These are module-level and use the default "office" theme colors)
PANEL_BORDER_COLORS = {
    # 3-Panel TUI v0.5.0
    "manager_chat": KANTORKU_THEME["primary"],
    "workers_live": KANTORKU_THEME["secondary"],
    "contract": KANTORKU_THEME["accent"],
    # Legacy tab panels (still accessible via slash commands)
    "workers": KANTORKU_THEME["primary"],
    "events": KANTORKU_THEME["info"],
    "health": KANTORKU_THEME["success"],
    "memory": KANTORKU_THEME["secondary"],
    "dag": KANTORKU_THEME["accent"],
    "briefing": KANTORKU_THEME["secondary"],
    "pool": KANTORKU_THEME["info"],
    "queue": KANTORKU_THEME["warning"],
    "observe": KANTORKU_THEME["primary"],
    "alerts": KANTORKU_THEME["error"],
    "transcript": KANTORKU_THEME["secondary"],
    "redteam": KANTORKU_THEME["error"],
    "middleware": KANTORKU_THEME["info"],
    "worker_detail": KANTORKU_THEME["primary"],
}

# 3-Panel TUI state icons
PANEL_STATE_ICONS = {
    "idle": "\U0001f4a4",
    "manager_thinking": "\U0001f914",
    "clarifying": "\U0001f4ac",
    "contract_presented": "\U0001f4cb",
    "awaiting_revision": "\u270f\ufe0f",
    "team_review": "\U0001f465",
    "todo_review": "\U0001f4dd",
    "client_feedback": "\U0001f504",
    "working": "\u26a1",
    "accepted": "\u2705",
    "done": "\u2705",
    "failed": "\u274c",
}

# Workers Live phase styling
WORKERS_PHASE_STYLES = {
    "idle": ("dim", "IDLE"),
    "briefing": ("magenta bold", "\U0001f465 BRIEFING"),
    "execution": ("green bold", "\u26a1 EXECUTING"),
    "verification": ("blue bold", "\U0001f50d VERIFYING"),
    "done": ("green", "\u2705 COMPLETE"),
    "failed": ("red bold", "\u274c FAILED"),
}
