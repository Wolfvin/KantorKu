"""
RepoIntake — Repository and directory ingestion for KantorKu Library.

The RepoIntake class enables the Library to ingest knowledge from
external repositories (via git clone) and local directories. It scans
for README files, CI configurations, package manifests, SKILL.md files,
and extracts high-signal insights that are classified and stored as
Library entries.

Ingestion flow:
    1. Clone/fetch the repository or scan a directory
    2. Scan README, CI/CD configs, manifests, SKILL.md
    3. Extract insights from each source
    4. Classify insights into Library entries
    5. Store entries with proper metadata
    6. Generate summary report
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from kantorku.library.core.models import EntrySource, EntryType, LibraryEntry
from kantorku.library.core.librarian import Librarian
from kantorku.library.core.indexer import Indexer
from kantorku.library.storage.archive import Archive

logger = logging.getLogger(__name__)

# File patterns to scan
_README_PATTERNS: list[str] = ["README.md", "README.rst", "README.txt", "README"]
_MANIFEST_PATTERNS: list[str] = [
    "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
    "requirements.txt", "setup.py", "setup.cfg", "Gemfile",
    "pom.xml", "build.gradle", "Makefile", "CMakeLists.txt",
]
_SKILL_PATTERNS: list[str] = ["SKILL.md", "SKILLS.md", ".SKILL.md"]
_CI_PATTERNS: list[str] = [
    ".github/workflows/*.yml", ".github/workflows/*.yaml",
    ".gitlab-ci.yml", "Jenkinsfile", ".circleci/config.yml",
    "azure-pipelines.yml",
]


class RepoIntake:
    """Repository and directory ingestion for KantorKu Library.

    Ingests knowledge from git repositories and local directories
    by scanning key files and extracting high-signal content.

    Example::

        intake = RepoIntake(librarian, archive, indexer)
        report = await intake.intake_repo("https://github.com/example/repo", name="example-repo")
        print(report)
    """

    def __init__(
        self,
        librarian: Librarian,
        archive: Archive,
        indexer: Indexer | None = None,
    ) -> None:
        """Initialize the RepoIntake.

        Args:
            librarian: The Librarian for classifying extracted insights.
            archive: The Archive for storing entries.
            indexer: The Indexer for indexing entries (optional).
        """
        self._librarian = librarian
        self._archive = archive
        self._indexer = indexer

    async def intake_repo(
        self,
        repo_url: str,
        name: str | None = None,
        keep: bool = False,
    ) -> dict[str, Any]:
        """Ingest a git repository into the Library.

        Clones the repository, scans key files, extracts insights,
        and stores them as Library entries.

        Args:
            repo_url: The git repository URL to clone.
            name: Optional name for the repository. If not provided,
                derived from the URL.
            keep: If True, keep the cloned repository. If False,
                it is removed after ingestion.

        Returns:
            A summary report dict.
        """
        # Derive name from URL if not provided
        if not name:
            name = repo_url.rstrip("/").split("/")[-1]
            if name.endswith(".git"):
                name = name[:-4]

        logger.info("Ingesting repository: %s (%s)", name, repo_url)

        # Clone the repository
        clone_dir = tempfile.mkdtemp(prefix="kantorku_repo_")

        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, clone_dir],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                logger.error("Git clone failed: %s", result.stderr)
                return {
                    "success": False,
                    "error": f"Git clone failed: {result.stderr[:200]}",
                    "repo": name,
                }

        except FileNotFoundError:
            logger.error("git is not installed")
            return {
                "success": False,
                "error": "git is not installed",
                "repo": name,
            }
        except subprocess.TimeoutExpired:
            logger.error("Git clone timed out")
            return {
                "success": False,
                "error": "Git clone timed out",
                "repo": name,
            }

        try:
            # Ingest the cloned directory
            report = await self.intake_directory(clone_dir)
            report["repo"] = name
            report["repo_url"] = repo_url
            return report

        finally:
            if not keep and os.path.exists(clone_dir):
                import shutil
                shutil.rmtree(clone_dir, ignore_errors=True)

    async def intake_directory(self, path: str) -> dict[str, Any]:
        """Ingest a local directory into the Library.

        Scans key files, extracts insights, and stores them.

        Args:
            path: The local directory path to scan.

        Returns:
            A summary report dict.
        """
        if not os.path.isdir(path):
            return {"success": False, "error": f"Directory not found: {path}"}

        logger.info("Scanning directory: %s", path)

        all_insights: list[dict[str, Any]] = []

        # Scan README
        readme_insights = self._scan_readme(path)
        all_insights.extend(readme_insights)

        # Scan manifests
        manifest_insights = self._scan_manifests(path)
        all_insights.extend(manifest_insights)

        # Scan SKILL.md files
        for pattern in _SKILL_PATTERNS:
            skill_path = os.path.join(path, pattern)
            if os.path.exists(skill_path):
                try:
                    content = Path(skill_path).read_text(encoding="utf-8")
                    insights = self._extract_insights(content, f"SKILL.md ({pattern})")
                    all_insights.extend(insights)
                except Exception as exc:
                    logger.warning("Failed to read %s: %s", skill_path, exc)

        # Classify and store insights
        dir_name = os.path.basename(path)
        entries_created = await self._classify_and_store(all_insights, dir_name)

        report = self.generate_report(dir_name, all_insights, entries_created)
        report["success"] = True
        report["path"] = path

        return report

    def _scan_readme(self, path: str) -> list[dict[str, Any]]:
        """Extract high-signal content from README files.

        Args:
            path: The directory to scan.

        Returns:
            A list of insight dicts.
        """
        insights: list[dict[str, Any]] = []

        for pattern in _README_PATTERNS:
            readme_path = os.path.join(path, pattern)
            if os.path.exists(readme_path):
                try:
                    content = Path(readme_path).read_text(encoding="utf-8")
                    if content.strip():
                        insights.extend(
                            self._extract_insights(content, f"README ({pattern})")
                        )
                except Exception as exc:
                    logger.warning("Failed to read %s: %s", readme_path, exc)
                break  # Only process the first found README

        return insights

    def _scan_manifests(self, path: str) -> list[dict[str, Any]]:
        """Extract insights from package manifests.

        Args:
            path: The directory to scan.

        Returns:
            A list of insight dicts.
        """
        insights: list[dict[str, Any]] = []

        for pattern in _MANIFEST_PATTERNS:
            manifest_path = os.path.join(path, pattern)
            if os.path.exists(manifest_path):
                try:
                    content = Path(manifest_path).read_text(encoding="utf-8")
                    source = f"Manifest ({pattern})"

                    # Try to extract structured info from JSON manifests
                    if pattern.endswith(".json"):
                        try:
                            data = json.loads(content)
                            name = data.get("name", "")
                            description = data.get("description", "")
                            deps = list(data.get("dependencies", {}).keys())
                            dev_deps = list(data.get("devDependencies", {}).keys())

                            if description:
                                insights.append({
                                    "content": f"# {name}\n\n{description}\n\nDependencies: {', '.join(deps[:20])}",
                                    "source": source,
                                    "type": "project_overview",
                                })

                            if deps or dev_deps:
                                insights.append({
                                    "content": f"Dependencies: {', '.join(deps + dev_deps[:30])}",
                                    "source": source,
                                    "type": "dependencies",
                                })
                            continue
                        except json.JSONDecodeError:
                            pass

                    # For other manifests, extract as text
                    if content.strip():
                        insights.append({
                            "content": content[:2000],
                            "source": source,
                            "type": "manifest",
                        })

                except Exception as exc:
                    logger.warning("Failed to read %s: %s", manifest_path, exc)

        return insights

    def _extract_insights(
        self,
        content: str,
        source: str,
    ) -> list[dict[str, Any]]:
        """Extract key patterns and insights from content.

        Looks for:
        - Key patterns (API patterns, configuration examples)
        - Best practices (sections with "best practice", "recommended")
        - Code examples (code blocks)
        - Architecture patterns

        Args:
            content: The text content to extract from.
            source: The source file name.

        Returns:
            A list of insight dicts.
        """
        insights: list[dict[str, Any]] = []

        # Extract sections that look like key insights
        sections = re.split(r"^#+\s+", content, flags=re.MULTILINE)

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Check for high-signal sections
            section_title = section.split("\n")[0].strip()[:80]
            section_body = "\n".join(section.split("\n")[1:]).strip()

            if not section_body:
                continue

            # Filter: only include sections with substantial content
            if len(section_body) < 50:
                continue

            # Determine insight type
            insight_type = "general"
            lower_title = section_title.lower()
            if any(kw in lower_title for kw in ["api", "endpoint", "route"]):
                insight_type = "api_patterns"
            elif any(kw in lower_title for kw in ["best practice", "recommended", "should"]):
                insight_type = "best_practices"
            elif any(kw in lower_title for kw in ["install", "setup", "getting started", "config"]):
                insight_type = "setup"
            elif any(kw in lower_title for kw in ["architecture", "design", "structure"]):
                insight_type = "architecture"

            # Truncate long sections
            if len(section_body) > 2000:
                section_body = section_body[:1997] + "..."

            insights.append({
                "content": f"# {section_title}\n\n{section_body}",
                "source": source,
                "type": insight_type,
            })

        # If no section-based insights, use the whole content
        if not insights and len(content) > 50:
            truncated = content[:2000]
            if len(content) > 2000:
                truncated += "..."
            insights.append({
                "content": truncated,
                "source": source,
                "type": "overview",
            })

        return insights

    async def _classify_and_store(
        self,
        insights: list[dict[str, Any]],
        source_name: str,
    ) -> list[LibraryEntry]:
        """Classify insights and create Library entries.

        Args:
            insights: The extracted insights.
            source_name: The name of the source repository/directory.

        Returns:
            A list of created LibraryEntry objects.
        """
        entries: list[LibraryEntry] = []

        for insight in insights:
            content = insight.get("content", "")
            source = insight.get("source", source_name)

            if not content.strip():
                continue

            try:
                entry = await self._librarian.ingest(
                    content=content,
                    title=f"{source_name}: {source}",
                    source=EntrySource.IMPORT,
                    user_hint=insight.get("type", ""),
                )

                # Tag with source
                if source_name not in entry.keywords:
                    entry.keywords.append(source_name)

                await self._archive.update(entry)

                if self._indexer:
                    await self._indexer.index_entry(entry)

                entries.append(entry)

            except Exception as exc:
                logger.warning("Failed to ingest insight from %s: %s", source, exc)

        return entries

    def generate_report(
        self,
        source: str,
        insights: list[dict[str, Any]],
        entries_created: list[LibraryEntry],
    ) -> dict[str, Any]:
        """Generate a summary report of the intake.

        Args:
            source: The source name (repo or directory).
            insights: The extracted insights.
            entries_created: The created Library entries.

        Returns:
            A report dict.
        """
        type_counts: dict[str, int] = {}
        for insight in insights:
            t = insight.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "source": source,
            "insights_found": len(insights),
            "entries_created": len(entries_created),
            "insight_types": type_counts,
            "entry_ids": [e.id for e in entries_created[:20]],
        }
