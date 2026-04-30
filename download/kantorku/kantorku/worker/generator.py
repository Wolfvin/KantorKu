"""
WorkerGenerator — Scaffold new kantorku workers.

Creates the complete directory structure for a plug-and-play worker:
    my_worker/
    ├── plugin.json    (metadata: id, model, squad, role, capabilities)
    ├── SKILL.md       (system prompt / skill description)
    ├── worker.py      (custom BaseWorker subclass)
    └── __init__.py    (re-exports for Python import)

Usage:
    # CLI
    kantorku worker create my_worker --squad coding --model "anthropic/claude-sonnet-4-6"

    # Programmatic
    from kantorku.worker.generator import WorkerGenerator
    gen = WorkerGenerator()
    gen.create("my_worker", squad="support", model="ollama/llama3")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ─────────────────────────────────────────────────
#  Templates
# ─────────────────────────────────────────────────

PLUGIN_JSON_TEMPLATE = """{{
  "id": "{worker_id}",
  "model": "{model}",
  "squad": "{squad}",
  "role": "{role}",
  "capabilities": {capabilities},
  "description": "{description}"
}}"""

SKILL_MD_TEMPLATE = """# {worker_id} — {role_title}

You are the **{role_title}** of kantorku.

## Role

Describe your worker's role here. This text is injected into the LLM system prompt,
so be specific about what this worker does, its expertise, and how it should behave.

## Key Expertise

- **Skill 1** — Describe a key skill
- **Skill 2** — Describe another skill
- **Skill 3** — Describe another skill

## Interaction with Other Workers

- **worker_a**: How this worker interacts with worker_a
- **worker_b**: How this worker interacts with worker_b

## Output

You produce:
- Describe what this worker outputs
- Include file types, formats, etc.

## Methodology

1. **Step 1** — First step in your process
2. **Step 2** — Second step
3. **Step 3** — Third step
"""

def _get_worker_py_template(worker_id: str, role_title: str) -> str:
    """Generate worker.py content. Uses string concat to avoid format conflicts."""
    return f'''"""
{worker_id} — {role_title}.

Custom worker implementation for kantorku.
This file is auto-detected when the worker directory is loaded.
"""

from __future__ import annotations

from typing import Any
from kantorku.worker.base import BaseWorker, Task, TaskResult


class Worker(BaseWorker):
    """
    {role_title} worker.

    Override handle() to implement custom logic.
    Use self.llm_call() for LLM calls (auto-injects SKILL.md as system prompt).
    Use self.llm_call_structured() for JSON responses.
    Use self.get_context(task.id) for prefetched context from Ring1.
    """

    async def handle(self, task: Task) -> TaskResult:
        """Process a task and return the result."""

        # Option 1: Simple LLM call (SKILL.md is automatically used as system prompt)
        response = await self.llm_call(
            f"Task: {{task.instruction}}\\n\\nContext: {{task.context}}"
        )

        return TaskResult(
            task_id=task.id,
            status="done",
            output=response,
            files=[],
        )

        # Option 2: Structured LLM call (returns parsed JSON)
        # result = await self.llm_call_structured(
        #     f"Task: {{task.instruction}}\\n\\nRespond with JSON."
        # )
        # return TaskResult(
        #     task_id=task.id,
        #     status="done",
        #     output=str(result),
        #     data=result,
        # )

        # Option 3: With prefetched context
        # context = await self.get_context(task.id)
        # if context:
        #     prompt = f"Context: {{context}}\\n\\nTask: {{task.instruction}}"
        # else:
        #     prompt = f"Task: {{task.instruction}}"
        # response = await self.llm_call(prompt)
        # return TaskResult(task_id=task.id, status="done", output=response)
'''

INIT_PY_TEMPLATE = '''"""kantorku worker: {worker_id}"""

from {worker_id}.worker import Worker

__all__ = ["Worker"]
'''


class WorkerGenerator:
    """
    Generator for creating new kantorku worker scaffolds.

    Usage:
        gen = WorkerGenerator()
        path = gen.create(
            "my_translator",
            base_dir=Path("workers"),
            model="ollama/llama3",
            squad="support",
            role="Language translator",
            capabilities=["translation", "localization"],
            description="Translates text between languages",
        )
    """

    def create(
        self,
        worker_id: str,
        base_dir: Path = Path("workers"),
        model: str = "ollama/llama3",
        squad: str = "support",
        role: str = "",
        capabilities: list[str] | None = None,
        description: str = "",
        skill_md_content: str | None = None,
        worker_py_content: str | None = None,
        overwrite: bool = False,
    ) -> Path:
        """
        Create a new worker directory with all required files.

        Args:
            worker_id: Unique identifier (alphanumeric + underscores)
            base_dir: Parent directory to create the worker in
            model: LLM model assignment (provider/model format)
            squad: Squad membership (coding, verification, support, translation)
            role: Human-readable role description
            capabilities: List of capability strings
            description: Short description for plugin.json
            skill_md_content: Custom SKILL.md content (uses template if None)
            worker_py_content: Custom worker.py content (uses template if None)
            overwrite: If True, overwrite existing files

        Returns:
            Path to the created worker directory

        Raises:
            ValueError: If worker_id is invalid
            FileExistsError: If directory already exists and overwrite=False
        """
        # Validate worker_id
        if not worker_id or not worker_id.replace("_", "").isalnum():
            raise ValueError(
                f"Invalid worker_id '{worker_id}'. "
                f"Must be alphanumeric with underscores only."
            )

        if model and "/" not in model:
            raise ValueError(
                f"Model must be 'provider/model' format, got: {model}"
            )

        # Set defaults
        role = role or worker_id.replace("_", " ").title()
        capabilities = capabilities or []
        description = description or f"{role} worker for kantorku"

        # Create directory
        worker_dir = base_dir / worker_id
        if worker_dir.exists() and not overwrite:
            if (worker_dir / "plugin.json").exists():
                raise FileExistsError(
                    f"Worker directory already exists: {worker_dir}. "
                    f"Use overwrite=True to replace."
                )

        worker_dir.mkdir(parents=True, exist_ok=True)

        # Generate plugin.json
        plugin_data = {
            "id": worker_id,
            "model": model,
            "squad": squad,
            "role": role,
            "capabilities": capabilities,
            "description": description,
        }
        self._write_file(
            worker_dir / "plugin.json",
            json.dumps(plugin_data, indent=2, ensure_ascii=False) + "\n",
            overwrite=overwrite,
        )

        # Generate SKILL.md
        role_title = role
        if skill_md_content:
            skill_content = skill_md_content
        else:
            skill_content = SKILL_MD_TEMPLATE.format(
                worker_id=worker_id,
                role_title=role_title,
            )
        self._write_file(
            worker_dir / "SKILL.md",
            skill_content,
            overwrite=overwrite,
        )

        # Generate worker.py
        if worker_py_content:
            py_content = worker_py_content
        else:
            py_content = _get_worker_py_template(worker_id, role_title)
        self._write_file(
            worker_dir / "worker.py",
            py_content,
            overwrite=overwrite,
        )

        # Generate __init__.py
        init_content = INIT_PY_TEMPLATE.format(worker_id=worker_id)
        self._write_file(
            worker_dir / "__init__.py",
            init_content,
            overwrite=overwrite,
        )

        return worker_dir

    def _write_file(self, path: Path, content: str, overwrite: bool = False) -> None:
        """Write content to a file, respecting overwrite flag."""
        if path.exists() and not overwrite:
            return
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def get_squads() -> list[str]:
        """Get list of known squad names."""
        return ["coding", "verification", "support", "translation"]

    @staticmethod
    def get_quickstart_guide() -> str:
        """Return a quickstart guide for creating workers."""
        return """
╔══════════════════════════════════════════════════════════════╗
║           kantorku Worker Plug-and-Play Guide                ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. CREATE a worker:                                         ║
║     kantorku worker create my_worker                         ║
║     kantorku worker create translator --squad translation    ║
║                                                              ║
║  2. CUSTOMIZE the files:                                     ║
║     workers/my_worker/                                       ║
║     ├── plugin.json    ← metadata (id, model, squad)        ║
║     ├── SKILL.md       ← system prompt for the LLM          ║
║     └── worker.py      ← custom Python logic                ║
║                                                              ║
║  3. USE it — just drop the folder:                           ║
║     # Auto-discovered at startup from workers/ directory     ║
║     office = Office.from_config("kantorku.toml")            ║
║     await office.initialize()                                ║
║                                                              ║
║  4. HOT-PLUG at runtime:                                     ║
║     office.hot_plug_worker("workers/my_worker/")             ║
║                                                              ║
║  5. PROGRAMMATIC:                                            ║
║     office.hire_worker(                                      ║
║         "my_worker",                                         ║
║         model="ollama/llama3",                               ║
║         squad="support",                                     ║
║         worker_class=MyWorkerClass,                          ║
║     )                                                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
