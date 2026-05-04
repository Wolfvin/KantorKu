"""
kantorku.tui — 3-Panel Office Interface for Coders.

A full-featured TUI built with Textual + Rich that provides
a natural office workflow through 3 panels:

Layout:
    ┌─────────────────────────────────────────────────────────────────────┐
    │  kantorku v0.5.0  │  Connected  │  session: abc123                 │
    ├──────────────┬───────────────────────────┬─────────────────────────┤
    │              │                           │                         │
    │   MANAGER    │      WORKERS LIVE         │      CONTRACT           │
    │   CHAT       │                           │                         │
    │              │  👥 BRIEFING               │  📋 Contract: ...       │
    │  You: Build  │    coder_backend: ...     │  State: presented       │
    │  me X        │    coder_frontend: ...    │                         │
    │              │    conductor: summary     │  Tasks (3):             │
    │  Manager:    │                           │  ○ Implement rate limit │
    │  Sure! Let   │  ⚡ EXECUTING             │  ○ Add UI               │
    │  me draft... │    ● coder_backend: ...   │  ○ Wire everything      │
    │              │    ○ coder_frontend: ...   │                         │
    │  ──────────  │                           │  [ACCEPT] [REVISE]      │
    │  [INTERRUPT] │  🔍 VERIFYING             │                         │
    │              │    ✓ Design: OK            │                         │
    │  > type msg  │    ✓ Engineering: OK      │                         │
    │              │                           │                         │
    ├──────────────┴───────────────────────────┴─────────────────────────┤
    │  Ctrl+Q:Quit  Ctrl+A:Accept  Ctrl+R:Revise  Ctrl+I:Interrupt    │
    └─────────────────────────────────────────────────────────────────────┘

Panels:
    Left   — Chat with Manager (Conductor) + Interrupt button
    Center — Workers brainstorming & executing in real-time
    Right  — Contract display with Accept/Revise actions

Workflow:
    1. Chat with Manager in LEFT panel
    2. Manager drafts contract → appears in RIGHT panel
    3. Accept contract → Workers brainstorm in CENTER panel
    4. Workers execute → Live output in CENTER panel
    5. Need to change direction? Hit INTERRUPT → back to Manager chat

Slash commands still work as secondary tools — /help for list.

Usage:
    kantorku tui                    # Connect to default server
    kantorku tui --url ws://...     # Custom server URL
    kantorku tui --embedded         # In-process mode
    kantorku tui --config ...       # Use config file
"""

from kantorku.tui.app import KantorKuTUI, EmbeddedKantorKuTUI

__all__ = ["KantorKuTUI", "EmbeddedKantorKuTUI"]
