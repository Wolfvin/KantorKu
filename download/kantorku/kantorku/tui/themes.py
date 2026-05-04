"""
Themes — Color themes and style constants for the KantorKu TUI.

Provides complete styling for ALL framework features:
- KANTORKU_THEME: Primary color palette applied to all CSS
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

# KantorKu color palette
KANTORKU_THEME = {
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
}

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
}

# Contract/conductor state colors (all 11 states from Conductor)
CONTRACT_STATE_COLORS = {
    "idle": "dim",
    "manager_thinking": "yellow",
    "clarifying": "yellow",
    "contract_presented": "cyan",
    "team_review": "magenta",
    "todo_review": "blue",
    "client_feedback": "yellow",
    "working": "green bold",
    "verifying": "magenta",
    "done": "green",
    "failed": "red",
    "drafting": "yellow",
    "proposed": "cyan",
    "negotiating": "yellow",
    "accepted": "green",
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

# Panel border colors
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
    "idle": "💤",
    "manager_thinking": "🤔",
    "clarifying": "💬",
    "contract_presented": "📋",
    "team_review": "👥",
    "todo_review": "📝",
    "client_feedback": "🔄",
    "working": "⚡",
    "done": "✅",
    "failed": "❌",
}

# Workers Live phase styling
WORKERS_PHASE_STYLES = {
    "idle": ("dim", "IDLE"),
    "briefing": ("magenta bold", "👥 BRIEFING"),
    "execution": ("green bold", "⚡ EXECUTING"),
    "verification": ("blue bold", "🔍 VERIFYING"),
    "done": ("green", "✅ COMPLETE"),
    "failed": ("red bold", "❌ FAILED"),
}
