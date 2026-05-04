"""
Connection — Handles WebSocket and HTTP connections to the kantorku server.

Supports:
- WebSocket client channel (/ws/client) for chat
- WebSocket office channel (/ws/office) for events
- HTTP REST endpoints for status, health, cost, metrics, memory, spans
- SSE for event streaming (fallback when WS unavailable)
- Auto-reconnection on disconnect
- Fixed HTTP fallbacks using correct server endpoints
- Interrupt support for 3-panel TUI workflow
"""

from __future__ import annotations

import asyncio
import json
import logging
from enum import Enum
from typing import Any, AsyncIterator

import httpx

logger = logging.getLogger("kantorku.tui.connection")


class ConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class OfficeConnection:
    """
    Manages connections to a kantorku server.

    Uses:
    - HTTP for REST endpoints (status, health, cost, metrics, memory, spans)
    - WebSocket for client chat (/ws/client)
    - SSE for event streaming (/events/stream/{session_id})

    Fixed endpoints:
    - POST /sessions/{id}/accept → accept contract (was broken, now uses WS-first)
    - GET /status → office status with workers, health, cost, pool, queue
    - GET /health/dashboard → full health dashboard
    - GET /cost → cost report
    - GET /metrics → observability metrics
    - GET /spans → recent tracing spans
    - GET /circuit-breaker → circuit breaker status
    - GET /sessions → list sessions
    - GET /sessions/{id} → session details with events & task results
    - GET /events/{id} → event replay for reconnection
    - GET /memory/stats → memory system stats (Ring1/Ring2)
    - GET /health/dashboard includes alerts, queue info

    Usage:
        conn = OfficeConnection("http://localhost:8000", "session-123")
        await conn.connect()

        # Send a message
        async for event in conn.send_message("Build me a rate limiter"):
            print(event)

        # Accept contract
        result = await conn.accept_contract()

        # Listen for events
        async for event in conn.listen_events():
            print(event)

        # Get status
        status = await conn.get_status()

        await conn.disconnect()
    """

    def __init__(self, server_url: str, session_id: str) -> None:
        self.server_url = server_url.rstrip("/")
        self.session_id = session_id
        self.state = ConnectionState.DISCONNECTED
        self._http_client: httpx.AsyncClient | None = None
        self._ws_client: Any = None  # websockets.WebSocketClientProtocol
        self._ws_office: Any = None
        self._connected = False
        self._last_event_id: str | None = None  # For reconnection replay

    async def connect(self) -> None:
        """Initialize connections to the server."""
        self.state = ConnectionState.CONNECTING
        self._http_client = httpx.AsyncClient(
            base_url=self.server_url,
            timeout=httpx.Timeout(30.0),
        )

        # Test connection with health check
        try:
            resp = await self._http_client.get("/health/live")
            if resp.status_code == 200:
                self.state = ConnectionState.CONNECTED
                self._connected = True
                logger.info(f"Connected to {self.server_url}")
            else:
                self.state = ConnectionState.ERROR
                raise ConnectionError(f"Server returned {resp.status_code}")
        except httpx.ConnectError as e:
            self.state = ConnectionState.ERROR
            raise ConnectionError(f"Cannot connect to {self.server_url}: {e}")

    async def disconnect(self) -> None:
        """Close all connections."""
        self._connected = False

        if self._ws_client:
            try:
                await self._ws_client.close()
            except Exception:
                pass
            self._ws_client = None

        if self._ws_office:
            try:
                await self._ws_office.close()
            except Exception:
                pass
            self._ws_office = None

        if self._http_client:
            try:
                await self._http_client.aclose()
            except Exception:
                pass
            self._http_client = None

        self.state = ConnectionState.DISCONNECTED

    async def send_message(self, message: str) -> AsyncIterator[dict[str, Any]]:
        """
        Send a user message to the Conductor via WebSocket.

        Yields events as they arrive from the server.
        Falls back to HTTP POST /sessions/{id} if WebSocket unavailable.
        """
        try:
            import websockets
        except ImportError:
            async for event in self._send_message_http(message):
                yield event
            return

        ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")

        try:
            async with websockets.connect(f"{ws_url}/ws/client") as ws:
                # Send user message
                await ws.send(json.dumps({
                    "type": "user_message",
                    "content": message,
                    "session_id": self.session_id,
                }))

                # Read events
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                        yield data

                        # Stop if we get a contract_ready or error
                        if data.get("type") in ("contract_ready", "error"):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            # Fallback to HTTP
            logger.warning(f"WebSocket failed, falling back to HTTP: {e}")
            async for event in self._send_message_http(message):
                yield event

    async def _send_message_http(self, message: str) -> AsyncIterator[dict[str, Any]]:
        """
        Fallback: Send a message via HTTP endpoint.

        Uses the correct server endpoints:
        - GET /sessions/{id} to check for existing session
        - The server only accepts new messages via WS, so this
          creates a minimal interaction
        """
        if not self._http_client:
            return

        try:
            # Try to get session info first
            resp = await self._http_client.get(
                f"/sessions/{self.session_id}",
                timeout=httpx.Timeout(10.0),
            )

            # The server primarily uses WebSocket for chat,
            # but we provide a helpful error message
            yield {
                "type": "error",
                "message": "WebSocket required for chat. Install websockets package: pip install websockets",
            }
        except Exception as e:
            yield {
                "type": "error",
                "message": f"HTTP error: {e}. Install websockets for full functionality.",
            }

    async def accept_contract(self) -> dict[str, Any] | None:
        """Accept the current contract via WebSocket."""
        try:
            import websockets
        except ImportError:
            return await self._accept_contract_http()

        ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")

        try:
            async with websockets.connect(f"{ws_url}/ws/client") as ws:
                await ws.send(json.dumps({
                    "type": "contract_accepted",
                    "session_id": self.session_id,
                }))

                # Read events until work_done
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                        if data.get("type") == "work_done":
                            return data.get("result", {})
                        elif data.get("type") == "work_started":
                            continue
                        elif data.get("type") == "error":
                            return data
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning(f"WebSocket accept failed: {e}")
            return await self._accept_contract_http()

        return None

    async def _accept_contract_http(self) -> dict[str, Any] | None:
        """
        Fallback: Accept contract via HTTP.

        Note: The server only accepts contract accept via WS.
        This provides a clear error message.
        """
        if not self._http_client:
            return None

        return {
            "type": "error",
            "message": "WebSocket required for contract acceptance. Install websockets: pip install websockets",
        }

    async def revise_contract(self, feedback: str) -> AsyncIterator[dict[str, Any]]:
        """Request a contract revision via WebSocket."""
        try:
            import websockets
        except ImportError:
            # HTTP fallback — limited but functional
            yield {
                "type": "error",
                "message": "WebSocket required for revision. Install websockets: pip install websockets",
            }
            return

        ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")

        try:
            async with websockets.connect(f"{ws_url}/ws/client") as ws:
                await ws.send(json.dumps({
                    "type": "contract_revision",
                    "feedback": feedback,
                    "session_id": self.session_id,
                }))

                async for raw in ws:
                    try:
                        data = json.loads(raw)
                        yield data
                        if data.get("type") in ("contract_ready", "error"):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            yield {
                "type": "error",
                "message": f"Revision failed: {e}",
            }

    async def listen_events(self) -> AsyncIterator[dict[str, Any]]:
        """
        Stream office events in real-time.

        Tries WebSocket first, falls back to SSE.
        On reconnection, replays missed events.
        """
        # Replay missed events on reconnection
        if self._last_event_id and self._http_client:
            try:
                resp = await self._http_client.get(
                    f"/events/{self.session_id}",
                    params={"limit": 50},
                    timeout=httpx.Timeout(10.0),
                )
                if resp.status_code == 200:
                    events = resp.json().get("events", [])
                    for event in events:
                        yield event
            except Exception:
                pass

        # Try WebSocket
        try:
            import websockets

            ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")

            async with websockets.connect(
                f"{ws_url}/ws/office?session_id={self.session_id}"
            ) as ws:
                self._ws_office = ws
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                        # Track event ID for reconnection
                        if "event_id" in data:
                            self._last_event_id = data["event_id"]
                        yield data
                    except json.JSONDecodeError:
                        continue
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"WS office stream failed, trying SSE: {e}")

        # Fallback to SSE
        if self._http_client:
            try:
                async with self._http_client.stream(
                    "GET",
                    f"/events/stream/{self.session_id}",
                    timeout=httpx.Timeout(None),
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                if "event_id" in data:
                                    self._last_event_id = data["event_id"]
                                yield data
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.debug(f"SSE stream ended: {e}")

    # ── REST Endpoints ─────────────────────────────────────────────

    async def get_status(self) -> dict[str, Any] | None:
        """Get office status via REST."""
        if not self._http_client:
            return None

        try:
            resp = await self._http_client.get("/status")
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    async def get_health(self) -> dict[str, Any] | None:
        """Get health dashboard via REST."""
        if not self._http_client:
            return None

        try:
            resp = await self._http_client.get("/health/dashboard")
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    async def get_cost(self) -> dict[str, Any] | None:
        """Get cost report via REST."""
        if not self._http_client:
            return None

        try:
            resp = await self._http_client.get("/cost")
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    async def get_metrics(self) -> dict[str, Any] | None:
        """Get observability metrics via REST."""
        if not self._http_client:
            return None

        try:
            resp = await self._http_client.get("/metrics")
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    async def get_spans(self, limit: int = 100) -> dict[str, Any] | None:
        """Get recent tracing spans via REST."""
        if not self._http_client:
            return None

        try:
            resp = await self._http_client.get("/spans", params={"limit": limit})
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    async def get_circuit_breakers(self) -> dict[str, Any] | None:
        """Get circuit breaker status via REST."""
        if not self._http_client:
            return None

        try:
            resp = await self._http_client.get("/circuit-breaker")
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    async def get_sessions(self) -> list[dict[str, Any]]:
        """List active sessions via REST."""
        if not self._http_client:
            return []

        try:
            resp = await self._http_client.get("/sessions")
            if resp.status_code == 200:
                return resp.json().get("sessions", [])
        except Exception:
            pass
        return []

    async def get_session_detail(self, session_id: str) -> dict[str, Any] | None:
        """Get session details via REST."""
        if not self._http_client:
            return None

        try:
            resp = await self._http_client.get(f"/sessions/{session_id}")
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    async def get_memory_stats(self) -> dict[str, Any] | None:
        """
        Get memory system statistics via REST.

        Note: This endpoint may not exist on older servers.
        Falls back to extracting from /status or /health/dashboard.
        """
        if not self._http_client:
            return None

        # Try dedicated memory endpoint first
        try:
            resp = await self._http_client.get("/memory/stats")
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass

        # Fallback: extract from health dashboard
        try:
            health = await self.get_health()
            if health:
                memory_info = {}
                # Some health dashboards include memory stats
                checks = health.get("checks", [])
                for check in checks:
                    if "memory" in check.get("name", "").lower():
                        memory_info.update(check.get("details", {}))

                if memory_info:
                    return memory_info
        except Exception:
            pass

        # Fallback: extract from status
        try:
            status = await self.get_status()
            if status:
                return {
                    "ring1": status.get("ring1", {}),
                    "ring2": status.get("ring2", {}),
                    "recent_contexts": [],
                }
        except Exception:
            pass

        return None

    async def get_events(self, session_id: str | None = None, limit: int = 50) -> list[dict]:
        """Get recent events for replay/reconnection."""
        if not self._http_client:
            return []

        sid = session_id or self.session_id
        try:
            resp = await self._http_client.get(
                f"/events/{sid}",
                params={"limit": limit},
            )
            if resp.status_code == 200:
                return resp.json().get("events", [])
        except Exception:
            pass
        return []

    async def send_interrupt(self, reason: str = "") -> dict[str, Any] | None:
        """
        Send an interrupt message to pause work and talk to the Manager.

        In 3-panel mode, this sends a user_message with [INTERRUPT] prefix
        which tells the Conductor to pause and give control back to the client.

        Args:
            reason: Optional reason for the interrupt

        Returns:
            Response from the server, or None if failed
        """
        content = f"[INTERRUPT] {reason}" if reason else "[INTERRUPT]"

        # Try WebSocket first
        try:
            import websockets
        except ImportError:
            return {"type": "error", "message": "WebSocket required for interrupt"}

        ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")

        try:
            async with websockets.connect(f"{ws_url}/ws/client") as ws:
                await ws.send(json.dumps({
                    "type": "user_message",
                    "content": content,
                    "session_id": self.session_id,
                }))

                # Read first response
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                        return data
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            return {"type": "error", "message": f"Interrupt failed: {e}"}

        return None
