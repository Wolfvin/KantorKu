"""
SettingsScreen — Full settings panel overlay for the KantorKu TUI.

A Textual Screen subclass that provides a 4-tab settings interface:
  - General: Theme, Language, Conductor model, Redteam toggle
  - Workers: Browse/edit worker identities, system prompts, tools, API config
  - Skills: Browse/edit skill markdown files
  - API Keys: View and manage provider API keys (masked)

Pushed via `app.push_screen(SettingsScreen(app_ref))`.
Closed via ESC → `app.pop_screen()`.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
    TextArea,
)

from kantorku.tui.themes import KANTORKU_THEME, SQUAD_COLORS

logger = logging.getLogger(__name__)

# ─── Constants ─────────────────────────────────────────────────────────

# Resolve paths relative to the kantorku package location
_PACKAGE_DIR = Path(__file__).resolve().parent.parent  # kantorku/
_PROJECT_ROOT = _PACKAGE_DIR.parent  # framework/
WORKERS_DIR = _PROJECT_ROOT / "workers"
SKILLS_DIR = _PROJECT_ROOT / "skills"
CONFIG_PATH = _PROJECT_ROOT / "kantorku.toml"

BULLET_CHAR = "\u2022"
MASK_CHAR = "\u2022"
CHECK_MARK = "\u2713"
CROSS_MARK = "\u2717"


def _mask_value(value: str) -> str:
    """Mask a string value with bullet characters. Never expose the real value."""
    if not value:
        return "(unset)"
    if value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        is_set = bool(os.environ.get(env_var))
        status = (
            f"[green]{CHECK_MARK} set[/green]"
            if is_set
            else f"[red]{CROSS_MARK} unset[/red]"
        )
        return f"${{{env_var}}}  {status}"
    return MASK_CHAR * 8


def _load_workers_from_dir() -> list[Any]:
    """Load WorkerIdentity objects from the workers directory."""
    from kantorku.worker.identity import WorkerIdentity

    workers: list[WorkerIdentity] = []
    if not WORKERS_DIR.exists():
        return workers
    for subdir in sorted(WORKERS_DIR.iterdir()):
        if subdir.is_dir() and (subdir / "plugin.json").exists():
            try:
                identity = WorkerIdentity.from_directory(subdir)
                workers.append(identity)
            except Exception:
                logger.warning("Skipping problematic worker: %s", subdir, exc_info=True)
    return workers


def _load_config() -> dict[str, Any]:
    """Load kantorku.toml config if available."""
    try:
        from kantorku.config.settings import KantorkuConfig

        if CONFIG_PATH.exists():
            config = KantorkuConfig.from_toml(str(CONFIG_PATH))
            return {
                "conductor_model": config.conductor_model,
                "providers": config.providers,
                "workers": {
                    wid: {"model": w.model, "squad": w.squad, "role": w.role}
                    for wid, w in config.workers.items()
                },
            }
    except Exception:
        logger.debug("Could not load kantorku.toml", exc_info=True)
    return {}


def _load_skills() -> list[dict[str, str]]:
    """Load skill files from the skills directory."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    skills: list[dict[str, str]] = []
    for fpath in sorted(SKILLS_DIR.glob("*.md")):
        try:
            content = fpath.read_text(encoding="utf-8")
            skills.append({"name": fpath.stem, "content": content, "path": str(fpath)})
        except Exception:
            logger.warning("Could not read skill: %s", fpath, exc_info=True)
    return skills


def _collect_api_keys(
    config_data: dict[str, Any], workers: list[Any]
) -> list[dict[str, Any]]:
    """Collect all API keys from config and worker plugin.json files."""
    keys: list[dict[str, Any]] = []
    seen: set[str] = set()

    # From config providers
    providers = config_data.get("providers", {})
    for provider_name, provider_config in providers.items():
        for field_name, value in provider_config.items():
            if "key" in field_name.lower() or "api_key" in field_name.lower():
                key_id = f"config:{provider_name}:{field_name}"
                if key_id not in seen:
                    seen.add(key_id)
                    is_set = False
                    if (
                        isinstance(value, str)
                        and value.startswith("${")
                        and value.endswith("}")
                    ):
                        env_var = value[2:-1]
                        is_set = bool(os.environ.get(env_var))
                    elif value:
                        is_set = True
                    keys.append(
                        {
                            "source": "kantorku.toml",
                            "provider": provider_name,
                            "field": field_name,
                            "value": value,
                            "is_set": is_set,
                            "key_id": key_id,
                        }
                    )

    # From worker plugin.json files
    for worker in workers:
        api = worker.api if hasattr(worker, "api") else None
        if api and api.api_key:
            key_id = f"worker:{worker.id}:api_key"
            if key_id not in seen:
                seen.add(key_id)
                is_set = False
                raw_key = api.api_key
                if raw_key.startswith("${") and raw_key.endswith("}"):
                    env_var = raw_key[2:-1]
                    is_set = bool(os.environ.get(env_var))
                elif raw_key:
                    is_set = True
                keys.append(
                    {
                        "source": f"worker/{worker.id}",
                        "provider": api.provider or worker.id,
                        "field": "api_key",
                        "value": raw_key,
                        "is_set": is_set,
                        "key_id": key_id,
                    }
                )

    return keys


# ─── CSS ───────────────────────────────────────────────────────────────

_CSS = f"""
SettingsScreen {{
    background: {KANTORKU_THEME['background']};
    layout: vertical;
}}

#settings-header {{
    background: {KANTORKU_THEME['surface']};
    color: {KANTORKU_THEME['text']};
    padding: 0 2;
    height: 3;
    border-bottom: solid {KANTORKU_THEME['primary']};
}}

#settings-header-label {{
    color: {KANTORKU_THEME['text']};
}}

#settings-main {{
    height: 1fr;
}}

TabbedContent {{
    height: 1fr;
}}

/* General tab */
.general-row {{
    layout: horizontal;
    height: 3;
    padding: 0 1;
    align: left middle;
}}

.general-row-label {{
    width: 22;
    color: {KANTORKU_THEME['text']};
}}

.general-row Input {{
    width: 1fr;
}}

.general-row Select {{
    width: 1fr;
}}

.general-row Switch {{
    width: auto;
}}

#redteam-status {{
    color: {KANTORKU_THEME['muted']};
    margin-left: 1;
}}

/* Workers tab */
#workers-layout {{
    layout: horizontal;
    height: 1fr;
}}

#workers-sidebar {{
    width: 28;
    height: 1fr;
    border-right: solid {KANTORKU_THEME['primary']};
    background: {KANTORKU_THEME['surface']};
}}

#workers-sidebar-header {{
    background: {KANTORKU_THEME['surface']};
    color: {KANTORKU_THEME['text']};
    padding: 0 1;
    height: 2;
    text-style: bold;
}}

#worker-list {{
    height: 1fr;
}}

#worker-list ListItem {{
    padding: 0 1;
}}

#worker-list ListItem:hover {{
    background: {KANTORKU_THEME['primary']} 22;
}}

#worker-list ListItem.-active {{
    background: {KANTORKU_THEME['primary']} 33;
}}

#workers-detail {{
    width: 1fr;
    height: 1fr;
}}

#workers-detail-header {{
    background: {KANTORKU_THEME['surface']};
    color: {KANTORKU_THEME['text']};
    padding: 0 1;
    height: 2;
    text-style: bold;
    border-bottom: solid {KANTORKU_THEME['muted']};
}}

#worker-detail-tabs {{
    height: 1fr;
}}

#worker-detail-content {{
    height: 1fr;
}}

#skill-textarea {{
    height: 1fr;
}}

#tools-list {{
    height: 1fr;
}}

#worker-tools-content {{
    height: 1fr;
    padding: 0 1;
}}

.tools-section-header {{
    color: #f1f5f9;
    text-style: bold;
    margin-top: 1;
    height: 2;
}}

.tool-item-row {{
    layout: horizontal;
    height: 3;
    padding: 0 1;
    align: left middle;
}}

.tool-item-name {{
    width: 1fr;
    color: #f1f5f9;
}}

.tool-remove-btn {{
    width: 6;
    background: #1e293b;
    color: #ef4444;
    margin-left: 1;
}}

.tool-remove-btn:hover {{
    background: #ef4444;
    color: $text;
}}

.tool-add-row {{
    layout: horizontal;
    height: 3;
    padding: 0 1;
    align: left middle;
    dock: bottom;
}}

.tool-add-input {{
    width: 1fr;
}}

.tool-add-btn {{
    width: 10;
    background: #3b82f6;
    color: $text;
    text-style: bold;
    margin-left: 1;
}}

.tool-add-btn:hover {{
    background: #2563eb;
}}

#worker-skills-content {{
    height: 1fr;
    padding: 0 1;
}}

#delete-worker-btn {{
    background: #ef4444;
    color: $text;
    text-style: bold;
    margin-left: 1;
}}

#delete-worker-btn:hover {{
    background: #dc2626;
}}

.api-field-row {{
    layout: horizontal;
    height: 3;
    padding: 0 1;
    align: left middle;
}}

.api-field-label {{
    width: 14;
    color: {KANTORKU_THEME['text']};
}}

.api-field-row Input {{
    width: 1fr;
}}

#workers-bottom-bar {{
    dock: bottom;
    height: 3;
    padding: 0 1;
    background: {KANTORKU_THEME['surface']};
    layout: horizontal;
}}

#save-worker-btn {{
    background: {KANTORKU_THEME['success']};
    color: $text;
    text-style: bold;
    margin-right: 1;
}}

#save-worker-btn:hover {{
    background: #059669;
}}

#new-worker-btn {{
    background: {KANTORKU_THEME['info']};
    color: $text;
    text-style: bold;
}}

#new-worker-btn:hover {{
    background: #2563eb;
}}

#worker-save-status {{
    color: {KANTORKU_THEME['text']};
    margin-left: 2;
    padding: 1 0;
}}

/* Skills tab */
#skills-layout {{
    layout: horizontal;
    height: 1fr;
}}

#skills-sidebar {{
    width: 24;
    height: 1fr;
    border-right: solid {KANTORKU_THEME['accent']};
    background: {KANTORKU_THEME['surface']};
}}

#skills-sidebar-header {{
    background: {KANTORKU_THEME['surface']};
    color: {KANTORKU_THEME['text']};
    padding: 0 1;
    height: 2;
    text-style: bold;
}}

#skill-list {{
    height: 1fr;
}}

#skill-list ListItem {{
    padding: 0 1;
}}

#skill-list ListItem:hover {{
    background: {KANTORKU_THEME['accent']} 22;
}}

#skill-list ListItem.-active {{
    background: {KANTORKU_THEME['accent']} 33;
}}

#skills-detail {{
    width: 1fr;
    height: 1fr;
}}

#skills-detail-header {{
    background: {KANTORKU_THEME['surface']};
    color: {KANTORKU_THEME['text']};
    padding: 0 1;
    height: 2;
    text-style: bold;
    border-bottom: solid {KANTORKU_THEME['muted']};
}}

#skill-editor-area {{
    height: 1fr;
}}

#skills-bottom-bar {{
    dock: bottom;
    height: 3;
    padding: 0 1;
    background: {KANTORKU_THEME['surface']};
    layout: horizontal;
}}

#save-skill-btn {{
    background: {KANTORKU_THEME['success']};
    color: $text;
    text-style: bold;
    margin-right: 1;
}}

#save-skill-btn:hover {{
    background: #059669;
}}

#new-skill-btn {{
    background: {KANTORKU_THEME['accent']};
    color: $text;
    text-style: bold;
}}

#new-skill-btn:hover {{
    background: #d97706;
}}

#skill-save-status {{
    color: {KANTORKU_THEME['text']};
    margin-left: 2;
    padding: 1 0;
}}

/* API Keys tab */
#api-keys-list {{
    height: 1fr;
}}

.api-key-row {{
    layout: horizontal;
    height: 3;
    padding: 0 1;
    align: left middle;
    border-bottom: solid {KANTORKU_THEME['surface']};
}}

.api-key-row:hover {{
    background: {KANTORKU_THEME['surface']};
}}

.api-key-provider {{
    width: 18;
    color: {KANTORKU_THEME['text']};
    text-style: bold;
}}

.api-key-source {{
    width: 20;
    color: {KANTORKU_THEME['muted']};
}}

.api-key-value {{
    width: 1fr;
    color: {KANTORKU_THEME['muted']};
}}

.api-key-status {{
    width: 10;
}}

.api-key-edit-btn {{
    width: 10;
    background: {KANTORKU_THEME['surface']};
    color: {KANTORKU_THEME['text']};
    margin-left: 1;
}}

.api-key-edit-btn:hover {{
    background: {KANTORKU_THEME['primary']};
}}

/* API key edit dialog */
#api-key-edit-dialog {{
    layout: vertical;
    padding: 1 2;
    height: auto;
    background: {KANTORKU_THEME['surface']};
    border: solid {KANTORKU_THEME['primary']};
    margin: 1;
}}

#api-key-edit-dialog Label {{
    color: {KANTORKU_THEME['text']};
}}

#api-key-edit-input {{
    width: 1fr;
    margin-bottom: 1;
}}

#api-key-edit-btns {{
    layout: horizontal;
    height: 3;
}}

#api-key-save-btn {{
    background: {KANTORKU_THEME['success']};
    color: $text;
    text-style: bold;
    margin-right: 1;
}}

#api-key-cancel-btn {{
    background: {KANTORKU_THEME['error']};
    color: $text;
    text-style: bold;
}}
"""


class SettingsScreen(Screen):
    """
    Settings overlay for the KantorKu TUI.

    4-tab interface:
      1. General   — Theme, Language, Conductor model, Redteam toggle
      2. Workers   — Browse/edit workers, system prompts, tools, API config
      3. Skills    — Browse/edit skill markdown files
      4. API Keys  — View and manage provider API keys (masked)
    """

    CSS = _CSS

    BINDINGS = [
        Binding("escape", "close_settings", "Close", show=True),
    ]

    # ── Reactive state ──

    selected_worker_id: reactive[str] = reactive("")
    selected_skill_name: reactive[str] = reactive("")
    worker_save_status: reactive[str] = reactive("")
    skill_save_status: reactive[str] = reactive("")
    redteam_enabled: reactive[bool] = reactive(True)

    def __init__(self, tui_app: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._tui_app = tui_app
        self._workers: list[Any] = _load_workers_from_dir()
        self._config_data: dict[str, Any] = _load_config()
        self._skills: list[dict[str, str]] = _load_skills()
        self._api_keys: list[dict[str, Any]] = _collect_api_keys(
            self._config_data, self._workers
        )
        self._editing_api_key_id: str = ""
        # Track dirty state for the currently selected worker
        self._worker_skill_cache: dict[str, str] = {}
        self._worker_api_cache: dict[str, dict[str, str]] = {}
        self._worker_caps_cache: dict[str, dict[str, bool]] = {}
        self._worker_tools_cache: dict[str, list[str]] = {}
        self._worker_skills_cache: dict[str, list[str]] = {}

    # ── Compose ────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="settings-header"):
            yield Label(
                "[bold]KantorKu Settings[/bold]  [dim]ESC to close[/dim]",
                id="settings-header-label",
            )

        with VerticalScroll(id="settings-main"):
            with TabbedContent():
                # ── Tab 1: General ──
                with TabPane("General", id="general-tab"):
                    # Theme selector
                    with Horizontal(classes="general-row"):
                        yield Label("Theme", classes="general-row-label")
                        yield Select(
                            options=[
                                ("KantorKu", "kantorku"),
                                ("Dark", "dark"),
                                ("Light", "light"),
                            ],
                            value="kantorku",
                            id="theme-select",
                        )
                    # Language (placeholder)
                    with Horizontal(classes="general-row"):
                        yield Label("Language", classes="general-row-label")
                        yield Input(
                            value="English",
                            placeholder="Language preference (placeholder)",
                            id="language-input",
                        )
                    # Conductor model display
                    conductor_model = self._config_data.get(
                        "conductor_model", "anthropic/claude-opus-4-6"
                    )
                    with Horizontal(classes="general-row"):
                        yield Label("Conductor Model", classes="general-row-label")
                        yield Input(
                            value=conductor_model,
                            id="conductor-model-input",
                        )
                    # Redteam toggle
                    redteam_env = os.environ.get(
                        "KANTORKU_REDTEAM_ENABLED", "true"
                    ).lower() in ("true", "1", "yes")
                    self.redteam_enabled = redteam_env
                    with Horizontal(classes="general-row"):
                        yield Label("Redteam Enabled", classes="general-row-label")
                        yield Switch(value=redteam_env, id="redteam-switch")
                        yield Label(
                            f"[{'green' if redteam_env else 'red'}]"
                            f"{'ON' if redteam_env else 'OFF'}[/]",
                            id="redteam-status",
                        )

                # ── Tab 2: Workers ──
                with TabPane("Workers", id="workers-tab"):
                    with Horizontal(id="workers-layout"):
                        # Left sidebar: worker list
                        with Vertical(id="workers-sidebar"):
                            yield Label(
                                "Workers", id="workers-sidebar-header"
                            )
                            worker_list_items = []
                            for w in self._workers:
                                squad = w.squad or "uncategorized"
                                squad_color = SQUAD_COLORS.get(squad, "dim")
                                display = (
                                    f"[{squad_color}][{squad}][/{squad_color}] {w.id}"
                                )
                                worker_list_items.append(
                                    ListItem(Label(display), name=w.id)
                                )
                            yield ListView(*worker_list_items, id="worker-list")

                        # Right detail panel
                        with Vertical(id="workers-detail"):
                            yield Label(
                                "Select a worker", id="workers-detail-header"
                            )
                            with TabbedContent(id="worker-detail-tabs"):
                                # System Prompt sub-tab
                                with TabPane(
                                    "System Prompt", id="worker-prompt-tab"
                                ):
                                    yield TextArea(
                                        id="skill-textarea",
                                        language="markdown",
                                    )
                                # Tools sub-tab
                                with TabPane("Tools", id="worker-tools-tab"):
                                    with Vertical(id="worker-tools-content"):
                                        yield Label("Allowed Tools", classes="tools-section-header")
                                        with VerticalScroll(id="allowed-tools-list"):
                                            pass  # Populated dynamically
                                        yield Label("Allowed Skills", classes="tools-section-header")
                                        with VerticalScroll(id="allowed-skills-list"):
                                            pass  # Populated dynamically
                                        with Horizontal(classes="tool-add-row"):
                                            yield Input(
                                                placeholder="Add tool (e.g. write_code)",
                                                id="add-tool-input",
                                                classes="tool-add-input",
                                            )
                                            yield Button("+ Tool", id="add-tool-btn", classes="tool-add-btn")
                                # API Config sub-tab
                                with TabPane("API Config", id="worker-api-tab"):
                                    with Vertical(id="worker-detail-content"):
                                        with Horizontal(classes="api-field-row"):
                                            yield Label(
                                                "Provider",
                                                classes="api-field-label",
                                            )
                                            yield Input(
                                                id="worker-api-provider",
                                                placeholder="e.g. anthropic",
                                            )
                                        with Horizontal(classes="api-field-row"):
                                            yield Label(
                                                "Model",
                                                classes="api-field-label",
                                            )
                                            yield Input(
                                                id="worker-api-model",
                                                placeholder="e.g. claude-sonnet-4-6",
                                            )
                                        with Horizontal(classes="api-field-row"):
                                            yield Label(
                                                "API Key",
                                                classes="api-field-label",
                                            )
                                            yield Input(
                                                id="worker-api-key",
                                                placeholder="${ENV_VAR} or value",
                                                password=True,
                                            )
                                        with Horizontal(classes="api-field-row"):
                                            yield Label(
                                                "Base URL",
                                                classes="api-field-label",
                                            )
                                            yield Input(
                                                id="worker-api-base-url",
                                                placeholder="https://api.example.com/v1",
                                            )
                                # Skills sub-tab
                                with TabPane("Skills", id="worker-skills-tab"):
                                    with Vertical(id="worker-skills-content"):
                                        yield Label("Allowed Skills", classes="tools-section-header")
                                        with VerticalScroll(id="worker-skills-list"):
                                            pass  # Populated dynamically
                                        with Horizontal(classes="tool-add-row"):
                                            yield Input(
                                                placeholder="Add skill (e.g. rust_expert)",
                                                id="add-skill-input",
                                                classes="tool-add-input",
                                            )
                                            yield Button("+ Skill", id="add-skill-btn", classes="tool-add-btn")

                    # Bottom bar (outside workers-layout, inside workers tab)
                    with Horizontal(id="workers-bottom-bar"):
                        yield Button(
                            f"{CHECK_MARK} Save Worker", id="save-worker-btn"
                        )
                        yield Button("+ New Worker", id="new-worker-btn")
                        yield Button(f"{CROSS_MARK} Delete Worker", id="delete-worker-btn")
                        yield Label("", id="worker-save-status")

                # ── Tab 3: Skills ──
                with TabPane("Skills", id="skills-tab"):
                    with Horizontal(id="skills-layout"):
                        # Left sidebar: skill list
                        with Vertical(id="skills-sidebar"):
                            yield Label("Skills", id="skills-sidebar-header")
                            skill_list_items = []
                            for s in self._skills:
                                skill_list_items.append(
                                    ListItem(Label(s["name"]), name=s["name"])
                                )
                            yield ListView(*skill_list_items, id="skill-list")

                        # Right detail panel
                        with Vertical(id="skills-detail"):
                            yield Label(
                                "Select a skill", id="skills-detail-header"
                            )
                            yield TextArea(
                                id="skill-editor-area", language="markdown"
                            )

                    # Bottom bar
                    with Horizontal(id="skills-bottom-bar"):
                        yield Button(
                            f"{CHECK_MARK} Save Skill", id="save-skill-btn"
                        )
                        yield Button("+ New Skill", id="new-skill-btn")
                        yield Label("", id="skill-save-status")

                # ── Tab 4: API Keys ──
                with TabPane("API Keys", id="api-keys-tab"):
                    with VerticalScroll(id="api-keys-list"):
                        for key_info in self._api_keys:
                            with Horizontal(classes="api-key-row"):
                                yield Label(
                                    key_info["provider"],
                                    classes="api-key-provider",
                                )
                                yield Label(
                                    key_info["source"], classes="api-key-source"
                                )
                                yield Label(
                                    _mask_value(key_info["value"]),
                                    classes="api-key-value",
                                )
                                status_color = (
                                    "green" if key_info["is_set"] else "red"
                                )
                                if key_info["is_set"]:
                                    status_text = (
                                        f"[{status_color}]{CHECK_MARK} set[/{status_color}]"
                                    )
                                else:
                                    status_text = (
                                        f"[{status_color}]{CROSS_MARK} unset[/{status_color}]"
                                    )
                                yield Label(
                                    status_text, classes="api-key-status"
                                )
                                yield Button(
                                    "Edit",
                                    classes="api-key-edit-btn",
                                    name=key_info["key_id"],
                                )

        yield Footer()

    # ── Lifecycle ──────────────────────────────────────────────────────

    def on_mount(self) -> None:
        """Initialize UI state on mount."""
        # Load first worker if available
        if self._workers:
            self.selected_worker_id = self._workers[0].id
            self._populate_worker_detail(self._workers[0])

        # Load first skill if available
        if self._skills:
            self.selected_skill_name = self._skills[0]["name"]
            self._populate_skill_detail(self._skills[0])

    # ── Actions ────────────────────────────────────────────────────────

    def action_close_settings(self) -> None:
        """Close the settings overlay."""
        self.app.pop_screen()

    # ── General Tab Handlers ───────────────────────────────────────────

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch toggle events."""
        if event.switch.id == "redteam-switch":
            self.redteam_enabled = event.value
            try:
                status_label = self.query_one("#redteam-status", Label)
                if event.value:
                    status_label.update("[green]ON[/green]")
                    os.environ["KANTORKU_REDTEAM_ENABLED"] = "true"
                else:
                    status_label.update("[red]OFF[/red]")
                    os.environ["KANTORKU_REDTEAM_ENABLED"] = "false"
            except Exception:
                pass

    # ── Workers Tab Handlers ───────────────────────────────────────────

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle list item selection in worker and skill sidebars."""
        item = event.item
        item_name = item.name if hasattr(item, "name") and item.name else ""

        # Worker list
        if item_name and item_name in {w.id for w in self._workers}:
            # Cache current worker edits before switching
            self._cache_current_worker_edits()
            self.selected_worker_id = item_name
            worker = next(
                (w for w in self._workers if w.id == item_name), None
            )
            if worker:
                self._populate_worker_detail(worker)
            return

        # Skill list
        if item_name and item_name in {s["name"] for s in self._skills}:
            self.selected_skill_name = item_name
            skill = next(
                (s for s in self._skills if s["name"] == item_name), None
            )
            if skill:
                self._populate_skill_detail(skill)

    def _populate_worker_detail(self, worker: Any) -> None:
        """Populate the worker detail panel with data from a WorkerIdentity."""
        try:
            header = self.query_one("#workers-detail-header", Label)
            squad = worker.squad or "uncategorized"
            squad_color = SQUAD_COLORS.get(squad, "dim")
            header.update(
                f"[{squad_color}][{squad}][/{squad_color}] "
                f"{worker.display_name or worker.id}  "
                f"[dim]{worker.role or ''}[/dim]"
            )
        except Exception:
            pass

        # System Prompt (SKILL.md)
        skill_text = worker.skill_md or ""
        # Use cache if available
        if worker.id in self._worker_skill_cache:
            skill_text = self._worker_skill_cache[worker.id]
        try:
            textarea = self.query_one("#skill-textarea", TextArea)
            textarea.load_text(skill_text)
        except Exception:
            pass

        # Allowed Tools
        try:
            tools_list = self.query_one("#allowed-tools-list", VerticalScroll)
            tools_list.remove_children()
            tools = worker.allowed_tools or []
            if worker.id in self._worker_tools_cache:
                tools = self._worker_tools_cache[worker.id]
            for tool in tools:
                row = Horizontal(classes="tool-item-row")
                tool_label = Label(tool, classes="tool-item-name")
                remove_btn = Button("X", classes="tool-remove-btn", name=f"remove_tool:{tool}")
                row.mount(tool_label)
                row.mount(remove_btn)
                tools_list.mount(row)
        except Exception:
            pass

        # Allowed Skills (in worker detail)
        try:
            skills_list = self.query_one("#worker-skills-list", VerticalScroll)
            skills_list.remove_children()
            skills = worker.allowed_skills or []
            if worker.id in self._worker_skills_cache:
                skills = self._worker_skills_cache[worker.id]
            for skill in skills:
                row = Horizontal(classes="tool-item-row")
                skill_label = Label(skill, classes="tool-item-name")
                remove_btn = Button("X", classes="tool-remove-btn", name=f"remove_skill:{skill}")
                row.mount(skill_label)
                row.mount(remove_btn)
                skills_list.mount(row)
        except Exception:
            pass

        # API Config
        api = worker.api if hasattr(worker, "api") else None
        if api:
            # Use cache if available
            api_cache = self._worker_api_cache.get(worker.id, {})
            try:
                provider_input = self.query_one("#worker-api-provider", Input)
                provider_input.value = api_cache.get("provider", api.provider or "")
            except Exception:
                pass
            try:
                model_input = self.query_one("#worker-api-model", Input)
                model_input.value = api_cache.get("model", api.model or "")
            except Exception:
                pass
            try:
                key_input = self.query_one("#worker-api-key", Input)
                key_input.value = api_cache.get("api_key", api.api_key or "")
            except Exception:
                pass
            try:
                base_url_input = self.query_one("#worker-api-base-url", Input)
                base_url_input.value = api_cache.get(
                    "base_url", api.base_url or ""
                )
            except Exception:
                pass

    def _cache_current_worker_edits(self) -> None:
        """Cache edits from the current worker detail before switching."""
        if not self.selected_worker_id:
            return
        wid = self.selected_worker_id

        # Cache SKILL.md text
        try:
            textarea = self.query_one("#skill-textarea", TextArea)
            self._worker_skill_cache[wid] = textarea.text
        except Exception:
            pass

        # Cache API fields
        api_cache: dict[str, str] = {}
        try:
            api_cache["provider"] = self.query_one(
                "#worker-api-provider", Input
            ).value
        except Exception:
            pass
        try:
            api_cache["model"] = self.query_one(
                "#worker-api-model", Input
            ).value
        except Exception:
            pass
        try:
            api_cache["api_key"] = self.query_one(
                "#worker-api-key", Input
            ).value
        except Exception:
            pass
        try:
            api_cache["base_url"] = self.query_one(
                "#worker-api-base-url", Input
            ).value
        except Exception:
            pass
        if api_cache:
            self._worker_api_cache[wid] = api_cache

        # Cache allowed tools
        try:
            worker = next(
                (w for w in self._workers if w.id == wid), None
            )
            if worker:
                # Read current allowed_tools from the list
                tools_list = self.query_one("#allowed-tools-list", VerticalScroll)
                tools = []
                for child in tools_list.children:
                    try:
                        label = child.query_one(".tool-item-name", Label)
                        tools.append(str(label.renderable))
                    except Exception:
                        pass
                if tools or worker.allowed_tools:
                    self._worker_tools_cache[wid] = tools
        except Exception:
            pass

        # Cache allowed skills
        try:
            worker = next(
                (w for w in self._workers if w.id == wid), None
            )
            if worker:
                skills_list = self.query_one("#worker-skills-list", VerticalScroll)
                skills = []
                for child in skills_list.children:
                    try:
                        label = child.query_one(".tool-item-name", Label)
                        skills.append(str(label.renderable))
                    except Exception:
                        pass
                if skills or worker.allowed_skills:
                    self._worker_skills_cache[wid] = skills
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses across all tabs."""
        btn = event.button
        btn_id = btn.id or ""
        btn_classes = btn.classes

        # Save Worker
        if btn_id == "save-worker-btn":
            self._save_worker()
            return

        # New Worker
        if btn_id == "new-worker-btn":
            self._create_new_worker()
            return

        # Delete Worker
        if btn_id == "delete-worker-btn":
            self._delete_worker()
            return

        # Add Tool
        if btn_id == "add-tool-btn":
            self._add_tool()
            return

        # Add Skill
        if btn_id == "add-skill-btn":
            self._add_skill()
            return

        # Remove tool/skill
        if "tool-remove-btn" in btn_classes:
            name = btn.name or ""
            self._remove_tool_or_skill(name)
            return

        # Save Skill
        if btn_id == "save-skill-btn":
            self._save_skill()
            return

        # New Skill
        if btn_id == "new-skill-btn":
            self._create_new_skill()
            return

        # API Key edit
        if "api-key-edit-btn" in btn_classes:
            key_id = btn.name or ""
            if key_id:
                self._edit_api_key(key_id)
            return

        # API Key edit dialog buttons
        if btn_id == "api-key-save-btn":
            self._save_api_key_edit()
            return

        if btn_id == "api-key-cancel-btn":
            self._cancel_api_key_edit()
            return

    # ── Worker Persistence ─────────────────────────────────────────────

    def _save_worker(self) -> None:
        """Save the currently selected worker's changes to disk."""
        if not self.selected_worker_id:
            return

        wid = self.selected_worker_id
        worker = next((w for w in self._workers if w.id == wid), None)
        if not worker:
            return

        try:
            source_dir = (
                Path(worker.source_dir) if worker.source_dir else WORKERS_DIR / wid
            )
            if not source_dir.exists():
                self._set_worker_save_status(
                    f"[red]{CROSS_MARK} Worker directory not found[/red]"
                )
                return

            # Flush caches
            self._cache_current_worker_edits()

            # Update SKILL.md
            skill_text = self._worker_skill_cache.get(wid, worker.skill_md or "")
            skill_path = source_dir / "SKILL.md"
            skill_path.write_text(skill_text, encoding="utf-8")
            worker.skill_md = skill_text

            # Update API config
            api_cache = self._worker_api_cache.get(wid, {})
            if api_cache:
                if "provider" in api_cache:
                    worker.api.provider = api_cache["provider"]
                if "model" in api_cache:
                    worker.api.model = api_cache["model"]
                if "api_key" in api_cache:
                    worker.api.api_key = api_cache["api_key"]
                if "base_url" in api_cache:
                    worker.api.base_url = api_cache["base_url"]

            # Update allowed_tools
            tools_cache = self._worker_tools_cache.get(wid, None)
            if tools_cache is not None:
                worker.allowed_tools = tools_cache

            # Update allowed_skills
            skills_cache = self._worker_skills_cache.get(wid, None)
            if skills_cache is not None:
                worker.allowed_skills = skills_cache

            # Write plugin.json using to_plugin_json()
            plugin_path = source_dir / "plugin.json"
            plugin_data = worker.to_plugin_json()
            plugin_path.write_text(
                json.dumps(plugin_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            # Try hot-reload in embedded mode
            office = self._get_office()
            if office and hasattr(office, "registry"):
                registry = office.registry
                # Check if reload_worker method exists
                if hasattr(registry, "reload_worker"):
                    try:
                        registry.reload_worker(wid)
                        self._set_worker_save_status(
                            f"[green]{CHECK_MARK} Saved & reloaded[/green]"
                        )
                        return
                    except Exception:
                        pass

                # Fallback: re-register identity
                try:
                    from kantorku.worker.identity import WorkerIdentity

                    updated_identity = WorkerIdentity.from_directory(source_dir)
                    registry.register_identity(updated_identity)
                except Exception:
                    pass

            self._set_worker_save_status(
                f"[yellow]{CHECK_MARK} Saved — restart to apply[/yellow]"
            )

        except PermissionError:
            self._set_worker_save_status(
                f"[red]{CROSS_MARK} Permission denied writing files[/red]"
            )
        except Exception as e:
            self._set_worker_save_status(f"[red]{CROSS_MARK} Error: {e}[/red]")

    def _set_worker_save_status(self, message: str) -> None:
        """Update the worker save status label."""
        self.worker_save_status = message
        try:
            status = self.query_one("#worker-save-status", Label)
            status.update(message)
        except Exception:
            pass

    def _create_new_worker(self) -> None:
        """Create a new worker using WorkerGenerator."""
        try:
            from kantorku.worker.generator import WorkerGenerator

            # Generate a unique worker ID
            existing_ids = {w.id for w in self._workers}
            base_id = "new_worker"
            counter = 1
            new_id = base_id
            while new_id in existing_ids:
                new_id = f"{base_id}_{counter}"
                counter += 1

            gen = WorkerGenerator()
            gen.create(
                new_id,
                base_dir=WORKERS_DIR,
                model="ollama/llama3",
                squad="support",
            )

            # Reload workers list
            self._workers = _load_workers_from_dir()
            self._rebuild_worker_list()

            # Select the new worker
            self.selected_worker_id = new_id
            new_worker = next(
                (w for w in self._workers if w.id == new_id), None
            )
            if new_worker:
                self._populate_worker_detail(new_worker)

            self._set_worker_save_status(
                f"[green]{CHECK_MARK} Created: {new_id}[/green]"
            )

        except FileExistsError:
            self._set_worker_save_status("[yellow]Worker already exists[/yellow]")
        except ValueError as e:
            self._set_worker_save_status(f"[red]{CROSS_MARK} {e}[/red]")
        except Exception as e:
            self._set_worker_save_status(f"[red]{CROSS_MARK} Error: {e}[/red]")

    def _rebuild_worker_list(self) -> None:
        """Rebuild the worker sidebar list after changes."""
        try:
            list_view = self.query_one("#worker-list", ListView)
            list_view.remove_children()
            for w in self._workers:
                squad = w.squad or "uncategorized"
                squad_color = SQUAD_COLORS.get(squad, "dim")
                display = (
                    f"[{squad_color}][{squad}][/{squad_color}] {w.id}"
                )
                list_view.append(ListItem(Label(display), name=w.id))
        except Exception:
            pass

    def _delete_worker(self) -> None:
        """Delete the currently selected worker."""
        if not self.selected_worker_id:
            return

        wid = self.selected_worker_id
        worker = next((w for w in self._workers if w.id == wid), None)
        if not worker:
            return

        try:
            source_dir = (
                Path(worker.source_dir) if worker.source_dir else WORKERS_DIR / wid
            )
            if source_dir.exists():
                import shutil
                shutil.rmtree(source_dir)

            # Remove from Office registry if embedded
            office = self._get_office()
            if office and hasattr(office, "registry"):
                try:
                    office.registry.fire(wid)
                except Exception:
                    pass

            # Clear caches
            self._worker_skill_cache.pop(wid, None)
            self._worker_api_cache.pop(wid, None)
            self._worker_tools_cache.pop(wid, None)
            self._worker_skills_cache.pop(wid, None)

            # Reload workers
            self._workers = _load_workers_from_dir()
            self._rebuild_worker_list()

            # Select first worker if available
            if self._workers:
                self.selected_worker_id = self._workers[0].id
                self._populate_worker_detail(self._workers[0])
            else:
                self.selected_worker_id = ""

            self._set_worker_save_status(
                f"[red]{CROSS_MARK} Deleted: {wid}[/red]"
            )
        except Exception as e:
            self._set_worker_save_status(
                f"[red]{CROSS_MARK} Delete failed: {e}[/red]"
            )

    def _add_tool(self) -> None:
        """Add a tool to the current worker's allowed_tools list."""
        if not self.selected_worker_id:
            return

        try:
            tool_input = self.query_one("#add-tool-input", Input)
            tool_name = tool_input.value.strip()
            if not tool_name:
                return

            wid = self.selected_worker_id
            tools = self._worker_tools_cache.get(wid, [])

            # Also include existing tools from worker identity
            worker = next((w for w in self._workers if w.id == wid), None)
            if worker and not self._worker_tools_cache.get(wid):
                tools = list(worker.allowed_tools or [])

            if tool_name not in tools:
                tools.append(tool_name)
                self._worker_tools_cache[wid] = tools

                # Re-render the tools list
                tools_list = self.query_one("#allowed-tools-list", VerticalScroll)
                row = Horizontal(classes="tool-item-row")
                tool_label = Label(tool_name, classes="tool-item-name")
                remove_btn = Button("X", classes="tool-remove-btn", name=f"remove_tool:{tool_name}")
                row.mount(tool_label)
                row.mount(remove_btn)
                tools_list.mount(row)

            tool_input.value = ""
        except Exception:
            pass

    def _add_skill(self) -> None:
        """Add a skill to the current worker's allowed_skills list."""
        if not self.selected_worker_id:
            return

        try:
            skill_input = self.query_one("#add-skill-input", Input)
            skill_name = skill_input.value.strip()
            if not skill_name:
                return

            wid = self.selected_worker_id
            skills = self._worker_skills_cache.get(wid, [])

            worker = next((w for w in self._workers if w.id == wid), None)
            if worker and not self._worker_skills_cache.get(wid):
                skills = list(worker.allowed_skills or [])

            if skill_name not in skills:
                skills.append(skill_name)
                self._worker_skills_cache[wid] = skills

                skills_list = self.query_one("#worker-skills-list", VerticalScroll)
                row = Horizontal(classes="tool-item-row")
                skill_label = Label(skill_name, classes="tool-item-name")
                remove_btn = Button("X", classes="tool-remove-btn", name=f"remove_skill:{skill_name}")
                row.mount(skill_label)
                row.mount(remove_btn)
                skills_list.mount(row)

            skill_input.value = ""
        except Exception:
            pass

    def _remove_tool_or_skill(self, name: str) -> None:
        """Remove a tool or skill from the current worker's list."""
        if not self.selected_worker_id or not name:
            return

        wid = self.selected_worker_id

        if name.startswith("remove_tool:"):
            tool_name = name[len("remove_tool:"):]
            tools = self._worker_tools_cache.get(wid, [])
            if tool_name in tools:
                tools.remove(tool_name)
                self._worker_tools_cache[wid] = tools
            # Re-render
            worker = next((w for w in self._workers if w.id == wid), None)
            if worker:
                self._populate_worker_detail(worker)

        elif name.startswith("remove_skill:"):
            skill_name = name[len("remove_skill:"):]
            skills = self._worker_skills_cache.get(wid, [])
            if skill_name in skills:
                skills.remove(skill_name)
                self._worker_skills_cache[wid] = skills
            worker = next((w for w in self._workers if w.id == wid), None)
            if worker:
                self._populate_worker_detail(worker)

    # ── Skills Tab Handlers ────────────────────────────────────────────

    def _populate_skill_detail(self, skill: dict[str, str]) -> None:
        """Populate the skill editor with content."""
        try:
            header = self.query_one("#skills-detail-header", Label)
            header.update(f"[bold]{skill['name']}[/bold].md")
        except Exception:
            pass

        try:
            editor = self.query_one("#skill-editor-area", TextArea)
            editor.load_text(skill.get("content", ""))
        except Exception:
            pass

    def _save_skill(self) -> None:
        """Save the currently selected skill file."""
        if not self.selected_skill_name:
            return

        try:
            editor = self.query_one("#skill-editor-area", TextArea)
            content = editor.text

            skill_path = SKILLS_DIR / f"{self.selected_skill_name}.md"
            skill_path.write_text(content, encoding="utf-8")

            # Update local cache
            for s in self._skills:
                if s["name"] == self.selected_skill_name:
                    s["content"] = content
                    break

            self._set_skill_save_status(
                f"[green]{CHECK_MARK} Saved: {self.selected_skill_name}.md[/green]"
            )

        except PermissionError:
            self._set_skill_save_status(
                f"[red]{CROSS_MARK} Permission denied[/red]"
            )
        except Exception as e:
            self._set_skill_save_status(f"[red]{CROSS_MARK} Error: {e}[/red]")

    def _set_skill_save_status(self, message: str) -> None:
        """Update the skill save status label."""
        self.skill_save_status = message
        try:
            status = self.query_one("#skill-save-status", Label)
            status.update(message)
        except Exception:
            pass

    def _create_new_skill(self) -> None:
        """Create a new skill markdown file."""
        existing_names = {s["name"] for s in self._skills}
        base_name = "new_skill"
        counter = 1
        new_name = base_name
        while new_name in existing_names:
            new_name = f"{base_name}_{counter}"
            counter += 1

        try:
            SKILLS_DIR.mkdir(parents=True, exist_ok=True)
            skill_path = SKILLS_DIR / f"{new_name}.md"
            default_content = f"# {new_name}\n\nDescribe this skill here.\n"
            skill_path.write_text(default_content, encoding="utf-8")

            # Reload skills
            self._skills = _load_skills()
            self._rebuild_skill_list()

            # Select the new skill
            self.selected_skill_name = new_name
            new_skill = next(
                (s for s in self._skills if s["name"] == new_name), None
            )
            if new_skill:
                self._populate_skill_detail(new_skill)

            self._set_skill_save_status(
                f"[green]{CHECK_MARK} Created: {new_name}.md[/green]"
            )

        except Exception as e:
            self._set_skill_save_status(f"[red]{CROSS_MARK} Error: {e}[/red]")

    def _rebuild_skill_list(self) -> None:
        """Rebuild the skill sidebar list after changes."""
        try:
            list_view = self.query_one("#skill-list", ListView)
            list_view.remove_children()
            for s in self._skills:
                list_view.append(ListItem(Label(s["name"]), name=s["name"]))
        except Exception:
            pass

    # ── API Keys Tab Handlers ──────────────────────────────────────────

    def _edit_api_key(self, key_id: str) -> None:
        """Show an inline editor for an API key."""
        self._editing_api_key_id = key_id

        key_info = next(
            (k for k in self._api_keys if k["key_id"] == key_id), None
        )
        if not key_info:
            return

        # Find the api-keys-list container and add an edit dialog
        try:
            api_keys_list = self.query_one("#api-keys-list", VerticalScroll)

            # Remove any existing edit dialog
            try:
                existing = self.query_one("#api-key-edit-dialog")
                existing.remove()
            except Exception:
                pass

            # Build the edit dialog programmatically
            dialog = Vertical(id="api-key-edit-dialog")
            title_label = Label(
                f"[bold]Edit API Key: {key_info['provider']} "
                f"({key_info['source']})[/bold]"
            )
            hint_label = Label(
                "[dim]Use ${ENV_VAR} pattern to reference environment "
                "variables,[/dim]\n"
                "[dim]or enter a direct value (stored in plain text).[/dim]"
            )
            key_input = Input(
                value=key_info.get("value", ""),
                placeholder="${API_KEY_NAME} or direct value",
                id="api-key-edit-input",
                password=True,
            )
            btns = Horizontal(id="api-key-edit-btns")
            save_btn = Button(
                f"{CHECK_MARK} Save", id="api-key-save-btn"
            )
            cancel_btn = Button("Cancel", id="api-key-cancel-btn")
            btns.mount(save_btn)
            btns.mount(cancel_btn)
            dialog.mount(title_label)
            dialog.mount(hint_label)
            dialog.mount(key_input)
            dialog.mount(btns)

            api_keys_list.mount(dialog)
            key_input.focus()

        except Exception as e:
            logger.warning(
                "Could not open API key editor: %s", e, exc_info=True
            )

    def _save_api_key_edit(self) -> None:
        """Save the edited API key value."""
        key_id = self._editing_api_key_id
        if not key_id:
            return

        try:
            key_input = self.query_one("#api-key-edit-input", Input)
            new_value = key_input.value.strip()
        except Exception:
            new_value = ""

        # Determine where to write the key
        key_info = next(
            (k for k in self._api_keys if k["key_id"] == key_id), None
        )
        if not key_info:
            self._cancel_api_key_edit()
            return

        source = key_info.get("source", "")

        if source == "kantorku.toml":
            # Write to kantorku.toml — update the provider config
            self._write_api_key_to_config(key_info, new_value)
        elif source.startswith("worker/"):
            # Write to worker's plugin.json
            worker_id = source.replace("worker/", "")
            self._write_api_key_to_worker(worker_id, new_value)

        # Update local cache
        key_info["value"] = new_value
        is_set = False
        if new_value.startswith("${") and new_value.endswith("}"):
            env_var = new_value[2:-1]
            is_set = bool(os.environ.get(env_var))
        elif new_value:
            is_set = True
        key_info["is_set"] = is_set

        # Rebuild the API keys tab
        self._rebuild_api_keys_list()
        self._cancel_api_key_edit()

    def _write_api_key_to_config(
        self, key_info: dict[str, Any], new_value: str
    ) -> None:
        """Write an API key value to kantorku.toml (best effort)."""
        try:
            if not CONFIG_PATH.exists():
                return

            content = CONFIG_PATH.read_text(encoding="utf-8")
            provider = key_info.get("provider", "")
            field = key_info.get("field", "api_key")

            # Find the [providers.PROVIDER] section and update the api_key line
            lines = content.split("\n")
            in_section = False
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped == f"[providers.{provider}]":
                    in_section = True
                    continue
                if in_section:
                    if stripped.startswith("[") and stripped.endswith("]"):
                        in_section = False
                        continue
                    if stripped.startswith(f"{field} ="):
                        lines[i] = f'{field} = "{new_value}"'
                        break

            CONFIG_PATH.write_text("\n".join(lines), encoding="utf-8")
        except Exception as e:
            logger.warning(
                "Could not write API key to config: %s", e, exc_info=True
            )

    def _write_api_key_to_worker(self, worker_id: str, new_value: str) -> None:
        """Write an API key value to a worker's plugin.json."""
        worker_dir = WORKERS_DIR / worker_id
        plugin_path = worker_dir / "plugin.json"
        if not plugin_path.exists():
            return

        try:
            with open(plugin_path, encoding="utf-8") as f:
                plugin_data = json.load(f)

            # Update the api section
            if "api" not in plugin_data:
                plugin_data["api"] = {}
            plugin_data["api"]["api_key"] = new_value

            plugin_path.write_text(
                json.dumps(plugin_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            # Update the local worker cache
            for w in self._workers:
                if w.id == worker_id:
                    w.api.api_key = new_value
                    break

        except Exception as e:
            logger.warning(
                "Could not write API key to worker: %s", e, exc_info=True
            )

    def _cancel_api_key_edit(self) -> None:
        """Cancel the API key edit dialog."""
        self._editing_api_key_id = ""
        try:
            dialog = self.query_one("#api-key-edit-dialog")
            dialog.remove()
        except Exception:
            pass

    def _rebuild_api_keys_list(self) -> None:
        """Rebuild the API keys list after changes."""
        try:
            keys_list = self.query_one("#api-keys-list", VerticalScroll)
            # Remove all children except the edit dialog
            for child in list(keys_list.children):
                if child.id != "api-key-edit-dialog":
                    child.remove()

            for key_info in self._api_keys:
                row = Horizontal(classes="api-key-row")
                row.mount(
                    Label(key_info["provider"], classes="api-key-provider")
                )
                row.mount(
                    Label(key_info["source"], classes="api-key-source")
                )
                row.mount(
                    Label(
                        _mask_value(key_info["value"]),
                        classes="api-key-value",
                    )
                )
                status_color = "green" if key_info["is_set"] else "red"
                if key_info["is_set"]:
                    status_text = (
                        f"[{status_color}]{CHECK_MARK} set[/{status_color}]"
                    )
                else:
                    status_text = (
                        f"[{status_color}]{CROSS_MARK} unset[/{status_color}]"
                    )
                row.mount(Label(status_text, classes="api-key-status"))
                row.mount(
                    Button(
                        "Edit",
                        classes="api-key-edit-btn",
                        name=key_info["key_id"],
                    )
                )
                keys_list.mount(row)
        except Exception:
            pass

    # ── Helpers ────────────────────────────────────────────────────────

    def _get_office(self) -> Any:
        """Get the Office instance if in embedded mode."""
        if self._tui_app and hasattr(self._tui_app, "_office"):
            return self._tui_app._office
        return None
