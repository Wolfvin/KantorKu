"""
Persistence — Session checkpoint, crash recovery, and state management.

Provides:
- SessionSnapshot: Full serializable snapshot of session state
- CheckpointManager: Automatic + manual checkpointing to Ring1/Ring2
- CrashRecovery: Restore office state after server restart
- Atomic writes: .tmp + rename pattern for safe persistence

The persistence layer ensures kantorku survives crashes gracefully.
Every state transition can be checkpointed, and on restart, the
office can restore to the last known good state.

Usage:
    from kantorku.persistence import CheckpointManager, CrashRecovery

    # Inside Office:
    checkpoint = CheckpointManager(ring1=ring1, ring2=ring2, bus=bus)
    await checkpoint.save_session(session_id, office_state)
    await checkpoint.save_office_snapshot(office_state)

    # On startup:
    recovery = CrashRecovery(ring1=ring1, ring2=ring2)
    state = await recovery.try_recover()
    if state:
        office.restore_state(state)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kantorku.events.bus import EventBus
from kantorku.observability import get_tracer

logger = logging.getLogger("kantorku.persistence")


# ── Atomic Writes ─────────────────────────────────────────────────────


def atomic_write(path: str | Path, data: str | bytes) -> None:
    """
    Write data atomically using .tmp + rename pattern.

    Writes to a temporary file first, then renames to the final path.
    This ensures that:
    1. Partial writes never corrupt the original file
    2. Readers always see either the old or new complete file
    3. Crash during write doesn't leave a corrupted file

    Args:
        path: Target file path
        data: Content to write (str or bytes)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = path.with_suffix(path.suffix + ".tmp")

    try:
        mode = "w" if isinstance(data, str) else "wb"
        encoding = "utf-8" if isinstance(data, str) else None
        with open(tmp_path, mode, encoding=encoding) as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

        # Atomic rename (POSIX) or replace (Windows)
        tmp_path.replace(path)
    except Exception:
        # Clean up temp file on failure
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def atomic_write_json(path: str | Path, data: dict[str, Any]) -> None:
    """Write JSON data atomically."""
    atomic_write(path, json.dumps(data, indent=2, default=str, ensure_ascii=False))


def atomic_read_json(path: str | Path) -> dict[str, Any] | None:
    """
    Read JSON data with corruption detection.

    Returns None if file doesn't exist or is corrupted.
    """
    path = Path(path)
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Corrupted or unreadable file {path}: {e}")
        # Try to read from .bak if available
        bak_path = path.with_suffix(path.suffix + ".bak")
        if bak_path.exists():
            try:
                with open(bak_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"Recovered from backup: {bak_path}")
                return data
            except (json.JSONDecodeError, OSError):
                pass
        return None


# ── Session Snapshot ──────────────────────────────────────────────────


@dataclass
class SessionSnapshot:
    """
    Complete snapshot of a session's state.

    Captures everything needed to resume a session after crash:
    - Contract and negotiation state
    - Task execution progress
    - Worker assignments and results
    - Conversation history
    - Observability context (trace IDs)

    Serialized to JSON for storage in Ring1 or filesystem.
    """

    session_id: str = ""
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Contract state
    contract: dict[str, Any] = field(default_factory=dict)
    contract_state: str = "idle"

    # Conversation
    client_messages: list[dict[str, str]] = field(default_factory=list)
    manager_messages: list[dict[str, str]] = field(default_factory=list)

    # Execution
    plan: dict[str, Any] = field(default_factory=dict)
    task_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    verification_results: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Workers
    worker_status: dict[str, str] = field(default_factory=dict)
    worker_assignments: dict[str, str] = field(default_factory=dict)

    # Metadata
    cost_usd: float = 0.0
    total_tokens: int = 0
    trace_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for storage."""
        return {
            "session_id": self.session_id,
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "contract": self.contract,
            "contract_state": self.contract_state,
            "client_messages": self.client_messages,
            "manager_messages": self.manager_messages,
            "plan": self.plan,
            "task_results": self.task_results,
            "verification_results": self.verification_results,
            "worker_status": self.worker_status,
            "worker_assignments": self.worker_assignments,
            "cost_usd": self.cost_usd,
            "total_tokens": self.total_tokens,
            "trace_id": self.trace_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionSnapshot:
        """Deserialize from dict."""
        return cls(
            session_id=data.get("session_id", ""),
            snapshot_id=data.get("snapshot_id", ""),
            timestamp=data.get("timestamp", ""),
            contract=data.get("contract", {}),
            contract_state=data.get("contract_state", "idle"),
            client_messages=data.get("client_messages", []),
            manager_messages=data.get("manager_messages", []),
            plan=data.get("plan", {}),
            task_results=data.get("task_results", {}),
            verification_results=data.get("verification_results", {}),
            worker_status=data.get("worker_status", {}),
            worker_assignments=data.get("worker_assignments", {}),
            cost_usd=data.get("cost_usd", 0.0),
            total_tokens=data.get("total_tokens", 0),
            trace_id=data.get("trace_id", ""),
        )


@dataclass
class OfficeSnapshot:
    """
    Complete snapshot of the entire office state.

    Captures all sessions, worker registry, cost tracker state,
    and configuration. Used for full crash recovery.
    """

    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    version: str = "0.3.0"

    # All session snapshots
    sessions: dict[str, SessionSnapshot] = field(default_factory=dict)

    # Worker registry state
    workers: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Provider status
    providers: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Cost and metrics summary
    cost_report: dict[str, Any] = field(default_factory=dict)
    metrics_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "version": self.version,
            "sessions": {
                k: v.to_dict() for k, v in self.sessions.items()
            },
            "workers": self.workers,
            "providers": self.providers,
            "cost_report": self.cost_report,
            "metrics_summary": self.metrics_summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OfficeSnapshot:
        sessions = {}
        for k, v in data.get("sessions", {}).items():
            sessions[k] = SessionSnapshot.from_dict(v)
        return cls(
            snapshot_id=data.get("snapshot_id", ""),
            timestamp=data.get("timestamp", ""),
            version=data.get("version", "0.3.0"),
            sessions=sessions,
            workers=data.get("workers", {}),
            providers=data.get("providers", {}),
            cost_report=data.get("cost_report", {}),
            metrics_summary=data.get("metrics_summary", {}),
        )


# ── Checkpoint Manager ────────────────────────────────────────────────


class CheckpointManager:
    """
    Manages session and office checkpointing.

    Provides automatic and manual checkpointing:
    - Auto-checkpoint: Every N operations or on key state transitions
    - Manual checkpoint: On demand (e.g., before risky operations)
    - Snapshot rotation: Keep last N snapshots, delete older ones

    Storage:
    - Ring1 (DuckDB): Current session state (hot, fast access)
    - Filesystem: Full office snapshots (for crash recovery)
    - Ring2 (SQLite): Audit trail of all checkpoints

    Usage:
        checkpoint = CheckpointManager(
            ring1=ring1, ring2=ring2, bus=bus,
            snapshot_dir="data/snapshots"
        )

        # Auto-checkpoint every 5 operations
        checkpoint.auto_interval = 5

        # Manual checkpoint
        snapshot_id = await checkpoint.save_session("sess-1", state)

        # Full office snapshot
        await checkpoint.save_office_snapshot(office)
    """

    def __init__(
        self,
        ring1: Any = None,
        ring2: Any = None,
        bus: EventBus | None = None,
        snapshot_dir: str = "data/snapshots",
        max_snapshots: int = 10,
        auto_interval: int = 10,
    ) -> None:
        self.ring1 = ring1
        self.ring2 = ring2
        self.bus = bus
        self.snapshot_dir = Path(snapshot_dir)
        self.max_snapshots = max_snapshots
        self.auto_interval = auto_interval

        self._operation_count: dict[str, int] = {}  # session_id -> count
        self._last_snapshot: dict[str, float] = {}  # session_id -> timestamp
        self._tracer = get_tracer()

    async def save_session(
        self,
        session_id: str,
        contract: dict[str, Any] | None = None,
        contract_state: str = "idle",
        client_messages: list[dict[str, str]] | None = None,
        manager_messages: list[dict[str, str]] | None = None,
        plan: dict[str, Any] | None = None,
        task_results: dict[str, dict[str, Any]] | None = None,
        worker_status: dict[str, str] | None = None,
        cost_usd: float = 0.0,
        total_tokens: int = 0,
    ) -> str:
        """
        Save a session snapshot to Ring1.

        Returns the snapshot ID.
        """
        snapshot = SessionSnapshot(
            session_id=session_id,
            contract=contract or {},
            contract_state=contract_state,
            client_messages=client_messages or [],
            manager_messages=manager_messages or [],
            plan=plan or {},
            task_results=task_results or {},
            worker_status=worker_status or {},
            cost_usd=cost_usd,
            total_tokens=total_tokens,
        )

        with self._tracer.span(
            "checkpoint.save_session",
            attributes={"session_id": session_id, "snapshot_id": snapshot.snapshot_id},
        ):
            # Store in Ring1
            if self.ring1:
                await self.ring1.store_session(session_id, snapshot.to_dict())

            # Store snapshot file for crash recovery
            self._save_snapshot_file(session_id, snapshot)

            # Audit trail in Ring2
            if self.ring2:
                await self.ring2.log_audit(
                    session_id=session_id,
                    worker_id="checkpoint_manager",
                    action="session_checkpoint",
                    details={
                        "snapshot_id": snapshot.snapshot_id,
                        "contract_state": contract_state,
                    },
                )

            self._last_snapshot[session_id] = time.time()

        return snapshot.snapshot_id

    async def load_session(self, session_id: str) -> SessionSnapshot | None:
        """
        Load a session snapshot from Ring1 or filesystem.

        Tries Ring1 first (fastest), falls back to snapshot files.
        """
        # Try Ring1 first
        if self.ring1:
            data = await self.ring1.get_session(session_id)
            if data:
                return SessionSnapshot.from_dict(data)

        # Fall back to snapshot file
        return self._load_snapshot_file(session_id)

    async def auto_checkpoint(
        self,
        session_id: str,
        **kwargs: Any,
    ) -> str | None:
        """
        Auto-checkpoint if enough operations have occurred.

        Returns snapshot ID if checkpoint was saved, None otherwise.
        """
        count = self._operation_count.get(session_id, 0) + 1
        self._operation_count[session_id] = count

        if count >= self.auto_interval:
            self._operation_count[session_id] = 0
            return await self.save_session(session_id, **kwargs)

        return None

    def increment_operation(self, session_id: str) -> None:
        """Increment the operation counter for auto-checkpointing."""
        self._operation_count[session_id] = self._operation_count.get(session_id, 0) + 1

    async def save_office_snapshot(self, office: Any) -> str:
        """
        Save a full office snapshot for crash recovery.

        Captures all sessions, worker state, cost tracking, and metrics.
        """
        snapshot = OfficeSnapshot()

        # Capture session snapshots
        if hasattr(office, 'conductor') and hasattr(office.conductor, '_sessions'):
            for session_id, session_data in office.conductor._sessions.items():
                contract = session_data.get("contract")
                contract_dict = contract.to_dict() if contract and hasattr(contract, 'to_dict') else {}
                contract_state = session_data.get("state")
                state_value = contract_state.value if hasattr(contract_state, 'value') else str(contract_state)

                snap = SessionSnapshot(
                    session_id=session_id,
                    contract=contract_dict,
                    contract_state=state_value,
                )
                snapshot.sessions[session_id] = snap

        # Capture worker status
        if hasattr(office, 'registry'):
            for worker_id in office.registry.all_worker_ids:
                try:
                    worker = office.registry.hire(worker_id)
                    snapshot.workers[worker_id] = worker.to_dict()
                except Exception:
                    pass

        # Capture cost report
        if hasattr(office, 'cost_tracker') and office.cost_tracker:
            snapshot.cost_report = office.cost_tracker.get_report()

        # Capture metrics
        if hasattr(office, '_metrics'):
            snapshot.metrics_summary = office._metrics.get_summary()

        # Capture provider status
        if hasattr(office, 'router'):
            snapshot.providers = {
                name: {"configured": True}
                for name in office.router.configured_providers
            }
            cb_status = office.router.get_circuit_breaker_status()
            for name, status in cb_status.items():
                if name in snapshot.providers:
                    snapshot.providers[name].update(status)

        # Save atomically
        self._save_office_snapshot_file(snapshot)

        return snapshot.snapshot_id

    def _save_snapshot_file(self, session_id: str, snapshot: SessionSnapshot) -> None:
        """Save session snapshot to filesystem (atomic write)."""
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        path = self.snapshot_dir / f"session_{session_id}.json"
        atomic_write_json(path, snapshot.to_dict())

        # Rotate: keep .bak of previous
        bak_path = self.snapshot_dir / f"session_{session_id}.json.bak"
        if path.exists():
            try:
                shutil.copy2(str(path), str(bak_path))
            except Exception:
                pass

    def _load_snapshot_file(self, session_id: str) -> SessionSnapshot | None:
        """Load session snapshot from filesystem."""
        path = self.snapshot_dir / f"session_{session_id}.json"
        data = atomic_read_json(path)
        if data:
            return SessionSnapshot.from_dict(data)
        return None

    def _save_office_snapshot_file(self, snapshot: OfficeSnapshot) -> None:
        """Save full office snapshot to filesystem."""
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = self.snapshot_dir / f"office_{timestamp}.json"
        atomic_write_json(path, snapshot.to_dict())

        # Rotate old snapshots
        self._rotate_snapshots()

    def _rotate_snapshots(self) -> None:
        """Delete old office snapshots beyond max_snapshots."""
        office_snapshots = sorted(
            self.snapshot_dir.glob("office_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for old_path in office_snapshots[self.max_snapshots:]:
            try:
                old_path.unlink()
                logger.debug(f"Rotated old snapshot: {old_path}")
            except Exception as e:
                logger.warning(f"Failed to rotate snapshot {old_path}: {e}")

    def list_snapshots(self) -> list[dict[str, Any]]:
        """List all available snapshots."""
        result = []
        if not self.snapshot_dir.exists():
            return result

        for path in sorted(self.snapshot_dir.glob("*.json"), reverse=True):
            data = atomic_read_json(path)
            if data:
                result.append({
                    "path": str(path),
                    "snapshot_id": data.get("snapshot_id", ""),
                    "timestamp": data.get("timestamp", ""),
                    "type": "office" if path.name.startswith("office_") else "session",
                })

        return result

    async def delete_session(self, session_id: str) -> None:
        """Delete a session's snapshot files."""
        path = self.snapshot_dir / f"session_{session_id}.json"
        bak_path = self.snapshot_dir / f"session_{session_id}.json.bak"

        for p in [path, bak_path]:
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass

        self._operation_count.pop(session_id, None)
        self._last_snapshot.pop(session_id, None)


# ── Crash Recovery ────────────────────────────────────────────────────


class CrashRecovery:
    """
    Recover office state after a crash.

    On startup, the recovery process:
    1. Check for office snapshots (most recent first)
    2. Check for individual session snapshots
    3. Validate snapshot integrity
    4. Return recoverable state

    The office can then restore from the recovered state,
    resuming in-progress sessions and maintaining continuity.

    Usage:
        recovery = CrashRecovery(ring1=ring1, ring2=ring2)

        # Try to recover on startup
        state = await recovery.try_recover(snapshot_dir="data/snapshots")
        if state:
            office.restore_state(state)
    """

    def __init__(
        self,
        ring1: Any = None,
        ring2: Any = None,
        snapshot_dir: str = "data/snapshots",
    ) -> None:
        self.ring1 = ring1
        self.ring2 = ring2
        self.snapshot_dir = Path(snapshot_dir)
        self._tracer = get_tracer()

    async def try_recover(self) -> OfficeSnapshot | None:
        """
        Attempt to recover office state after a crash.

        Tries in order:
        1. Most recent office snapshot file
        2. Individual session snapshots from filesystem
        3. Session data from Ring1 (DuckDB)

        Returns:
            OfficeSnapshot if recovery data found, None otherwise
        """
        with self._tracer.span("crash_recovery.try_recover"):
            # 1. Try office snapshot
            office_snap = self._recover_from_office_snapshot()
            if office_snap:
                logger.info(
                    f"Recovered from office snapshot: {office_snap.snapshot_id} "
                    f"({len(office_snap.sessions)} sessions)"
                )
                return office_snap

            # 2. Try session snapshots
            session_snaps = self._recover_session_snapshots()
            if session_snaps:
                snapshot = OfficeSnapshot(sessions=session_snaps)
                logger.info(
                    f"Recovered {len(session_snaps)} session snapshots"
                )
                return snapshot

            # 3. Try Ring1
            ring1_snap = await self._recover_from_ring1()
            if ring1_snap:
                logger.info(
                    f"Recovered from Ring1: {len(ring1_snap.sessions)} sessions"
                )
                return ring1_snap

            logger.info("No recovery data found — starting fresh")
            return None

    def _recover_from_office_snapshot(self) -> OfficeSnapshot | None:
        """Find and load the most recent valid office snapshot."""
        if not self.snapshot_dir.exists():
            return None

        office_files = sorted(
            self.snapshot_dir.glob("office_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for path in office_files:
            data = atomic_read_json(path)
            if data and self._validate_office_snapshot(data):
                return OfficeSnapshot.from_dict(data)

        return None

    def _recover_session_snapshots(self) -> dict[str, SessionSnapshot]:
        """Recover all individual session snapshots."""
        if not self.snapshot_dir.exists():
            return {}

        sessions: dict[str, SessionSnapshot] = {}
        for path in self.snapshot_dir.glob("session_*.json"):
            # Skip .bak files
            if ".bak" in path.name:
                continue

            data = atomic_read_json(path)
            if data and data.get("session_id"):
                snap = SessionSnapshot.from_dict(data)
                sessions[snap.session_id] = snap

        return sessions

    async def _recover_from_ring1(self) -> OfficeSnapshot | None:
        """Recover session data from Ring1 (DuckDB)."""
        if not self.ring1:
            return None

        try:
            # This is a simplified approach — in practice,
            # Ring1 would need a method to list all sessions
            # For now, we return None and rely on snapshot files
            return None
        except Exception as e:
            logger.warning(f"Ring1 recovery failed: {e}")
            return None

    def _validate_office_snapshot(self, data: dict[str, Any]) -> bool:
        """Validate that an office snapshot has the minimum required fields."""
        required = ["snapshot_id", "timestamp", "version"]
        return all(k in data for k in required)

    def get_recovery_info(self) -> dict[str, Any]:
        """Get information about available recovery data."""
        info: dict[str, Any] = {
            "snapshot_dir": str(self.snapshot_dir),
            "office_snapshots": 0,
            "session_snapshots": 0,
            "latest_office_snapshot": None,
        }

        if not self.snapshot_dir.exists():
            return info

        office_files = list(self.snapshot_dir.glob("office_*.json"))
        session_files = [
            f for f in self.snapshot_dir.glob("session_*.json")
            if ".bak" not in f.name
        ]

        info["office_snapshots"] = len(office_files)
        info["session_snapshots"] = len(session_files)

        if office_files:
            latest = max(office_files, key=lambda p: p.stat().st_mtime)
            data = atomic_read_json(latest)
            if data:
                info["latest_office_snapshot"] = {
                    "path": str(latest),
                    "snapshot_id": data.get("snapshot_id", ""),
                    "timestamp": data.get("timestamp", ""),
                    "session_count": len(data.get("sessions", {})),
                }

        return info
