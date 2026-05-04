"""
kantorku.tui — Chat-Driven 3-Panel Office Interface for Coders.

A full-featured TUI built with Textual + Rich that provides
a natural office workflow through chat-first interaction:

Layout:
    ┌─────────────────────────────────────────────────────────────────────┐
    │  kantorku v0.6.0  │  ⚡ working  │  conn:✓  │  $0.0023            │
    ├──────────────┬───────────────────────────┬─────────────────────────┤
    │              │                           │                         │
    │   MANAGER    │      WORKERS LIVE         │      CONTRACT           │
    │   CHAT       │                           │                         │
    │              │  👥 BRIEFING               │  📋 Contract: ...       │
    │  You: Build  │    coder_backend: ...     │  State: PRESENTED       │
    │  me X        │    coder_frontend: ...    │                         │
    │              │    conductor: summary     │  Tasks (3):             │
    │  Manager:    │                           │  ○ Implement rate limit │
    │  Sure! Here  │  ⚡ EXECUTING             │  ○ Add UI               │
    │  's the      │    ● coder_backend: ...   │  ○ Wire everything      │
    │  contract... │    ○ coder_frontend: ...   │                         │
    │              │                           │  [✓ ACCEPT] [✏ REVISE]  │
    │  ──────────  │  🔍 VERIFYING             │                         │
    │  [⚡ DISRUPT]│    ✓ Design: OK            │                         │
    │              │    ✓ Engineering: OK      │                         │
    │  > Type msg  │                           │                         │
    │              │                           │                         │
    ├──────────────┴───────────────────────────┴─────────────────────────┤
    │  Ctrl+Q:Quit  Ctrl+A:Accept  Ctrl+R:Revise  Ctrl+I:Disrupt      │
    └─────────────────────────────────────────────────────────────────────┘

Panels:
    Left   — Chat with Manager (Conductor) + Disrupt button
    Center — Workers brainstorming & executing in real-time
    Right  — Contract display + Accept/Revise BUTTONS

Chat-Driven Workflow:
    1. Type naturally in LEFT panel — Manager handles everything
    2. When contract is presented:
       - Type "yes", "ok", "accept" → auto-accept
       - Type "revise", "change X" → auto-revise with feedback
       - Or click ✓ ACCEPT / ✏ REVISE buttons in right panel
    3. Workers brainstorm & execute in CENTER panel (live)
    4. Need to redirect? Click ⚡ DISRUPT or type "stop"/"wait"

Natural Language Actions (no slash commands needed):
    Accept:  yes, ok, accept, approve, go ahead, sure, ship it, ...
    Revise:  no, revise, change X, I want Y, not quite, could you, ...
    Disrupt: stop, wait, pause, halt, disrupt, cancel, ...

Slash commands still work as secondary tools — /help for list.

Usage:
    kantorku tui                    # Connect to default server
    kantorku tui --url ws://...     # Custom server URL
    kantorku tui --embedded         # In-process mode
    kantorku tui --config ...       # Use config file
"""

from kantorku.tui.app import KantorKuTUI, EmbeddedKantorKuTUI

__all__ = ["KantorKuTUI", "EmbeddedKantorKuTUI"]
