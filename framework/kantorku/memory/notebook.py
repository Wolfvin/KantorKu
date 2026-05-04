"""
ProjectNotebook — Shared persistent knowledge base per project.

Unlike GroupChannel (ephemeral, per-session), the Notebook is
persistent storage that survives across sessions. Like a project
wiki or Confluence — decisions, contracts, and notes that workers
should remember between sessions.

Categories:
- tech_decisions: "pakai fred, bukan redis-rs"
- api_contracts: interface agreements between workers
- known_issues: known but unfixed issues
- conventions: team-agreed conventions
- skipped_cleanups: code intentionally not cleaned + reason
- architecture: architectural decisions and rationale

Storage: Ring2 (SQLite) — persists across restarts.
"""

from __future__ import annotations

from typing import Any

from kantorku.layers.execution_channel import ExecutionChannel


class ProjectNotebook:
    """
    Shared persistent knowledge base for a project.

    All workers can read and write. Persists in Ring2 (SQLite)
    so knowledge survives across sessions and restarts.

    Usage:
        notebook = ProjectNotebook(project_id="pixel-art-app", ring2=ring2)
        await notebook.initialize()

        # Add a decision
        await notebook.add(
            category="tech_decisions",
            key="Redis client",
            value="Pakai fred v0.12, bukan redis-rs",
            added_by="coder_backend",
        )

        # Get all tech decisions
        notes = await notebook.get(category="tech_decisions")

        # Get formatted text for LLM prompt
        context = await notebook.get_context_for_worker("coder_backend")

        # Propose a note to the group (with confirmation)
        approved = await notebook.propose(
            from_id="coder_backend",
            category="api_contracts",
            key="Image conversion endpoint",
            value="POST /convert, multipart form, returns base64 or blob URL",
            channel=exec_channel,
            session_id=session_id,
        )
    """

    def __init__(self, project_id: str, ring2: Any) -> None:
        self.project_id = project_id
        self.ring2 = ring2  # Ring2Memory instance

    async def initialize(self) -> None:
        """Ensure the project_notes table exists in Ring2."""
        # Ring2 must be initialized before this
        if self.ring2 and hasattr(self.ring2, '_db') and self.ring2._db:
            await self.ring2._db.executescript("""
                CREATE TABLE IF NOT EXISTS project_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    added_by TEXT NOT NULL,
                    session_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_id, category, key) ON CONFLICT REPLACE
                );
                CREATE INDEX IF NOT EXISTS idx_notes_project
                    ON project_notes(project_id);
                CREATE INDEX IF NOT EXISTS idx_notes_category
                    ON project_notes(project_id, category);
            """)
            await self.ring2._db.commit()

    async def add(
        self,
        category: str,
        key: str,
        value: str,
        added_by: str,
        session_id: str = "",
    ) -> None:
        """
        Add or update a note in the notebook.

        Uses UNIQUE constraint (project_id, category, key) —
        if a note with the same category+key exists, it's replaced.

        Args:
            category: Note category (tech_decisions, api_contracts, etc.)
            key: Short identifier for the note
            value: The note content
            added_by: Worker ID that added this note
            session_id: Session where this was added
        """
        if not self.ring2 or not hasattr(self.ring2, '_db') or not self.ring2._db:
            return

        await self.ring2._db.execute(
            """INSERT OR REPLACE INTO project_notes
               (project_id, category, key, value, added_by, session_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [self.project_id, category, key, value, added_by, session_id],
        )
        await self.ring2._db.commit()

    async def get(
        self,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get notes, optionally filtered by category.

        Args:
            category: Filter by category, or None for all notes

        Returns:
            List of note dicts
        """
        if not self.ring2 or not hasattr(self.ring2, '_db') or not self.ring2._db:
            return []

        if category:
            cursor = await self.ring2._db.execute(
                """SELECT category, key, value, added_by, session_id, created_at
                   FROM project_notes
                   WHERE project_id = ? AND category = ?
                   ORDER BY category, key""",
                [self.project_id, category],
            )
        else:
            cursor = await self.ring2._db.execute(
                """SELECT category, key, value, added_by, session_id, created_at
                   FROM project_notes
                   WHERE project_id = ?
                   ORDER BY category, key""",
                [self.project_id],
            )

        rows = await cursor.fetchall()
        return [
            {
                "category": r[0],
                "key": r[1],
                "value": r[2],
                "added_by": r[3],
                "session_id": r[4],
                "created_at": r[5],
            }
            for r in rows
        ]

    async def get_formatted(self, category: str | None = None) -> str:
        """
        Get notes as formatted text for LLM prompt injection.

        Args:
            category: Filter by category, or None for all

        Returns:
            Formatted string, or "(No notes yet)" if empty
        """
        notes = await self.get(category)
        if not notes:
            return "(No notes yet)"

        lines: list[str] = []
        current_category = None
        for note in notes:
            if note["category"] != current_category:
                current_category = note["category"]
                lines.append(f"\n### {current_category.upper()}")
            lines.append(
                f"- [{note['added_by']}] {note['key']}: {note['value']}"
            )

        return "\n".join(lines)

    async def propose(
        self,
        from_id: str,
        category: str,
        key: str,
        value: str,
        channel: ExecutionChannel,
        session_id: str,
        timeout: float = 30.0,
    ) -> bool:
        """
        Propose a note to the group before saving.

        If approved (or no one objects within timeout), the note is saved.
        If denied, the note is discarded.

        Args:
            from_id: Worker proposing the note
            category: Note category
            key: Short identifier
            value: Note content
            channel: ExecutionChannel to ask on
            session_id: Current session ID
            timeout: Seconds to wait for objections

        Returns:
            True if note was saved, False if rejected
        """
        result = await channel.ask_permission(
            from_id=from_id,
            question=f"Add to project notebook?",
            context=f"Category: {category}\n{key}: {value}",
            timeout=timeout,
            default_answer="proceed",  # Default: approved if no objection
        )

        if result.approved:
            await self.add(category, key, value, from_id, session_id)

        return result.approved

    async def get_context_for_worker(self, worker_id: str = "") -> str:
        """
        Get relevant notebook context for a worker's LLM prompt.

        Called during task assignment to inject shared knowledge
        into the worker's context.

        Args:
            worker_id: Optional worker ID for future personalization

        Returns:
            Formatted notebook context, or empty string if no notes
        """
        formatted = await self.get_formatted()
        if formatted == "(No notes yet)":
            return ""

        return (
            f"===== PROJECT NOTEBOOK (Shared Knowledge) =====\n"
            f"{formatted}\n"
            f"==============================================="
        )

    async def remove(self, category: str, key: str) -> bool:
        """
        Remove a specific note from the notebook.

        Returns:
            True if a note was removed, False if not found
        """
        if not self.ring2 or not hasattr(self.ring2, '_db') or not self.ring2._db:
            return False

        cursor = await self.ring2._db.execute(
            """DELETE FROM project_notes
               WHERE project_id = ? AND category = ? AND key = ?""",
            [self.project_id, category, key],
        )
        await self.ring2._db.commit()
        return cursor.rowcount > 0
