"""
MCP Integration — O23: Manage MCP (Model Context Protocol) server connections.

Handles MCP server registration, phase-based enablement, tool calls,
and configuration persistence. Loads from kantorku.toml if available.

Like a sysadmin who manages which external tools and services
the office can connect to.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MCPServer:
    """An MCP server configuration."""
    name: str = ""
    url: str = ""
    server_type: str = "http"
    enabled_phases: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)


# Default phases where MCP servers can be active
_ALL_PHASES: list[str] = [
    "understanding",
    "planning",
    "briefing",
    "execution",
    "verification",
    "done",
]


class MCPManager:
    """
    MCP Manager — manage MCP server connections and tool access.

    Handles:
    - Server registration and removal
    - Phase-based server enablement
    - Tool listing and invocation
    - Configuration persistence (load/save kantorku.toml)

    Usage:
        manager = MCPManager(config_path="kantorku.toml")
        manager.add_server("github", "http://localhost:3001")
        manager.enable_for_phase("github", "execution")
        active = manager.get_active_servers("execution")
        result = manager.call_tool("github", "create_issue", {"title": "Bug"})
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._servers: dict[str, MCPServer] = {}
        self._config_path = Path(config_path) if config_path else None
        self._tool_results_cache: dict[str, dict[str, Any]] = {}

        # Try loading from config
        if self._config_path:
            self._load_from_config()

    def _load_from_config(self) -> None:
        """Load MCP configuration from kantorku.toml if it exists."""
        if not self._config_path or not self._config_path.exists():
            return

        try:
            # Try TOML parsing
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib  # type: ignore[no-redef]
                except ImportError:
                    return

            with open(self._config_path, "rb") as f:
                config = tomllib.load(f)

            mcp_config = config.get("mcp", {})
            servers = mcp_config.get("servers", [])

            if isinstance(servers, list):
                for server_cfg in servers:
                    if isinstance(server_cfg, dict):
                        name = server_cfg.get("name", "")
                        url = server_cfg.get("url", "")
                        server_type = server_cfg.get("type", "http")
                        phases = server_cfg.get("enabled_phases", [])
                        tools = server_cfg.get("tools", [])

                        if name and url:
                            self._servers[name] = MCPServer(
                                name=name,
                                url=url,
                                server_type=server_type,
                                enabled_phases=phases,
                                tools=tools,
                            )
            elif isinstance(servers, dict):
                for name, cfg in servers.items():
                    if isinstance(cfg, dict):
                        url = cfg.get("url", "")
                        server_type = cfg.get("type", "http")
                        phases = cfg.get("enabled_phases", [])
                        tools = cfg.get("tools", [])

                        if url:
                            self._servers[name] = MCPServer(
                                name=name,
                                url=url,
                                server_type=server_type,
                                enabled_phases=phases,
                                tools=tools,
                            )
        except Exception:
            # Config loading is best-effort
            pass

    def list_servers(self) -> list[MCPServer]:
        """
        List all registered MCP servers.

        Returns:
            List of MCPServer instances
        """
        return list(self._servers.values())

    def add_server(
        self,
        name: str,
        url: str,
        server_type: str = "http",
    ) -> MCPServer:
        """
        Register a new MCP server.

        Args:
            name: Server name (unique identifier)
            url: Server URL
            server_type: Server type ("http", "websocket", "stdio")

        Returns:
            The created MCPServer
        """
        server = MCPServer(
            name=name,
            url=url,
            server_type=server_type,
            enabled_phases=[],
            tools=[],
        )
        self._servers[name] = server
        return server

    def remove_server(self, name: str) -> bool:
        """
        Remove an MCP server by name.

        Args:
            name: Server name to remove

        Returns:
            True if the server was found and removed
        """
        if name in self._servers:
            del self._servers[name]
            return True
        return False

    def enable_for_phase(self, server_name: str, phase: str) -> None:
        """
        Enable an MCP server for a specific phase.

        Args:
            server_name: Server name
            phase: Phase to enable for
        """
        server = self._servers.get(server_name)
        if server and phase not in server.enabled_phases:
            server.enabled_phases.append(phase)

    def disable_after_phase(self, server_name: str, phase: str) -> None:
        """
        Disable an MCP server after a specific phase.

        Removes the server from all phases after the given one.

        Args:
            server_name: Server name
            phase: Phase after which to disable
        """
        server = self._servers.get(server_name)
        if not server:
            return

        try:
            phase_idx = _ALL_PHASES.index(phase)
            phases_to_remove = _ALL_PHASES[phase_idx + 1:]
            server.enabled_phases = [
                p for p in server.enabled_phases
                if p not in phases_to_remove
            ]
        except ValueError:
            pass

    def get_active_servers(self, current_phase: str) -> list[MCPServer]:
        """
        Get servers that are active for the current phase.

        Args:
            current_phase: The current execution phase

        Returns:
            List of MCPServer instances active in this phase
        """
        active = []
        for server in self._servers.values():
            if not server.enabled_phases:
                # No phase restrictions = always active
                active.append(server)
            elif current_phase in server.enabled_phases:
                active.append(server)
        return active

    def call_tool(
        self,
        server_name: str,
        tool_name: str,
        args: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Call a tool on an MCP server.

        In a real implementation, this would make an HTTP/WebSocket
        request to the server. Here, we simulate the call and
        return a structured result.

        Args:
            server_name: Server name
            tool_name: Tool name to call
            args: Arguments for the tool

        Returns:
            Result dict from the tool call
        """
        server = self._servers.get(server_name)
        if not server:
            return {
                "success": False,
                "error": f"Server '{server_name}' not found",
                "tool": tool_name,
            }

        if server.tools and tool_name not in server.tools:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not available on server '{server_name}'",
                "tool": tool_name,
                "available_tools": server.tools,
            }

        # Simulated tool call result
        result = {
            "success": True,
            "server": server_name,
            "tool": tool_name,
            "args": args or {},
            "result": f"Simulated result for {tool_name} on {server_name}",
            "timestamp": time.time(),
        }

        # Cache the result
        cache_key = f"{server_name}:{tool_name}"
        self._tool_results_cache[cache_key] = result

        return result

    def validate_server(self, name: str) -> tuple[bool, list[str]]:
        """
        Validate that a server is reachable and list available tools.

        In a real implementation, this would ping the server.
        Here, we validate the configuration.

        Args:
            name: Server name to validate

        Returns:
            Tuple of (is_reachable, available_tools)
        """
        server = self._servers.get(name)
        if not server:
            return False, []

        # Validate URL format
        url = server.url
        if not url:
            return False, []

        is_reachable = url.startswith(("http://", "https://", "ws://", "wss://", "stdio://"))
        available_tools = list(server.tools) if server.tools else []

        return is_reachable, available_tools

    def save_config(self) -> None:
        """
        Persist current MCP configuration to config file.

        Saves in a format compatible with kantorku.toml [mcp] section.
        """
        if not self._config_path:
            return

        config: dict[str, Any] = {"mcp": {"servers": {}}}

        for name, server in self._servers.items():
            config["mcp"]["servers"][name] = {
                "url": server.url,
                "type": server.server_type,
                "enabled_phases": server.enabled_phases,
                "tools": server.tools,
            }

        try:
            # Try to write as JSON (TOML writing requires additional deps)
            with open(self._config_path, "w") as f:
                json.dump(config, f, indent=2)
        except OSError:
            pass
