"""
Themes — Color themes for the KantorKu TUI.
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

# Squad color mapping
SQUAD_COLORS = {
    "coding": "cyan",
    "verification": "magenta",
    "support": "yellow",
    "translation": "blue",
}

# Worker status icons
STATUS_ICONS = {
    "idle": "\u25cb",       # ○
    "thinking": "\u25d0",   # ◐
    "active": "\u25cf",     # ●
    "done": "\u2713",       # ✓
    "failed": "\u2717",     # ✗
}

STATUS_COLORS = {
    "idle": "dim",
    "thinking": "yellow",
    "active": "green bold",
    "done": "green",
    "failed": "red bold",
}

# Event type styling
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
    "manager_message": ("green bold", "manager"),
    "manager_question": ("yellow bold", "question"),
    "work_started": ("green bold", "work"),
    "work_done": ("green bold", "complete"),
    "error_logged": ("red", "error"),
    "verify_design_start": ("magenta", "v_design"),
    "verify_design_done": ("magenta", "v_design"),
    "verify_engineer_start": ("magenta", "v_engineer"),
    "verify_engineer_done": ("magenta", "v_engineer"),
}
