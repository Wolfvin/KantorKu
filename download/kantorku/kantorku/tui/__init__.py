"""
kantorku.tui — Chat-Driven 3-Panel Office Interface for Coders.

A full-featured TUI built with Textual + Rich that provides
a natural office workflow through chat-first interaction:

Layout:
    ┌─────────────────────────────────────────────────────────────────────┐
    │  kantorku v0.7.0  │  📋 contract_presented  │  conn:✓  │  rev:1  │
    ├──────────────┬───────────────────────────┬─────────────────────────┤
    │              │                           │                         │
    │   MANAGER    │      WORKERS LIVE         │      CONTRACT           │
    │   CHAT       │                           │                         │
    │              │  👥 BRIEFING               │  📋 CONTRACT PRESENTED  │
    │  You: Build  │    coder_backend: ...     │                         │
    │  me X        │    coder_frontend: ...    │  Tasks (3):             │
    │              │    conductor: summary     │  ○ Implement rate limit │
    │  Manager:    │                           │  ○ Add UI               │
    │  Sure! Here  │                           │  ○ Wire everything      │
    │  's the      │                           │                         │
    │  contract... │                           │  [✓ ACCEPT] [✏ REVISE]  │
    │              │                           │                         │
    │  ──────────  │                           │                         │
    │  [⚡ DISRUPT]│                           │  ─────────────────────  │
    │              │                           │  After REVISE click:    │
    │  > Type msg  │                           │  ✏️ AWAITING YOUR       │
    │              │                           │    REVISION             │
    │              │                           │  Write feedback below...│
    ├──────────────┴───────────────────────────┴─────────────────────────┤
    │  Ctrl+Q:Quit  Ctrl+A:Accept  Ctrl+R:Revise  Ctrl+I:Disrupt      │
    └─────────────────────────────────────────────────────────────────────┘

Panels:
    Left   — Chat with Manager (Conductor) + Disrupt button
    Center — Workers brainstorming & executing in real-time
    Right  — Contract display + Accept/Revise BUTTONS

Contract Accept/Revise Flow:
    1. Contract is presented in RIGHT panel with ACCEPT/REVISE buttons
    2. Click ACCEPT:
       - Contract is finalized and displayed as "CONTRACT ACCEPTED"
       - Workers begin execution
    3. Click REVISE:
       - Enter revision mode (input placeholder changes)
       - Write your feedback and press Enter
       - Manager brainstorms with workers (visible in center panel)
       - Manager may ask clarifying questions
       - New contract is presented with ACCEPT/REVISE buttons again
    4. Repeat until satisfied, then ACCEPT

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
