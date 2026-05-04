"""
SettingsScreen — Worker CRUD panel overlay for the KantorKu TUI.

A Textual Screen subclass providing a 3-column settings interface:
  - Left:   Scrollable worker list sidebar with CRUD buttons
  - Center: 3 tabs (System Prompt, Tools & API, Skills)
  - Right:  Live preview of changes before saving

Layout:
    ┌──────────┬───────────────────────┬──────────────┐
    │ Workers  │  System Prompt        │  Preview     │
    │ ──────── │  Tools & API          │  (live diff) │
    │ coder_fe │  Skills               │              │
    │ coder_ba │                       │              │
    │ ...      │  [Save Worker]        │              │
    │          │  [New] [Delete]       │              │
    └──────────┴───────────────────────┴──────────────┘

Pushed via `app.push_screen(SettingsScreen(app_ref))`.
Closed via ESC → `app.pop_screen()`.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timezone
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
    TabbedContent,
    TabPane,
    TextArea,
)

from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from kantorku.tui.themes import KANTORKU_THEME, SQUAD_COLORS

logger = logging.getLogger(__name__)

# ─── Constants ─────────────────────────────────────────────────────────

# Resolve paths relative to the kantorku package location
_PACKAGE_DIR = Path(__file__).resolve().parent.parent  # kantorku/
_PROJECT_ROOT = _PACKAGE_DIR.parent  # framework/
WORKERS_DIR = _PROJECT_ROOT / "workers"
SKILLS_DIR = _PROJECT_ROOT / "skills"
CONFIG_PATH = _PROJECT_ROOT / "kantorku.toml"

# Unicode simbol untuk UI
CHECK_MARK = "\u2713"
CROSS_MARK = "\u2717"
BULLET_CHAR = "\u2022"

# Daftar tool yang tersedia (referensi untuk tab Tools & API)
AVAILABLE_TOOLS = [
    "execute",
    "llm_call",
    "llm_call_stream",
    "llm_call_structured",
    "api_call",
    "speak_up",
    "receive_dm",
    "get_context",
    "dm",
    "broadcast",
    "delegate",
]

# Provider yang didukung oleh KantorKu (harus match PROVIDER_MAP di router.py)
VALID_PROVIDERS = [
    ("anthropic", "Anthropic (Claude)"),
    ("google", "Google (Gemini)"),
    ("minimax", "MiniMax"),
    ("deepseek", "DeepSeek"),
    ("openai", "OpenAI"),
    ("xai", "xAI (Grok)"),
    ("meta", "Meta (Llama)"),
    ("ollama", "Ollama (Local)"),
]

# Default provider/model untuk worker baru
DEFAULT_PROVIDER = "ollama"
DEFAULT_MODEL = "llama3"


def _mask_value(value: str) -> str:
    """Sembunyikan nilai sensitif dengan karakter bullet."""
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
    return BULLET_CHAR * 8


def _load_workers_from_dir() -> list[Any]:
    """Muat WorkerIdentity dari direktori workers."""
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
                logger.warning("Skip worker bermasalah: %s", subdir, exc_info=True)
    return workers


def _load_skills() -> list[dict[str, str]]:
    """Muat file skill dari direktori skills."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    skills: list[dict[str, str]] = []
    for fpath in sorted(SKILLS_DIR.glob("*.md")):
        try:
            content = fpath.read_text(encoding="utf-8")
            skills.append({"name": fpath.stem, "content": content, "path": str(fpath)})
        except Exception:
            logger.warning("Gagal baca skill: %s", fpath, exc_info=True)
    return skills


def _backup_file(path: Path) -> Path | None:
    """Buat backup file sebelum overwrite. Kembalikan path backup atau None."""
    if not path.exists():
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(f".{timestamp}.bak")
    try:
        shutil.copy2(path, backup_path)
        return backup_path
    except Exception:
        logger.debug("Gagal backup %s", path, exc_info=True)
        return None


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
    border-bottom: tall {KANTORKU_THEME['primary']};
}}

#settings-header-label {{
    color: {KANTORKU_THEME['text']};
}}

#settings-main {{
    height: 1fr;
    layout: horizontal;
}}

/* ── Left Sidebar ── */
#sidebar {{
    width: 26;
    height: 1fr;
    border-right: tall {KANTORKU_THEME['primary']};
    background: {KANTORKU_THEME['surface']};
    layout: vertical;
}}

#sidebar-header {{
    background: {KANTORKU_THEME['surface']};
    color: {KANTORKU_THEME['primary']};
    padding: 0 1;
    height: 2;
    text-style: bold;
}}

#worker-list {{
    height: 1fr;
    scrollbar-size: 1 1;
    scrollbar-color: {KANTORKU_THEME['primary']} 30%;
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

#sidebar-btns {{
    dock: bottom;
    height: auto;
    padding: 0 1;
    layout: vertical;
    gap: 1;
}}

#new-worker-btn {{
    background: {KANTORKU_THEME['info']} 15%;
    color: {KANTORKU_THEME['info']};
    text-style: bold;
    width: 100%;
    border: tall {KANTORKU_THEME['info']};
}}

#new-worker-btn:hover {{
    background: {KANTORKU_THEME['info']} 30%;
    color: $text;
}}

#delete-worker-btn {{
    background: {KANTORKU_THEME['error']} 15%;
    color: {KANTORKU_THEME['error']};
    text-style: bold;
    width: 100%;
    border: tall {KANTORKU_THEME['error']};
}}

#delete-worker-btn:hover {{
    background: {KANTORKU_THEME['error']} 30%;
    color: $text;
}}

/* ── Center Panel ── */
#center-panel {{
    width: 1fr;
    height: 1fr;
    layout: vertical;
}}

#center-tabs {{
    height: 1fr;
}}

#skill-textarea {{
    height: 1fr;
    scrollbar-size: 1 1;
}}

/* Tools & API tab */
#tools-api-content {{
    height: 1fr;
    padding: 0 1;
    scrollbar-size: 1 1;
    scrollbar-color: {KANTORKU_THEME['primary']} 30%;
}}

.tools-section-header {{
    color: {KANTORKU_THEME['primary']};
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
    color: {KANTORKU_THEME['text']};
}}

.tool-remove-btn {{
    width: 6;
    background: {KANTORKU_THEME['surface']};
    color: {KANTORKU_THEME['error']};
    margin-left: 1;
    border: tall {KANTORKU_THEME['error']} 30%;
}}

.tool-remove-btn:hover {{
    background: {KANTORKU_THEME['error']} 25%;
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
    background: {KANTORKU_THEME['info']} 15%;
    color: {KANTORKU_THEME['info']};
    text-style: bold;
    margin-left: 1;
    border: tall {KANTORKU_THEME['info']};
}}

.tool-add-btn:hover {{
    background: {KANTORKU_THEME['info']} 30%;
    color: $text;
}}

.available-tools-hint {{
    color: {KANTORKU_THEME['muted']};
    margin-top: 1;
    height: auto;
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

/* Skills tab */
#skills-tab-content {{
    height: 1fr;
    padding: 0 1;
    scrollbar-size: 1 1;
    scrollbar-color: {KANTORKU_THEME['primary']} 30%;
}}

.skill-item-row {{
    layout: horizontal;
    height: 3;
    padding: 0 1;
    align: left middle;
}}

.skill-item-name {{
    width: 1fr;
    color: {KANTORKU_THEME['text']};
}}

.skill-add-row {{
    layout: horizontal;
    height: 3;
    padding: 0 1;
    align: left middle;
}}

.skill-add-input {{
    width: 1fr;
}}

.skill-add-btn {{
    width: 14;
    background: {KANTORKU_THEME['accent']} 15%;
    color: {KANTORKU_THEME['accent']};
    text-style: bold;
    margin-left: 1;
    border: tall {KANTORKU_THEME['accent']};
}}

.skill-add-btn:hover {{
    background: {KANTORKU_THEME['accent']} 30%;
    color: $text;
}}

#add-skill-file-btn {{
    background: {KANTORKU_THEME['accent']} 15%;
    color: {KANTORKU_THEME['accent']};
    text-style: bold;
    margin-top: 1;
    width: 100%;
    border: tall {KANTORKU_THEME['accent']};
}}

#add-skill-file-btn:hover {{
    background: {KANTORKU_THEME['accent']} 30%;
    color: $text;
}}

/* ── Bottom bar ── */
#save-bar {{
    dock: bottom;
    height: 3;
    padding: 0 1;
    background: {KANTORKU_THEME['surface']};
    layout: horizontal;
    border-top: tall {KANTORKU_THEME['primary']} 30%;
}}

#save-worker-btn {{
    background: {KANTORKU_THEME['success']} 15%;
    color: {KANTORKU_THEME['success']};
    text-style: bold;
    margin-right: 1;
    border: tall {KANTORKU_THEME['success']};
}}

#save-worker-btn:hover {{
    background: {KANTORKU_THEME['success']} 30%;
    color: $text;
}}

#worker-save-status {{
    color: {KANTORKU_THEME['text']};
    margin-left: 2;
    padding: 1 0;
}}

/* ── Right Preview Panel ── */
#preview-panel {{
    width: 32;
    height: 1fr;
    border-left: tall {KANTORKU_THEME['accent']};
    background: {KANTORKU_THEME['surface']};
    layout: vertical;
    scrollbar-size: 1 1;
    scrollbar-color: {KANTORKU_THEME['accent']} 30%;
}}

#preview-header {{
    background: {KANTORKU_THEME['surface']};
    color: {KANTORKU_THEME['accent']};
    padding: 0 1;
    height: 2;
    text-style: bold;
    border-bottom: tall {KANTORKU_THEME['muted']} 40%;
}}

#preview-content {{
    height: 1fr;
    padding: 0 1;
    scrollbar-size: 1 1;
}}
"""


class SettingsScreen(Screen):
    """
    Settings overlay untuk KantorKu TUI — Worker CRUD dengan 3-kolom.

    Layout:
      Left:   Daftar worker (sidebar) + New/Delete
      Center: 3 tab — System Prompt, Tools & API, Skills
      Right:  Preview perubahan sebelum simpan

    Mendukung:
      - KantorKuTUI (remote): CRUD file lokal saja
      - EmbeddedKantorKuTUI: CRUD + hot-reload via registry
    """

    CSS = _CSS

    BINDINGS = [
        Binding("escape", "close_settings", "Close", show=True),
    ]

    # ── Reactive state ──

    selected_worker_id: reactive[str] = reactive("")
    worker_save_status: reactive[str] = reactive("")

    def __init__(self, tui_app: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._tui_app = tui_app
        self._workers: list[Any] = _load_workers_from_dir()
        self._skills: list[dict[str, str]] = _load_skills()
        # Cache untuk menyimpan perubahan sementara sebelum save
        self._worker_skill_cache: dict[str, str] = {}
        self._worker_api_cache: dict[str, dict[str, str]] = {}
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

        with Horizontal(id="settings-main"):
            # ── Left: Worker Sidebar ──
            with Vertical(id="sidebar"):
                yield Label("Workers", id="sidebar-header")
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
                with Vertical(id="sidebar-btns"):
                    yield Button("+ New Worker", id="new-worker-btn")
                    yield Button(f"{CROSS_MARK} Delete Worker", id="delete-worker-btn")

            # ── Center: Tabs ──
            with Vertical(id="center-panel"):
                with TabbedContent(id="center-tabs"):
                    # Tab 1: System Prompt (SKILL.md)
                    with TabPane("System Prompt", id="worker-prompt-tab"):
                        yield TextArea(
                            id="skill-textarea",
                            language="markdown",
                        )

                    # Tab 2: Tools & API (plugin.json)
                    with TabPane("Tools & API", id="worker-tools-api-tab"):
                        with VerticalScroll(id="tools-api-content"):
                            # API Config
                            yield Label("API Config", classes="tools-section-header")
                            with Horizontal(classes="api-field-row"):
                                yield Label("Provider", classes="api-field-label")
                                yield Select(
                                    [(label, value) for value, label in VALID_PROVIDERS],
                                    id="worker-api-provider",
                                    allow_blank=True,
                                    prompt="Select provider...",
                                )
                            with Horizontal(classes="api-field-row"):
                                yield Label("Model", classes="api-field-label")
                                yield Input(
                                    id="worker-api-model",
                                    placeholder="e.g. claude-sonnet-4-6",
                                )
                            with Horizontal(classes="api-field-row"):
                                yield Label("API Key", classes="api-field-label")
                                yield Input(
                                    id="worker-api-key",
                                    placeholder="${ENV_VAR} or value",
                                    password=True,
                                )
                            with Horizontal(classes="api-field-row"):
                                yield Label("Base URL", classes="api-field-label")
                                yield Input(
                                    id="worker-api-base-url",
                                    placeholder="https://api.example.com/v1",
                                )

                            # Allowed Tools
                            yield Label("Allowed Tools", classes="tools-section-header")
                            with VerticalScroll(id="allowed-tools-list"):
                                pass  # Diisi dinamis
                            with Horizontal(classes="tool-add-row"):
                                yield Input(
                                    placeholder="Add tool (e.g. llm_call)",
                                    id="add-tool-input",
                                    classes="tool-add-input",
                                )
                                yield Button("+ Tool", id="add-tool-btn", classes="tool-add-btn")

                            # Referensi tool yang tersedia
                            yield Label(
                                f"[dim]Available: {', '.join(AVAILABLE_TOOLS)}[/dim]",
                                classes="available-tools-hint",
                            )

                    # Tab 3: Skills (allowed_skills)
                    with TabPane("Skills", id="worker-skills-tab"):
                        with VerticalScroll(id="skills-tab-content"):
                            yield Label("Allowed Skills", classes="tools-section-header")
                            with VerticalScroll(id="allowed-skills-list"):
                                pass  # Diisi dinamis
                            with Horizontal(classes="skill-add-row"):
                                yield Input(
                                    placeholder="Skill name (e.g. rust_expert)",
                                    id="add-skill-input",
                                    classes="skill-add-input",
                                )
                                yield Button("+ Skill", id="add-skill-btn", classes="skill-add-btn")
                            yield Button(
                                "Add Skill File (create .md)",
                                id="add-skill-file-btn",
                            )

                # Bottom bar
                with Horizontal(id="save-bar"):
                    yield Button(
                        f"{CHECK_MARK} Save Worker", id="save-worker-btn"
                    )
                    yield Label("", id="worker-save-status")

            # ── Right: Preview ──
            with Vertical(id="preview-panel"):
                yield Label("Preview", id="preview-header")
                with VerticalScroll(id="preview-content"):
                    yield Static(id="preview-static")

        yield Footer()

    # ── Lifecycle ──────────────────────────────────────────────────────

    def on_mount(self) -> None:
        """Inisialisasi state UI saat mount."""
        if self._workers:
            self.selected_worker_id = self._workers[0].id
            self._populate_worker_detail(self._workers[0])

    # ── Actions ────────────────────────────────────────────────────────

    def action_close_settings(self) -> None:
        """Tutup overlay settings."""
        self.app.pop_screen()

    # ── Worker Selection ───────────────────────────────────────────────

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle pilihan worker di sidebar."""
        item = event.item
        item_name = item.name if hasattr(item, "name") and item.name else ""

        if item_name and item_name in {w.id for w in self._workers}:
            # Simpan cache worker sebelumnya
            self._cache_current_worker_edits()
            self.selected_worker_id = item_name
            worker = next(
                (w for w in self._workers if w.id == item_name), None
            )
            if worker:
                self._populate_worker_detail(worker)

    def _populate_worker_detail(self, worker: Any) -> None:
        """Isi panel detail worker dari WorkerIdentity."""
        # System Prompt (SKILL.md)
        skill_text = worker.skill_md or ""
        if worker.id in self._worker_skill_cache:
            skill_text = self._worker_skill_cache[worker.id]
        try:
            textarea = self.query_one("#skill-textarea", TextArea)
            textarea.load_text(skill_text)
        except Exception:
            pass

        # API Config
        api = worker.api if hasattr(worker, "api") else None
        api_cache = self._worker_api_cache.get(worker.id, {})
        if api:
            try:
                provider_val = api_cache.get("provider", api.provider or "")
                select = self.query_one("#worker-api-provider", Select)
                # Set value langsung; Select.value menerima string atau Select.BLANK
                if provider_val:
                    select.value = provider_val
                else:
                    select.value = Select.BLANK
            except Exception:
                pass
            try:
                self.query_one("#worker-api-model", Input).value = (
                    api_cache.get("model", api.model or "")
                )
            except Exception:
                pass
            try:
                self.query_one("#worker-api-key", Input).value = (
                    api_cache.get("api_key", api.api_key or "")
                )
            except Exception:
                pass
            try:
                self.query_one("#worker-api-base-url", Input).value = (
                    api_cache.get("base_url", api.base_url or "")
                )
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
                remove_btn = Button(
                    "X", classes="tool-remove-btn", name=f"remove_tool:{tool}"
                )
                row.mount(tool_label)
                row.mount(remove_btn)
                tools_list.mount(row)
        except Exception:
            pass

        # Allowed Skills
        try:
            skills_list = self.query_one("#allowed-skills-list", VerticalScroll)
            skills_list.remove_children()
            skills = worker.allowed_skills or []
            if worker.id in self._worker_skills_cache:
                skills = self._worker_skills_cache[worker.id]
            for skill in skills:
                row = Horizontal(classes="skill-item-row")
                skill_label = Label(skill, classes="skill-item-name")
                remove_btn = Button(
                    "X", classes="tool-remove-btn", name=f"remove_skill:{skill}"
                )
                row.mount(skill_label)
                row.mount(remove_btn)
                skills_list.mount(row)
        except Exception:
            pass

        # Update preview
        self._update_preview(worker)

    def _cache_current_worker_edits(self) -> None:
        """Simpan perubahan dari worker yang sedang dipilih sebelum pindah."""
        if not self.selected_worker_id:
            return
        wid = self.selected_worker_id

        # Cache SKILL.md
        try:
            textarea = self.query_one("#skill-textarea", TextArea)
            self._worker_skill_cache[wid] = textarea.text
        except Exception:
            pass

        # Cache API fields
        api_cache: dict[str, str] = {}
        # Provider pakai Select widget — baca .value berbeda dari Input
        try:
            provider_select = self.query_one("#worker-api-provider", Select)
            provider_val = provider_select.value
            if provider_val is not Select.BLANK and provider_val:
                api_cache["provider"] = str(provider_val)
        except Exception:
            pass
        for field_id, key in [
            ("#worker-api-model", "model"),
            ("#worker-api-key", "api_key"),
            ("#worker-api-base-url", "base_url"),
        ]:
            try:
                api_cache[key] = self.query_one(field_id, Input).value
            except Exception:
                pass
        if api_cache:
            self._worker_api_cache[wid] = api_cache

        # Cache allowed tools
        try:
            tools_list = self.query_one("#allowed-tools-list", VerticalScroll)
            tools = []
            for child in tools_list.children:
                try:
                    label = child.query_one(".tool-item-name", Label)
                    tools.append(str(label.renderable))
                except Exception:
                    pass
            worker = next((w for w in self._workers if w.id == wid), None)
            if tools or (worker and worker.allowed_tools):
                self._worker_tools_cache[wid] = tools
        except Exception:
            pass

        # Cache allowed skills
        try:
            skills_list = self.query_one("#allowed-skills-list", VerticalScroll)
            skills = []
            for child in skills_list.children:
                try:
                    label = child.query_one(".skill-item-name", Label)
                    skills.append(str(label.renderable))
                except Exception:
                    pass
            worker = next((w for w in self._workers if w.id == wid), None)
            if skills or (worker and worker.allowed_skills):
                self._worker_skills_cache[wid] = skills
        except Exception:
            pass

    # ── Preview Panel ──────────────────────────────────────────────────

    def _update_preview(self, worker: Any) -> None:
        """Update panel preview di sebelah kanan dengan state worker saat ini."""
        try:
            preview_static = self.query_one("#preview-static", Static)
        except Exception:
            return

        parts: list[Any] = []

        # Header worker
        wid = worker.id or "?"
        squad = worker.squad or "uncategorized"
        squad_color = SQUAD_COLORS.get(squad, "dim")
        parts.append(Text.from_markup(
            f"[bold]{wid}[/bold]  [{squad_color}][{squad}][/{squad_color}]"
        ))
        if worker.role:
            parts.append(Text.from_markup(f"[dim]{worker.role}[/dim]"))
        parts.append(Text.from_markup(""))

        # API Config
        api = worker.api if hasattr(worker, "api") else None
        api_cache = self._worker_api_cache.get(wid, {})
        provider = api_cache.get("provider", api.provider if api else "")
        model = api_cache.get("model", api.model if api else "")
        api_key_raw = api_cache.get("api_key", api.api_key if api else "")
        base_url = api_cache.get("base_url", api.base_url if api else "")

        parts.append(Text.from_markup("[bold]API:[/bold]"))
        parts.append(Text.from_markup(f"  Provider: {provider or '(unset)'}"))
        parts.append(Text.from_markup(f"  Model: {model or '(unset)'}"))
        parts.append(Text.from_markup(f"  Key: {_mask_value(api_key_raw)}"))
        if base_url:
            parts.append(Text.from_markup(f"  URL: {base_url}"))
        parts.append(Text.from_markup(""))

        # Allowed Tools
        tools = worker.allowed_tools or []
        if wid in self._worker_tools_cache:
            tools = self._worker_tools_cache[wid]
        parts.append(Text.from_markup(f"[bold]Tools:[/bold] {', '.join(tools) if tools else '(none)'}"))

        # Allowed Skills
        skills = worker.allowed_skills or []
        if wid in self._worker_skills_cache:
            skills = self._worker_skills_cache[wid]
        parts.append(Text.from_markup(f"[bold]Skills:[/bold] {', '.join(skills) if skills else '(none)'}"))
        parts.append(Text.from_markup(""))

        # SKILL.md preview (first 20 lines)
        skill_text = worker.skill_md or ""
        if wid in self._worker_skill_cache:
            skill_text = self._worker_skill_cache[wid]
        if skill_text:
            lines = skill_text.split("\n")[:20]
            preview_text = "\n".join(lines)
            if len(skill_text.split("\n")) > 20:
                preview_text += "\n..."
            parts.append(Text.from_markup("[bold]SKILL.md (preview):[/bold]"))
            parts.append(Text(preview_text))

        # Source dir
        if worker.source_dir:
            parts.append(Text.from_markup(""))
            parts.append(Text.from_markup(f"[dim]Source: {worker.source_dir}[/dim]"))

        preview_static.update(
            Panel(
                Group(*parts),
                title="Worker Preview",
                border_style=KANTORKU_THEME["accent"],
                padding=(0, 1),
            )
        )

    # ── Button Handlers ────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle semua klik tombol."""
        btn = event.button
        btn_id = btn.id or ""
        btn_classes = btn.classes

        if btn_id == "save-worker-btn":
            self._save_worker()
            return
        if btn_id == "new-worker-btn":
            self._create_new_worker()
            return
        if btn_id == "delete-worker-btn":
            self._delete_worker()
            return
        if btn_id == "add-tool-btn":
            self._add_tool()
            return
        if btn_id == "add-skill-btn":
            self._add_skill()
            return
        if btn_id == "add-skill-file-btn":
            self._add_skill_file()
            return

        # Remove tool/skill
        if "tool-remove-btn" in btn_classes:
            name = btn.name or ""
            self._remove_tool_or_skill(name)
            return

    # ── Text change handlers (auto-update preview) ────────────────────

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Update preview saat SKILL.md berubah."""
        if event.text_area.id == "skill-textarea":
            self._cache_current_worker_edits()
            self._refresh_preview_for_current()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Update preview saat field API berubah."""
        input_id = event.input.id or ""
        if input_id.startswith("worker-api-"):
            self._cache_current_worker_edits()
            self._refresh_preview_for_current()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Update preview saat Select provider berubah."""
        select_id = event.select.id or ""
        if select_id == "worker-api-provider":
            self._cache_current_worker_edits()
            self._refresh_preview_for_current()

    def _refresh_preview_for_current(self) -> None:
        """Refresh preview untuk worker yang sedang dipilih."""
        if not self.selected_worker_id:
            return
        worker = next(
            (w for w in self._workers if w.id == self.selected_worker_id), None
        )
        if worker:
            self._update_preview(worker)

    # ── Worker Persistence ─────────────────────────────────────────────

    def _save_worker(self) -> None:
        """Simpan perubahan worker ke disk."""
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

            # Validate provider
            api_cache = self._worker_api_cache.get(wid, {})
            provider = api_cache.get("provider", worker.api.provider or "")
            valid_provider_values = [v for v, _ in VALID_PROVIDERS]
            if provider and provider not in valid_provider_values:
                self._set_worker_save_status(
                    f"[red]{CROSS_MARK} Invalid provider: '{provider}'[/red]\n"
                    f"[dim]Valid: {', '.join(valid_provider_values)}[/dim]"
                )
                return

            # Warn if using default/stub config
            warnings: list[str] = []
            if provider == DEFAULT_PROVIDER and worker.api.model == DEFAULT_MODEL:
                warnings.append(f"provider={DEFAULT_PROVIDER}/{DEFAULT_MODEL} (default)")
            if worker.squad == "support" and worker.role == "New worker":
                warnings.append("squad/role still at defaults")
            if warnings:
                # Show warning but still allow save
                self._set_worker_save_status(
                    f"[yellow]⚠ Warning: {'; '.join(warnings)}[/yellow]"
                )

            # Backup & write SKILL.md
            skill_text = self._worker_skill_cache.get(wid, worker.skill_md or "")
            skill_path = source_dir / "SKILL.md"
            _backup_file(skill_path)
            skill_path.write_text(skill_text, encoding="utf-8")
            worker.skill_md = skill_text

            # Update API config dari cache
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

            # Update allowed_tools dari cache
            tools_cache = self._worker_tools_cache.get(wid, None)
            if tools_cache is not None:
                worker.allowed_tools = tools_cache

            # Update allowed_skills dari cache
            skills_cache = self._worker_skills_cache.get(wid, None)
            if skills_cache is not None:
                worker.allowed_skills = skills_cache

            # Backup & write plugin.json via to_plugin_json()
            plugin_path = source_dir / "plugin.json"
            _backup_file(plugin_path)
            plugin_data = worker.to_plugin_json()
            plugin_path.write_text(
                json.dumps(plugin_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            # Hot-reload di embedded mode
            office = self._get_office()
            if office and hasattr(office, "registry"):
                registry = office.registry
                if hasattr(registry, "reload_worker"):
                    try:
                        registry.reload_worker(wid)
                        self._set_worker_save_status(
                            f"[green]{CHECK_MARK} Saved & reloaded[/green]"
                        )
                        self._update_preview(worker)
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
            self._update_preview(worker)

        except PermissionError:
            self._set_worker_save_status(
                f"[red]{CROSS_MARK} Permission denied writing files[/red]"
            )
        except Exception as e:
            self._set_worker_save_status(f"[red]{CROSS_MARK} Error: {e}[/red]")

    def _set_worker_save_status(self, message: str) -> None:
        """Update label status penyimpanan worker."""
        self.worker_save_status = message
        try:
            status = self.query_one("#worker-save-status", Label)
            status.update(message)
        except Exception:
            pass

    def _create_new_worker(self) -> None:
        """Buat worker baru dengan dialog sederhana."""
        if not self.selected_worker_id:
            # Jika belum ada worker terpilih, buat langsung
            self._do_create_new_worker()
            return
        # Simpan dulu cache worker saat ini
        self._cache_current_worker_edits()
        self._do_create_new_worker()

    def _do_create_new_worker(self) -> None:
        """Buat worker baru — buat direktori dengan plugin.json dan SKILL.md."""
        try:
            from kantorku.worker.identity import WorkerIdentity, WorkerAPI

            # Generate unique ID
            existing_ids = {w.id for w in self._workers}
            base_id = "new_worker"
            counter = 1
            new_id = base_id
            while new_id in existing_ids:
                new_id = f"{base_id}_{counter}"
                counter += 1

            # Buat direktori
            worker_dir = WORKERS_DIR / new_id
            worker_dir.mkdir(parents=True, exist_ok=True)

            # Buat plugin.json
            identity = WorkerIdentity(
                id=new_id,
                api=WorkerAPI(provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL),
                squad="support",
                role="New worker",
            )
            plugin_data = identity.to_plugin_json()
            plugin_path = worker_dir / "plugin.json"
            plugin_path.write_text(
                json.dumps(plugin_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            # Buat SKILL.md default
            skill_path = worker_dir / "SKILL.md"
            skill_path.write_text(
                f"# {new_id}\n\nDescribe what this worker does here.\n",
                encoding="utf-8",
            )

            # Reload workers list
            self._workers = _load_workers_from_dir()
            self._rebuild_worker_list()

            # Pilih worker baru
            self.selected_worker_id = new_id
            new_worker = next(
                (w for w in self._workers if w.id == new_id), None
            )
            if new_worker:
                self._populate_worker_detail(new_worker)

            self._set_worker_save_status(
                f"[green]{CHECK_MARK} Created: {new_id}[/green] "
                f"[yellow]⚠ Update provider, model, squad & role before deploying![/yellow]"
            )

        except FileExistsError:
            self._set_worker_save_status("[yellow]Worker already exists[/yellow]")
        except ValueError as e:
            self._set_worker_save_status(f"[red]{CROSS_MARK} {e}[/red]")
        except Exception as e:
            self._set_worker_save_status(f"[red]{CROSS_MARK} Error: {e}[/red]")

    def _rebuild_worker_list(self) -> None:
        """Rebuild daftar worker di sidebar setelah perubahan."""
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
        """Hapus worker yang sedang dipilih."""
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
                shutil.rmtree(source_dir)

            # Remove dari Office registry jika embedded
            office = self._get_office()
            if office and hasattr(office, "registry"):
                try:
                    office.registry.fire(wid)
                except Exception:
                    pass

            # Bersihkan cache
            self._worker_skill_cache.pop(wid, None)
            self._worker_api_cache.pop(wid, None)
            self._worker_tools_cache.pop(wid, None)
            self._worker_skills_cache.pop(wid, None)

            # Reload workers
            self._workers = _load_workers_from_dir()
            self._rebuild_worker_list()

            # Pilih worker pertama jika ada
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

    # ── Tools Management ───────────────────────────────────────────────

    def _add_tool(self) -> None:
        """Tambah tool ke daftar allowed_tools worker saat ini."""
        if not self.selected_worker_id:
            return

        try:
            tool_input = self.query_one("#add-tool-input", Input)
            tool_name = tool_input.value.strip()
            if not tool_name:
                return

            wid = self.selected_worker_id
            tools = self._worker_tools_cache.get(wid, [])

            # Tambah dari worker identity jika belum ada cache
            worker = next((w for w in self._workers if w.id == wid), None)
            if worker and not self._worker_tools_cache.get(wid):
                tools = list(worker.allowed_tools or [])

            if tool_name not in tools:
                tools.append(tool_name)
                self._worker_tools_cache[wid] = tools

                # Re-render tools list
                tools_list = self.query_one("#allowed-tools-list", VerticalScroll)
                row = Horizontal(classes="tool-item-row")
                tool_label = Label(tool_name, classes="tool-item-name")
                remove_btn = Button(
                    "X", classes="tool-remove-btn", name=f"remove_tool:{tool_name}"
                )
                row.mount(tool_label)
                row.mount(remove_btn)
                tools_list.mount(row)

            tool_input.value = ""

            # Update preview
            self._refresh_preview_for_current()
        except Exception:
            pass

    def _add_skill(self) -> None:
        """Tambah skill ke daftar allowed_skills worker saat ini."""
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

                # Re-render skills list
                skills_list = self.query_one("#allowed-skills-list", VerticalScroll)
                row = Horizontal(classes="skill-item-row")
                skill_label = Label(skill_name, classes="skill-item-name")
                remove_btn = Button(
                    "X", classes="tool-remove-btn", name=f"remove_skill:{skill_name}"
                )
                row.mount(skill_label)
                row.mount(remove_btn)
                skills_list.mount(row)

            skill_input.value = ""

            # Update preview
            self._refresh_preview_for_current()
        except Exception:
            pass

    def _add_skill_file(self) -> None:
        """Buat file skill .md baru di direktori skills/ dan tambahkan ke allowed_skills."""
        if not self.selected_worker_id:
            return

        try:
            skill_input = self.query_one("#add-skill-input", Input)
            skill_name = skill_input.value.strip()
            if not skill_name:
                self._set_worker_save_status(
                    "[yellow]Enter a skill name first[/yellow]"
                )
                return

            # Buat file skill .md
            SKILLS_DIR.mkdir(parents=True, exist_ok=True)
            skill_path = SKILLS_DIR / f"{skill_name}.md"

            if not skill_path.exists():
                default_content = f"# {skill_name}\n\nDescribe this skill here.\n"
                skill_path.write_text(default_content, encoding="utf-8")

            # Tambah ke allowed_skills worker
            wid = self.selected_worker_id
            skills = self._worker_skills_cache.get(wid, [])

            worker = next((w for w in self._workers if w.id == wid), None)
            if worker and not self._worker_skills_cache.get(wid):
                skills = list(worker.allowed_skills or [])

            if skill_name not in skills:
                skills.append(skill_name)
                self._worker_skills_cache[wid] = skills

                # Re-render skills list
                skills_list = self.query_one("#allowed-skills-list", VerticalScroll)
                row = Horizontal(classes="skill-item-row")
                skill_label = Label(skill_name, classes="skill-item-name")
                remove_btn = Button(
                    "X", classes="tool-remove-btn", name=f"remove_skill:{skill_name}"
                )
                row.mount(skill_label)
                row.mount(remove_btn)
                skills_list.mount(row)

            skill_input.value = ""

            # Reload skills list (for the skills tab reference)
            self._skills = _load_skills()

            self._set_worker_save_status(
                f"[green]{CHECK_MARK} Created skill file: {skill_name}.md[/green]"
            )

            # Update preview
            self._refresh_preview_for_current()
        except Exception as e:
            self._set_worker_save_status(
                f"[red]{CROSS_MARK} Skill file error: {e}[/red]"
            )

    def _remove_tool_or_skill(self, name: str) -> None:
        """Hapus tool atau skill dari daftar worker saat ini."""
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

    # ── Helpers ────────────────────────────────────────────────────────

    def _get_office(self) -> Any:
        """Dapatkan instance Office jika mode embedded."""
        if self._tui_app and hasattr(self._tui_app, "_office"):
            return self._tui_app._office
        return None
