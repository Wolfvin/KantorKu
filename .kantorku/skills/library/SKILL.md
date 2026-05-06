# Library Skill

## Purpose
The **Library** skill provides knowledge management, search, and retrieval capabilities. It manages the project's knowledge base including document ingestion, semantic search, shelf organization, and intelligent browsing of indexed content.

## Capabilities

1. **Search** — Perform semantic and keyword search across the knowledge base
2. **Ask** — Answer questions using retrieved context from the library
3. **Ingest** — Import and index documents, code, and URLs into the library
4. **Browse** — Navigate and explore the knowledge base interactively
5. **Shelf** — Organize content into named shelves (collections) for structured access
6. **Book** — Create, read, and manage individual knowledge entries (books)

## Output Schema

```json
{
  "skill": "library",
  "action": "search|ask|ingest|browse|shelf|book",
  "result": {
    "query": "string",
    "matches": [
      {
        "id": "string",
        "title": "string",
        "content": "string",
        "shelf": "string",
        "relevance": 0.0,
        "source": "string"
      }
    ],
    "total": 0,
    "truncated": false
  },
  "metadata": {
    "tokens_used": 0,
    "latency_ms": 0,
    "provider": "string"
  }
}
```

## Key Rules

1. **Always cite sources** — Every retrieved fact must include its source document
2. **Respect shelf boundaries** — Searches can be scoped to specific shelves
3. **Ingest before search** — Content must be indexed before it can be found
4. **Rate-limit ingestion** — Batch large ingestion jobs to avoid overwhelming the indexer
5. **Deduplicate results** — Merge overlapping entries before returning results
6. **Cache hot queries** — Frequently accessed content stays in Ring 1 (DuckDB)
7. **Fallback gracefully** — If semantic search fails, fall back to keyword search
