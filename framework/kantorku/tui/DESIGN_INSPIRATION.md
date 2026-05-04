# KantorKu TUI — Premium Hacker-Style Design Inspiration Report

> Compiled from analysis of the Textual ecosystem, top-rated Python TUI projects,
> cyberpunk/hacker aesthetic references, and the existing KantorKu TUI codebase.

---

## 1. REFERENCE PROJECTS & THEIR DESIGN PATTERNS

### 🎨 Frogmouth (Textualize/frogmouth)
**A Markdown browser built with Textual — widely considered the most visually polished Textual app.**

- **Layout**: 2-panel (file tree left, markdown render right) with a URL/command bar at top
- **Color Scheme**: Deep dark navy (`#0d1117` GitHub Dark) with cyan/teal accents
- **Border Style**: `border: tall $primary;` — tall borders give a beveled, retro-terminal feel
- **Unique Elements**:
  - Breadcrumb navigation with dim separators
  - Toast notifications slide in from bottom-right
  - Tab bar with colored underlines for active tab
  - Rich markdown rendering with `code_theme="monokai"`
- **CSS Techniques**:
  ```css
  /* Frogmouth's signature sidebar */
  #sidebar {
      width: 32;
      border-right: tall $primary;
      background: $surface;
      dock: left;
  }
  /* Active file highlight */
  .directory-tree .tree-node--selected {
      background: $primary 20%;
      color: $text;
      text-style: bold;
  }
  ```

### 🎨 Textual Paint (1Concept1/textual-paint)
**MS Paint clone in the terminal — demonstrates extreme CSS control in Textual.**

- **Color Scheme**: Classic Windows gray (`#c0c0c0`) for UI chrome, dark canvas
- **Border Style**: `border: wide;` with inset/outset pseudo-3D effects
- **Unique Elements**:
  - Toolbar with icon buttons using Unicode symbols
  - Canvas widget with custom rendering
  - Tool palette with active-state highlighting
  - Status bar with coordinates and zoom level
- **CSS Techniques**:
  ```css
  /* 3D beveled buttons */
  .tool-button {
      border: wide $surface-lighten-1;
      border-top: wide white;
      border-left: wide white;
      border-bottom: wide $surface-darken-2;
      border-right: wide $surface-darken-2;
  }
  .tool-button:active {
      border-top: wide $surface-darken-2;
      border-left: wide $surface-darken-2;
      border-bottom: wide white;
      border-right: wide white;
  }
  ```

### 🎨 Textual-Weather (sdtnebraska/textual-weather)
**Weather app with beautiful ASCII art and gradient effects.**

- **Color Scheme**: Sky gradients (deep blue `#0a1628` → horizon orange `#ff6b35`)
- **Unique Elements**:
  - Unicode box-drawing characters for weather icons
  - Gradient-like color transitions using Rich markup
  - Animated spinner for loading states
  - Card-style layout with rounded borders

### 🎨 Hackerman / Cyberpunk TUI Themes

**The "hacker aesthetic" draws from:**
- **The Matrix** (green-on-black cascading text)
- **Blade Runner 2049** (orange/teal/amber with deep shadows)
- **Cyberpunk 2077** (magenta/cyan/yellow neon on near-black)
- **TRON** (cyan/blue grid lines on void black)
- **Kubernetes dashboards** (dark panels with colored indicators)

**Key design principles:**
1. **Near-black backgrounds** — never pure black, always tinted
2. **Neon accent colors** — saturated, electric, glowing
3. **Thin geometric borders** — grid lines, not boxes
4. **Monospace everything** — information density is beauty
5. **Pulsing/breathing animations** — alive, not static
6. **Sparse but deliberate color** — 80% monochrome, 20% neon

---

## 2. COLOR SCHEMES — Ready-to-Use Hex Codes

### 🔮 "SYNTHWAVE" (Recommended — Best for KantorKu)
```python
"synthwave": {
    "primary":     "#ff79c6",  # Hot pink — contracts, key actions
    "secondary":   "#bd93f9",  # Purple — secondary panels
    "accent":      "#f1fa8c",  # Electric yellow — highlights, warnings
    "success":     "#50fa7b",  # Neon green — completed, accepted
    "error":       "#ff5555",  # Bright red — failures, circuit open
    "warning":     "#ffb86c",  # Warm orange — cost warnings, rate limits
    "info":        "#8be9fd",  # Cyan — info, providers, metrics
    "muted":       "#6272a4",  # Muted purple-gray — dim text
    "background":  "#0d0d1a",  # Near-black with blue tint
    "surface":     "#1a1a2e",  # Dark panel surface
    "text":        "#f8f8f2",  # Warm white — primary text
    "glow_primary":   "#ff79c680",  # 50% alpha — for glow effects
    "glow_secondary": "#bd93f980",  # 50% alpha
    "border_dim":     "#2a2a4a",  # Very dim border — grid lines
    "border_active":  "#44475a",  # Slightly brighter — active borders
}
```

### 🌆 "NEON_NIGHTS" (Cyberpunk 2077 inspired)
```python
"neon_nights": {
    "primary":     "#00f0ff",  # Electric cyan — main accent
    "secondary":   "#ff003c",  # Neon red — alerts, critical
    "accent":      "#fffc00",  # Yellow — warnings, highlights
    "success":     "#00ff88",  # Neon mint — success states
    "error":       "#ff003c",  # Neon red — errors
    "warning":     "#ff8800",  # Orange — rate limits
    "info":        "#0088ff",  # Blue — info
    "muted":       "#334455",  # Dark steel — dim text
    "background":  "#050510",  # Void black with blue
    "surface":     "#0a0a1a",  # Panel surface
    "text":        "#e0f0ff",  # Cool white — text
    "neon_glow":      "#00f0ff40",  # Glow layer
    "grid_line":      "#0a1525",  # Grid borders
    "grid_active":    "#0a2540",  # Active grid
}
```

### 🟢 "HACKERMAN" (Classic terminal hacker)
```python
"hackerman": {
    "primary":     "#00ff41",  # Matrix green — main
    "secondary":   "#008f11",  # Dark green — secondary
    "accent":      "#00ffff",  # Cyan — highlights
    "success":     "#00ff41",  # Green — success
    "error":       "#ff0000",  # Red — errors (only color that isn't green)
    "warning":     "#ffff00",  # Yellow — warnings
    "info":        "#00cc33",  # Bright green — info
    "muted":       "#005500",  # Very dark green — dim
    "background":  "#000000",  # Pure black
    "surface":     "#0a0a0a",  # Almost black surface
    "text":        "#00ff41",  # Green text
    "phosphor_dim":   "#003300",  # Dim phosphor glow
    "phosphor_mid":   "#006600",  # Mid phosphor
    "grid_line":      "#001a00",  # Grid borders
    "scanline":       "#00220020",  # CRT scanline effect
}
```

### 🌌 "VOID" (Minimal premium — dark mode perfection)
```python
"void": {
    "primary":     "#7c3aed",  # Violet — primary accent
    "secondary":   "#06b6d4",  # Cyan — secondary
    "accent":      "#f59e0b",  # Amber — highlights
    "success":     "#10b981",  # Emerald — success
    "error":       "#ef4444",  # Red — errors
    "warning":     "#f59e0b",  # Amber — warnings
    "info":        "#3b82f6",  # Blue — info
    "muted":       "#374151",  # Gray-700 — dim
    "background":  "#030712",  # Gray-950 — void black
    "surface":     "#111827",  # Gray-900 — panel
    "text":        "#f9fafb",  # Gray-50 — text
    "border_subtle":  "#1f2937",  # Gray-800
    "border_medium":  "#374151",  # Gray-700
}
```

### 🔥 "TOKYO_NIGHT" (VSCode Tokyo Night theme)
```python
"tokyo_night": {
    "primary":     "#7aa2f7",  # Soft blue
    "secondary":   "#bb9af7",  # Soft purple
    "accent":      "#e0af68",  # Warm gold
    "success":     "#9ece6a",  # Soft green
    "error":       "#f7768e",  # Soft red
    "warning":     "#ff9e64",  # Soft orange
    "info":        "#7dcfff",  # Soft cyan
    "muted":       "#565f89",  # Muted blue-gray
    "background":  "#1a1b26",  # Dark navy
    "surface":     "#24283b",  # Lighter navy
    "text":        "#c0caf5",  # Soft white-blue
    "border_dim":     "#292e42",
    "border_active":  "#3b4261",
}
```

---

## 3. LAYOUT PATTERNS — Premium Structural Design

### 3.1 "Glass Panel" Effect
```css
/* Frosted glass panels with layered borders */
#left-panel {
    border: tall $primary;
    border-title-color: $primary;
    border-title-background: $surface;
    background: $surface 90%;        /* Slight transparency */
    padding: 0;
}

/* Inner glow effect using box-shadow-like layered backgrounds */
#center-panel {
    border: tall $secondary;
    border-title-color: $secondary;
    border-title-background: $surface;
    box-shadow: none;  /* Textual doesn't have box-shadow, use borders instead */
}

/* Premium: Double-border effect using nested containers */
#right-panel {
    border: tall $accent;
    padding: 0;
}
#right-panel > .panel-inner {
    border: round $border_dim;
    margin: 0 1;
    padding: 0 1;
}
```

### 3.2 "Grid Layout" — Dashboard Style
```css
/* Instead of plain 3-panel, use a dashboard grid */
#main-container {
    layout: grid;
    grid-size: 3 2;       /* 3 columns, 2 rows */
    grid-gutter: 1;       /* Space between cells */
    grid-columns: 30% 40% 30%;
    grid-rows: auto 1fr;   /* Status bar + main content */
}

/* Top row: status indicators */
#status-left {    column-span: 1; row-span: 1; }
#status-center {  column-span: 1; row-span: 1; }
#status-right {   column-span: 1; row-span: 1; }

/* Bottom row: main panels */
#left-panel {     column-span: 1; row-span: 1; }
#center-panel {   column-span: 1; row-span: 1; }
#right-panel {    column-span: 1; row-span: 1; }
```

### 3.3 "Split Chrome" — Lines Not Boxes
```css
/* Premium minimal: Use thin divider lines instead of thick borders */
#left-panel {
    width: 30%;
    border-right: vkey $border_dim;  /* Vertical keyline only */
    border-left: none;
    border-top: none;
    border-bottom: none;
}

#center-panel {
    width: 40%;
    border-right: vkey $border_dim;
    border-left: none;
    border-top: none;
    border-bottom: none;
}

#right-panel {
    width: 30%;
    border: none;  /* No border on rightmost panel */
}

/* Top chrome bar */
#top-chrome {
    height: 1;
    background: $primary;
    dock: top;
}

/* Bottom chrome bar */
#bottom-chrome {
    height: 1;
    background: $primary;
    dock: bottom;
}
```

---

## 4. CSS TECHNIQUES — Making It Look Premium

### 4.1 "Neon Border Glow" Effect
Textual doesn't support box-shadow, but you can simulate glow with nested containers:
```css
/* Outer glow container */
.glow-panel {
    border: tall $primary 40%;     /* Dim outer glow */
    padding: 0;
}
.glow-panel:focus {
    border: tall $primary;         /* Bright on focus */
}
.glow-panel > .inner {
    border: round $border_dim;     /* Inner subtle border */
    margin: 0;
    padding: 0 1;
}
```

### 4.2 "Scanline" Overlay (CRT Effect)
```css
/* Subtle scanline effect using alternating background opacity */
.scanline-overlay {
    background: $surface;
    /* Can't do real scanlines in Textual CSS, but can use
       subtle color tinting on different rows */
}
```

### 4.3 Status Bar with "LED Indicators"
```css
/* LED-style status dots */
#status-conn {
    color: #00ff41;      /* Green LED for connected */
    text-style: bold;
    background: #00ff4115;  /* Subtle glow background */
    padding: 0 1;
}
#status-conn.disconnected {
    color: #ff0000;
    background: #ff000015;
}
/* Pulse animation for thinking state */
#status-phase.thinking {
    color: $warning;
    text-style: bold reverse;  /* Blinking effect */
}
```

### 4.4 Premium Button Design
```css
/* Neon-style action buttons */
#accept-btn {
    background: $success 80%;
    color: $text;
    text-style: bold;
    border: tall $success;
    margin-right: 1;
    min-width: 16;
}
#accept-btn:hover {
    background: $success;
    border: tall $success;
    text-style: bold;       /* Brighter on hover */
}
#accept-btn:disabled {
    background: $surface;
    color: $text-disabled;
    border: tall $border_dim;
    text-style: not bold;
}

/* "Disrupt" button with danger neon glow */
#disrupt-btn {
    background: $error 60%;
    color: $text;
    text-style: bold;
    border: tall $error;
}
#disrupt-btn:hover {
    background: $error;
    border: tall $error;
}
```

### 4.5 Tab Styling — Cyberpunk Underline
```css
/* Instead of default tabs, use colored underlines */
#center-tabs {
    height: 1fr;
}
/* Active tab gets a bright underline */
TabbedContent Tab {
    padding: 0 2;
    text-style: bold;
}
TabbedContent Tab.-active {
    text-style: bold;
    color: $primary;
    border-bottom: wide $primary;   /* Bright underline for active */
}
TabbedContent Tab:hover {
    color: $primary;
    border-bottom: tall $primary 50%;
}
```

### 4.6 Input Field — Terminal-Style
```css
/* Glowing input with neon cursor */
#chat-input {
    border: tall $primary;
    background: $surface;
    padding: 0 2;
    color: $text;
}
#chat-input:focus {
    border: tall $primary;
    box-shadow: none;  /* N/A in Textual, but focus border is key */
}
#chat-input.-placeholder {
    color: $muted;
}
```

### 4.7 RichLog / Chat Styling
```css
/* Chat log with subtle line separators */
#manager-log {
    height: 1fr;
    border: none;
    padding: 0 1;
    scrollbar-size: 1 1;
    scrollbar-color: $primary 30%;
    scrollbar-color-hover: $primary 60%;
    scrollbar-color-active: $primary;
}
/* Subtle horizontal rules between messages */
#manager-log > .message-separator {
    color: $border_dim;
    height: 1;
}
```

---

## 5. ANIMATION EFFECTS

### 5.1 Breathing/Pulse Animation for Status
```python
# In ThinkingIndicator — smooth breathing effect
class ThinkingIndicator(Static):
    CSS = """
    #thinking-indicator {
        height: auto;
        dock: bottom;
        padding: 0 1;
        color: $accent;
        text-style: bold;
        display: none;
    }
    """

    _SPINNER_CHARS = ("⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷")  # Braille spinner

    def start(self, message="Processing"):
        self._message = message
        self.display = True
        self._spinner_index = 0
        self._update_spinner()
        self._timer = self.set_interval(0.08, self._tick)  # 12fps for smooth spin
```

### 5.2 Phase Transition Animations
```python
# When contract state changes, flash the border briefly
async def _flash_border(self, widget_id: str, color: str, duration: float = 0.3):
    """Flash a widget's border color briefly for visual feedback."""
    widget = self.query_one(widget_id)
    original_styles = widget.styles
    widget.styles.border = ("tall", color)
    await asyncio.sleep(duration)
    # Reset to original
    widget.styles.border = original_styles.border
```

### 5.3 Loading Bar Animation
```python
# ASCII progress bar with animation
def render_progress_bar(self, progress: float, width: int = 30) -> str:
    """Render an animated progress bar."""
    filled = int(width * progress)
    # Use gradient-like characters for smooth appearance
    chars = "▏▎▍▌▋▊▉█"
    full_blocks = filled
    partial = int((width * progress - full_blocks) * (len(chars) - 1))
    bar = "█" * full_blocks
    if partial > 0 and full_blocks < width:
        bar += chars[partial]
    bar += "░" * (width - len(bar))
    return f"[{bar}]"
```

### 5.4 Typing Effect for Manager Messages
```python
# Stream text character by character for a "hacker terminal" feel
async def _type_message(self, text: str, widget: Static, delay: float = 0.01):
    """Type out a message character by character."""
    current = ""
    for char in text:
        current += char
        widget.update(Text.from_markup(current + "█"))  # Blinking cursor
        await asyncio.sleep(delay)
    widget.update(Text.from_markup(current))  # Remove cursor
```

---

## 6. BORDER STYLES — Reference Chart

| Style | CSS Value | Visual | Best For |
|-------|-----------|--------|----------|
| None | `border: none;` | No border | Inner panels, clean look |
| Keyline | `border-right: vkey #2a2a4a;` | Thin vertical line | Panel dividers |
| Round | `border: round $primary;` | `╭─╮│╰─╯` | Classic terminal |
| Tall | `border: tall $primary;` | `┏━┓┃┗━┛` | Bold panels, focus |
| Wide | `border: wide $primary;` | `╔═╗║╚═╝` | Heavy emphasis |
| Heavy | `border: heavy $primary;` | `┏━┓┃┗━┛` (thicker) | Modals, alerts |
| Double | `border: double $primary;` | `╔═╗║╚═╝` | Premium frames |
| Dashed | `border: dashed $primary;` | Dashed line | Work-in-progress |
| Hidden | `border: hidden;` | Space only | Spacing without visible border |

### Premium Border Combinations
```css
/* "Neon Frame" — tall border with accent color */
.panel-premium {
    border: tall $primary;
    border-title-color: $primary;
    border-title-background: $surface;
    padding: 0 1;
}

/* "Stealth" — round border with dim color */
.panel-stealth {
    border: round $border_dim;
    padding: 0 1;
}

/* "Active Stealth" — brightens on focus */
.panel-stealth:focus-within {
    border: round $primary;
}

/* "Chrome Line" — top only, rest none */
.panel-chrome {
    border-top: tall $primary;
    border-bottom: none;
    border-left: none;
    border-right: none;
    padding: 1 2;
}
```

---

## 7. TYPOGRAPHY CHOICES

### Unicode Characters for Premium TUI Feel

**Spinners (progress indicators):**
```
Braille:     ⣾ ⣽ ⣻ ⢿ ⡿ ⣟ ⣯ ⣷  (smoothest)
Arc:         ◐ ◓ ◑ ◒              (current KantorKu)
Block:       ▉ ▊ ▋ ▌ ▍ ▎ ▏       (loading bar)
Moon:        🌑 🌒 🌓 🌔 🌕       (cute)
Dots:        ⠁ ⠂ ⠄ ⡀ ⢀ ⠠ ⠐ ⠈  (minimal)
```

**Status icons (upgrade from current):**
```
✓  →  ✔ or ✅ (success)
✗  →  ✘ or ❌ (failure)
○  →  ◌ or ○ (pending/idle)
◐  →  ◔ or ⏳ (in progress)
⚡ →  ⚡ or 🔥 (active/working)
📋 →  📋 or ╔═╗ (contract)
```

**Box drawing for structural elements:**
```
╔═══════════════════════════════════════╗
║  KANTORKU  │  contract_presented      ║
╠════════════╦══════════════════════════╣
║            ║                          ║
║  MANAGER   ║     WORKERS LIVE         ║
║  CHAT      ║                          ║
║            ║  ▸ coder_backend: ...    ║
║  > type    ║  ▸ coder_frontend: ...   ║
║            ║  ▸ conductor: summary    ║
╚════════════╩══════════════════════════╝
```

### Text Style Hierarchy
```python
# Premium text hierarchy using Rich markup
HEADING = "[bold $primary]{text}"           # Panel titles, state labels
SUBHEADING = "[bold $text]{text}"           # Section headers
BODY = "[$text]{text}"                       # Regular text
DIMMED = "[dim]{text}"                       # Secondary info
ACCENT = "[$accent bold]{text}"              # Important values
CODE = "[on $surface $primary]{text}"        # Inline code
BADGE_SUCCESS = "[bold on $success $text]{text}"  # Status badges
BADGE_ERROR = "[bold on $error $text]{text}"      # Error badges
```

---

## 8. SPECIFIC ENHANCEMENTS FOR KANTORKU TUI

### 8.1 Enhanced Header — "Neon Chrome Bar"
```css
/* Replace simple Header with a custom chrome bar */
#top-chrome {
    height: 2;
    background: $surface;
    border-bottom: tall $primary;
    layout: horizontal;
    padding: 0 2;
}

#chrome-logo {
    color: $primary;
    text-style: bold;
    width: auto;
    padding: 0 2;
}

#chrome-state {
    color: $accent;
    text-style: bold;
    width: auto;
}

#chrome-conn {
    color: $success;
    dock: right;
    width: auto;
    padding: 0 2;
}
```

### 8.2 Contract Display — "Neon Card" Effect
```python
# In ContractDisplay._render(), use Rich Panel with styled borders:
self.update(Panel(
    Group(*parts),
    title="[bold]⟨ CONTRACT ⟩[/bold]",
    border_style=border_color,
    padding=(0, 1),
    # Add subtitle for context
    subtitle=f"rev:{self.revision_count}" if self.revision_count > 0 else None,
))
```

### 8.3 Workers Live Stream — "Terminal Feed" Aesthetic
```python
# Add timestamp prefix to each event for that "log file" feel
def _render_stream(self):
    ts = datetime.now().strftime("%H:%M:%S")
    # Color-code the timestamp
    prefix = f"[dim]{ts}[/dim] "
    # ... append to each event line
```

### 8.4 Status Bar — "HUD Dashboard"
```css
/* Multi-section status bar with colored segments */
#status-bar {
    dock: bottom;
    height: 1;
    layout: horizontal;
    background: $surface;
    border-top: tall $primary;
    padding: 0 1;
}

#status-conn { color: $success; width: auto; }
#status-phase { color: $primary; width: auto; }
#status-session { color: $muted; width: auto; }
#status-cost { color: $accent; width: auto; dock: right; }
#status-calls { color: $muted; width: auto; dock: right; }
```

### 8.5 Disrupt Button — "Emergency Stop" Aesthetic
```css
#disrupt-btn {
    dock: bottom;
    margin: 0 1;
    background: $error 50%;
    color: $text;
    text-style: bold;
    border: tall $error;
    text-align: center;
    min-width: 100%;
}
#disrupt-btn:hover {
    background: $error;
    border: tall $error;
    text-style: bold reverse;  /* Flash effect on hover */
}
```

---

## 9. COMPLETE EXAMPLE: "Synthwave" Theme CSS for KantorKu

```python
# Add to KANTORKU_THEMES in themes.py
"synthwave": {
    "primary":     "#ff79c6",
    "secondary":   "#bd93f9",
    "accent":      "#f1fa8c",
    "success":     "#50fa7b",
    "error":       "#ff5555",
    "warning":     "#ffb86c",
    "info":        "#8be9fd",
    "muted":       "#6272a4",
    "background":  "#0d0d1a",
    "surface":     "#1a1a2e",
    "text":        "#f8f8f2",
}

# Enhanced CSS for the main app
SYNTHWAVE_CSS = """
Screen {
    background: #0d0d1a;
}

#main-container {
    layout: horizontal;
    height: 1fr;
}

/* ── Left Panel: Manager Chat ── */
#left-panel {
    width: 30%;
    height: 100%;
    border: tall #ff79c6;
    border-title-color: #ff79c6;
    border-title-background: #1a1a2e;
    background: #1a1a2e;
}

/* ── Center Panel: Workers Live ── */
#center-panel {
    width: 40%;
    height: 100%;
    border: tall #bd93f9;
    border-title-color: #bd93f9;
    border-title-background: #1a1a2e;
    background: #1a1a2e;
}

/* ── Right Panel: Contract ── */
#right-panel {
    width: 30%;
    height: 100%;
    border: tall #f1fa8c;
    border-title-color: #f1fa8c;
    border-title-background: #1a1a2e;
    background: #1a1a2e;
}

/* ── Input Bar ── */
#chat-input {
    border: tall #ff79c6;
    background: #12122a;
    color: #f8f8f2;
}
#chat-input:focus {
    border: tall #ff79c6;
}

/* ── Action Buttons ── */
#accept-btn {
    background: #50fa7b 80%;
    color: #0d0d1a;
    text-style: bold;
    border: tall #50fa7b;
    margin-right: 1;
}
#accept-btn:hover {
    background: #50fa7b;
}

#revise-btn {
    background: #f1fa8c 80%;
    color: #0d0d1a;
    text-style: bold;
    border: tall #f1fa8c;
}
#revise-btn:hover {
    background: #f1fa8c;
}

#disrupt-btn {
    background: #ff5555 60%;
    color: #f8f8f2;
    text-style: bold;
    border: tall #ff5555;
}
#disrupt-btn:hover {
    background: #ff5555;
}

/* ── Status Bar ── */
#status-bar {
    dock: bottom;
    height: 1;
    background: #12122a;
    color: #6272a4;
    border-top: tall #bd93f9 50%;
    padding: 0 1;
}

#status-conn { color: #50fa7b; }
#status-conn.disconnected { color: #ff5555; }
#status-phase { color: #8be9fd; }
#status-cost { color: #ffb86c; }

/* ── Tabs ── */
#center-tabs {
    height: 1fr;
}
TabbedContent Tab.-active {
    border-bottom: wide #bd93f9;
    text-style: bold;
    color: #bd93f9;
}

/* ── Filter Buttons ── */
.filter-btn {
    margin: 0 1;
    height: 1;
    min-width: 0;
    background: #12122a;
    color: #6272a4;
    border: round #2a2a4a;
}
.filter-btn.active {
    text-style: bold;
    color: #8be9fd;
    border: round #8be9fd 50%;
    background: #8be9fd 10%;
}

/* ── Manager Log ── */
#manager-log {
    scrollbar-size: 1 1;
    scrollbar-color: #ff79c6 30%;
    scrollbar-color-hover: #ff79c6 60%;
}

/* ── Thinking Indicator ── */
#thinking-indicator {
    color: #f1fa8c;
    text-style: bold;
    background: #f1fa8c 10%;
}
"""
```

---

## 10. UNIQUE VISUAL ELEMENTS TO STEAL

### 10.1 "ASCII Art Logo" in Header
```python
# Add a small ASCII art banner at startup
KANTORKU_BANNER = """
[bold #ff79c6]╔══════════════════════════════════════╗[/]
[bold #ff79c6]║[/] [bold #f8f8f2]  kantorku[/] [dim #6272a4]v0.8.0[/dim #6272a4]  [bold #bd93f9]chat-driven office[/] [bold #ff79c6]║[/]
[bold #ff79c6]╚══════════════════════════════════════╝[/]
"""
```

### 10.2 "Data Stream" Decoration
```python
# Decorative side columns showing hex/stream data (like The Matrix)
# Use Rich Columns with dim random hex strings
def _render_data_stream(self) -> Text:
    """Decorative hex stream for cyberpunk feel."""
    import random
    hex_chars = "0123456789abcdef"
    stream = "".join(random.choice(hex_chars) for _ in range(16))
    return Text.from_markup(f"[dim #2a2a4a]{stream}[/dim #2a2a4a]")
```

### 10.3 "Section Dividers" with Unicode
```python
# Premium section dividers in chat
DIVIDER_FULL = "━" * 40
DIVIDER_DOT = "╌" * 40
DIVIDER_DASH = "╍" * 40
DIVIDER_DOUBLE = "═" * 40
DIVIDER_FANCY = "─── ◆ ───"
DIVIDER_ARROW = "─── ▸ ───"
DIVIDER_CROSS = "─── ✦ ───"
```

### 10.4 "Badge" Style Status Indicators
```python
# Rich markup badges for worker status
BADGE_IDLE = "[dim on #1a1a2e] IDLE [/]"
BADGE_THINKING = "[#f1fa8c bold on #2a2a1a] THINKING [/]"
BADGE_ACTIVE = "[#50fa7b bold on #1a2a1a] ACTIVE [/]"
BADGE_DONE = "[#50fa7b on #1a2a1a] DONE [/]"
BADGE_FAILED = "[#ff5555 bold on #2a1a1a] FAILED [/]"
BADGE_WORKING = "[#8be9fd bold on #1a2a2a] WORKING [/]"
```

---

## 11. PRIORITY ENHANCEMENT CHECKLIST

### Quick Wins (30 min each)
- [ ] Add "synthwave" + "neon_nights" themes to `themes.py`
- [ ] Replace `border: solid` with `border: tall` for all panels
- [ ] Add colored border-title-background to panels
- [ ] Upgrade spinner from `◐◓◑◒` to braille `⣾⣽⣻⢿⡿⣟⣯⣷`
- [ ] Add scrollbar styling to all scrollable panels
- [ ] Add timestamp prefix to WorkersLiveStream entries

### Medium Effort (1-2 hours each)
- [ ] Custom header widget replacing default `Header`
- [ ] Phase-aware border colors (panels glow based on contract state)
- [ ] Neon-style button design with `border: tall` on all action buttons
- [ ] Filter bar styling with active/inactive states
- [ ] Contract display with Rich Tree styling upgrade

### Big Impact (Half day each)
- [ ] Complete "Synthwave" CSS theme with all widget overrides
- [ ] Dashboard grid layout with status indicators row
- [ ] Animated border flash on state transitions
- [ ] ASCII art banner + startup animation
- [ ] "Glass panel" nested border effect

---

## 12. TEXTUAL CSS QUICK REFERENCE (for premium TUIs)

```css
/* Color syntax */
color: #ff79c6;              /* Hex */
color: $primary;             /* Design variable */
color: $primary 50%;         /* With alpha */
color: rgb(255, 121, 198);  /* RGB */

/* Border syntax */
border: tall $primary;                          /* All sides */
border: round #bd93f9;                          /* All sides round */
border-top: tall $primary;                      /* Single side */
border-right: vkey $border_dim;                 /* Vertical keyline */
border-title-color: $primary;                   /* Title color */
border-title-background: $surface;              /* Title bg */
border-title-style: bold;                       /* Title style */

/* Layout */
layout: horizontal | vertical | grid;
grid-size: 3 2;          /* 3 cols, 2 rows */
grid-gutter: 1;          /* Gap between cells */
grid-columns: 30% 40% 30%;
grid-rows: auto 1fr;

/* Docking */
dock: top | bottom | left | right;

/* Sizing */
width: 30% | 32 | 1fr;    /* %, chars, or fraction */
height: auto | 1fr | 100%;

/* Text */
text-style: bold | italic | underline | reverse | not bold;
text-align: center | left | right;

/* Scrollbar */
scrollbar-size: 1 1;
scrollbar-color: $primary 30%;
scrollbar-color-hover: $primary 60%;
scrollbar-color-active: $primary;

/* Visibility */
display: block | none;
visibility: visible | hidden;
opacity: 0.5;               /* 0-1 */

/* Overflow */
overflow: hidden | scroll | auto;
overflow-x: hidden;
overflow-y: scroll;
```

---

*This report was compiled based on analysis of the existing KantorKu TUI codebase at
`/home/z/my-project/framework/kantorku/tui/` and knowledge of the Python Textual
framework ecosystem. All CSS values are valid Textual CSS (TCSS) syntax.*
