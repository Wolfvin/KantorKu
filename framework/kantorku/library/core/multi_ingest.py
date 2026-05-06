"""
MultiFormatIngest — Multi-format file and URL ingestion for KantorKu Library.

The MultiFormatIngest class provides a unified interface for ingesting
content from various sources: local files (auto-detected format),
URLs (web content extraction), and clipboard content.

Supported file formats:
    .py, .js, .rs, .md, .txt, .json, .yaml, .toml
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from kantorku.library.core.models import EntrySource
from kantorku.library.core.librarian import Librarian
from kantorku.library.storage.archive import Archive

logger = logging.getLogger(__name__)

# Format detection map
_FORMAT_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".rs": "rust",
    ".md": "markdown",
    ".txt": "text",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".html": "html",
    ".xml": "xml",
    ".csv": "csv",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".sh": "shell",
    ".sql": "sql",
}


class MultiFormatIngest:
    """Multi-format file and URL ingestion for KantorKu Library.

    Provides a unified interface for ingesting content from files,
    URLs, and the clipboard with automatic format detection.

    Example::

        ingest = MultiFormatIngest(librarian, archive)
        entry = await ingest.ingest_file("/path/to/readme.md")
        entry = await ingest.ingest_url("https://example.com/doc")
        entry = await ingest.ingest_clipboard()
    """

    def __init__(
        self,
        librarian: Librarian,
        archive: Archive,
    ) -> None:
        """Initialize the MultiFormatIngest.

        Args:
            librarian: The Librarian for classifying ingested content.
            archive: The Archive for storing entries.
        """
        self._librarian = librarian
        self._archive = archive

    async def ingest_file(self, file_path: str) -> Any | None:
        """Ingest a file with automatic format detection.

        Detects the file format by extension, extracts text content,
        and calls the Librarian's ingest pipeline.

        Args:
            file_path: Path to the file to ingest.

        Returns:
            The created LibraryEntry, or None if ingestion failed.
        """
        if not os.path.exists(file_path):
            logger.error("File not found: %s", file_path)
            return None

        fmt = self._detect_format(file_path)
        text = self._extract_text(file_path, fmt)

        if not text or not text.strip():
            logger.warning("No text content extracted from %s", file_path)
            return None

        title = os.path.basename(file_path)
        try:
            entry = await self._librarian.ingest(
                content=text,
                title=title,
                source=EntrySource.IMPORT,
                user_hint=fmt,
            )
            logger.info("Ingested file %s as %s (entry %s)", file_path, fmt, entry.id[:8])
            return entry
        except Exception as exc:
            logger.error("Failed to ingest file %s: %s", file_path, exc)
            return None

    async def ingest_url(self, url: str) -> Any | None:
        """Fetch a URL, extract content, and ingest.

        Uses the z-ai-web-dev-sdk for content extraction when
        available, falling back to httpx-based fetching.

        Args:
            url: The URL to fetch and ingest.

        Returns:
            The created LibraryEntry, or None if ingestion failed.
        """
        text = await self._extract_from_url(url)

        if not text or not text.strip():
            logger.warning("No content extracted from URL: %s", url)
            return None

        title = url.split("/")[-1] or url[:80]
        try:
            entry = await self._librarian.ingest(
                content=text,
                title=title,
                source=EntrySource.IMPORT,
                user_hint="web",
            )
            logger.info("Ingested URL %s (entry %s)", url[:50], entry.id[:8])
            return entry
        except Exception as exc:
            logger.error("Failed to ingest URL %s: %s", url[:50], exc)
            return None

    async def ingest_clipboard(self) -> Any | None:
        """Read clipboard content and ingest.

        Tries pyperclip first, then falls back to platform-specific
        clipboard commands.

        Returns:
            The created LibraryEntry, or None if ingestion failed.
        """
        text = self._read_clipboard()

        if not text or not text.strip():
            logger.warning("No content in clipboard")
            return None

        try:
            entry = await self._librarian.ingest(
                content=text,
                title="Clipboard Content",
                source=EntrySource.MANUAL,
                user_hint="clipboard",
            )
            logger.info("Ingested clipboard content (entry %s)", entry.id[:8])
            return entry
        except Exception as exc:
            logger.error("Failed to ingest clipboard content: %s", exc)
            return None

    # ── Format detection ────────────────────────────────────────────────

    @staticmethod
    def _detect_format(file_path: str) -> str:
        """Detect the format of a file by its extension.

        Args:
            file_path: The file path to detect.

        Returns:
            A format string (e.g., "python", "markdown", "json").
        """
        ext = Path(file_path).suffix.lower()
        return _FORMAT_MAP.get(ext, "text")

    # ── Text extraction ─────────────────────────────────────────────────

    @staticmethod
    def _extract_text(file_path: str, fmt: str) -> str:
        """Extract text content from a file based on its format.

        Args:
            file_path: The file to extract text from.
            fmt: The detected format.

        Returns:
            The extracted text content.
        """
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.error("Failed to read file %s: %s", file_path, exc)
            return ""

        if fmt == "json":
            try:
                data = json.loads(content)
                # Pretty-print and add structure info
                text = json.dumps(data, indent=2, ensure_ascii=False)
                # Add metadata
                if isinstance(data, dict):
                    keys = list(data.keys())[:20]
                    text = f"JSON Object with keys: {', '.join(keys)}\n\n{text}"
                return text[:10000]  # Limit size
            except json.JSONDecodeError:
                return content

        elif fmt == "yaml":
            # Basic YAML text extraction — just return the raw text
            return content[:10000]

        elif fmt == "toml":
            # Basic TOML text extraction
            return content[:10000]

        elif fmt in ("python", "javascript", "typescript", "rust", "go",
                      "java", "ruby", "shell", "sql"):
            # Source code: return as-is with language hint
            return f"```{fmt}\n{content}\n```"

        elif fmt == "markdown":
            return content

        elif fmt == "html":
            # Strip HTML tags for basic text extraction
            clean = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", content)
            clean = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", clean)
            clean = re.sub(r"<[^>]+>", " ", clean)
            clean = re.sub(r"\s+", " ", clean).strip()
            return clean[:10000]

        else:
            return content[:10000]

    async def _extract_from_url(self, url: str) -> str:
        """Fetch and parse a URL to extract text content.

        Tries z-ai-web-dev-sdk first, then httpx.

        Args:
            url: The URL to fetch.

        Returns:
            The extracted text content.
        """
        # Try z-ai-web-dev-sdk
        try:
            from z_ai_web_dev_sdk import WebReaderClient

            client = WebReaderClient()
            result = client.extract(url)
            if result and result.get("content"):
                return result["content"][:20000]
        except ImportError:
            logger.debug("z-ai-web-dev-sdk not available for URL extraction")
        except Exception as exc:
            logger.warning("z-ai-web-dev-sdk URL extraction failed: %s", exc)

        # Fallback: httpx
        try:
            import httpx

            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if "html" in content_type:
                    # Basic HTML to text
                    clean = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", response.text)
                    clean = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", clean)
                    clean = re.sub(r"<[^>]+>", " ", clean)
                    clean = re.sub(r"\s+", " ", clean).strip()
                    return clean[:20000]
                else:
                    return response.text[:20000]

        except ImportError:
            logger.debug("httpx not available for URL fetching")
        except Exception as exc:
            logger.warning("httpx URL fetch failed: %s", exc)

        return ""

    @staticmethod
    def _read_clipboard() -> str:
        """Read content from the system clipboard.

        Tries pyperclip first, then platform-specific commands.

        Returns:
            The clipboard content as a string, or empty string on failure.
        """
        # Try pyperclip
        try:
            import pyperclip
            return pyperclip.paste()
        except ImportError:
            pass
        except Exception:
            pass

        # Try platform-specific commands
        import subprocess

        try:
            if os.name == "posix":
                # Linux: try xclip, xsel, wl-paste
                for cmd in [
                    ["xclip", "-selection", "clipboard", "-o"],
                    ["xsel", "--clipboard", "--output"],
                    ["wl-paste"],
                ]:
                    try:
                        result = subprocess.run(
                            cmd, capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            return result.stdout
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        continue

            elif os.name == "nt":
                # Windows: use powershell
                result = subprocess.run(
                    ["powershell", "-command", "Get-Clipboard"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    return result.stdout

            elif os.name == "mac":
                result = subprocess.run(
                    ["pbpaste"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    return result.stdout

        except Exception:
            pass

        return ""
