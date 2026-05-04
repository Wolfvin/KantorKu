"""
Connection — Handles WebSocket and HTTP connections to the kantorku server.

Supports:
- WebSocket client channel (/ws/client) for chat
- WebSocket office channel (/ws/office) for events
- HTTP REST endpoints for status, health, cost
- SSE for event streaming (fallback when WS unavailable)
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
    - HTTP for REST endpoints (status, health, cost)
    - WebSocket for client chat (/ws/client)
    - SSE for event streaming (/events/stream/{session_id})

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
        """
        try:
            import websockets
        except ImportError:
            # Fallback to HTTP
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
        """Fallback: Send a message via HTTP run endpoint."""
        if not self._http_client:
            return

        try:
            resp = await self._http_client.post(
                "/run",
                json={"message": message, "session_id": self.session_id},
                timeout=httpx.Timeout(120.0),
            )
            if resp.status_code == 200:
                result = resp.json()
                yield {
                    "type": "manager_message",
                    "content": "Task completed.",
                }
                yield {
                    "type": "work_done",
                    "result": result,
                }
            else:
                yield {
                    "type": "error",
                    "message": f"Server error: {resp.status_code}",
                }
        except Exception as e:
            yield {
                "type": "error",
                "message": f"HTTP error: {e}",
            }

    async def accept_contract(self) -> dict[str, Any] | None:
        """Accept the current contract."""
        try:
            import websockets
        except ImportError:
            return await self._accept_contract_http()

        ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")

        try:
            async with websockets.connect(f"{ws_url}/ws/client") as ws:
                await ws.send(json.dumps({"type": "contract_accepted"}))

                # Read events until work_done
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                        if data.get("type") == "work_done":
                            return data.get("result", {})
                        elif data.get("type") == "work_started":
                            continue
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning(f"WebSocket accept failed: {e}")
            return await self._accept_contract_http()

        return None

    async def _accept_contract_http(self) -> dict[str, Any] | None:
        """Fallback: Accept contract via HTTP."""
        if not self._http_client:
            return None
        try:
            resp = await self._http_client.post(
                f"/sessions/{self.session_id}/accept",
                timeout=httpx.Timeout(300.0),
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    async def revise_contract(self, feedback: str) -> AsyncIterator[dict[str, Any]]:
        """Request a contract revision."""
        try:
            import websockets
        except ImportError:
            return

        ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")

        try:
            async with websockets.connect(f"{ws_url}/ws/client") as ws:
                await ws.send(json.dumps({
                    "type": "contract_revision",
                    "feedback": feedback,
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
        """
        # Try WebSocket
        try:
            import websockets

            ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")

            async with websockets.connect(
                f"{ws_url}/ws/office?session_id={self.session_id}"
            ) as ws:
                async for raw in ws:
                    try:
                        data = json.loads(raw)
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
                                yield data
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.debug(f"SSE stream ended: {e}")

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
