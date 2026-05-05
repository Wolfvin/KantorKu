"""
kantorku CLI — Just type `kantorku` and you're in.

Usage:
    kantorku                        Launch the TUI (embedded mode, no server needed)
    kantorku --config PATH          Launch with config file
    kantorku --remote --url URL     Connect to a running server
    kantorku --version              Show version

Everything else is a slash command INSIDE the TUI:
    /serve [--host HOST] [--port PORT]   Start API server
    /init [name]                         Scaffold a new project
    /run <message>                       One-shot task (auto-accept)
    /version                             Show version + runtime info
    /help                                Show all 45+ commands

Like Codex CLI — type `kantorku` and you're in.
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    """CLI entry point — just type `kantorku` to launch the TUI."""
    parser = argparse.ArgumentParser(
        prog="kantorku",
        description="kantorku - Kantor digital yang sesungguhnya - AI worker orchestration",
    )
    parser.add_argument("--config", "-c", help="Path to kantorku.toml")
    parser.add_argument("--remote", "-r", action="store_true",
                        help="Connect to a running server instead of embedded mode")
    parser.add_argument("--url", "-u", default="http://localhost:8000",
                        help="Server URL for remote mode (default: http://localhost:8000)")
    parser.add_argument("--version", "-V", action="store_true",
                        help="Show version and exit")
    parser.add_argument("--embedded", "-e", action="store_true", default=True,
                        help="Run Office in-process (default, no server needed)")

    args = parser.parse_args()

    # --version: quick exit without loading TUI
    if args.version:
        try:
            from kantorku import __version__
        except ImportError:
            __version__ = "unknown"
        print(f"kantorku v{__version__}")
        return

    # Launch the TUI — that's it, everything else is slash commands inside
    try:
        from kantorku.tui.app import KantorKuTUI, EmbeddedKantorKuTUI
    except ImportError as e:
        print("Error: TUI dependencies not installed.")
        print('  Install with: pip install "kantorku[all] @ git+https://github.com/Wolfvin/KantorKu.git"')
        print(f"  Details: {e}")
        sys.exit(1)

    config_path = getattr(args, "config", None)
    embedded = not getattr(args, "remote", False)

    if embedded:
        # Embedded mode — run Office directly in-process (default)
        app = EmbeddedKantorKuTUI(config_path=config_path)
    else:
        # Remote mode — connect to a running server
        app = KantorKuTUI(server_url=args.url, config_path=config_path)

    app.run()


if __name__ == "__main__":
    main()
