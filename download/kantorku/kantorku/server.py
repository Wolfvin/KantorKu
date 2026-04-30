"""
kantorku server — FastAPI + 2 WebSocket channels.

Channel 1 (/ws/client): User ↔ Manager chat (Panel 1)
Channel 2 (/ws/office): Live office event stream (Panel 2)

Usage:
    uvicorn kantorku.server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

from kantorku.office import Office
from kantorku.events.bus import EventBus
from kantorku.config.settings import KantorkuConfig


# Global office instance — initialized on startup
_office: Office | None = None


def create_office(config_path: str | None = None) -> Office:
    """Create and configure the Office instance."""
    global _office

    if config_path:
        _office = Office.from_config(config_path)
    else:
        # Default configuration
        config = KantorkuConfig()
        _office = Office(config=config)

    return _office


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Initialize office on startup
    if _office:
        await _office.initialize()
    yield
    # Cleanup on shutdown
    if _office:
        await _office.shutdown()


app = FastAPI(
    title="kantorku",
    description="Kantor digital yang sesungguhnya — AI worker orchestration",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check."""
    return {
        "name": "kantorku",
        "version": "0.1.0",
        "status": "running",
        "workers": len(_office.registry.all_worker_ids) if _office else 0,
        "pool": _office.get_pool_status() if _office else {},
    }


@app.get("/status")
async def status():
    """Get office status."""
    if not _office:
        return {"error": "Office not initialized"}

    return {
        "workers": _office.get_worker_status(),
        "pool": _office.get_pool_status(),
    }


@app.websocket("/ws/client")
async def client_channel(ws: WebSocket):
    """
    Client ↔ Manager WebSocket channel (Panel 1).

    Protocol:
    - Client sends: {"type": "user_message", "content": "..."}
    - Client sends: {"type": "contract_accepted", "contract": {...}}
    - Client sends: {"type": "contract_revision", "feedback": "..."}
    - Server sends: {"type": "manager_message", "content": "..."}
    - Server sends: {"type": "contract_ready", "contract": {...}}
    - Server sends: {"type": "work_started"}
    """
    await ws.accept()
    session_id = uuid.uuid4().hex[:12]

    try:
        async for raw in ws.iter_text():
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = data.get("type", "")

            if msg_type == "user_message":
                # Client sent a message — Conductor understands
                async for event in _office.chat(session_id, data["content"]):
                    await ws.send_json(event)

            elif msg_type == "contract_accepted":
                # Client accepted contract — start work
                result = await _office.accept_and_run(session_id)
                await ws.send_json({"type": "work_started", "session_id": session_id})
                # Send final result
                await ws.send_json({"type": "work_done", "result": result})

            elif msg_type == "contract_revision":
                # Client wants revision
                async for event in _office.revise(session_id, data.get("feedback", "")):
                    await ws.send_json(event)

            else:
                await ws.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                })

    except WebSocketDisconnect:
        await _office.cleanup_session(session_id)


@app.websocket("/ws/office")
async def office_channel(
    ws: WebSocket,
    session_id: str = Query(...),
):
    """
    Office event stream WebSocket channel (Panel 2).

    Streams all office events for a session in real-time:
    - briefing_opened, plan_drafted, plan_revised
    - task_assigned, task_started, task_done, task_failed
    - worker_dm, worker_broadcast
    - context_fetch_start, context_fetch_done
    - verify_design_start/done, verify_engineer_start/done
    - error_logged, skill_updated

    Query params:
        session_id: Required session identifier
    """
    await ws.accept()

    try:
        # Subscribe to session events
        async with _office.bus.subscribe(session_id) as events:
            async for event in events:
                try:
                    await ws.send_json(event.to_dict())
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@app.get("/events/{session_id}")
async def get_events(session_id: str, limit: int = 50):
    """Get recent events for a session (for reconnection/replay)."""
    if not _office:
        return {"events": []}
    return {"events": _office.get_events(session_id, limit)}


def main():
    """CLI entry point — start the server."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="kantorku server")
    parser.add_argument("--config", "-c", help="Path to kantorku.toml")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Port to bind")
    args = parser.parse_args()

    # Initialize office before server starts
    office = create_office(args.config)

    uvicorn.run(
        "kantorku.server:app",
        host=args.host,
        port=args.port,
        reload=False,
        lifespan="on",
    )


if __name__ == "__main__":
    main()
