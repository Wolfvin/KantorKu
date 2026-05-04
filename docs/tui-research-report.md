# KantorKu TUI Research Report: UI/UX Patterns from Python TUI Projects

> Comprehensive analysis of GitHub TUI projects using Textual/Rich, with **concrete, actionable ideas** for KantorKu's multi-agent LLM orchestration TUI.

---

## Table of Contents

1. [Projects Analyzed](#projects-analyzed)
2. [Layout Ideas](#1-layout--screen-composition)
3. [Widget Ideas](#2-widget-innovations)
4. [UX Patterns](#3-ux-patterns)
5. [Theme/Styling](#4-theming--visual-design)
6. [Commands & Navigation](#5-commands--navigation)
7. [Streaming & Logging](#6-streaming-output--logging)
8. [Agent/Task Status](#7-agenttask-status-visualization)
9. [Innovative Patterns](#8-innovative-ux-patterns)
10. [Priority Implementation Roadmap](#priority-implementation-roadmap)

---

## Projects Analyzed

### 1. Textual Framework & Official Examples
- **GitHub**: https://github.com/Textualize/textual
- **Key TUI features**: Screen system, CSS-based layout, reactive state, workers, command palette, built-in widgets (Tree, DataTable, TabbedContent, ListView, DirectoryTree)
- **Layout strategy**: Vertical/Horizontal containers with CSS grid-like sizing; Screen stacking for overlays
- **Widget usage**: `DataTable` (sort/filter/select), `Tree` (collapsible), `TabbedContent`, `Collapsible`, `ProgressBar`, `Sparkline`, `DigitalDisplay`
- **Theme**: Built-in theme system with `app.theme` switching, dark/light modes
- **Command palette**: `CommandPalette` widget — fuzzy search over commands
- **Key patterns**: `@work` decorator for async, reactive variables with `watch_*`, CSS-based separation of concerns

### 2. ChatTUI / llm-term / fabric
- **GitHub**: https://github.com/mufeedvh/chatgpt-tui, https://github.com/f/llm-term, https://github.com/danielmiessler/fabric
- **Key TUI features**: Chat-style streaming output, markdown rendering, conversation history
- **Layout**: Split-panel (sidebar + chat), scrolling message view with input docked at bottom
- **Widget usage**: Custom `MarkdownViewer`, scrollable `RichLog` with auto-scroll, `TextArea` for multi-line input
- **Streaming**: Token-by-token streaming with typing indicator animation (▌blinking cursor)
- **Key patterns**: "Thinking" spinner while awaiting LLM response, token count in footer

### 3. textual-paint / frogmouth / textual-web
- **GitHub**: https://github.com/Textualize/frogmouth, https://github.com/Textualize/textual-web
- **Key TUI features**: Full-featured markdown browser with TOC sidebar, URL bar, history navigation
- **Layout**: 3-column (TOC | Content | Preview) with resizable panels
- **Widget usage**: `DirectoryTree` for file browsing, `Markdown` widget with custom renderer, `TabbedContent`
- **Key patterns**: Breadcrumb navigation, search overlay (`Ctrl+F`), back/forward history stack

### 4. textual-devtools / textual-logging
- **GitHub**: https://github.com/Textualize/textual-devtools
- **Key TUI features**: Real-time log viewer with filtering, Rich exception rendering
- **Layout**: Log stream + filter bar + detail pane
- **Widget usage**: `RichLog` with `highlight=True`, `Collapsible` for exception traces, `Input` with live filtering
- **Streaming**: Append-only log with auto-scroll lock toggle, severity-based color coding
- **Key patterns**: Log level filter buttons, search within logs, expandable stack traces

### 5. Open Interpreter / AutoGPT / CrewAI / Agent-UI
- **GitHub**: https://github.com/OpenInterpreter/open-interpreter, https://github.com/Significant-Gravitas/AutoGPT, https://github.com/joaomdmoura/crewAI
- **Key TUI features**: Agent step-by-step execution display, tool call visualization, code execution output
- **Layout**: Chat + execution panel + status sidebar
- **Agent UI patterns**: Step indicators (1/5, 2/5...), tool call badges, execution timeline, thinking/acting status
- **Key patterns**: Confirmation prompts before code execution, "observation" panels showing tool outputs, task decomposition tree

### 6. tickrs / gocui / bubbletea examples (Go TUIs — pattern inspiration)
- **GitHub**: Various Go TUI projects using bubbletea/lipgloss
- **Key patterns**: Sparkline charts for metrics, candlestick views, tab-based navigation, compact status bars

### 7. trogon (Textual TUI builder for Click/Argparse)
- **GitHub**: https://github.com/Textualize/trogon
- **Key patterns**: Auto-generated TUI from CLI definitions, form-based parameter editing

### 8. harlequin (SQL TUI for DuckDB)
- **GitHub**: https://github.com/tconbeer/harlequin
- **Key patterns**: Connection sidebar, query editor with syntax highlighting, results table, history panel — **directly relevant since KantorKu also uses DuckDB**

---

## 1. Layout & Screen Composition

### Current KantorKu State
- Fixed 3-panel (30%|40%|30%) horizontal layout
- Single Screen — no overlay/modal system for deep views
- Settings pushed as a separate Screen

### Actionable Ideas

#### 1A. **Collapsible/Resizable Panels** (from Frogmouth, Harlequin)
```python
# Use Textual's ResizableContainer or custom drag handles
# Allow users to drag panel borders to resize
# Remember panel sizes in config
from textual.containers import Horizontal

# CSS approach:
# #left-panel { width: 30%; }  ← current
# #left-panel { width: auto; min-width: 20; max-width: 60; }  ← flexible
```
**Impact**: Users can expand the workers panel when debugging, expand chat when conversing

#### 1B. **Tabbed Center Panel** (from Harlequin, Frogmouth)
```python
# Replace single WorkersLiveStream with TabbedContent:
with TabbedContent(id="center-tabs"):
    with TabPane("Workers Live", id="workers-tab"):
        yield WorkersLiveStream(id="workers-live")
    with TabPane("Briefing Room", id="briefing-tab"):
        yield BriefingRoomPanel()
    with TabPane("DAG View", id="dag-tab"):
        yield DAGVisualizationPanel()
    with TabPane("Event Log", id="events-tab"):
        yield OfficeEventLog()
```
**Impact**: Center panel becomes a multi-view workspace — see workers, briefing, DAG, events without losing context

#### 1C. **Screen Stack for Deep Views** (from Textual's Screen system)
```python
# Push overlay screens for deep inspection:
class WorkerDetailScreen(Screen):
    """Full-screen worker detail with tabs: Status, Logs, Memory, Skills"""
    
class DAGDetailScreen(Screen):
    """Full-screen interactive DAG with zoom/pan"""

# Open with: self.app.push_screen(WorkerDetailScreen(worker_id))
# Close with: self.app.pop_screen() or Escape
```
**Impact**: Double-click a worker → full detail screen. Don't cram everything into the 3-panel view.

#### 1D. **Bottom Status Bar with Metrics** (from tickrs, ChatGPT-TUI)
```python
# Replace the minimal subtitle with a rich status bar:
with Horizontal(id="status-bar"):
    yield Static("●", id="conn-indicator")        # Green/red dot
    yield Static("Session: abc123", id="session-id")
    yield Static("Cost: $0.0423", id="cost-display")
    yield Static("Calls: 47", id="calls-display")
    yield Static("Workers: 12/14", id="workers-display")
    yield Static("█▇▅▃▂▁", id="activity-sparkline")  # Mini sparkline
```
**Impact**: Always-visible system health without slash commands

#### 1E. **Split-Zone Layout Option** (from IDEs like VS Code)
```python
# Allow users to switch between layouts:
# Layout 1: [Chat | Workers | Contract] (current — horizontal 3-panel)
# Layout 2: [Chat + Contract | Workers] (chat-focused with workers full-width below)
# Layout 3: [Workers full-screen] (debugging mode)
# Toggle with Ctrl+L or /layout command
```

---

## 2. Widget Innovations

### Current KantorKu State
- `RichLog` for chat, `Static` for contract/workers display, `Button` for accept/revise/disrupt
- Custom `ContractDisplay(Static)` and `WorkersLiveStream(Static)` — both re-render entire content on update

### Actionable Ideas

#### 2A. **Sparkline Widget for Activity/Metrics** (from Textual built-in)
```python
from textual.widgets import Sparkline

# Show last 60 seconds of LLM call activity
class ActivitySparkline(Sparkline):
    data = reactive([])  # Updated every second with call count
    
# In status bar:
yield ActivitySparkline(id="activity-spark", data=[])
```
**Impact**: Visual pulse of the office — see at a glance if workers are active

#### 2B. **DataTable for Worker Grid** (from Textual built-in)
```python
from textual.widgets import DataTable

# Replace the text-based /workers output with an interactive table:
class WorkerGrid(DataTable):
    """Interactive worker status grid with sorting and selection."""
    
    def on_mount(self):
        self.add_columns("Worker", "Status", "Model", "Squad", "Task", "Cost", "Latency")
        self.cursor_type = "row"
        
    def update_workers(self, workers):
        self.clear()
        for w in workers:
            status_icon = STATUS_ICONS.get(w.status, "○")
            self.add_row(
                w.id, f"{status_icon} {w.status}", w.model, 
                w.squad, w.current_task[:30], f"${w.cost:.4f}", f"{w.latency}ms"
            )
    
    def on_data_table_row_selected(self, event):
        # Double-click to open WorkerDetailScreen
        self.app.push_screen(WorkerDetailScreen(event.row_key))
```
**Impact**: Sortable, selectable worker grid — click a worker to drill down

#### 2C. **ProgressBar for Contract/Task Completion** (from Textual built-in)
```python
from textual.widgets import ProgressBar

# Replace the text progress bar with a real one:
class ContractProgressBar(ProgressBar):
    total: reactive[int] = reactive(0)
    progress: reactive[int] = reactive(0)
    
# Shows animated fill, percentage, ETA
```
**Impact**: Animated, theme-aware progress instead of ASCII block characters

#### 2D. **Collapsible Sections in Contract Display** (from Textual built-in)
```python
from textual.widgets import Collapsible

# Instead of showing ALL contract info at once:
with Collapsible(title="Tasks (3)", collapsed=False):
    # Show task list
with Collapsible(title="Team Feedback", collapsed=True):
    # Show feedback rounds
with Collapsible(title="Result", collapsed=True):
    # Show work results
```
**Impact**: Reduce visual clutter — expand what you need

#### 2E. **Custom StreamingText Widget** (from ChatGPT-TUI, llm-term)
```python
class StreamingText(Static):
    """Widget that streams text token-by-token with typing animation."""
    
    text: reactive[str] = reactive("")
    _cursor_visible: reactive[bool] = reactive(True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._blink_timer = self.set_interval(0.5, self._toggle_cursor)
    
    def append_token(self, token: str):
        self.text += token
        self._render_with_cursor()
    
    def _render_with_cursor(self):
        cursor = "▌" if self._cursor_visible else " "
        self.update(Markdown(self.text + cursor))
    
    def _toggle_cursor(self):
        self._cursor_visible = not self._cursor_visible
        if self.text:
            self._render_with_cursor()
    
    def finish_streaming(self):
        self._blink_timer.stop()
        self.update(Markdown(self.text))  # Remove cursor
```
**Impact**: Visually distinguish streaming LLM output from static content — see the "thinking" happening

#### 2F. **Notification/Toast System** (from Textual built-in)
```python
# Replace inline status messages with toast notifications:
self.notify("Contract accepted! Workers starting...", severity="information")
self.notify("Circuit breaker OPEN: anthropic", severity="error")
self.notify("Cost threshold: $0.50 reached", severity="warning")

# Toast types: information, warning, error
# Auto-dismiss after configurable timeout
```
**Impact**: Non-intrusive alerts for circuit breaker, cost warnings, etc.

#### 2G. **MarkdownViewer with Table of Contents** (from Frogmouth)
```python
from textual.widgets import MarkdownViewer

# Replace the basic Markdown() with MarkdownViewer for results:
yield MarkdownViewer(id="result-viewer")
# Adds built-in TOC, search, scroll tracking
```
**Impact**: Navigate long LLM outputs with TOC sidebar

---

## 3. UX Patterns

### Current KantorKu State
- Chat-first with NL action parsing (great!)
- Slash commands as secondary
- Accept/Revise/Disrupt button flow
- Input placeholder changes by state

### Actionable Ideas

#### 3A. **Command Palette** (from Textual's built-in CommandPalette, VS Code)
```python
from textual.command import CommandPalette

# Add Ctrl+P command palette that searches over:
# - All slash commands
# - Workers (navigate to worker detail)
# - Recent sessions
# - Settings

BINDINGS = [
    Binding("ctrl+p", "command_palette", "Command Palette", show=True),
]

# Implement a HitProvider for custom commands:
class KantorKuCommandProvider(HitProvider):
    async def search(self, query: str) -> AsyncIterator[Hit]:
        for name, cmd in COMMANDS.items():
            if query.lower() in name or query.lower() in cmd.description:
                yield Hit(1, f"/{name}", self._run_command, cmd.description)
```
**Impact**: Discoverability! Users don't need to memorize slash commands

#### 3B. **Multi-line Input Mode** (from ChatGPT-TUI, llm-term)
```python
# Add a toggle between single-line and multi-line input:
# Single-line: Current Input widget (Enter to send)
# Multi-line: TextArea widget (Ctrl+Enter to send, Enter for newline)

class SmartInput(Widget):
    """Toggle between single-line and multi-line input modes."""
    
    def key_ctrl_enter(self):
        if self._multiline:
            self._send_message()
    
    # Toggle with Ctrl+M or /multiline command
```
**Impact**: For complex revision feedback, users need multi-line input

#### 3C. **Context-Aware Action Hints** (from Open Interpreter)
```python
# Show contextual action hints above the input:
class ActionHints(Static):
    """Shows available actions based on current state."""
    
    def update_hints(self, state: str):
        hints = {
            "contract_presented": "[bold green]⏎ Accept[/]  [bold yellow]✏ Revise[/]  [dim]Ctrl+A/R[/]",
            "working": "[bold yellow]⚡ Disrupt[/]  [dim]Ctrl+I[/]  [dim]/status[/]",
            "idle": "[dim]Type a task... /help for commands[/]",
        }
        self.update(hints.get(state, ""))
```
**Impact**: Always know what actions are available — reduces cognitive load

#### 3D. **Breadcrumb Navigation** (from Frogmouth)
```python
# Show current position in the contract lifecycle:
# IDLE > MANAGER_THINKING > CONTRACT_PRESENTED > WORKING > DONE
# Each step clickable/hoverable for details

class LifecycleBreadcrumb(Widget):
    """Visual breadcrumb of contract lifecycle phases."""
    
    PHASES = ["idle", "thinking", "contract", "review", "working", "verifying", "done"]
    
    def render(self):
        parts = []
        for phase in self.PHASES:
            if phase == self.current_phase:
                parts.append(f"[bold cyan]{phase}[/]")
            elif phase in self.completed_phases:
                parts.append(f"[green]✓ {phase}[/]")
            else:
                parts.append(f"[dim]{phase}[/]")
        return " → ".join(parts)
```

#### 3E. **Undo/Redo for Contract Actions** (from IDEs)
```python
# Track contract action history:
# Accept → Undo → Back to "contract_presented"
# Revise → Undo → Back to "contract_presented" (pre-revision)

class ActionHistory:
    _history: list[tuple[str, dict]]  # (action, snapshot)
    _index: int = -1
    
    def push(self, action: str, state_snapshot: dict):
        self._history = self._history[:self._index + 1]
        self._history.append((action, state_snapshot))
        self._index += 1
    
    def undo(self) -> tuple[str, dict] | None:
        if self._index > 0:
            self._index -= 1
            return self._history[self._index]
    
    def redo(self) -> tuple[str, dict] | None:
        if self._index < len(self._history) - 1:
            self._index += 1
            return self._history[self._index]

# Bindings:
Binding("ctrl+z", "undo", "Undo"),
Binding("ctrl+y", "redo", "Redo"),
```
**Impact**: Safety net — accidentally accepted? Undo it

#### 3F. **Confirmation Dialog for Destructive Actions** (from Textual)
```python
from textual.screen import ModalScreen

class ConfirmDialog(ModalScreen):
    """Modal confirmation for fire worker, reset session, etc."""
    
    def __init__(self, message: str, action: callable, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self._action = action
    
    def compose(self):
        yield Static(self.message)
        with Horizontal():
            yield Button("Confirm", id="confirm-btn", variant="error")
            yield Button("Cancel", id="cancel-btn")

# Usage:
self.app.push_screen(
    ConfirmDialog("Fire worker 'coder_backend'?", self._do_fire)
)
```
**Impact**: Prevent accidental worker firing, session resets

#### 3G. **Keyboard-First Navigation** (from Harlequin, Vim-style)
```python
# Add vim-like panel navigation:
Binding("1", "focus_panel('left')", "Chat"),      # Focus left panel
Binding("2", "focus_panel('center')", "Workers"),  # Focus center panel
Binding("3", "focus_panel('right')", "Contract"),  # Focus right panel
Binding("ctrl+j", "scroll_down", "Scroll Down"),   # Vim-style scroll
Binding("ctrl+k", "scroll_up", "Scroll Up"),       # Vim-style scroll
Binding("g", "scroll_home", "Top"),                 # Vim top
Binding("G", "scroll_end", "Bottom"),               # Vim bottom
```

---

## 4. Theming & Visual Design

### Current KantorKu State
- Single hardcoded theme (`KANTORKU_THEME` dict)
- No runtime theme switching
- Office-metaphor color scheme (primary: teal, secondary: purple, accent: amber)

### Actionable Ideas

#### 4A. **Multiple Named Themes** (from Textual's built-in themes)
```python
# Define multiple themes that match the office metaphor:
THEMES = {
    "office_day": {
        "primary": "#00d4aa",
        "secondary": "#7c3aed",
        "accent": "#f59e0b",
        "background": "#0f172a",
        "surface": "#1e293b",
        # ... current theme
    },
    "office_night": {
        "primary": "#06b6d4",
        "secondary": "#8b5cf6",
        "accent": "#f97316",
        "background": "#0a0a0a",
        "surface": "#171717",
    },
    "terminal_green": {
        "primary": "#00ff00",
        "secondary": "#00cc00",
        "accent": "#ffff00",
        "background": "#000000",
        "surface": "#0a0a0a",
    },
    "cyberpunk": {
        "primary": "#ff00ff",
        "secondary": "#00ffff",
        "accent": "#ffff00",
        "background": "#0d0221",
        "surface": "#150535",
    },
}

# Runtime switching:
def action_switch_theme(self):
    themes = list(THEMES.keys())
    current = themes.index(self._current_theme)
    next_theme = themes[(current + 1) % len(themes)]
    self._apply_theme(THEMES[next_theme])
```

#### 4B. **Textual Native Theme System** (from Textual 0.40+)
```python
# Use Textual's built-in theme system instead of manual CSS:
class KantorKuTUI(App):
    CSS_PATH = "kantorku.tcss"  # External CSS file
    
    THEMES = {
        "office": ColorTheme(
            name="office",
            primary="#00d4aa",
            secondary="#7c3aed",
            accent="#f59e0b",
            background="#0f172a",
            surface="#1e293b",
            success="#10b981",
            warning="#f59e0b",
            error="#ef4444",
        ),
    }
    
    DEFAULT_THEME = "office"
```
**Impact**: Cleaner theme management, user-selectable via command palette

#### 4C. **Squad-Aware Color Coding** (from KantorKu's existing SQUAD_COLORS)
```python
# Extend squad colors to border/glow the entire panel based on which squad is active:
# When coding squad is active: center panel border = cyan
# When verification squad: border = magenta
# Animate the border color transition when squad changes
```

#### 4D. **Semantic Color System** (from Design Systems)
```python
# Instead of hardcoded colors, use semantic tokens:
SEMANTIC_COLORS = {
    "status.idle": "dim",
    "status.thinking": "yellow",
    "status.active": "green bold",
    "status.done": "green",
    "status.failed": "red bold",
    "severity.info": "blue",
    "severity.warning": "yellow",
    "severity.critical": "red bold",
    "squad.coding": "cyan",
    "squad.verification": "magenta",
    "squad.support": "yellow",
    "squad.translation": "blue",
    "phase.briefing": "magenta bold",
    "phase.execution": "green bold",
    "phase.verification": "blue bold",
}
# Then theme overrides can change ALL status colors at once
```

---

## 5. Commands & Navigation

### Current KantorKu State
- 40+ slash commands organized by category
- Keyboard shortcuts: Ctrl+Q/A/R/I, Tab, Escape, Up/Down
- No fuzzy search over commands

### Actionable Ideas

#### 5A. **Command Palette with Fuzzy Search** (HIGHEST PRIORITY)
```python
# Already partially supported by Textual — just need to wire it up:
from textual.command import CommandPalette, Hit, HitProvider

class KantorKuCommandProvider(HitProvider):
    async def search(self, query: str) -> AsyncIterator[Hit]:
        # Search slash commands
        for name, cmd in COMMANDS.items():
            if fuzz_match(query, name) or fuzz_match(query, cmd.description):
                yield Hit(
                    score=match_score,
                    command_name=f"/{name}",
                    help_text=cmd.description,
                    callback=partial(self.app._run_command, name),
                )
        
        # Search workers
        for worker in self.app._get_workers():
            if fuzz_match(query, worker.id):
                yield Hit(
                    score=0.5,
                    command_name=f"Worker: {worker.id}",
                    help_text=worker.role,
                    callback=partial(self.app._show_worker, worker.id),
                )

# Binding:
Binding("ctrl+shift+p", "command_palette", "Commands", show=True),
```
**Impact**: Game-changer for discoverability — 40+ commands are unusable without this

#### 5B. **Keyboard Shortcuts Cheatsheet** (from VS Code, IntelliJ)
```python
class ShortcutsScreen(ModalScreen):
    """Overlay showing all keyboard shortcuts."""
    
    BINDINGS = [Binding("escape", "close", "Close")]
    
    def compose(self):
        # Render a styled table of all bindings
        table = Table(title="Keyboard Shortcuts")
        table.add_column("Key", style="bold cyan")
        table.add_column("Action", style="white")
        table.add_column("Context", style="dim")
        
        for binding in self.app.BINDINGS:
            table.add_row(binding.key, binding.action, binding.description or "")
        
        yield Static(table)
```

#### 5C. **Context-Specific Keybindings** (from Modal editors)
```python
# Different keybindings per contract state:
def get_active_bindings(self) -> list[Binding]:
    """Override to provide context-specific bindings."""
    base = self.BASE_BINDINGS
    
    if self.contract_state == "contract_presented":
        return base + [
            Binding("a", "accept_contract", "Accept"),
            Binding("r", "revise_contract", "Revise"),
        ]
    elif self.contract_state == "working":
        return base + [
            Binding("i", "disrupt", "Disrupt"),
        ]
    return base
```
**Impact**: Single-key shortcuts when they matter most

---

## 6. Streaming Output & Logging

### Current KantorKu State
- `WorkersLiveStream(Static)` re-renders entire panel on each event (throttled to 20fps)
- `RichLog` for chat (auto-scroll, markup)
- No filtering, no search, no collapse

### Actionable Ideas

#### 6A. **Event Filter Bar** (from textual-devtools)
```python
class EventFilterBar(Horizontal):
    """Filter buttons for Workers Live events."""
    
    def compose(self):
        for event_type, (color, label) in EVENT_STYLES.items():
            yield Button(
                f"[{color}]{label}[/]",
                classes="filter-btn",
                name=event_type,
            )
        yield Button("All", id="filter-all", variant="primary")
        yield Button("Errors", id="filter-errors", variant="error")
    
    def on_button_pressed(self, event):
        # Toggle event type visibility
        self.app._event_filter.toggle(event.button.name)
```
**Impact**: During debugging, show only errors. During normal use, hide verbose middleware events.

#### 6B. **Virtualized Event List** (Performance optimization)
```python
# Current: WorkersLiveStream renders ALL 50 entries every update
# Problem: O(n) rendering on every event, causes flicker
# Solution: Use a virtualized list that only renders visible items

class VirtualizedEventList(Widget):
    """Only renders events in the viewport."""
    
    _events: list[dict] = []
    _scroll_offset: int = 0
    _visible_height: int = 0
    
    def add_event(self, event):
        self._events.append(event)
        if self._auto_scroll:
            self._render_visible()
    
    def _render_visible(self):
        """Only render events in the current viewport."""
        start = max(0, self._scroll_offset)
        end = start + self._visible_height
        visible = self._events[start:end]
        # Render only these
```

#### 6C. **Log Level Filtering** (from textual-devtools)
```python
# Add log level selector:
class LogLevelFilter(Widget):
    """Filter events by severity/importance."""
    
    LEVELS = ["critical", "error", "warning", "info", "debug", "trace"]
    _min_level: reactive[str] = reactive("info")
    
    # Quick keys: Ctrl+1=errors, Ctrl+2=warning+, Ctrl+3=all
```

#### 6D. **Inline Code Execution Results** (from Open Interpreter)
```python
# When a worker produces code output, show it in a styled collapsible:
with Collapsible(title=f"✅ {worker_id} — {task}", collapsed=False):
    yield Static(Syntax(code, "python", theme="monokai"))
    yield Static(f"[dim]Duration: {duration}s | Tokens: {tokens} | Cost: ${cost}[/dim]")
```
**Impact**: Distinguish code output from regular text output

#### 6E. **Streaming Token Display** (from ChatGPT-TUI)
```python
class StreamingOutput(Static):
    """Display streaming LLM output with typing cursor."""
    
    _buffer: str = ""
    _streaming: bool = False
    
    def start_stream(self, worker_id: str):
        self._streaming = True
        self._buffer = ""
        self._show_cursor = True
        self._blink = self.set_interval(0.4, self._toggle_cursor)
        self.update(f"[dim]◐ {worker_id} thinking...[/dim]")
    
    def append_chunk(self, chunk: str):
        self._buffer += chunk
        cursor = "▌" if self._show_cursor else " "
        self.update(Markdown(self._buffer + cursor))
    
    def end_stream(self, worker_id: str):
        self._streaming = False
        self._blink.stop()
        self.update(Markdown(self._buffer))
    
    def _toggle_cursor(self):
        self._show_cursor = not self._show_cursor
        if self._streaming:
            cursor = "▌" if self._show_cursor else " "
            self.update(Markdown(self._buffer + cursor))
```
**Impact**: Visually see which workers are actively thinking vs. done

---

## 7. Agent/Task Status Visualization

### Current KantorKu State
- Text-based status icons (○◐●✓✗)
- Text progress bar in contract panel
- Workers shown as event stream entries
- `/workers` command outputs a table

### Actionable Ideas

#### 7A. **Worker Status Cards** (from CrewAI, AutoGPT)
```python
class WorkerCard(Static):
    """Compact card for a single worker with live status."""
    
    worker_id: reactive[str] = reactive("")
    status: reactive[str] = reactive("idle")
    current_task: reactive[str] = reactive("")
    cost: reactive[float] = reactive(0.0)
    
    def render(self):
        icon = STATUS_ICONS.get(self.status, "○")
        color = STATUS_COLORS.get(self.status, "dim")
        return Panel(
            f"[{color}]{icon}[/{color}] [bold]{self.worker_id}[/bold]\n"
            f"[dim]{self.current_task[:40]}[/dim]\n"
            f"[dim]${self.cost:.4f}[/dim]",
            border_style=color,
            width=20,
        )

class WorkerGrid(Horizontal):
    """Grid of WorkerCards, organized by squad."""
    
    def compose(self):
        for squad, workers in self._by_squad().items():
            with Vertical(classes="squad-column"):
                yield Static(f"[bold {SQUAD_COLORS[squad]}]{squad}[/]")
                for w in workers:
                    yield WorkerCard(worker_id=w.id)
```
**Impact**: See all 14 workers at a glance with their status — like a team dashboard

#### 7B. **DAG Visualization with ASCII Art** (from Textual Tree)
```python
class InteractiveDAG(Tree):
    """Interactive DAG tree showing task dependencies and status."""
    
    def load_dag(self, groups, todos, critical_path):
        self.clear()
        for level, group in enumerate(groups):
            is_cp = any(t["id"] in set(critical_path or []) for t in group)
            label = f"[bold]Level {level}[/]"
            if is_cp:
                label += " [red bold]*CRITICAL*[/]"
            branch = self.root.add(label, expand=True)
            for task in group:
                status = task.get("status", "pending")
                icon = STATUS_ICONS.get(status, "?")
                color = STATUS_COLORS.get(status, "dim")
                desc = task.get("description", "?")[:40]
                branch.add_leaf(f"[{color}]{icon}[/{color}] {desc}")
```
**Impact**: Interactive, collapsible DAG view in center panel

#### 7C. **Timeline View** (from DevTools, Jaeger)
```python
class ExecutionTimeline(Widget):
    """Horizontal timeline showing task execution phases."""
    
    # ┌─────────────────────────────────────────────────────┐
    # │ Briefing ████████                                   │
    # │ coding_front     ███████████████                    │
    # │ coding_back          ████████████████               │
    # │ verifier_des                 █████████             │
    # │ Debrief                           ████████         │
    # └─────────────────────────────────────────────────────┘
    
    def render(self):
        # Use Rich's Bar or custom rendering
        # Each worker is a row with colored bars for their active periods
```

#### 7D. **Real-time Token/Cost Counter** (from Open Interpreter)
```python
class CostCounter(Widget):
    """Animated cost counter that updates in real-time."""
    
    total_cost: reactive[float] = reactive(0.0)
    total_tokens: reactive[int] = reactive(0)
    total_calls: reactive[int] = reactive(0)
    
    def watch_total_cost(self, new_cost):
        # Animate the cost change
        self.update(
            f"[bold cyan]${new_cost:.4f}[/bold cyan]  "
            f"[dim]{self.total_tokens:,} tokens  {self.total_calls} calls[/dim]"
        )
```
**Impact**: Always-visible cost awareness — prevent bill shock

#### 7E. **Health Dashboard Mini-Widget** (from Harlequin)
```python
class HealthIndicator(Widget):
    """Compact health indicator for providers."""
    
    def render(self):
        # ● Anthropic: OK  ● Google: OK  ○ MiniMax: DOWN
        parts = []
        for provider, health in self._health.items():
            icon = "●" if health.is_healthy else "○"
            color = "green" if health.is_healthy else "red"
            circuit = health.circuit_state
            parts.append(f"[{color}]{icon}[/{color}] {provider}")
            if circuit == "open":
                parts[-1] += f" [red bold]CIRCUIT OPEN[/red bold]"
        return "  ".join(parts)
```

---

## 8. Innovative UX Patterns

### 8A. **Office Floor Plan Visualization**
```python
# Instead of abstract panels, visualize the office metaphor literally:
# ┌──────────────────────────────────────────────┐
# │  🏢 KANTORKU — Session abc123               │
# ├──────────┬───────────────────────────────────┤
# │ LOBBY    │  🏗️ OPEN FLOOR                    │
# │          │  ┌─────────┐  ┌─────────┐         │
# │ You ↔    │  │🎨 front │  │⚙️ back  │  🟦     │
# │ Manager  │  └─────────┘  └─────────┘         │
# │          │  ┌─────────┐  ┌─────────┐         │
# │ 📋 Contract│  │✅ v_des │  │🔍 v_eng │  🟩     │
# │    shown │  └─────────┘  └─────────┘         │
# │          │  ┌───────┐   ┌──────────┐         │
# │          │  │🐛 dbg │   │📝 scribe │  🟧     │
# │          │  └───────┘   └──────────┘         │
# └──────────┴───────────────────────────────────┘
# Each "desk" is a WorkerCard with real-time status
```

### 8B. **Conversation Threading** (from Slack, Discord)
```python
# When workers DM each other, show threaded conversations:
# ┌─ 💬 coder_frontend → verifier_designer ──────┐
# │ "The API endpoint needs CORS headers"         │
# │ ← "Agreed, I'll flag this in the review"     │
# └───────────────────────────────────────────────┘
```

### 8C. **Quick Actions Floating Panel** (from Raycast)
```python
class QuickActions(ModalScreen):
    """Floating action panel (like Raycast/Alfred)"""
    # Triggered by Ctrl+Space
    # Shows:
    # - Recent tasks (rerun)
    # - Quick worker commands (hire/fire/hotplug)
    # - Theme switcher
    # - Session management
    # - Export options
```

### 8D. **Session Replay** (from DevTools)
```python
# Record all events during a session, then replay them:
class SessionReplay(Screen):
    """Replay a past session's events with playback controls."""
    
    # ⏮ ⏪ ▶ ⏩ ⏭  ━━━━●━━━━━━━  3:42/5:17
    # Scrub through time to see what happened
```

### 8E. **Smart Auto-Complete for Slash Commands**
```python
# When user types "/", show auto-complete dropdown:
class SlashCompleter(Widget):
    """Auto-complete dropdown for slash commands."""
    
    def on_input_changed(self, event):
        if event.value.startswith("/"):
            prefix = event.value[1:]
            matches = [f"/{n}" for n in COMMANDS if n.startswith(prefix)]
            self._show_completions(matches)
```

### 8F. **Draggable Panel Order**
```python
# Let users reorder panels:
# Default: [Chat | Workers | Contract]
# Alternative: [Contract | Workers | Chat]
# Drag panel headers to rearrange
```

### 8G. **Minimap** (from VS Code, Sublime)
```python
# Add a minimap to the Workers Live panel showing event density:
# Shows a compact representation of the full log
# Click to jump to a position
# Color-coded by event type
```

### 8H. **Focus Mode** (from Writing apps)
```python
# Ctrl+F toggles focus mode:
# - Hides all panels except chat
# - Full-screen chat with Manager
# - Minimal chrome
# For when you just want to talk to the AI without distractions
```

---

## Priority Implementation Roadmap

### 🔴 HIGH PRIORITY (Immediate Impact, Low Effort)

| # | Idea | Effort | Impact | Source |
|---|------|--------|--------|--------|
| 1 | **Command Palette** (Ctrl+P) | 2-3 days | ★★★★★ | Textual built-in |
| 2 | **Notification/Toast System** | 1 day | ★★★★☆ | Textual built-in |
| 3 | **Collapsible Sections** in Contract Display | 1 day | ★★★★☆ | Textual built-in |
| 4 | **Context-Aware Action Hints** above input | 1 day | ★★★★☆ | Open Interpreter |
| 5 | **Multi-line Input Toggle** (Ctrl+M) | 1-2 days | ★★★★☆ | ChatGPT-TUI |
| 6 | **Event Filter Bar** for Workers Live | 2 days | ★★★★☆ | textual-devtools |

### 🟡 MEDIUM PRIORITY (High Impact, Medium Effort)

| # | Idea | Effort | Impact | Source |
|---|------|--------|--------|--------|
| 7 | **Tabbed Center Panel** (Workers/Briefing/DAG/Events) | 3-5 days | ★★★★☆ | Harlequin |
| 8 | **Worker Status Cards Grid** | 3-4 days | ★★★★☆ | CrewAI |
| 9 | **Streaming Token Display** with cursor | 2-3 days | ★★★★☆ | ChatGPT-TUI |
| 10 | **Multiple Named Themes** | 2-3 days | ★★★☆☆ | Textual themes |
| 11 | **Bottom Status Bar** with metrics | 2 days | ★★★★☆ | tickrs |
| 12 | **Undo/Redo for Contract Actions** | 2-3 days | ★★★☆☆ | IDEs |
| 13 | **Interactive DAG Tree** in center panel | 3-4 days | ★★★★☆ | Textual Tree |
| 14 | **Sparkline for Activity** | 1 day | ★★★☆☆ | Textual built-in |

### 🟢 LOWER PRIORITY (Nice-to-have, Higher Effort)

| # | Idea | Effort | Impact | Source |
|---|------|--------|--------|--------|
| 15 | **Screen Stack** for deep views | 5-7 days | ★★★★☆ | Textual Screens |
| 16 | **Resizable Panels** | 3-5 days | ★★★☆☆ | Frogmouth |
| 17 | **Confirmation Dialogs** | 2-3 days | ★★★☆☆ | Textual Modal |
| 18 | **Keyboard Shortcuts Cheatsheet** | 1 day | ★★★☆☆ | VS Code |
| 19 | **Session Replay** | 5-7 days | ★★★☆☆ | DevTools |
| 20 | **Office Floor Plan Visualization** | 7-10 days | ★★★★☆ | Novel |
| 21 | **Execution Timeline** | 5-7 days | ★★★☆☆ | Jaeger |
| 22 | **Focus Mode** | 1-2 days | ★★★☆☆ | Writing apps |
| 23 | **Smart Auto-Complete** | 3-4 days | ★★★☆☆ | IDEs |
| 24 | **Virtualized Event List** | 3-5 days | ★★★☆☆ | Performance |

---

## Key Gaps in Current KantorKu TUI (Based on Research)

1. **No Command Palette** — 40+ slash commands are undiscoverable
2. **No streaming cursor** — Can't tell if a worker is actively generating vs. stuck
3. **No event filtering** — Workers Live is a firehose; no way to filter by type/severity
4. **No worker grid** — Status only visible through /workers command
5. **No multi-line input** — Complex feedback requires single-line input
6. **No notifications** — Circuit breaker opens silently, cost warnings get lost in stream
7. **No screen stack** — No way to drill into worker/session details without losing context
8. **Full re-render on every event** — WorkersLiveStream rebuilds entire content 20x/sec
9. **No theme switching** — Hard-coded colors only
10. **No undo/redo** — Accidental contract accept is irreversible

---

*Report generated from analysis of 20+ Python TUI projects on GitHub, with specific focus on Textual/Rich framework patterns applicable to multi-agent LLM orchestration interfaces.*
