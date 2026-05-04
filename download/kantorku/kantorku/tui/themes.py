"""
Themes — Color themes and style constants for the KantorKu TUI.

Provides:
- KANTORKU_THEME: The primary color palette applied to all CSS
- SQUAD_COLORS: Per-squad color mapping (used in WorkerGrid, DAG, etc.)
- STATUS_ICONS: Unicode icons for worker/task status (used everywhere)
- STATUS_COLORS: Color names for status states
- EVENT_STYLES: (color, label) tuples for event type rendering
- CONTRACT_STATE_COLORS: Colors for contract states
- SEVERITY_COLORS: Colors for alert severity levels
- PANEL_BORDER_COLORS: Default border colors for panels
"""

# KantorKu color palette — inspired by office/aesthetic terminal vibes
KANTORKU_THEME = {
    "primary": "#00d4aa",      # Teal green — the KantorKu brand color
    "secondary": "#7c3aed",   # Purple — for coding squad
    "accent": "#f59e0b",      # Amber — for warnings/highlights
    "success": "#10b981",     # Green — for success states
    "error": "#ef4444",       # Red — for errors/failures
    "warning": "#f59e0b",     # Amber — for warnings
    "info": "#3b82f6",        # Blue — for informational
    "muted": "#6b7280",       # Gray — for dimmed text
    "background": "#0f172a",  # Dark navy — background
    "surface": "#1e293b",     # Lighter navy — surfaces/panels
    "text": "#f1f5f9",        # Light gray — primary text
}

# Squad color mapping — used in WorkerGrid, DAG panel, etc.
SQUAD_COLORS = {
    "coding": "cyan",
    "verification": "magenta",
    "support": "yellow",
    "translation": "blue",
}

# Worker/task status icons — Unicode symbols for compact display
STATUS_ICONS = {
    "idle": "\u25cb",       # ○
    "thinking": "\u25d0",   # ◐
    "active": "\u25cf",     # ●
    "done": "\u2713",       # ✓
    "failed": "\u2717",     # ✗
    "pending": "\u25cb",    # ○
    "in_progress": "\u25d0", # ◐
}

# Status color mapping — used throughout for consistent styling
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

# Event type styling — (color, display_label) tuples
# Used by EventsStream widget for consistent event rendering
EVENT_STYLES = {
    "briefing_opened": ("magenta", "briefing"),
    "plan_drafted": ("blue", "plan"),
    "contract_ready": ("green bold", "contract"),
    "contract_accepted": ("green", "accepted"),
    "task_assigned": ("cyan", "assigned"),
    "task_started": ("yellow", "started"),
    "task_done": ("green bold", "done"),
    "task_failed": ("red bold", "failed"),
    "worker_speak_up": ("magenta", "speak_up"),
    "worker_dm": ("dim", "dm"),
    "worker_broadcast": ("cyan", "broadcast"),
    "context_fetch_start": ("dim", "fetch"),
    "context_fetch_done": ("dim", "fetched"),
    "verify_design_start": ("magenta", "v_design"),
    "verify_design_done": ("magenta", "v_design"),
    "verify_engineer_start": ("magenta", "v_engineer"),
    "verify_engineer_done": ("magenta", "v_engineer"),
    "error_logged": ("red", "error"),
    "manager_message": ("green bold", "manager"),
    "manager_question": ("yellow bold", "question"),
    "llm_stream_start": ("dim", "stream"),
    "llm_stream_chunk": ("dim", "chunk"),
    "llm_stream_done": ("dim", "stream_done"),
    "work_started": ("green bold", "work"),
    "work_done": ("green bold", "complete"),
    "briefing_message": ("magenta", "briefing"),
    "delegation_request": ("cyan", "delegate"),
    "delegation_result": ("cyan", "delegated"),
}

# Contract state colors — for ContractPanel and /dag
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

# Panel border colors — consistent look across all tabs
PANEL_BORDER_COLORS = {
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
}
