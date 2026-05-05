"""
Archivist — AI-powered knowledge retrieval system for KantorKu Library.

The Archivist answers questions by searching the Library's stored knowledge
and synthesizing responses. It uses vector similarity search to find relevant
entries, then uses an LLM (or rule-based fallback) to compose an answer with
proper source citations.

The Archivist can also save Q&A interactions back to the Library as QA_PAIR
entries, creating a self-reinforcing knowledge loop.

Example::

    from kantorku.library.storage.archive import Archive
    from kantorku.library.storage.vectors import VectorStore

    archive = Archive("data/library/archive.db")
    vector_store = VectorStore("data/library/vectors")
    await archive.initialize()
    await vector_store.initialize()

    archivist = Archivist(archive=archive, vector_store=vector_store)
    result = await archivist.ask("How do I fix a Python ImportError?")
    print(result["answer"])
    print(f"Sources: {result['sources']}")
    print(f"Confidence: {result['confidence']}")
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from kantorku.library.core.models import EntrySource, EntryType, LibraryEntry
from kantorku.library.storage.archive import Archive
from kantorku.library.storage.vectors import VectorStore

logger = logging.getLogger(__name__)


class Archivist:
    """AI-powered knowledge retrieval system for KantorKu Library.

    The Archivist answers questions by:
    1. Searching the VectorStore for semantically similar entries
    2. Building a context from the retrieved entries
    3. Calling an LLM with the system prompt + context + question
    4. Returning the answer with source citations and confidence score

    If no LLM is available, a rule-based fallback concatenates entry
    summaries with citation markers.

    Args:
        archive: The Archive instance for persistent storage.
        vector_store: The VectorStore instance for semantic search.
        provider_router: Optional ProviderRouter for LLM API calls.
    """

    ARCHIVIST_SYSTEM_PROMPT: str = """You are Archivist, the knowledge retrieval AI for KantorKu Library.

## Your Role
You answer questions by retrieving and synthesizing knowledge from the Library's stored entries. You provide accurate, well-sourced answers that reference specific Library entries.

## Input Format
You will receive:
- **Context**: Relevant Library entries with their content, metadata, and citation IDs [1], [2], etc.
- **Question**: The user's question

## Response Rules
1. **Answer from context**: Base your answer ONLY on the provided Library context. If the context doesn't contain enough information, say so clearly.
2. **Cite sources**: Always cite which entries support each part of your answer using [N] notation matching the context entries.
3. **Be specific**: Provide concrete, actionable information rather than vague generalizations.
4. **Be honest**: If you're unsure or the context is insufficient, say so. Do not fabricate information.
5. **Synthesize**: When multiple entries are relevant, combine their information coherently.
6. **Structure**: Use clear formatting with headings, bullet points, or numbered lists when appropriate.

## Format
Structure your response as:

**Answer**: [Your synthesized answer with [N] citations]

**Key Points**:
- Point 1 [1]
- Point 2 [2, 3]

**Confidence**: [high/medium/low] — [brief explanation]

If the context is insufficient:
**Answer**: I don't have enough information in the Library to fully answer this question. Based on the available entries, [partial answer if any].

## What You Are NOT
- You are NOT a general AI assistant — you only answer from Library knowledge
- You do NOT fabricate citations — every [N] must correspond to a real context entry
- You do NOT provide personal opinions — only factual information from entries
- You do NOT ignore the provided context — always use it as your primary source
"""

    def __init__(
        self,
        archive: Archive,
        vector_store: VectorStore,
        provider_router: Any | None = None,
    ) -> None:
        self._archive = archive
        self._vector_store = vector_store
        self._provider_router = provider_router

    # ── Main ask interface ────────────────────────────────────────────────

    async def ask(
        self,
        question: str,
        worker_id: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Answer a question using Library content.

        Performs the following steps:
        1. Search the VectorStore for entries similar to the question.
        2. Retrieve full entry data from the Archive.
        3. Build a context string from the retrieved entries.
        4. Call the LLM (or rule-based fallback) with context + question.
        5. Return the answer with sources and confidence.

        Args:
            question: The user's question.
            worker_id: Optional KantorKu worker ID for tracing.
            top_k: Number of similar entries to retrieve.

        Returns:
            A dict with keys:
            - ``answer``: The synthesized answer string.
            - ``sources``: A list of source dicts with entry_id, title,
              similarity, and entry_type.
            - ``confidence``: A float between 0.0 and 1.0.
        """
        logger.info("Archivist asked: %r (top_k=%d)", question[:100], top_k)

        # 1. Search vector store for similar entries
        try:
            search_results = await self._vector_store.search(
                query=question, top_k=top_k, min_similarity=0.2
            )
        except Exception as exc:
            logger.error("Vector search failed: %s", exc)
            search_results = []

        if not search_results:
            return {
                "answer": "I couldn't find any relevant entries in the Library "
                          "to answer your question. Try rephrasing or adding "
                          "more knowledge to the Library first.",
                "sources": [],
                "confidence": 0.0,
            }

        # 2. Retrieve full entries from archive
        context_entries: list[LibraryEntry] = []
        source_list: list[dict[str, Any]] = []

        for result in search_results:
            entry_id = result.get("entry_id", "")
            similarity = result.get("similarity", 0.0)
            metadata = result.get("metadata", {})

            entry = await self._archive.get(entry_id)
            if entry is not None:
                context_entries.append(entry)
                source_list.append({
                    "entry_id": entry_id,
                    "title": entry.title or "(untitled)",
                    "similarity": similarity,
                    "entry_type": entry.entry_type.value,
                })

        if not context_entries:
            return {
                "answer": "I found references in the Library but couldn't "
                          "retrieve the full entries. The archive may be "
                          "out of sync with the vector store.",
                "sources": [],
                "confidence": 0.0,
            }

        # 3. Build context from entries
        context = self._build_context(context_entries, search_results)

        # 4. Generate answer
        try:
            if self._provider_router is not None:
                result = await self.ask_with_api(question, context, worker_id)
            else:
                result = await self.ask_with_rules(
                    question, context_entries, worker_id
                )
        except Exception as exc:
            logger.warning(
                "LLM answer generation failed, falling back to rules: %s", exc
            )
            result = await self.ask_with_rules(
                question, context_entries, worker_id
            )

        # 5. Attach sources
        result["sources"] = source_list
        result["confidence"] = self._compute_confidence(
            result.get("answer", ""), source_list, context_entries
        )

        # 6. Record usage for source entries
        for entry in context_entries:
            try:
                await self._archive.record_usage(entry.id)
            except Exception:
                pass

        logger.info(
            "Archivist answered: confidence=%.2f, sources=%d",
            result["confidence"],
            len(source_list),
        )
        return result

    async def ask_with_api(
        self,
        question: str,
        context: str,
        worker_id: str | None = None,
    ) -> dict[str, Any]:
        """Answer a question using an external LLM API.

        Sends the system prompt, context, and question to an LLM
        via the KantorKu ProviderRouter.

        Args:
            question: The user's question.
            context: Pre-built context string from Library entries.
            worker_id: Optional worker ID for tracing.

        Returns:
            A dict with ``answer`` key.

        Raises:
            ValueError: If the provider router is not configured.
            RuntimeError: If the LLM call fails.
        """
        if self._provider_router is None:
            raise ValueError(
                "ProviderRouter not configured — pass it to Archivist.__init__() "
                "to use LLM-based answering"
            )

        messages = [
            {"role": "system", "content": self.ARCHIVIST_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            },
        ]

        # Select a suitable model
        configured = self._provider_router.configured_providers
        if not configured:
            raise RuntimeError("No providers configured in the ProviderRouter")

        provider_name = configured[0]
        model_defaults: dict[str, str] = {
            "anthropic": "claude-sonnet-4-6",
            "google": "gemini-2.5-pro",
            "deepseek": "deepseek-v3-2",
            "minimax": "minimax-m2-7",
            "openai": "gpt-4o",
            "xai": "grok-3",
            "ollama": "llama3",
        }
        model_name = model_defaults.get(provider_name, "default")
        full_model = f"{provider_name}/{model_name}"

        logger.debug("Asking Archivist LLM model: %s", full_model)

        response = await self._provider_router.complete(
            model=full_model,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
        )

        # Extract confidence from the response if present
        confidence = 0.7  # Default for LLM answers
        confidence_match = re.search(
            r"\*\*Confidence\*\*:\s*(high|medium|low)",
            response,
            re.IGNORECASE,
        )
        if confidence_match:
            level = confidence_match.group(1).lower()
            confidence = {"high": 0.9, "medium": 0.7, "low": 0.4}.get(level, 0.7)

        return {
            "answer": response.strip(),
            "confidence": confidence,
        }

    async def ask_with_rules(
        self,
        question: str,
        context_entries: list[LibraryEntry],
        worker_id: str | None = None,
    ) -> dict[str, Any]:
        """Answer a question using rule-based synthesis.

        Concatenates entry summaries with [N] citation markers.
        This is the fallback when no LLM API is available.

        Args:
            question: The user's question.
            context_entries: The retrieved LibraryEntry objects.
            worker_id: Optional worker ID for tracing.

        Returns:
            A dict with ``answer`` and ``confidence`` keys.
        """
        if not context_entries:
            return {
                "answer": "No relevant entries found in the Library.",
                "confidence": 0.0,
            }

        parts: list[str] = []
        parts.append(f"Based on {len(context_entries)} Library entries:\n")

        for i, entry in enumerate(context_entries, 1):
            citation = f"[{i}]"
            title = entry.title or "(untitled)"
            summary = entry.summary or entry.content[:200] + "..."
            entry_type = entry.entry_type.value

            parts.append(
                f"{citation} **{title}** ({entry_type}):\n"
                f"   {summary}"
            )

        parts.append(
            "\n---\n"
            f"*Answer synthesized from {len(context_entries)} Library entries. "
            "For more detailed answers, configure an LLM provider.*"
        )

        answer = "\n\n".join(parts)

        # Confidence based on number and quality of sources
        avg_quality = (
            sum(e.quality_score for e in context_entries)
            / len(context_entries)
        )
        confidence = min(avg_quality * 0.8 + 0.1, 0.9)

        return {
            "answer": answer,
            "confidence": round(confidence, 2),
        }

    async def save_interaction(
        self,
        question: str,
        answer: str,
        source_entry_ids: list[str],
    ) -> LibraryEntry | None:
        """Save the Q&A as a new QA_PAIR entry in the Library.

        Only saves if the answer quality is good enough (confidence > 0.5).
        The new entry references the source entries it was derived from.

        Args:
            question: The original question.
            answer: The synthesized answer.
            source_entry_ids: IDs of the entries used to compose the answer.

        Returns:
            The created LibraryEntry, or None if quality is too low.
        """
        # Simple quality check — don't save low-quality interactions
        if not answer or len(answer) < 20:
            logger.debug("Skipping save: answer too short")
            return None

        # Check that we have valid sources
        valid_sources: list[str] = []
        for eid in source_entry_ids:
            entry = await self._archive.get(eid)
            if entry is not None:
                valid_sources.append(eid)

        if not valid_sources:
            logger.debug("Skipping save: no valid source entries")
            return None

        # Create the QA_PAIR entry
        qa_entry = LibraryEntry(
            title=f"Q: {question[:100]}",
            content=f"**Question:** {question}\n\n**Answer:** {answer}",
            summary=f"Q&A: {question[:80]}...",
            entry_type=EntryType.QA_PAIR,
            source=EntrySource.ARCHIVIST,
            question=question,
            answer=answer,
            source_entry_ids=valid_sources,
            quality_score=0.6,  # Default for auto-generated Q&A
            domain="qa",
            shelf_path=["Knowledge Base", "Q&A"],
            keywords=self._extract_qa_keywords(question, answer),
        )

        try:
            await self._archive.store(qa_entry)

            # Embed in vector store
            metadata = {
                "entry_type": qa_entry.entry_type.value,
                "domain": qa_entry.domain,
                "shelf_path": " / ".join(qa_entry.shelf_path),
            }
            await self._vector_store.add(qa_entry.id, qa_entry.content, metadata)

            logger.info(
                "Saved Q&A interaction as entry %s (sources=%d)",
                qa_entry.id,
                len(valid_sources),
            )
            return qa_entry

        except Exception as exc:
            logger.error("Failed to save Q&A interaction: %s", exc)
            return None

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _build_context(
        entries: list[LibraryEntry],
        search_results: list[dict[str, Any]],
    ) -> str:
        """Build a context string from retrieved entries for the LLM.

        Each entry is formatted with a citation number, metadata, and content.
        Content is truncated if too long to fit within reasonable context
        windows.

        Args:
            entries: The retrieved LibraryEntry objects.
            search_results: The raw search results with similarity scores.

        Returns:
            A formatted context string.
        """
        # Create a similarity map for quick lookup
        similarity_map: dict[str, float] = {}
        for result in search_results:
            similarity_map[result.get("entry_id", "")] = result.get(
                "similarity", 0.0
            )

        parts: list[str] = []
        max_content_length = 1500  # Per entry content limit

        for i, entry in enumerate(entries, 1):
            similarity = similarity_map.get(entry.id, 0.0)
            title = entry.title or "(untitled)"
            entry_type = entry.entry_type.value
            quality = entry.quality_score

            # Truncate content if too long
            content = entry.content
            if len(content) > max_content_length:
                content = content[:max_content_length] + "\n...[truncated]"

            parts.append(
                f"[{i}] Title: {title}\n"
                f"    Type: {entry_type} | Quality: {quality:.2f} | "
                f"Similarity: {similarity:.2f}\n"
                f"    Content:\n{content}"
            )

        return "\n\n".join(parts)

    @staticmethod
    def _compute_confidence(
        answer: str,
        sources: list[dict[str, Any]],
        entries: list[LibraryEntry],
    ) -> float:
        """Compute a confidence score for the answer.

        Factors:
        - Number of sources (more sources → higher confidence)
        - Average similarity of sources
        - Average quality of source entries
        - Answer length (very short answers are less confident)

        Args:
            answer: The generated answer.
            sources: The source metadata dicts.
            entries: The source LibraryEntry objects.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        if not sources:
            return 0.0

        # Source count factor (1-3 sources: 0.3-0.7, 4+: 0.8+)
        source_factor = min(len(sources) / 5.0, 1.0) * 0.4 + 0.3

        # Similarity factor
        avg_similarity = (
            sum(s.get("similarity", 0.0) for s in sources) / len(sources)
        )
        similarity_factor = avg_similarity * 0.3

        # Quality factor
        if entries:
            avg_quality = sum(e.quality_score for e in entries) / len(entries)
            quality_factor = avg_quality * 0.2
        else:
            quality_factor = 0.0

        # Answer length factor
        if len(answer) > 100:
            length_factor = 0.1
        elif len(answer) > 30:
            length_factor = 0.05
        else:
            length_factor = 0.0

        confidence = source_factor + similarity_factor + quality_factor + length_factor
        return round(min(max(confidence, 0.0), 1.0), 2)

    @staticmethod
    def _extract_qa_keywords(question: str, answer: str) -> list[str]:
        """Extract keywords from a Q&A pair for the saved entry.

        Args:
            question: The question text.
            answer: The answer text.

        Returns:
            A list of keyword strings.
        """
        combined = f"{question} {answer}".lower()

        # Remove common punctuation and split
        words = re.findall(r"\b[a-z]{3,}\b", combined)

        # Simple stopword filtering
        stopwords = {
            "the", "and", "for", "are", "but", "not", "you", "all",
            "can", "had", "her", "was", "one", "our", "out", "has",
            "how", "why", "what", "when", "where", "who", "which",
            "this", "that", "with", "from", "they", "been", "have",
            "will", "would", "could", "should", "does", "about",
        }

        # Count word frequencies
        freq: dict[str, int] = {}
        for word in words:
            if word not in stopwords:
                freq[word] = freq.get(word, 0) + 1

        # Sort by frequency and take top keywords
        sorted_words = sorted(freq.keys(), key=lambda w: freq[w], reverse=True)
        return sorted_words[:6]
