"""
Enhanced Checkpoint — O16: Full state checkpoint with artifact sweep and repair.

Provides enhanced checkpointing that goes beyond basic state snapshots:
- Artifact sweep: extracts structured artifacts from conversation history
- Memory deduplication: removes duplicate memory entries
- MCP consistency verification: checks for drift between config and reality
- Full checkpoint creation and restoration with repair

Like a meticulous admin who not only saves your work but also
cleans up duplicates and verifies everything is consistent.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckpointData:
    """Complete checkpoint data for office state."""
    label: str = ""
    timestamp: float = field(default_factory=time.time)
    conversation_state: dict[str, Any] = field(default_factory=dict)
    contract_state: dict[str, Any] = field(default_factory=dict)
    worker_states: dict[str, Any] = field(default_factory=dict)
    task_progress: dict[str, Any] = field(default_factory=dict)
    memory_snapshot: dict[str, Any] = field(default_factory=dict)


# Artifact extraction patterns
_ARTIFACT_PATTERNS: list[tuple[str, str]] = [
    (r"SMART_PLAN:\s*\n([\s\S]*?)(?=\n\n|\Z)", "smart_plan"),
    (r"DEBUG_REPORT:\s*\n([\s\S]*?)(?=\n\n|\Z)", "debug_report"),
    (r"REVIEW_RESULT:\s*\n([\s\S]*?)(?=\n\n|\Z)", "review_result"),
    (r"VERIFICATION:\s*\n([\s\S]*?)(?=\n\n|\Z)", "verification"),
    (r"```(\w+)\n([\s\S]*?)```", "code_block"),
    (r"CONTRACT:\s*\{[\s\S]*?\}", "contract"),
]


class EnhancedCheckpoint:
    """
    Enhanced Checkpoint — full state checkpoint with artifact sweep and repair.

    Provides:
    - Artifact sweep: scans conversation history for structured artifacts
    - Memory deduplication: removes duplicate memory entries
    - MCP consistency verification: checks for config vs reality drift
    - Full checkpoint creation with all state
    - Restoration with automatic repair of inconsistencies

    Usage:
        cp = EnhancedCheckpoint()
        artifacts = cp.artifact_sweep(conversation_history)
        deduped = cp.dedup_memory(memory_entries)
        is_consistent, drift = cp.verify_mcp_consistency(config, actual_status)
        checkpoint = cp.create_full_checkpoint(office_state, "pre-deploy")
        restored, repairs = cp.restore_with_repair(checkpoint)
    """

    def artifact_sweep(
        self, conversation_history: list[dict[str, Any]] | str
    ) -> list[dict[str, Any]]:
        """
        Scan conversation history for structured artifacts.

        Extracts SMART_PLAN, DEBUG_REPORT, REVIEW_RESULT, VERIFICATION,
        code blocks, and CONTRACT patterns from conversation messages.

        Args:
            conversation_history: List of message dicts or raw text string

        Returns:
            List of extracted artifact dicts with type, content, and source
        """
        artifacts: list[dict[str, Any]] = []

        if not conversation_history:
            return artifacts

        # Convert to text if list of dicts
        if isinstance(conversation_history, list):
            messages_text = []
            for i, msg in enumerate(conversation_history):
                if isinstance(msg, dict):
                    content = msg.get("content", msg.get("response", ""))
                    role = msg.get("role", msg.get("from", "unknown"))
                    messages_text.append(f"[{role}] {content}")
                else:
                    messages_text.append(str(msg))
            text = "\n\n".join(messages_text)
        else:
            text = str(conversation_history)

        # Extract artifacts using patterns
        for pattern, artifact_type in _ARTIFACT_PATTERNS:
            matches = re.finditer(pattern, text, re.MULTILINE)
            for match in matches:
                artifact: dict[str, Any] = {
                    "type": artifact_type,
                    "extracted_at": time.time(),
                }
                if artifact_type == "code_block":
                    artifact["language"] = match.group(1)
                    artifact["content"] = match.group(2).strip()
                else:
                    artifact["content"] = match.group(1).strip() if match.lastindex else match.group(0).strip()

                if artifact.get("content"):
                    artifacts.append(artifact)

        return artifacts

    def dedup_memory(
        self, memory_entries: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Remove duplicate memory entries.

        Deduplication is based on content hash (key fields combined).
        Keeps the most recent entry when duplicates are found.

        Args:
            memory_entries: List of memory entry dicts

        Returns:
            Deduplicated list of memory entries
        """
        if not memory_entries:
            return []

        seen: dict[str, dict[str, Any]] = {}

        for entry in memory_entries:
            if not isinstance(entry, dict):
                continue

            # Create a content-based key from significant fields
            key_parts = []
            for key in ("lesson", "event_type", "category", "source", "data"):
                val = entry.get(key)
                if val is not None:
                    key_parts.append(str(val))

            dedup_key = "|".join(key_parts)

            if dedup_key in seen:
                # Keep the more recent one
                existing_ts = seen[dedup_key].get("timestamp", 0)
                current_ts = entry.get("timestamp", 0)
                if current_ts > existing_ts:
                    seen[dedup_key] = entry
            else:
                seen[dedup_key] = entry

        return list(seen.values())

    def verify_mcp_consistency(
        self,
        config: dict[str, Any] | None = None,
        actual_mcp_status: dict[str, Any] | None = None,
    ) -> tuple[bool, list[dict[str, Any]]]:
        """
        Verify MCP (Model Context Protocol) consistency between config and reality.

        Checks for drift between configured MCP servers and their
        actual status.

        Args:
            config: MCP configuration dict with server definitions
            actual_mcp_status: Actual status of MCP servers

        Returns:
            Tuple of (is_consistent, list of drift items)
        """
        drift_items: list[dict[str, Any]] = []

        if not config and not actual_mcp_status:
            return True, []

        config = config or {}
        actual = actual_mcp_status or {}

        # Check configured servers that aren't in actual status
        config_servers = set()
        if isinstance(config.get("servers"), list):
            for server in config["servers"]:
                name = server.get("name", "") if isinstance(server, dict) else str(server)
                if name:
                    config_servers.add(name)
        elif isinstance(config.get("servers"), dict):
            config_servers = set(config["servers"].keys())

        actual_servers = set()
        if isinstance(actual.get("servers"), list):
            for server in actual["servers"]:
                name = server.get("name", "") if isinstance(server, dict) else str(server)
                if name:
                    actual_servers.add(name)
        elif isinstance(actual.get("servers"), dict):
            actual_servers = set(actual["servers"].keys())

        # Configured but not running
        missing = config_servers - actual_servers
        for name in missing:
            drift_items.append({
                "type": "missing_server",
                "server": name,
                "description": f"Server '{name}' configured but not running",
                "severity": "warn",
            })

        # Running but not configured
        extra = actual_servers - config_servers
        for name in extra:
            drift_items.append({
                "type": "extra_server",
                "server": name,
                "description": f"Server '{name}' running but not in config",
                "severity": "info",
            })

        # Check server health
        if isinstance(actual.get("servers"), dict):
            for name, status in actual["servers"].items():
                if isinstance(status, dict):
                    if status.get("status") == "error":
                        drift_items.append({
                            "type": "unhealthy_server",
                            "server": name,
                            "description": f"Server '{name}' is in error state: {status.get('error', 'unknown')}",
                            "severity": "error",
                        })

        is_consistent = len(drift_items) == 0
        return is_consistent, drift_items

    def create_full_checkpoint(
        self, office_state: dict[str, Any], label: str = ""
    ) -> CheckpointData:
        """
        Create a full checkpoint of the office state.

        Captures conversation state, contract state, worker states,
        task progress, and a memory snapshot.

        Args:
            office_state: Dict containing the full office state
            label: Descriptive label for the checkpoint

        Returns:
            CheckpointData with complete state snapshot
        """
        return CheckpointData(
            label=label or f"checkpoint_{int(time.time())}",
            timestamp=time.time(),
            conversation_state=office_state.get("conversation", {}),
            contract_state=office_state.get("contract", {}),
            worker_states=office_state.get("workers", {}),
            task_progress=office_state.get("task_progress", {}),
            memory_snapshot=office_state.get("memory", {}),
        )

    def restore_with_repair(
        self, checkpoint_data: CheckpointData | dict[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        """
        Restore office state from a checkpoint with automatic repair.

        Repairs common issues:
        - Missing required fields → fill with defaults
        - Stale references → clear
        - Inconsistent states → normalize

        Args:
            checkpoint_data: CheckpointData or dict to restore from

        Returns:
            Tuple of (restored_state, list of repairs applied)
        """
        repairs: list[str] = []

        if isinstance(checkpoint_data, CheckpointData):
            state = {
                "conversation": checkpoint_data.conversation_state,
                "contract": checkpoint_data.contract_state,
                "workers": checkpoint_data.worker_states,
                "task_progress": checkpoint_data.task_progress,
                "memory": checkpoint_data.memory_snapshot,
                "label": checkpoint_data.label,
            }
        else:
            state = dict(checkpoint_data)

        # Repair: ensure conversation has required structure
        if "conversation" not in state:
            state["conversation"] = {}
            repairs.append("Added missing conversation state")

        # Repair: ensure contract has required fields
        contract = state.get("contract", {})
        if not isinstance(contract, dict):
            state["contract"] = {}
            contract = {}
            repairs.append("Reset malformed contract state")
        for req_field in ("id", "title", "description"):
            if req_field not in contract:
                contract[req_field] = ""
                repairs.append(f"Added missing contract field: {req_field}")
        state["contract"] = contract

        # Repair: ensure workers dict exists
        if "workers" not in state:
            state["workers"] = {}
            repairs.append("Added missing workers state")

        # Repair: ensure task_progress dict exists
        if "task_progress" not in state:
            state["task_progress"] = {}
            repairs.append("Added missing task_progress state")

        # Repair: deduplicate memory entries
        memory = state.get("memory", {})
        if isinstance(memory, dict):
            entries = memory.get("entries", [])
            if isinstance(entries, list):
                deduped = self.dedup_memory(entries)
                if len(deduped) < len(entries):
                    memory["entries"] = deduped
                    state["memory"] = memory
                    repairs.append(
                        f"Deduplicated memory: {len(entries)} → {len(deduped)} entries"
                    )

        # Repair: clear stale references
        workers = state.get("workers", {})
        if isinstance(workers, dict):
            for wid, wstate in list(workers.items()):
                if isinstance(wstate, dict):
                    # Clear references to tasks that don't exist in task_progress
                    assigned = wstate.get("assigned_tasks", [])
                    if isinstance(assigned, list):
                        task_progress = state.get("task_progress", {})
                        valid_assigned = [
                            t for t in assigned
                            if t in task_progress
                        ]
                        if len(valid_assigned) < len(assigned):
                            wstate["assigned_tasks"] = valid_assigned
                            repairs.append(
                                f"Cleared {len(assigned) - len(valid_assigned)} stale task references for {wid}"
                            )

        return state, repairs
