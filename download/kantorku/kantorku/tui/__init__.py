"""
kantorku.tui — Terminal User Interface for coders.

A full-featured TUI built with Textual + Rich that provides
a powerful terminal-first interface to ALL KantorKu features.

Layout:
    ┌─────────────────────────────────────────────────────────────────┐
    │  kantorku v0.4.0  │  Connected  │  session: abc123            │
    ├────────────────────────────────┬────────────────────────────────┤
    │                                │  [Workers] [Events] [Health]  │
    │   Chat with Conductor         │  [Memory]  [DAG]   [Briefing] │
    │                                │  [Pool]    [Queue] [Observe]  │
    │   > your message here         │  [Alerts]                      │
    │                                │                                │
    │   Conductor responds...       │  (tabbed content)              │
    │                                │                                │
    ├────────────────────────────────┴────────────────────────────────┤
    │  Ctrl+Q:Quit  Tab:Switch  Enter:Send  ↑/↓:History  Ctrl+C:Cancel│
    └─────────────────────────────────────────────────────────────────┘

Panels:
    Workers   — Live worker grid with status icons
    Events    — Real-time office event stream
    Health    — Provider health, circuit breakers, cost, alerts
    Memory    — 3-Ring memory explorer (Ring1/Ring2/Ring3)
    DAG       — Task dependency graph visualization
    Briefing  — Briefing room transcript viewer
    Pool      — Context pool prefetch status
    Queue     — Task queue & dead letter queue
    Observe   — Observability (spans, metrics, traces)
    Alerts    — Active health alerts

Commands:
    /help /status /workers /health /cost /memory /dag /briefing
    /pool /queue /trace /metrics /hooks /cache /config /alerts
    /delegate /export /theme /accept /revise /code /ask /reset /sessions

Usage:
    kantorku tui                    # Connect to default server
    kantorku tui --url ws://...     # Custom server URL
    kantorku tui --embedded         # In-process mode
    kantorku tui --config ...       # Use config file
"""

from kantorku.tui.app import KantorKuTUI, EmbeddedKantorKuTUI

__all__ = ["KantorKuTUI", "EmbeddedKantorKuTUI"]
