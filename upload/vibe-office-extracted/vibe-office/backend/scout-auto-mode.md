# Backend — Scout Auto Web Search Mode (Fase 3)

> **Konteks untuk session baru:**
> Scout punya dua mode web search:
>   1. Manual: conductor kirim research request ke scout untuk task tertentu
>   2. Auto: kamu aktifkan via settings/command → scout proactively web search
>      topik relevan saat idle → hasil kirim ke auditor → kalau approved → curator
> Auto mode butuh TypeScript MCP karena web fetch ops lebih natural di sana.
> File terkait:
>   - `backend/knowledge-approval.md` → approval pipeline setelah scout kirim data
>   - `backend/workers.md` → scout worker definition
>   - `design/design-workers.md` → TypeScript MCP setup (shared dengan design workers)

---

## Cara Aktifkan Auto Mode

```
Via chat panel command:
  /scout auto on              → aktifkan auto mode
  /scout auto off             → matikan
  /scout auto on --topic rust → fokus topik tertentu
  /scout auto status          → lihat queue, results count

Via Settings panel:
  AI → Scout → Auto Web Search [ON/OFF]
  Topics whitelist: [rust, python, css, ...]  (kosong = semua relevan)
  Frequency: [low / normal / high]            → seberapa sering search
  Send to auditor: [ON/OFF]                   → kalau OFF, hanya simpan di Ring 2 tanpa approval
```

---

## Auto Mode Flow

```
Scout idle + auto mode ON
  ↓
scout pilih topik dari research_queue
  (diisi oleh: conductor saat planning, atau kamu via /scout topic add)
  ↓
scout web search (TypeScript MCP fetch)
  ↓
scout parse hasil → extract key knowledge
  ↓
bridge.relay('scout', 'curator', web_research_result)
  ↓
curator classify + clean
  ↓
bridge.relay('curator', 'auditor', knowledge_review_request)
  ↓
approval pipeline (lihat knowledge-approval.md)
  ↓ APPROVED
Ring 2 episode type: "scout_web"
SKILL.md update
```

---

## TypeScript MCP — Scout Web Search Tools

```typescript
// packages/mcp-scout/src/index.ts
// TypeScript MCP server untuk scout web operations
// Shared dengan design workers (archivist juga pakai fetch)

import { Server } from "@modelcontextprotocol/sdk/server/index.js"
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js"

const server = new Server(
  { name: "vibe-scout-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
)

// Tool 1: Web search
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "web_search",
      description: "Search the web for research topics",
      inputSchema: {
        type: "object",
        properties: {
          query:      { type: "string" },
          max_results:{ type: "number", default: 5 },
          focus:      { type: "string", enum: ["technical", "tutorial", "reference", "news"] }
        },
        required: ["query"]
      }
    },
    {
      name: "fetch_url",
      description: "Fetch content from a URL. Sends Accept: text/markdown header by default — Cloudflare-powered sites return clean markdown (80-99% token reduction). Falls back to HTML + Lightpanda parse if site tidak support markdown.",
      inputSchema: {
        type: "object",
        properties: {
          url:          { type: "string" },
          extract_mode: { type: "string", enum: ["full", "summary", "code_only"] },
          prefer_markdown: { type: "boolean", default: true }
        },
        required: ["url"]
      }
    },
    {
      name: "search_github",
      description: "Search GitHub for code examples and repos",
      inputSchema: {
        type: "object",
        properties: {
          query:    { type: "string" },
          type:     { type: "string", enum: ["code", "repo", "issue"] },
          language: { type: "string" }
        },
        required: ["query"]
      }
    }
  ]
}))

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  switch (request.params.name) {
    case "web_search":   return await handleWebSearch(request.params.arguments)
    case "fetch_url":    return await handleFetchUrl(request.params.arguments)
    case "search_github":return await handleGitHubSearch(request.params.arguments)
    default: throw new Error(`Unknown tool: ${request.params.name}`)\n  }\n})\n\nconst transport = new StdioServerTransport()\nawait server.connect(transport)\n```\n\n### handleFetchUrl — Cloudflare Markdown for Agents (Fase 3)\n\n> **Referensi:** https://blog.cloudflare.com/markdown-for-agents/\n> Cloudflare-powered sites (mayoritas web modern) support `Accept: text/markdown` header.\n> Response: clean markdown + `x-markdown-tokens` header dengan estimated token count.\n> Reduction: 80-99% token vs raw HTML. Claude Code sudah kirim header ini secara default.\n> Kita implement hal yang sama di scout MCP fetch layer.\n\n```typescript\n// packages/mcp-scout/src/handlers/fetch.ts\n\nimport fetch from \"node-fetch\"\nimport { Lightpanda } from \"../lightpanda\"\n\ninterface FetchResult {\n  content: string\n  format: \"markdown\" | \"html\"\n  estimated_tokens: number | null\n  token_reduction_pct: number | null\n  url: string\n  error_structured: CloudflareError | null\n}\n\ninterface CloudflareError {\n  // RFC 9457 structured error — Cloudflare kirim ini kalau rate-limited\n  // Jauh lebih kecil dari HTML error page, bisa dibaca deterministic\n  type: string\n  title: string\n  detail: string\n  retry_after?: number   // detik — kalau ada, pakai ini untuk exponential backoff\n}\n\nexport async function handleFetchUrl(args: {\n  url: string\n  extract_mode: \"full\" | \"summary\" | \"code_only\"\n  prefer_markdown?: boolean\n}): Promise<FetchResult> {\n  const preferMarkdown = args.prefer_markdown !== false  // default: true\n\n  try {\n    const resp = await fetch(args.url, {\n      headers: {\n        // Cloudflare Markdown for Agents — prefer markdown, fallback ke HTML\n        \"Accept\": preferMarkdown\n          ? \"text/markdown, text/html;q=0.9, */*;q=0.8\"\n          : \"text/html\",\n        \"User-Agent\": \"vibe-office-scout/1.0 (AI research agent)\"\n      },\n      timeout: 15000\n    })\n\n    const contentType = resp.headers.get(\"content-type\") ?? \"\"\n    const isMarkdown  = contentType.includes(\"text/markdown\")\n\n    // x-markdown-tokens: token estimate dari Cloudflare\n    // Conductor bisa pakai ini untuk decide: langsung feed atau RLM dulu\n    const markdownTokens = resp.headers.get(\"x-markdown-tokens\")\n    const estimatedTokens = markdownTokens ? parseInt(markdownTokens) : null\n\n    const body = await resp.text()\n\n    // Kalau Cloudflare return structured error (RFC 9457)\n    // Jauh lebih reliable untuk retry logic vs parse HTML error page\n    if (!resp.ok && contentType.includes(\"application/problem+json\")) {\n      const cfError: CloudflareError = JSON.parse(body)\n      return {\n        content: `[ERROR] ${cfError.title}: ${cfError.detail}`,\n        format: \"markdown\",\n        estimated_tokens: null,\n        token_reduction_pct: null,\n        url: args.url,\n        error_structured: cfError\n      }\n    }\n\n    // Kalau dapat markdown — langsung pakai, tidak perlu parse\n    if (isMarkdown) {\n      return {\n        content: body,\n        format: \"markdown\",\n        estimated_tokens: estimatedTokens,\n        token_reduction_pct: null,  // tidak bisa hitung tanpa tau ukuran HTML original\n        url: args.url,\n        error_structured: null\n      }\n    }\n\n    // Fallback: site tidak support markdown → Lightpanda parse HTML\n    const parsed = await Lightpanda.extractText(body, args.extract_mode)\n    return {\n      content: parsed.text,\n      format: \"html\",\n      estimated_tokens: estimatedTokens,\n      token_reduction_pct: null,\n      url: args.url,\n      error_structured: null\n    }\n\n  } catch (err: any) {\n    return {\n      content: `[FETCH_ERROR] ${err.message}`,\n      format: \"markdown\",\n      estimated_tokens: null,\n      token_reduction_pct: null,\n      url: args.url,\n      error_structured: null\n    }\n  }\n}\n```\n\n**Integrasi dengan RLM (scout_for_task dan proactive_research_loop):**\n```python\n# Scout Python side — pakai x-markdown-tokens untuk decide RLM threshold\nasync def fetch_and_maybe_rlm(url: str, task_query: str) -> str:\n    \"\"\"\n    Fetch URL via MCP, pakai token estimate dari Cloudflare untuk\n    decide apakah perlu RLM atau langsung feed ke LLM.\n    \"\"\"\n    result = await mcp.call_tool(\"fetch_url\", {\"url\": url, \"extract_mode\": \"full\"})\n    fetch_data = json.loads(result.content[0].text)\n\n    estimated = fetch_data.get(\"estimated_tokens\")\n\n    # Kalau Cloudflare kasih estimate dan masih di bawah 8K → langsung feed\n    if estimated and estimated < 8000:\n        return fetch_data[\"content\"]\n\n    # Kalau tidak ada estimate atau lebih dari 8K → RLM\n    return await rlm_client.completion(\n        prompt=f\"Extract relevant content for: {task_query}\",\n        context=fetch_data[\"content\"]\n    )\n```\n\n**Structured error → deterministic retry (bukan parse HTML):**\n```python\nasync def fetch_with_retry(url: str, max_retries: int = 3) -> dict:\n    for attempt in range(max_retries):\n        result = await mcp.call_tool(\"fetch_url\", {\"url\": url})\n        data = json.loads(result.content[0].text)\n\n        if data.get(\"error_structured\"):\n            err = data[\"error_structured\"]\n            retry_after = err.get(\"retry_after\", 2 ** attempt * 5)  # exponential fallback\n            await asyncio.sleep(retry_after)\n            continue\n\n        return data\n\n    return {\"content\": \"[MAX_RETRIES]\", \"format\": \"markdown\"}\n```

---

## Scout Auto Loop (Python side — call TypeScript MCP)

```python
# backend/workers/scout.py — mode 2: auto web search

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MCP_SCOUT_CMD = ["node", "packages/mcp-scout/dist/index.js"]

async def auto_research_loop():
    """
    Background loop: scout web search saat idle + auto mode ON.
    Berjalan parallel dengan main worker loop.
    """
    async with stdio_client(StdioServerParameters(command=MCP_SCOUT_CMD[0], args=MCP_SCOUT_CMD[1:])) as (r, w):
        async with ClientSession(r, w) as mcp:
            await mcp.initialize()

            while True:
                # Cek kondisi
                if not get_setting('scout_auto_mode'):
                    await asyncio.sleep(60)
                    continue

                if get_worker_state('scout') == 'working':
                    await asyncio.sleep(30)
                    continue

                # Ambil topik dari research_queue
                topic = await pop_research_queue()
                if not topic:
                    await asyncio.sleep(120)  # tidak ada topik → tunggu 2 menit
                    continue

                # Set state
                set_worker_state('scout', 'working')
                await ws_broadcast({
                    'type': 'state_change',
                    'worker_id': 'scout',
                    'new_state': 'working'
                })
                await ws_broadcast({
                    'type': 'speech_bubble',
                    'worker_id': 'scout',
                    'text': f'researching: {topic["query"]}...',
                    'color': '#C3E88D',
                    'duration_ms': 4000,
                })

                try:
                    result = await research_topic(mcp, topic)
                    await send_to_curator(result, source='scout_web')
                except Exception as e:
                    print(f"[scout] research error: {e}")

                set_worker_state('scout', 'idle')

                # Cooldown berdasarkan frequency setting
                freq = get_setting('scout_auto_frequency', 'normal')
                cooldown = {'low': 600, 'normal': 180, 'high': 60}[freq]
                await asyncio.sleep(cooldown)

async def research_topic(mcp: ClientSession, topic: dict) -> dict:
    """Satu research session untuk satu topik."""

    # Step 1: Web search
    search_result = await mcp.call_tool("web_search", {
        "query": topic['query'],
        "max_results": 5,
        "focus": topic.get('focus', 'technical')
    })

    urls = extract_urls(search_result)

    # Step 2: Fetch top 2 results
    contents = []
    for url in urls[:2]:
        try:
            page = await mcp.call_tool("fetch_url", {
                "url": url,
                "extract_mode": "summary"
            })
            contents.append({'url': url, 'content': page.content[0].text})
        except:
            continue

    # Step 3: GitHub search kalau topic teknikal
    if topic.get('include_github', True):
        gh_result = await mcp.call_tool("search_github", {
            "query": topic['query'],
            "type": "code",
            "language": topic.get('language', '')
        })
        contents.append({'url': 'github', 'content': gh_result.content[0].text})

    return {
        'title': f"Auto Research: {topic['query']}",
        'query': topic['query'],
        'sources': [c['url'] for c in contents],
        'content': '\n\n---\n\n'.join(c['content'] for c in contents),
        'topic_id': topic.get('id'),
    }

async def send_to_curator(result: dict, source: str):
    """Kirim hasil research ke curator via bridge."""
    await bridge.relay('scout', 'curator', {
        'task_type': 'knowledge_ingest',
        'source': source,
        'title': result['title'],
        'content': result['content'],
        'metadata': {
            'query': result['query'],
            'sources': result['sources'],
        }
    })
```

---

## Research Queue Management

```python
# Ring 1 DuckDB: research_queue table

"""
CREATE TABLE IF NOT EXISTS research_queue (
    id          TEXT PRIMARY KEY,
    query       TEXT NOT NULL,
    focus       TEXT DEFAULT 'technical',
    language    TEXT,
    priority    INTEGER DEFAULT 5,        -- 1=high, 10=low
    source      TEXT,                     -- 'conductor' | 'user' | 'auto'
    created_at  TEXT,
    attempted   INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'pending'    -- pending | done | failed
)
"""

async def pop_research_queue() -> dict | None:
    """Ambil topik dengan prioritas tertinggi yang belum dilakukan."""
    conn = get_ring1_conn()
    result = conn.execute("""
        SELECT * FROM research_queue
        WHERE status = 'pending'
        ORDER BY priority ASC, created_at ASC
        LIMIT 1
    """).fetchone()

    if result:
        conn.execute(
            "UPDATE research_queue SET status = 'in_progress', attempted = attempted + 1 WHERE id = ?",
            [result['id']]
        )
    return result

# Conductor otomatis isi queue saat planning task:
async def conductor_populate_research_queue(task: dict):
    """
    Kalau conductor detect topik yang mungkin butuh research,
    tambahkan ke scout's research queue.
    """
    topics = extract_research_topics(task)  # LLM extract dari task description
    for t in topics:
        await ring1_insert('research_queue', {
            'id': uuid4().hex,
            'query': t['query'],
            'focus': t.get('focus', 'technical'),
            'language': t.get('language'),
            'priority': t.get('priority', 5),
            'source': 'conductor',
            'created_at': now_iso(),
            'status': 'pending',
        })
```

---

## TypeScript MCP — Shared dengan Design Workers

```
packages/
  mcp-scout/          ← web_search, fetch_url, search_github
  mcp-design/         ← fetch_design_url, extract_css, color_palette
  mcp-shared/         ← utils: html parser, content extractor (shared)

Conductor (Python) connect ke keduanya via stdio MCP protocol.
Tidak perlu network — semua local process communication.
```

---

## Checklist Fase 3

```
[ ] mcp-scout TypeScript package: web_search, fetch_url, search_github tools
[ ] auto_research_loop() berjalan sebagai background asyncio task
[ ] research_queue table di Ring 1 DuckDB
[ ] /scout auto on/off command di chat panel
[ ] Settings panel: Scout auto mode toggle + frequency + topics whitelist
[ ] Scout send hasil ke curator via bridge
[ ] Approval pipeline handle source: "scout_web" (lihat knowledge-approval.md)
[ ] Cooldown berdasarkan frequency setting
[ ] conductor_populate_research_queue() saat planning
```
