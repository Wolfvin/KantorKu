"""
PoolWorker — A single DeepSeek instance in the context pool.

Each PoolWorker:
- Listens to the FIFO queue
- Processes one job at a time
- Stores results in Ring 1
- Emits events for Panel 2
"""

from __future__ import annotations

import asyncio
from typing import Any

from kantorku.events.bus import EventBus
from kantorku.events.emitter import EventEmitter
from kantorku.providers.router import ProviderRouter
from kantorku.memory.ring1 import Ring1Memory


class PoolWorker:
    """
    A single DeepSeek instance in the ContextPool.

    Listens to the shared queue, processes one job at a time,
    stores results in Ring 1, and emits events for monitoring.

    Usage:
        worker = PoolWorker(instance_id=0, model="deepseek/deepseek-v3-2")
        await worker.listen(queue, bus, ring1)
    """

    def __init__(
        self,
        instance_id: int,
        model: str = "deepseek/deepseek-v3-2",
        router: ProviderRouter | None = None,
    ) -> None:
        self.id = instance_id
        self.model = model
        self.router = router
        self.status: str = "idle"  # idle | busy

    async def listen(
        self,
        queue: asyncio.Queue[dict[str, Any]],
        bus: EventBus,
        ring1: Ring1Memory | None = None,
    ) -> None:
        """
        Main loop — listen to queue, process jobs one at a time.
        Runs forever until cancelled.
        """
        while True:
            try:
                job = await queue.get()
                self.status = "busy"

                try:
                    result = await self._fetch(job["query"], bus, job.get("session_id", ""))

                    # Store in Ring 1
                    if ring1:
                        await ring1.store_context(
                            task_id=job["task_id"],
                            context=result,
                        )

                    # Emit completion event
                    session_id = job.get("session_id", "")
                    if session_id:
                        emitter = EventEmitter(bus, session_id)
                        await emitter.context_fetch_done(
                            instance=self.id,
                            for_task=job["task_id"],
                            results=[result] if isinstance(result, dict) else [],
                        )

                        # If reactive — notify requesting worker
                        if job.get("type") == "reactive":
                            await emitter.context_delivered(
                                to=job.get("worker_id", ""),
                                summary=result.get("summary", str(result)) if isinstance(result, dict) else str(result),
                            )

                except Exception as e:
                    # Log error but don't crash the loop
                    session_id = job.get("session_id", "")
                    if session_id:
                        emitter = EventEmitter(bus, session_id)
                        await emitter.task_failed(
                            from_id=f"pool-{self.id}",
                            error=str(e),
                        )
                finally:
                    self.status = "idle"
                    queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception:
                # Keep running even on unexpected errors
                continue

    async def _fetch(
        self,
        query: str,
        bus: EventBus | None = None,
        session_id: str = "",
    ) -> dict[str, Any]:
        """
        Execute a context fetch using DeepSeek.
        Returns structured context result.
        """
        if self.router is None:
            # If no router configured, return placeholder
            return {
                "summary": f"Context fetch placeholder for: {query[:100]}",
                "files": [],
                "patterns": [],
                "references": [],
                "query": query,
            }

        response = await self.router.complete(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a context researcher. Find relevant code, patterns, "
                        "and references for the given task. Be concise and specific. "
                        "Return results in JSON format with keys: summary, files, "
                        "patterns, references."
                    ),
                },
                {"role": "user", "content": query},
            ],
            temperature=0.3,
            enable_cache=True,
        )

        # Try to parse as JSON
        import json
        try:
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {
                "summary": response[:500],
                "files": [],
                "patterns": [],
                "references": [],
                "query": query,
            }
