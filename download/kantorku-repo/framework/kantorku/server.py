"""
kantorku server — FastAPI + 2 WebSocket channels + SSE + Health.

Channel 1 (/ws/client): User ↔ Manager chat (Panel 1)
Channel 2 (/ws/office): Live office event stream (Panel 2)
SSE (/events/stream/{session_id}): Server-Sent Events for non-WS clients
Health (/health/*): Liveness, readiness, dashboard

Usage:
    uvicorn kantorku.server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

from kantorku.office import Office
from kantorku.events.bus import EventBus
from kantorku.config.settings import KantorkuConfig
from kantorku.health import HealthChecker, HealthStatus
from kantorku.middleware import (
    MiddlewarePipeline,
    MiddlewareContext,
    LoggingMiddleware,
    AuthMiddleware,
    RateLimitMiddleware,
    CostGuardMiddleware,
    AuditMiddleware,
)

logger = logging.getLogger("kantorku.server")


# Global office instance — initialized on startup
_office: Office | None = None
_health: HealthChecker | None = None
_pipeline: MiddlewarePipeline | None = None


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


def create_middleware_pipeline(office: Office) -> MiddlewarePipeline:
    """Create the middleware pipeline with default middleware."""
    pipeline = MiddlewarePipeline()
    pipeline.add(LoggingMiddleware())
    pipeline.add(RateLimitMiddleware(max_requests=200, window_seconds=60))
    if office.cost_tracker:
        pipeline.add(CostGuardMiddleware(
            max_session_cost=10.0,
            max_total_cost=100.0,
            cost_tracker=office.cost_tracker,
        ))
    return pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    global _health, _pipeline

    # Initialize office on startup
    if _office:
        await _office.initialize()

        # Initialize health checker
        _health = HealthChecker(office=_office, check_interval=30)
        await _health.start()

        # Initialize middleware pipeline
        _pipeline = create_middleware_pipeline(_office)

    yield

    # Cleanup on shutdown
    if _health:
        await _health.stop()
    if _office:
        await _office.shutdown()


app = FastAPI(
    title="kantorku",
    description="Kantor digital yang sesungguhnya — AI worker orchestration",
    version="0.3.0",
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


# ── Health Endpoints ──────────────────────────────────────────────────


@app.get("/")
async def root():
    """Root health check."""
    return {
        "name": "kantorku",
        "version": "0.3.0",
        "status": "running",
        "workers": len(_office.registry.all_worker_ids) if _office else 0,
    }


@app.get("/health/live")
async def liveness():
    """Liveness probe — is the server alive?"""
    if not _health:
        return JSONResponse(
            content={"status": "healthy", "message": "Server is alive"},
            status_code=200,
        )
    result = _health.liveness()
    status_code = 200 if result.is_healthy else 503
    return JSONResponse(content=result.to_dict(), status_code=status_code)


@app.get("/health/ready")
async def readiness():
    """Readiness probe — is the server ready to accept requests?"""
    if not _health:
        return JSONResponse(
            content={"status": "unhealthy", "message": "Not initialized"},
            status_code=503,
        )
    result = _health.readiness()
    status_code = 200 if result.is_healthy else 503
    return JSONResponse(content=result.to_dict(), status_code=status_code)


@app.get("/health/dashboard")
async def dashboard():
    """Full health dashboard with detailed subsystem status."""
    if not _health:
        return JSONResponse(
            content={"error": "Health checker not initialized"},
            status_code=503,
        )
    return _health.dashboard()


@app.get("/status")
async def status():
    """Get office status (workers, pool, costs, metrics)."""
    if not _office:
        return {"error": "Office not initialized"}

    result = {
        "workers": _office.get_worker_status(),
        "pool": _office.get_pool_status(),
    }

    # Add P3 data
    if _office.cost_tracker:
        result["cost"] = _office.cost_tracker.get_report()

    if _health:
        result["health"] = {
            "providers": {
                name: status.to_dict()
                for name, status in _health._provider_health.items()
            },
        }

    return result


# ── Cost & Metrics Endpoints ─────────────────────────────────────────


@app.get("/cost")
async def cost_report():
    """Get detailed cost report."""
    if not _office or not _office.cost_tracker:
        return {"cost_tracking": False}
    return _office.cost_tracker.get_report()


@app.get("/metrics")
async def metrics():
    """Get observability metrics."""
    if not _office:
        return {}
    return _office.get_metrics_summary()


@app.get("/circuit-breaker")
async def circuit_breaker_status():
    """Get circuit breaker status for all providers."""
    if not _office:
        return {}
    return _office.get_circuit_breaker_status()


@app.get("/spans")
async def spans(limit: int = 100):
    """Get recent tracing spans."""
    if not _office:
        return {"spans": []}
    return {"spans": _office.get_observability_spans(limit)}


# ── WebSocket: Client Channel ────────────────────────────────────────


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


# ── WebSocket: Office Channel ────────────────────────────────────────


@app.websocket("/ws/office")
async def office_channel(
    ws: WebSocket,
    session_id: str = Query(...),
):
    """
    Office event stream WebSocket channel (Panel 2).

    Streams all office events for a session in real-time.
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


# ── SSE: Server-Sent Events Stream ───────────────────────────────────


@app.get("/events/stream/{session_id}")
async def sse_stream(session_id: str):
    """
    Server-Sent Events stream for non-WebSocket clients.

    Provides the same event stream as /ws/office but via SSE,
    which works with standard HTTP and doesn't require WebSocket support.

    Usage (JavaScript):
        const source = new EventSource('/events/stream/session-123');
        source.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(data);
        };
    """
    async def event_generator():
        if not _office:
            yield {"event": "error", "data": json.dumps({"message": "Office not initialized"})}
            return

        try:
            async with _office.bus.subscribe(session_id) as events:
                async for event in events:
                    yield {
                        "event": event.type,
                        "data": json.dumps(event.to_dict()),
                    }
        except asyncio.CancelledError:
            pass
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(event_generator())


# ── REST: Events Replay ──────────────────────────────────────────────


@app.get("/events/{session_id}")
async def get_events(session_id: str, limit: int = 50):
    """Get recent events for a session (for reconnection/replay)."""
    if not _office:
        return {"events": []}
    return {"events": _office.get_events(session_id, limit)}


# ── REST: Sessions ───────────────────────────────────────────────────


@app.get("/sessions")
async def list_sessions():
    """List all active sessions."""
    if not _office:
        return {"sessions": []}

    sessions = []
    if hasattr(_office, 'conductor') and hasattr(_office.conductor, '_sessions'):
        for session_id, data in _office.conductor._sessions.items():
            contract = data.get("contract")
            sessions.append({
                "session_id": session_id,
                "state": data.get("state", "unknown"),
                "contract_title": contract.title if contract and hasattr(contract, 'title') else "",
            })

    return {"sessions": sessions}


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get details of a specific session."""
    if not _office:
        return {"error": "Office not initialized"}

    # Get contract
    contract = _office.conductor.get_contract(session_id) if _office.conductor else None
    if not contract:
        return {"error": "Session not found", "session_id": session_id}

    # Get events
    events = _office.get_events(session_id)

    # Get task results from Ring1
    task_results = []
    if _office.ring1:
        task_results = await _office.ring1.get_task_results(session_id)

    return {
        "session_id": session_id,
        "contract": contract.to_dict(),
        "events": events,
        "task_results": task_results,
    }


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Clean up and delete a session."""
    if not _office:
        return {"error": "Office not initialized"}

    await _office.cleanup_session(session_id)
    return {"status": "deleted", "session_id": session_id}


# ── CLI Entry Point ──────────────────────────────────────────────────


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
