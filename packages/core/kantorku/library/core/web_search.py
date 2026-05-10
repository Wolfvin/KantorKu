"""
WebSearch — Web search integration for KantorKu Library.

The LibraryWebSearch class enables the Library to escalate queries
to web search when internal knowledge is insufficient. It supports
multiple escalation levels and source tier tagging for quality
assessment of web-sourced content.

Escalation levels:
    quick:    1 source — fast, single-result lookup
    default:  3 sources — balanced depth and speed
    deep:     5+ sources — comprehensive research

Source tiers:
    Tier 1 (OFFICIAL):    Official documentation, vendor docs
    Tier 2 (VENDOR):      Vendor blogs, official tutorials
    Tier 3 (SECONDARY):   Stack Overflow, MDN, wiki
    Tier 4 (COMMUNITY):   Blog posts, forum answers, personal sites
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from kantorku.library.core.models import EntrySource, EntryType, LibraryEntry
from kantorku.library.core.librarian import Librarian
from kantorku.library.storage.archive import Archive

logger = logging.getLogger(__name__)


class SourceTier(str, Enum):
    """Source quality tier for web-sourced content."""

    TIER_1_OFFICIAL = "tier_1_official"
    TIER_2_VENDOR = "tier_2_vendor"
    TIER_3_SECONDARY = "tier_3_secondary"
    TIER_4_COMMUNITY = "tier_4_community"


class EscalationLevel(str, Enum):
    """Web search escalation level."""

    QUICK = "quick"
    DEFAULT = "default"
    DEEP = "deep"


# Number of results per escalation level
_ESCALATION_COUNTS: dict[EscalationLevel, int] = {
    EscalationLevel.QUICK: 1,
    EscalationLevel.DEFAULT: 3,
    EscalationLevel.DEEP: 5,
}

# Domain patterns for tier classification
_TIER_PATTERNS: dict[SourceTier, list[str]] = {
    SourceTier.TIER_1_OFFICIAL: [
        "docs.python.org", "docs.rs", "doc.rust-lang.org",
        "developer.mozilla.org", "docs.oracle.com",
        "kubernetes.io/docs", "docs.docker.com",
        "react.dev", "vuejs.org", "angular.io",
        "docs.microsoft.com", "cloud.google.com/docs",
        "aws.amazon.com/documentation",
    ],
    SourceTier.TIER_2_VENDOR: [
        "blog.python.org", "blog.rust-lang.org",
        "github.blog", "medium.com/firebase",
        "developers.google.com", "stripe.com/docs",
        "vercel.com", "netlify.com",
    ],
    SourceTier.TIER_3_SECONDARY: [
        "stackoverflow.com", "stackexchange.com",
        "wikipedia.org", "wikibooks.org",
        "en.wikipedia.org", "mdn.io",
        "archlinux.org/wiki",
    ],
    SourceTier.TIER_4_COMMUNITY: [
        "medium.com", "dev.to", "hashnode.com",
        "reddit.com", "hackernews", "news.ycombinator.com",
        "blog.", "wordpress.com", "substack.com",
    ],
}


@dataclass
class WebSearchResult:
    """A single web search result."""

    url: str
    title: str
    snippet: str
    source_tier: SourceTier = SourceTier.TIER_3_SECONDARY
    relevance_score: float = 0.0


class LibraryWebSearch:
    """Web search integration for KantorKu Library.

    Enables the Library to escalate queries to web search when
    internal knowledge is insufficient, and to ingest web results
    with source tier tagging.

    Example::

        web_search = LibraryWebSearch(archive, librarian, config)
        results = await web_search.search_and_ingest(
            "Python asyncio best practices",
            escalation="default",
        )
    """

    # Confidence threshold for auto-escalation
    AUTO_ESCALATE_THRESHOLD: float = 0.4

    def __init__(
        self,
        archive: Archive,
        librarian: Librarian,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the web search integration.

        Args:
            archive: The Archive instance for storing ingested results.
            librarian: The Librarian instance for classifying web results.
            config: Optional configuration dict with keys like
                'search_api_key', 'search_engine', etc.
        """
        self._archive = archive
        self._librarian = librarian
        self._config = config or {}

    async def search_and_ingest(
        self,
        query: str,
        escalation: str = "default",
    ) -> list[LibraryEntry]:
        """Search the web and ingest relevant results into the Library.

        Args:
            query: The search query.
            escalation: Escalation level — "quick", "default", or "deep".

        Returns:
            A list of LibraryEntry objects created from web results.
        """
        try:
            level = EscalationLevel(escalation)
        except ValueError:
            level = EscalationLevel.DEFAULT
            logger.warning("Invalid escalation level %r — using 'default'", escalation)

        num_results = _ESCALATION_COUNTS.get(level, 3)

        # Perform web search
        search_results = await self._web_search(query, num_results)

        if not search_results:
            logger.info("No web search results found for: %s", query[:80])
            return []

        # Ingest relevant results
        entries: list[LibraryEntry] = []
        for result in search_results:
            # Classify relevance
            is_relevant = self._classify_result(result)
            if not is_relevant:
                continue

            # Ingest the result
            entry = await self._ingest_result(result, query)
            if entry is not None:
                entries.append(entry)

        logger.info(
            "Web search and ingest: query=%r, level=%s, results=%d, ingested=%d",
            query[:50],
            level.value,
            len(search_results),
            len(entries),
        )

        return entries

    async def auto_escalate(
        self,
        query: str,
        library_confidence: float,
    ) -> list[LibraryEntry] | None:
        """Auto-escalate to web search if Library confidence is low.

        Only triggers if library_confidence < 0.4.

        Args:
            query: The query that had low confidence.
            library_confidence: The Library's confidence score.

        Returns:
            A list of ingested entries, or None if no escalation needed.
        """
        if library_confidence >= self.AUTO_ESCALATE_THRESHOLD:
            return None

        logger.info(
            "Auto-escalating to web search: confidence=%.2f < threshold=%.2f",
            library_confidence,
            self.AUTO_ESCALATE_THRESHOLD,
        )

        return await self.search_and_ingest(query, escalation="default")

    async def _web_search(
        self,
        query: str,
        num_results: int,
    ) -> list[WebSearchResult]:
        """Perform a web search using the configured search API.

        Tries z-ai-web-dev-sdk first, then falls back to httpx-based
        search. Returns a list of WebSearchResult objects.

        Args:
            query: The search query.
            num_results: Number of results to retrieve.

        Returns:
            A list of WebSearchResult objects.
        """
        results: list[WebSearchResult] = []

        # Try z-ai-web-dev-sdk
        try:
            from z_ai_web_dev_sdk import WebSearchClient

            client = WebSearchClient()
            raw_results = client.search(query, num_results=num_results)

            for raw in raw_results:
                url = raw.get("url", "")
                title = raw.get("title", "")
                snippet = raw.get("snippet", raw.get("content", ""))
                source_tier = self._classify_url_tier(url)

                results.append(WebSearchResult(
                    url=url,
                    title=title,
                    snippet=snippet,
                    source_tier=source_tier,
                ))

            return results
        except ImportError:
            logger.debug("z-ai-web-dev-sdk not available for web search")
        except Exception as exc:
            logger.warning("z-ai-web-dev-sdk search failed: %s", exc)

        # Fallback: httpx-based search (if configured)
        search_api_url = self._config.get("search_api_url")
        search_api_key = self._config.get("search_api_key")

        if search_api_url and search_api_key:
            try:
                import httpx

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        search_api_url,
                        params={
                            "q": query,
                            "num": num_results,
                            "key": search_api_key,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    for item in data.get("items", data.get("results", [])):
                        url = item.get("url", item.get("link", ""))
                        title = item.get("title", "")
                        snippet = item.get("snippet", item.get("description", ""))
                        source_tier = self._classify_url_tier(url)

                        results.append(WebSearchResult(
                            url=url,
                            title=title,
                            snippet=snippet,
                            source_tier=source_tier,
                        ))

            except Exception as exc:
                logger.warning("httpx-based search failed: %s", exc)

        if not results:
            logger.info("No web search backend available — returning empty results")

        return results[:num_results]

    def _classify_result(self, result: WebSearchResult) -> bool:
        """Determine if a web search result is relevant.

        Uses simple heuristics: non-empty snippet, reasonable length,
        and not a known low-quality source.

        Args:
            result: The WebSearchResult to classify.

        Returns:
            True if the result appears relevant.
        """
        if not result.snippet or len(result.snippet) < 20:
            return False

        if not result.title or len(result.title) < 5:
            return False

        # Skip known low-quality patterns
        low_quality_patterns = ["login", "signup", "register", "404", "forbidden"]
        title_lower = result.title.lower()
        if any(p in title_lower for p in low_quality_patterns):
            return False

        return True

    async def _ingest_result(
        self,
        result: WebSearchResult,
        query: str,
    ) -> LibraryEntry | None:
        """Create a LibraryEntry from a web search result.

        Args:
            result: The WebSearchResult to ingest.
            query: The original search query.

        Returns:
            The created LibraryEntry, or None if ingestion failed.
        """
        try:
            content = f"# {result.title}\n\n{result.snippet}\n\nSource: {result.url}"

            # Map source tier to quality adjustment
            tier_quality: dict[SourceTier, float] = {
                SourceTier.TIER_1_OFFICIAL: 0.8,
                SourceTier.TIER_2_VENDOR: 0.7,
                SourceTier.TIER_3_SECONDARY: 0.5,
                SourceTier.TIER_4_COMMUNITY: 0.4,
            }
            quality_estimate = tier_quality.get(result.source_tier, 0.5)

            entry = LibraryEntry(
                title=result.title,
                content=content,
                source=EntrySource.IMPORT,
                domain="web_text",
                quality_score=quality_estimate,
                entry_type=EntryType.KNOWLEDGE,
            )

            # Store source tier in keywords for tracking
            entry.keywords = [result.source_tier.value, "web-search"]

            # Store in archive
            await self._archive.store(entry)

            logger.debug("Ingested web result: %s (tier=%s)", result.title[:50], result.source_tier.value)
            return entry

        except Exception as exc:
            logger.error("Failed to ingest web result %s: %s", result.url, exc)
            return None

    @staticmethod
    def _classify_url_tier(url: str) -> SourceTier:
        """Classify a URL into a source quality tier.

        Args:
            url: The URL to classify.

        Returns:
            The SourceTier for the URL.
        """
        url_lower = url.lower()

        for tier, patterns in _TIER_PATTERNS.items():
            for pattern in patterns:
                if pattern in url_lower:
                    return tier

        # Default to Tier 3 (secondary)
        return SourceTier.TIER_3_SECONDARY
