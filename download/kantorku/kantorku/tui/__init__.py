"""
kantorku.tui — Terminal User Interface for coders.

A full-featured TUI built with Textual + Rich that provides
a powerful terminal-first interface to KantorKu's multi-agent office.

Layout:
    ┌─────────────────────────────────────────────────────────────────┐
    │  kantorku v0.4.0  │  Connected  │  session: abc123            │
    ├────────────────────────────────┬────────────────────────────────┤
    │                                │  [Workers] [Events] [Health]  │
    │   Chat with Conductor         │                                │
    │                                │  (tabbed content)              │
    │   > your message here         │                                │
    │                                │                                │
    │   Conductor responds...       │                                │
    │                                │                                │
    ├────────────────────────────────┴────────────────────────────────┤
    │  Ctrl+Q:Quit  Tab:Switch  Enter:Send  Ctrl+C:Cancel            │
    └─────────────────────────────────────────────────────────────────┘

Usage:
    kantorku tui                    # Connect to default server
    kantorku tui --url ws://...     # Custom server URL
    kantorku tui --config ...       # Use config file
"""

from kantorku.tui.app import KantorKuTUI

__all__ = ["KantorKuTUI"]
