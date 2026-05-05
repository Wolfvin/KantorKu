"""
Librarian — AI-powered categorization and indexing system for KantorKu Library.

The Librarian is responsible for automatically classifying incoming documents
into the Library's taxonomy. It determines entry type (KNOWLEDGE, SOLUTION,
QA_PAIR, PROCEDURE), assigns keywords, places entries on the correct shelf,
and estimates initial quality scores.

Two classification strategies are supported:
1. **LLM-based** (``classify_with_api``): Uses an external LLM via the
   KantorKu provider router for accurate, context-aware classification.
2. **Rule-based** (``classify_with_rules``): A deterministic fallback that
   uses content pattern matching, heuristics, and keyword extraction.

The full ingest pipeline (``ingest``) combines classification, storage,
and indexing in a single call.

Example::

    from kantorku.library.storage.archive import Archive
    from kantorku.library.storage.vectors import VectorStore
    from kantorku.library.storage.hot_index import HotIndex

    archive = Archive("data/library/archive.db")
    vector_store = VectorStore("data/library/vectors")
    await archive.initialize()
    await vector_store.initialize()

    librarian = Librarian(archive=archive, vector_store=vector_store)
    entry = await librarian.ingest(
        content="How to fix a Python ImportError...",
        title="Fixing Python Import Errors",
        user_hint="python debugging",
    )
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

# ── Stopwords for keyword extraction ─────────────────────────────────────────
# A minimal set of English + Indonesian stopwords to filter out from keywords.
_STOPWORDS: frozenset[str] = frozenset({
    # English
    "about", "above", "after", "again", "also", "and", "another", "because",
    "before", "below", "between", "both", "but", "could", "does", "doing",
    "down", "during", "each", "either", "every", "first", "from", "further",
    "had", "has", "have", "having", "here", "how", "however", "into", "just",
    "more", "most", "much", "must", "neither", "nor", "not", "only", "other",
    "others", "our", "over", "own", "same", "should", "since", "some", "such",
    "than", "that", "the", "their", "them", "then", "there", "these", "they",
    "this", "those", "through", "thus", "under", "until", "upon", "very",
    "was", "were", "what", "when", "where", "which", "while", "who", "whom",
    "why", "will", "with", "without", "would",
    # Indonesian
    "adalah", "akan", "antara", "apa", "atau", "bahwa", "bisa", "boleh",
    "buat", "dalam", "dan", "dari", "dengan", "di", "dia", "diantara",
    "ini", "itu", "juga", "kami", "karena", "ke", "kepada", "jika",
    "lagi", "lebih", "macam", "maka", "masih", "melainkan", "melalui",
    "memang", "memiliki", "menjadi", "mereka", "meskipun", "oleh",
    "pada", "per", "saat", "sebab", "sebuah", "secara", "sedangkan",
    "sejak", "sekali", "selain", "selama", "semua", "sudah", "supaya",
    "telah", "tentang", "terlalu", "tersebut", "tertentu", "tentu",
    "tidak", "toh", "untuk", "yaitu",
})


class Librarian:
    """AI-powered categorization and indexing system for KantorKu Library.

    The Librarian classifies incoming content using an LLM API when available,
    falling back to a rule-based heuristic system. It also manages the full
    ingest pipeline: classify → store → index → embed.

    Args:
        archive: The Archive instance for persistent storage.
        vector_store: The VectorStore instance for semantic search embeddings.
        provider_router: Optional ProviderRouter for LLM API calls.
            If not provided, classification falls back to rule-based only.
    """

    ARCHIVIST_SYSTEM_PROMPT: str = """You are Librarian, the categorization and indexing AI for KantorKu Library.

## Your Role
You analyze incoming documents and determine their proper classification within the Library's knowledge taxonomy. You assign entry types, keywords, shelf placement, and quality estimates.

## Input Format
You will receive:
- **content**: The full text content of the document (markdown)
- **title**: The document title (may be empty)
- **user_hint**: An optional user-provided hint about the document's topic

## Your Tasks
1. **Determine entry_type**: Classify the document as one of:
   - `KNOWLEDGE` — Factual knowledge, explanations, reference material
   - `SOLUTION` — A problem + solution pair, especially from real debugging/coding
   - `QA_PAIR` — A question and answer pair
   - `PROCEDURE` — Step-by-step instructions, how-to guides, tutorials

2. **Generate keywords**: Extract 3-8 significant keywords/phrases that capture the document's essential topics. Avoid generic words.

3. **Assign shelf_path**: Place the document in the Library's hierarchical shelf system. Use the most specific shelf that fits. Examples:
   - `["Engineering", "Backend", "Python"]`
   - `["Engineering", "DevOps", "Docker"]`
   - `["Mathematics", "Statistics"]`
   - `["Science", "Physics", "Quantum"]`
   - `["Philosophy", "Logic"]`

4. **Estimate quality_initial**: Rate the likely usefulness of this entry on a 0.0-1.0 scale:
   - 0.9-1.0: Comprehensive, well-structured, immediately useful
   - 0.7-0.9: Good quality, most information needed is present
   - 0.5-0.7: Adequate but may need improvement
   - 0.3-0.5: Incomplete or vague
   - 0.0-0.3: Very low quality, barely useful

5. **Determine domain**: Identify the knowledge domain (e.g., "web_text", "code", "mathematics", "science", "philosophy")

6. **Set shelf_confidence**: How confident are you in the shelf placement? (0.0-1.0)

7. **Generate summary**: Create a 1-3 sentence summary of the document.

## Output Format
Respond with ONLY a JSON object (no markdown fences, no explanation):
```json
{
  "entry_type": "KNOWLEDGE|SOLUTION|QA_PAIR|PROCEDURE",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "shelf_path": ["Category", "Subcategory"],
  "quality_initial": 0.75,
  "domain": "code",
  "shelf_confidence": 0.85,
  "summary": "A brief summary of the document."
}
```

## Shelf Naming Conventions
- Use Title Case for shelf names (e.g., "Backend" not "backend")
- Be specific but not overly narrow (3-4 levels maximum)
- Prefer existing shelf paths when the content fits
- Common top-level shelves: Engineering, Mathematics, Science, Philosophy, Business, Language, Arts
- Engineering sub-shelves: Backend, Frontend, DevOps, Architecture, Security
- Mathematics sub-shelves: Algebra, Calculus, Statistics, Logic
- Science sub-shelves: Physics, Chemistry, Biology

## Consistency Rules
- If user_hint is provided, weight it heavily in classification decisions
- Code-heavy content should typically go under Engineering
- Theoretical content should go under Mathematics or Science
- If content contains both problem and solution, prefer SOLUTION over KNOWLEDGE
- Step-by-step guides with numbered steps should be PROCEDURE
- FAQ-style or dialogue content should be QA_PAIR
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

    # ── Classification ───────────────────────────────────────────────────

    async def classify(
        self,
        content: str,
        title: str = "",
        user_hint: str = "",
    ) -> dict[str, Any]:
        """Classify a document using the Librarian system prompt.

        Tries LLM-based classification first via the provider router.
        If the router is not configured or the API call fails, falls
        back to rule-based classification.

        Args:
            content: The document content (markdown).
            title: Optional document title.
            user_hint: Optional hint about the document's topic.

        Returns:
            A dict with keys: entry_type, keywords, shelf_path,
            quality_initial, domain, shelf_confidence, summary.
        """
        try:
            if self._provider_router is not None:
                return await self.classify_with_api(content, title, user_hint)
        except Exception as exc:
            logger.warning(
                "LLM classification failed, falling back to rules: %s", exc
            )

        return await self.classify_with_rules(content, title, user_hint)

    async def classify_with_api(
        self,
        content: str,
        title: str = "",
        user_hint: str = "",
    ) -> dict[str, Any]:
        """Classify a document using an external LLM API.

        Uses the KantorKu ProviderRouter to call an LLM with the
        Librarian system prompt. The LLM returns a JSON classification
        which is parsed and validated.

        Args:
            content: The document content (markdown).
            title: Optional document title.
            user_hint: Optional hint about the document's topic.

        Returns:
            A dict with classification results.

        Raises:
            ValueError: If the provider router is not configured.
            RuntimeError: If the LLM response cannot be parsed.
        """
        if self._provider_router is None:
            raise ValueError(
                "ProviderRouter not configured — pass it to Librarian.__init__() "
                "to use LLM-based classification"
            )

        # Build the user message with all available context
        user_parts: list[str] = []
        if title:
            user_parts.append(f"Title: {title}")
        if user_hint:
            user_parts.append(f"User hint: {user_hint}")
        user_parts.append(f"Content:\n{content}")

        user_message = "\n\n".join(user_parts)

        messages = [
            {"role": "system", "content": self.ARCHIVIST_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        # Try to find a suitable model from configured providers
        # Default to the first configured provider
        configured = self._provider_router.configured_providers
        if not configured:
            raise RuntimeError("No providers configured in the ProviderRouter")

        # Use the first available provider with a reasonable model
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

        logger.debug("Classifying with LLM model: %s", full_model)

        response = await self._provider_router.complete(
            model=full_model,
            messages=messages,
            temperature=0.1,  # Low temperature for consistent classification
            max_tokens=1024,
        )

        # Parse the JSON response
        result = self._parse_classification_response(response)
        logger.info(
            "LLM classified as %s → %s (confidence=%.2f)",
            result.get("entry_type", "UNKNOWN"),
            " / ".join(result.get("shelf_path", [])),
            result.get("shelf_confidence", 0.0),
        )
        return result

    async def classify_with_rules(
        self,
        content: str,
        title: str = "",
        user_hint: str = "",
    ) -> dict[str, Any]:
        """Classify a document using rule-based heuristics.

        This is the fallback classification engine when no LLM API is
        available. It uses content patterns to determine entry type,
        extracts keywords, assigns shelf paths, and estimates quality.

        Classification rules:
        - **entry_type**: Code blocks → code domain; step-by-step patterns →
          PROCEDURE; Q&A patterns → QA_PAIR; problem+solution patterns →
          SOLUTION; else → KNOWLEDGE.
        - **keywords**: Extracts significant words (length > 4, not stopwords).
        - **shelf_path**: Assigned based on detected topics.
        - **quality_initial**: Estimated from content length, code presence,
          and specificity.

        Args:
            content: The document content (markdown).
            title: Optional document title.
            user_hint: Optional hint about the document's topic.

        Returns:
            A dict with classification results.
        """
        # ── Determine entry_type ──────────────────────────────────────
        entry_type = self._detect_entry_type(content)
        domain = self._detect_domain(content, user_hint)

        # ── Extract keywords ──────────────────────────────────────────
        keywords = self._extract_keywords(content, title, user_hint)

        # ── Assign shelf_path ─────────────────────────────────────────
        shelf_path = self._suggest_shelf_path(content, keywords, user_hint)
        shelf_confidence = self._estimate_shelf_confidence(
            content, keywords, shelf_path
        )

        # ── Estimate quality ──────────────────────────────────────────
        quality_initial = self._estimate_quality(content, entry_type)

        # ── Generate summary ──────────────────────────────────────────
        summary = self._generate_summary(content, title)

        result: dict[str, Any] = {
            "entry_type": entry_type.value,
            "keywords": keywords,
            "shelf_path": shelf_path,
            "quality_initial": quality_initial,
            "domain": domain,
            "shelf_confidence": shelf_confidence,
            "summary": summary,
        }

        logger.info(
            "Rule-based classified as %s → %s (confidence=%.2f, quality=%.2f)",
            entry_type.value,
            " / ".join(shelf_path) if shelf_path else "Uncategorized",
            shelf_confidence,
            quality_initial,
        )
        return result

    # ── Full Ingest Pipeline ──────────────────────────────────────────────

    async def ingest(
        self,
        content: str,
        title: str = "",
        source: EntrySource = EntrySource.MANUAL,
        user_hint: str = "",
        origin_session_id: str | None = None,
        origin_worker_id: str | None = None,
    ) -> LibraryEntry:
        """Full ingest pipeline: classify → create → store → index → embed.

        This is the primary entry point for adding new knowledge to the
        Library. The pipeline performs the following steps:

        1. **Classify** the content using the Librarian system.
        2. **Create** a ``LibraryEntry`` from the classification results.
        3. **Store** the entry in the Archive (SQLite).
        4. **Index** the entry in the HotIndex (if available).
        5. **Embed** the entry content in the VectorStore.
        6. **Return** the created entry.

        Args:
            content: The document content (markdown).
            title: Optional document title.
            source: Origin of the entry (MANUAL, KANTORKU, IMPORT, ARCHIVIST).
            user_hint: Optional hint about the document's topic.
            origin_session_id: Optional KantorKu session ID.
            origin_worker_id: Optional KantorKu worker ID.

        Returns:
            The created ``LibraryEntry`` with all classification metadata.
        """
        logger.info(
            "Ingesting document: title=%r, source=%s, hint=%r",
            title or "(untitled)",
            source.value,
            user_hint or "(none)",
        )

        # 1. Classify
        classification = await self.classify(content, title, user_hint)

        # 2. Create LibraryEntry
        entry_type = EntryType(classification.get("entry_type", "knowledge"))
        entry = LibraryEntry(
            title=title,
            content=content,
            summary=classification.get("summary", ""),
            keywords=classification.get("keywords", []),
            entry_type=entry_type,
            domain=classification.get("domain", "web_text"),
            shelf_path=classification.get("shelf_path", []),
            shelf_confidence=classification.get("shelf_confidence", 0.0),
            quality_score=classification.get("quality_initial", 0.5),
            source=source,
            origin_session_id=origin_session_id,
            origin_worker_id=origin_worker_id,
        )

        # Set type-specific fields based on classification
        if entry_type == EntryType.SOLUTION:
            entry.problem_description = self._extract_problem(content)
            entry.solution_code = self._extract_code_blocks(content)
            entry.verification_result = None
        elif entry_type == EntryType.QA_PAIR:
            entry.question = title or self._extract_question(content)
            entry.answer = content
        elif entry_type == EntryType.PROCEDURE:
            entry.steps = self._extract_steps(content)

        # 3. Store in archive
        await self._archive.store(entry)
        logger.debug("Stored entry %s in archive", entry.id)

        # 4. Index in hot_index (if the archive has a hot index reference)
        # The hot_index is accessed through a separate reference if available.
        # For now we rely on the caller to set up the hot_index separately,
        # or the Indexer class handles this.

        # 5. Embed in vector store
        try:
            metadata = {
                "entry_type": entry.entry_type.value,
                "domain": entry.domain,
                "shelf_path": " / ".join(entry.shelf_path) if entry.shelf_path else "",
            }
            await self._vector_store.add(entry.id, content, metadata)
            logger.debug("Embedded entry %s in vector store", entry.id)
        except Exception as exc:
            logger.warning(
                "Failed to embed entry %s in vector store: %s", entry.id, exc
            )

        logger.info(
            "Ingested entry %s: type=%s, shelf=%s, quality=%.2f",
            entry.id,
            entry.entry_type.value,
            entry.shelf_str,
            entry.quality_score,
        )
        return entry

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _parse_classification_response(response_text: str) -> dict[str, Any]:
        """Parse the LLM's classification response into a structured dict.

        Tries to extract a JSON object from the response text, handling
        cases where the LLM wraps it in markdown code fences.

        Args:
            response_text: Raw text response from the LLM.

        Returns:
            Parsed classification dict.

        Raises:
            RuntimeError: If the response cannot be parsed as valid JSON.
        """
        # Strip markdown code fences if present
        text = response_text.strip()
        if text.startswith("```"):
            # Remove opening fence
            first_newline = text.index("\n") if "\n" in text else len(text)
            text = text[first_newline + 1:]
            # Remove closing fence
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON within the text
            json_match = re.search(r"\{[\s\S]*\}", text)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"Failed to parse LLM classification response: {exc}"
                    ) from exc
            else:
                raise RuntimeError(
                    "No JSON object found in LLM classification response"
                )

        # Validate required fields
        required_fields = {"entry_type", "keywords", "shelf_path"}
        missing = required_fields - set(result.keys())
        if missing:
            logger.warning(
                "Classification response missing fields: %s — filling defaults",
                missing,
            )

        # Set defaults for missing fields
        result.setdefault("entry_type", "knowledge")
        result.setdefault("keywords", [])
        result.setdefault("shelf_path", [])
        result.setdefault("quality_initial", 0.5)
        result.setdefault("domain", "web_text")
        result.setdefault("shelf_confidence", 0.3)
        result.setdefault("summary", "")

        # Validate entry_type
        valid_types = {"knowledge", "solution", "qa_pair", "procedure"}
        if result["entry_type"].lower() not in valid_types:
            logger.warning(
                "Invalid entry_type %r — defaulting to 'knowledge'",
                result["entry_type"],
            )
            result["entry_type"] = "knowledge"

        return result

    @staticmethod
    def _detect_entry_type(content: str) -> EntryType:
        """Detect entry type based on content patterns.

        Pattern detection rules:
        - Code blocks (```...```) with domain context → code domain indicator
        - Step-by-step (numbered steps, "Step 1:", "Pertama:", etc.) → PROCEDURE
        - Q&A patterns ("Q:", "A:", "Question:", "Answer:", "Pertanyaan:") → QA_PAIR
        - Problem + solution ("Problem:", "Solution:", "Error:", "Fix:") → SOLUTION
        - Default → KNOWLEDGE

        Args:
            content: The document content.

        Returns:
            The detected EntryType.
        """
        content_lower = content.lower()

        # Check for Q&A patterns
        qa_patterns = [
            r"\bq\s*:", r"\ba\s*:", r"\bquestion\s*:", r"\banswer\s*:",
            r"\bpertanyaan\s*:", r"\bjawaban\s*:", r"\bjawab\s*:",
        ]
        for pattern in qa_patterns:
            if re.search(pattern, content_lower):
                return EntryType.QA_PAIR

        # Check for step-by-step / procedure patterns
        procedure_patterns = [
            r"step\s+\d+", r"langkah\s+\d+", r"pertama\b",
            r"kedua\b", r"ketiga\b", r"^\s*\d+\.\s+\w",
            r"^\s*-\s+step", r"how\s+to\b", r"cara\s+\w",
            r"tutorial", r"panduan\s+langkah",
        ]
        procedure_count = sum(
            1 for p in procedure_patterns
            if re.search(p, content_lower, re.MULTILINE)
        )
        if procedure_count >= 2:
            return EntryType.PROCEDURE

        # Check for problem + solution patterns
        problem_patterns = [
            r"\bproblem\b", r"\berror\b", r"\bbug\b", r"\bissue\b",
            r"\bmasalah\b", r"\bkesalahan\b",
        ]
        solution_patterns = [
            r"\bsolution\b", r"\bfix\b", r"\bresolve\b", r"\bsolved\b",
            r"\bsolusi\b", r"\bperbaikan\b", r"\bmemperbaiki\b",
        ]
        has_problem = any(re.search(p, content_lower) for p in problem_patterns)
        has_solution = any(re.search(p, content_lower) for p in solution_patterns)
        if has_problem and has_solution:
            return EntryType.SOLUTION

        # Check for code blocks — this alone doesn't determine type,
        # but combined with problem hints suggests SOLUTION
        has_code = bool(re.search(r"```[\s\S]*?```", content))
        if has_code and has_problem:
            return EntryType.SOLUTION

        # Default to KNOWLEDGE
        return EntryType.KNOWLEDGE

    @staticmethod
    def _detect_domain(content: str, user_hint: str = "") -> str:
        """Detect the knowledge domain from content and hints.

        Args:
            content: The document content.
            user_hint: Optional user-provided topic hint.

        Returns:
            A domain string (e.g., "code", "mathematics", "science").
        """
        combined = f"{content} {user_hint}".lower()

        # Code/domain detection
        code_indicators = [
            r"```", r"def\s+\w+", r"class\s+\w+", r"import\s+\w+",
            r"function\s+\w+", r"const\s+\w+", r"let\s+\w+",
            r"var\s+\w+", r"return\s+", r"console\.log",
            r"print\s*\(", r"npm\s+", r"pip\s+install",
        ]
        if any(re.search(p, combined) for p in code_indicators):
            return "code"

        # Mathematics detection
        math_indicators = [
            r"equation", r"theorem", r"proof", r"derivative",
            r"integral", r"matrix", r"vector", r"algebra",
            r"calculus", r"statistics", r"probability",
            r"\bπ\b", r"\b∞\b", r"∑", r"∫", r"√",
        ]
        if any(re.search(p, combined) for p in math_indicators):
            return "mathematics"

        # Science detection
        science_indicators = [
            r"experiment", r"hypothesis", r"molecule", r"atom",
            r"cell", r"organism", r"physics", r"chemistry",
            r"biology", r"quantum", r"energy", r"force",
        ]
        if any(re.search(p, combined) for p in science_indicators):
            return "science"

        return "web_text"

    @staticmethod
    def _extract_keywords(
        content: str,
        title: str = "",
        user_hint: str = "",
    ) -> list[str]:
        """Extract significant keywords from content.

        Extracts words that are:
        - Longer than 4 characters
        - Not in the stopwords list
        - Appear at least once in the text
        - Not purely numeric

        Also extracts multi-word technical terms in camelCase, snake_case,
        and kebab-case.

        Args:
            content: The document content.
            title: Optional document title.
            user_hint: Optional user hint.

        Returns:
            A list of 3-8 keyword strings.
        """
        # Combine all text sources
        all_text = f"{title} {user_hint} {content}"

        # Extract camelCase, snake_case, kebab-case identifiers
        technical_terms: list[str] = []
        for pattern in [
            r"[a-z][A-Z][a-zA-Z]+",       # camelCase
            r"[a-z]+_[a-z_]+",             # snake_case
            r"[a-z]+-[a-z-]+",             # kebab-case
            r"[A-Z][a-z]+(?:[A-Z][a-z]+)+", # PascalCase
        ]:
            technical_terms.extend(re.findall(pattern, all_text))

        # Extract regular words
        words = re.findall(r"\b[a-zA-Z]+\b", all_text.lower())

        # Filter words: length > 4, not stopwords, not numeric
        candidates: dict[str, int] = {}
        for word in words:
            if len(word) > 4 and word not in _STOPWORDS and not word.isdigit():
                candidates[word] = candidates.get(word, 0) + 1

        # Add technical terms (preserving original case)
        seen_lower: set[str] = set()
        for term in technical_terms:
            lower = term.lower()
            if lower not in seen_lower and lower not in _STOPWORDS:
                candidates[term] = candidates.get(term, 0) + 1
                seen_lower.add(lower)

        # Sort by frequency, then take top keywords
        sorted_keywords = sorted(
            candidates.keys(),
            key=lambda w: candidates[w],
            reverse=True,
        )

        # Return 3-8 keywords, deduplicated
        result: list[str] = []
        seen: set[str] = set()
        for kw in sorted_keywords:
            lower_kw = kw.lower()
            if lower_kw not in seen:
                result.append(kw)
                seen.add(lower_kw)
            if len(result) >= 8:
                break

        # Ensure at least 3 keywords
        if len(result) < 3:
            # Add words from user_hint as fallback
            hint_words = re.findall(r"\b\w+\b", user_hint.lower())
            for hw in hint_words:
                if hw not in seen and len(hw) > 2 and hw not in _STOPWORDS:
                    result.append(hw)
                    seen.add(hw)
                if len(result) >= 3:
                    break

        return result[:8]

    @staticmethod
    def _suggest_shelf_path(
        content: str,
        keywords: list[str],
        user_hint: str = "",
    ) -> list[str]:
        """Suggest a shelf path based on content, keywords, and hints.

        Uses topic detection to assign entries to the appropriate
        shelf in the Library's hierarchical taxonomy.

        Args:
            content: The document content.
            keywords: Extracted keywords.
            user_hint: Optional user hint.

        Returns:
            A list of shelf path segments (e.g., ["Engineering", "Backend", "Python"]).
        """
        combined = f"{content} {user_hint} {' '.join(keywords)}".lower()

        # Topic → shelf mapping
        topic_shelves: dict[str, list[list[str]]] = {
            # Engineering sub-shelves
            "backend": [
                ["Engineering", "Backend"],
                ["Engineering", "Backend", "API"],
                ["Engineering", "Backend", "Database"],
                ["Engineering", "Backend", "Python"],
                ["Engineering", "Backend", "JavaScript"],
            ],
            "frontend": [
                ["Engineering", "Frontend"],
                ["Engineering", "Frontend", "React"],
                ["Engineering", "Frontend", "CSS"],
            ],
            "devops": [
                ["Engineering", "DevOps"],
                ["Engineering", "DevOps", "Docker"],
                ["Engineering", "DevOps", "CI/CD"],
                ["Engineering", "DevOps", "Kubernetes"],
            ],
            "architecture": [
                ["Engineering", "Architecture"],
                ["Engineering", "Architecture", "Design Patterns"],
                ["Engineering", "Architecture", "Microservices"],
            ],
            "security": [
                ["Engineering", "Security"],
                ["Engineering", "Security", "Authentication"],
                ["Engineering", "Security", "Encryption"],
            ],
            # Mathematics sub-shelves
            "algebra": [["Mathematics", "Algebra"]],
            "calculus": [["Mathematics", "Calculus"]],
            "statistics": [["Mathematics", "Statistics"]],
            "logic": [["Mathematics", "Logic"]],
            # Science sub-shelves
            "physics": [["Science", "Physics"]],
            "chemistry": [["Science", "Chemistry"]],
            "biology": [["Science", "Biology"]],
            # Other top-level
            "philosophy": [["Philosophy"]],
            "business": [["Business"]],
            "language": [["Language"]],
            "arts": [["Arts"]],
        }

        # Indicator keywords for each topic
        topic_indicators: dict[str, list[str]] = {
            "backend": [
                "backend", "server", "api", "database", "sql", "nosql",
                "python", "java", "golang", "rust", "node", "express",
                "django", "flask", "fastapi", "orm", "migration",
            ],
            "frontend": [
                "frontend", "react", "vue", "angular", "css", "html",
                "tailwind", "bootstrap", "sass", "dom", "spa", "ssr",
                "nextjs", "svelte",
            ],
            "devops": [
                "devops", "docker", "container", "kubernetes", "k8s",
                "ci/cd", "jenkins", "github actions", "terraform",
                "ansible", "deploy", "infrastructure", "helm",
            ],
            "architecture": [
                "architecture", "design pattern", "microservice",
                "monolith", "event-driven", "cqs", "cqrs",
                "clean architecture", "hexagonal", "ddd",
            ],
            "security": [
                "security", "auth", "oauth", "jwt", "encryption",
                "ssl", "tls", "csrf", "xss", "vulnerability",
                "penetration", "firewall",
            ],
            "algebra": ["algebra", "matrix", "vector space", "linear"],
            "calculus": ["calculus", "derivative", "integral", "differential"],
            "statistics": ["statistics", "probability", "regression", "bayesian", "mean", "variance"],
            "logic": ["logic", "proposition", "predicate", "inference", "proof"],
            "physics": ["physics", "quantum", "relativity", "mechanics", "thermodynamics"],
            "chemistry": ["chemistry", "molecule", "reaction", "compound", "element"],
            "biology": ["biology", "cell", "dna", "evolution", "organism", "genetics"],
            "philosophy": ["philosophy", "ethics", "metaphysics", "epistemology", "aesthetics"],
            "business": ["business", "startup", "marketing", "finance", "strategy", "management"],
            "language": ["language", "linguistics", "grammar", "syntax", "nlp", "translation"],
            "arts": ["arts", "design", "music", "painting", "literature", "creative"],
        }

        # Score each topic based on how many indicators match
        topic_scores: dict[str, int] = {}
        for topic, indicators in topic_indicators.items():
            score = sum(1 for ind in indicators if ind in combined)
            if score > 0:
                topic_scores[topic] = score

        if not topic_scores:
            # No clear topic detected — try a broader match
            if any(w in combined for w in ["code", "programming", "software", "developer"]):
                return ["Engineering"]
            return []

        # Pick the best-matching topic
        best_topic = max(topic_scores, key=lambda t: topic_scores[t])
        score = topic_scores[best_topic]

        # Choose shelf depth based on score
        shelves = topic_shelves.get(best_topic, [["Engineering"]])
        if score >= 3 and len(shelves) > 1:
            return shelves[1]  # More specific shelf
        return shelves[0]  # Top-level shelf

    @staticmethod
    def _estimate_shelf_confidence(
        content: str,
        keywords: list[str],
        shelf_path: list[str],
    ) -> float:
        """Estimate confidence in the shelf placement.

        Args:
            content: The document content.
            keywords: Extracted keywords.
            shelf_path: The assigned shelf path.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        if not shelf_path:
            return 0.1

        # Base confidence from having a shelf at all
        confidence = 0.4

        # More specific shelves → higher confidence
        confidence += min(len(shelf_path) * 0.1, 0.3)

        # If keywords align with shelf name, boost confidence
        shelf_words = " ".join(shelf_path).lower()
        matching_keywords = sum(1 for kw in keywords if kw.lower() in shelf_words)
        confidence += min(matching_keywords * 0.1, 0.2)

        return min(confidence, 1.0)

    @staticmethod
    def _estimate_quality(content: str, entry_type: EntryType) -> float:
        """Estimate initial quality score based on content characteristics.

        Factors:
        - Content length (longer is generally better, up to a point)
        - Presence of code blocks
        - Structural specificity (headings, lists)
        - Entry type bonus (SOLUTION and PROCEDURE tend to be more useful)

        Args:
            content: The document content.
            entry_type: The detected entry type.

        Returns:
            Quality score between 0.0 and 1.0.
        """
        quality = 0.4  # Base quality

        # Content length bonus (diminishing returns)
        length = len(content)
        if length > 100:
            quality += 0.1
        if length > 500:
            quality += 0.1
        if length > 1500:
            quality += 0.05
        if length < 50:
            quality -= 0.2

        # Code presence bonus
        has_code = bool(re.search(r"```[\s\S]*?```", content))
        if has_code:
            quality += 0.1

        # Structural specificity bonus
        has_headings = bool(re.search(r"^#+\s+\w", content, re.MULTILINE))
        has_lists = bool(re.search(r"^\s*[-*]\s+\w", content, re.MULTILINE))
        has_numbered = bool(re.search(r"^\s*\d+\.\s+\w", content, re.MULTILINE))

        if has_headings:
            quality += 0.05
        if has_lists or has_numbered:
            quality += 0.05

        # Entry type bonus
        type_bonuses: dict[EntryType, float] = {
            EntryType.SOLUTION: 0.1,
            EntryType.PROCEDURE: 0.05,
            EntryType.QA_PAIR: 0.05,
            EntryType.KNOWLEDGE: 0.0,
        }
        quality += type_bonuses.get(entry_type, 0.0)

        return max(0.0, min(quality, 1.0))

    @staticmethod
    def _generate_summary(content: str, title: str = "") -> str:
        """Generate a brief summary from content.

        Takes the first meaningful paragraph or sentence from the content.

        Args:
            content: The document content.
            title: Optional document title.

        Returns:
            A summary string (1-3 sentences).
        """
        # Remove code blocks for summary purposes
        clean = re.sub(r"```[\s\S]*?```", "", content)
        # Remove markdown headers
        clean = re.sub(r"^#+\s+.*$", "", clean, flags=re.MULTILINE)
        # Remove list markers
        clean = re.sub(r"^\s*[-*]\s+", "", clean, flags=re.MULTILINE)
        # Collapse whitespace
        clean = re.sub(r"\n{2,}", "\n", clean).strip()

        if not clean:
            return title if title else ""

        # Take the first sentence or up to 200 chars
        sentences = re.split(r"(?<=[.!?])\s+", clean)
        summary_parts: list[str] = []
        char_count = 0

        for sentence in sentences:
            if char_count + len(sentence) > 200:
                break
            summary_parts.append(sentence.strip())
            char_count += len(sentence)
            if len(summary_parts) >= 3:
                break

        summary = " ".join(summary_parts)
        if not summary:
            # Fallback: take first 150 chars
            summary = clean[:150].rsplit(" ", 1)[0] + "..."

        return summary

    @staticmethod
    def _extract_problem(content: str) -> str:
        """Extract the problem description from SOLUTION-type content.

        Args:
            content: The document content.

        Returns:
            The extracted problem description.
        """
        # Try to find "Problem:" or "Error:" sections
        for pattern in [
            r"(?:problem|error|issue|masalah)\s*:\s*\n?([\s\S]*?)(?=\n(?:solution|fix|solusi|perbaikan)\s*:|\Z)",
        ]:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:500]

        # Fallback: first paragraph before code or solution
        lines = content.split("\n")
        problem_lines: list[str] = []
        for line in lines:
            if line.strip().startswith("```") or re.match(
                r"(?:solution|fix|solusi)\s*:", line, re.IGNORECASE
            ):
                break
            if line.strip():
                problem_lines.append(line.strip())

        return " ".join(problem_lines)[:500]

    @staticmethod
    def _extract_code_blocks(content: str) -> str | None:
        """Extract code blocks from content.

        Args:
            content: The document content.

        Returns:
            The extracted code as a string, or None if no code found.
        """
        blocks = re.findall(r"```(?:\w+)?\n([\s\S]*?)```", content)
        if blocks:
            return "\n\n".join(blocks)
        return None

    @staticmethod
    def _extract_question(content: str) -> str:
        """Extract the question from QA_PAIR-type content.

        Args:
            content: The document content.

        Returns:
            The extracted question.
        """
        # Try to find "Q:" or "Question:" patterns
        match = re.search(
            r"(?:q|question|pertanyaan)\s*:\s*(.*?)(?=\n(?:a|answer|jawaban)\s*:|\Z)",
            content,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()[:300]

        # Fallback: first sentence with a question mark
        sentences = re.split(r"(?<=[.!?])\s+", content)
        for s in sentences:
            if "?" in s:
                return s.strip()[:300]

        return content[:300]

    @staticmethod
    def _extract_steps(content: str) -> list[dict[str, Any]]:
        """Extract steps from PROCEDURE-type content.

        Args:
            content: The document content.

        Returns:
            A list of step dicts with "step", "action", "expected" keys.
        """
        steps: list[dict[str, Any]] = []
        step_num = 0

        # Try numbered steps: "1. Do something"
        numbered = re.findall(
            r"^\s*(\d+)\.\s+(.+?)(?=\n\s*\d+\.\s|\Z)",
            content,
            re.MULTILINE | re.DOTALL,
        )
        if numbered:
            for num_text, action in numbered:
                step_num += 1
                steps.append({
                    "step": int(num_text),
                    "action": action.strip()[:300],
                    "expected": "",
                })
            return steps

        # Try "Step N:" patterns
        step_matches = re.findall(
            r"step\s+(\d+)\s*:\s*(.+?)(?=\n\s*step\s+\d+\s*:|\Z)",
            content,
            re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )
        if step_matches:
            for num_text, action in step_matches:
                steps.append({
                    "step": int(num_text),
                    "action": action.strip()[:300],
                    "expected": "",
                })
            return steps

        # Fallback: each non-empty line is a step
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        for line in lines:
            if line.startswith("#") or line.startswith("```"):
                continue
            step_num += 1
            steps.append({
                "step": step_num,
                "action": line[:300],
                "expected": "",
            })
            if step_num >= 20:
                break

        return steps
