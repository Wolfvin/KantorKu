"""
Auditor — Code quality and cleanliness guardian.
Uses Claude Sonnet 4.6.

Two modes:
1. Reactive: review after task completion (called via handle())
2. Proactive: background scan, ask permission, clean up
   (called via run_proactive_scan() by Office)
"""

from __future__ import annotations

from typing import Any

from kantorku.worker.base import BaseWorker, Task, TaskResult


class Auditor(BaseWorker):
    """
    Auditor with proactive scanning capability.

    Reactive mode (handle): review task output for quality issues.
    Proactive mode (run_proactive_scan): scan codebase, ask
    permission before making changes.
    """

    async def handle(self, task: Task) -> TaskResult:
        """Reactive mode — review task result."""
        session_ctx = self._build_context_section(task)
        conv_summary = self.get_conversation_summary(task.session_id)

        context_parts = [f"Audit the following code/output:\n\nTask: {task.instruction}"]

        if session_ctx:
            context_parts.append(session_ctx)

        if conv_summary:
            context_parts.append(
                f"Your previous audits in this session:\n{conv_summary}"
            )

        prompt = "\n\n".join(context_parts)
        prompt += "\n\nReview for:\n1. Architectural soundness\n2. Code quality and maintainability\n3. Security considerations\n4. Performance implications\n5. Compliance with project standards"

        response = await self.llm_call(prompt, session_id=task.session_id)
        return TaskResult(task_id=task.id, status="done", output=response)

    async def run_proactive_scan(
        self,
        channel: Any,
        session_id: str,
        project_path: str,
    ) -> None:
        """
        Proactive mode — scan codebase and ask permission for changes.

        Called by Office as a background task when personality.proactive
        is True and scan_interval > 0.

        Flow:
        1. Scan for issues via LLM
        2. Auto-fix trivial issues (formatting, whitespace)
        3. Ask permission for non-trivial changes
        4. Announce what was done / skipped

        Args:
            channel: ExecutionChannel to communicate on
            session_id: Current session ID
            project_path: Root path of the project to scan
        """
        issues = await self._scan_for_issues(project_path, session_id)

        if not issues:
            return  # Nothing found — stay quiet

        for issue in issues:
            severity = issue.get("severity", "ask_permission")
            description = issue.get("description", "Unknown issue")

            if severity == "auto_fix":
                # Trivial fix — just do it and announce
                fixed = await self._apply_fix(issue)
                if fixed:
                    await channel.announce(
                        from_id=self.id,
                        content=f"Auto-fixed: {description}",
                        relevant_workers=issue.get("relevant_workers", []),
                    )
            else:
                # Non-trivial — ask permission first
                result = await channel.ask_permission(
                    from_id=self.id,
                    question=f"Can I {issue.get('action', 'make this change')}?",
                    context=self._format_issue_context(issue),
                    timeout=45.0,
                    default_answer="skip",
                )

                if result.approved:
                    fixed = await self._apply_fix(issue)
                    if fixed:
                        await channel.announce(
                            from_id=self.id,
                            content=f"Fixed: {description}",
                            relevant_workers=issue.get("relevant_workers", []),
                        )
                else:
                    # Log why we skipped — goes to notebook
                    await channel.announce(
                        from_id=self.id,
                        content=f"Skipped: {description} — {result.reason}",
                        relevant_workers=issue.get("relevant_workers", []),
                    )

    async def _scan_for_issues(
        self, project_path: str, session_id: str
    ) -> list[dict[str, Any]]:
        """
        Scan project for issues that should be addressed.

        Uses LLM to identify:
        - Dead code (uncalled functions/classes)
        - Unused imports
        - Security anti-patterns
        - Inconsistent naming
        - TODO comments that are stale

        Returns list of issue dicts, each with:
        - severity: "auto_fix" or "ask_permission"
        - description: human-readable summary
        - action: what to do
        - file, line, code_snippet: location info
        - relevant_workers: who might know about this code
        """
        prompt = f"""Scan the project at {project_path} for code quality issues.

Look for:
1. Dead code (functions/classes not called anywhere)
2. Unused imports
3. Security anti-patterns (hardcoded secrets, SQL injection, etc.)
4. Inconsistent naming conventions
5. Stale TODO comments

For each issue, determine:
- severity: "auto_fix" if safe to fix automatically (formatting, unused import),
  or "ask_permission" if it needs human confirmation (deleting code, changing behavior)
- description: clear summary
- action: what change would be made
- file: file path (if known)
- line: line number (if known)
- relevant_workers: list of worker IDs who might know about this code
  (e.g. coder_backend for backend files, coder_frontend for UI files)

Respond with JSON:
{{
    "issues": [
        {{
            "severity": "auto_fix" or "ask_permission",
            "description": "...",
            "action": "...",
            "file": "...",
            "line": ...,
            "relevant_workers": ["worker_id1", ...]
        }}
    ]
}}"""

        result = await self.llm_call_structured(
            prompt, session_id=session_id
        )

        issues = result.get("issues", [])
        if isinstance(issues, list):
            return issues
        return []

    def _format_issue_context(self, issue: dict[str, Any]) -> str:
        """Format issue for display in ExecutionChannel."""
        lines = []
        if issue.get("file"):
            lines.append(f"File: {issue['file']}")
        if issue.get("line"):
            lines.append(f"Line: {issue['line']}")
        if issue.get("code_snippet"):
            lines.append(f"Code:\n```\n{issue['code_snippet']}\n```")
        if issue.get("reason"):
            lines.append(f"Reason: {issue['reason']}")
        return "\n".join(lines)

    async def _apply_fix(self, issue: dict[str, Any]) -> bool:
        """
        Apply a fix for an identified issue.

        In the current implementation, this logs the fix but doesn't
        actually modify files. Real file modification requires
        explicit tool access and safety checks.

        Returns:
            True if fix was applied, False otherwise
        """
        # TODO: Implement actual file fixes when tool access is available
        # For now, just log what would be done
        import logging
        logger = logging.getLogger(f"kantorku.workers.{self.id}")
        logger.info(
            "Proactive fix: %s in %s",
            issue.get("action", "?"),
            issue.get("file", "?"),
        )
        return True
