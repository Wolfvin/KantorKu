# Backend — Memory System (Three-Ring + EdgeQuake)

> **Konteks untuk session baru:**
> Three-Ring Memory: DuckDB Ring 1 (hot) + SQLite Ring 2 (warm) + Ring 3 (smart cold).
> Ring 3 punya dua opsi:
> - Cognee (github.com/topoteretes/cognee) — lightweight, mudah setup, Fase 3 prototype
> - EdgeQuake (github.com/raphaelmansuy/edgequake) — Rust GraphRAG, production, Fase 4+
> EdgeQuake dievaluasi session 2026-03-16: GraphRAG berbasis LightRAG algorithm di Rust,
> PostgreSQL AGE + pgvector, 6 query modes, <200ms hybrid latency.
> Cognee tetap default untuk Fase 3. EdgeQuake target Fase 4+.

---

## Ring 1 — DuckDB (HOT, in-process)

**Repo:** https://duckdb.org — embedded, zero network, WAL gratis.

Satu-satunya source of truth untuk orchestrator decisions.
Ring 2 dan Ring 3 bisa stale — **jangan pernah query selain Ring 1 untuk real-time decisions.**

```python
import duckdb

# Satu DuckDB per project — TIDAK BOLEH shared
conn = duckdb.connect(f"~/.vibe-office/rings/{project_id}/ring1.duckdb")

conn.execute("""
    CREATE TABLE IF NOT EXISTS checkpoints (
        task_id TEXT PRIMARY KEY,
        status TEXT,  -- in_progress | completed | failed
        payload JSON,
        created_at TIMESTAMP DEFAULT now(),
        completed_at TIMESTAMP
    )
""")

conn.execute("""
    CREATE TABLE IF NOT EXISTS active_project_state (
        task_id TEXT,
        status TEXT,  -- pending | in_progress | completed | failed | deferred
        worker_id TEXT,
        depends_on TEXT[]
    )
""")

conn.execute("""
    CREATE TABLE IF NOT EXISTS hot_episodes (
        id TEXT PRIMARY KEY,
        episode_type TEXT,
        worker_id TEXT,
        task_id TEXT,
        content JSON,
        flushed_to_ring2 BOOLEAN DEFAULT false,
        created_at TIMESTAMP DEFAULT now()
    )
""")
```

**Aturan urutan (wajib, kalau dilanggar → task duplikat saat crash recovery):**
```python
checkpoint(task_id, "in_progress")  # 1. dulu
send_to_worker(task)                # 2. baru kirim
checkpoint(task_id, "completed")    # 3. update setelah selesai
```

**Async queue (DuckDB single-writer):**
```python
import asyncio

write_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

async def ring1_writer():
    while True:
        episode = await write_queue.get()
        conn.execute("INSERT INTO hot_episodes ...", episode)
        write_queue.task_done()

await write_queue.put(episode)  # workers push ke queue
```

**Background flush ke Ring 2 (s08 pattern dari learn-claude-code):**
```python
import threading

def flush_loop():
    while True:
        time.sleep(5)
        episodes = conn.execute(
            "SELECT * FROM hot_episodes WHERE flushed_to_ring2 = false LIMIT 100"
        ).fetchall()
        if episodes:
            flush_to_ring2(episodes)
            conn.execute("UPDATE hot_episodes SET flushed_to_ring2 = true WHERE ...")

threading.Thread(target=flush_loop, daemon=True).start()
```

---

## Ring 2 — SQLite + Parquet (WARM, local disk)

Sync dari Ring 1 setiap 5 detik background. Retain 7 hari.

```
~/.vibe-office/rings/{project_id}/
├── ring2/
│   ├── warm.db          ← SQLite untuk query fleksibel offline
│   └── parquet/         ← columnar untuk training pipeline (Unsloth Fase 4)
│       └── {date}/
│           └── episodes_{timestamp}.parquet
```

Kalau Ring 1→Ring 2 gagal: data aman di Ring 1, retry otomatis di cycle berikutnya.

---

## Ring 3 — Opsi A: Cognee (PROTOTYPE, Fase 3)

**Repo:** https://github.com/topoteretes/cognee
Apache-2.0, 11k stars. Memory untuk AI agents, 6 baris setup.

**Kapan pakai Cognee:** Fase 3 prototype — mudah setup, tidak butuh PostgreSQL.

```python
pip install cognee
```

```python
import cognee
import os

# Ollama lokal (tidak keluar data):
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["LLM_MODEL"] = "llama3"
os.environ["LLM_ENDPOINT"] = "http://localhost:11434/v1"

await cognee.add("episode content")
await cognee.cognify()           # build knowledge graph
await cognee.memify()
results = await cognee.search("query")
```

---

## Ring 3 — Opsi B: EdgeQuake (PRODUCTION, Fase 4+)

**Repo:** https://github.com/raphaelmansuy/edgequake
Apache-2.0, 109 stars. Rust GraphRAG, implementasi LightRAG algorithm.

**Kenapa EdgeQuake lebih bagus dari Cognee untuk production:**
- Ditulis Rust — Tokio async, zero-copy, 1000+ concurrent requests
- 6 query modes yang bisa dipilih per use case (bukan satu-size-fits-all)
- REST API + SSE streaming built-in
- Sigma.js graph visualization
- Hybrid query <200ms (vs Cognee yang tidak ada benchmark jelas)
- PostgreSQL AGE (graph) + pgvector (vector) — battle-tested storage

**Setup EdgeQuake:**
```bash
git clone https://github.com/raphaelmansuy/edgequake.git
cd edgequake
make install          # install semua deps

# Configure di .env:
# LLM: Ollama (local) atau OpenAI
# DB: PostgreSQL dengan AGE dan pgvector extensions

make dev              # PostgreSQL + Backend + Frontend
# Backend: http://localhost:8080
# Frontend: http://localhost:3000
# Swagger: http://localhost:8080/swagger-ui
```

**6 Query Modes — mana yang dipakai worker mana:**

| Mode | Latency | Dipakai untuk |
|------|---------|---------------|
| `naive` | ~100-300ms | Keyword lookup sederhana |
| `local` | ~200-500ms | Knowledge spesifik per entity/worker |
| `global` | ~300-800ms | Thematic query, "apa yang pernah dipelajari workers?" |
| `hybrid` | ~400-1000ms | Default — balance antara local dan global |
| `mix` | configurable | Weighted blend naive + graph |
| `bypass` | instant | Direct LLM, skip retrieval |

**Integrasi dengan vibe-office backend:**

```python
import httpx

class EdgeQuakeRing3:
    """Ring 3 berbasis EdgeQuake — production GraphRAG."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url

    async def store_episode(self, episode: dict):
        """Upload episode ke EdgeQuake untuk di-index ke knowledge graph."""
        text = f"""
        Task: {episode['task_type']}
        Worker: {episode['worker_id']}
        Instruction: {episode['instruction']}
        Result: {episode['result_summary']}
        Success: {episode['success']}
        Errors: {', '.join(episode.get('errors', []))}
        """
        async with httpx.AsyncClient() as client:
            await client.post(f"{self.base_url}/api/v1/documents", data={"text": text})

    async def query_worker_knowledge(
        self,
        worker_id: str,
        query: str,
        mode: str = "local"   # local untuk knowledge spesifik worker
    ) -> str:
        """Query knowledge yang relevan untuk worker tertentu."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/query",
                json={
                    "query": f"[{worker_id}] {query}",
                    "mode": mode
                }
            )
            return resp.json()["answer"]

    async def query_global_patterns(self, query: str) -> str:
        """Query patterns/themes across semua workers — pakai global mode."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/query",
                json={"query": query, "mode": "global"}
            )
            return resp.json()["answer"]
```

**Siklus self-improvement dengan EdgeQuake:**
```
Task selesai → episode masuk Ring 1
              ↓ flush ke Ring 2 (Parquet)
              ↓ async upload ke EdgeQuake Ring 3
              ↓ EdgeQuake: chunk → extract entities → build graph
              ↓
Orchestrator query EdgeQuake sebelum assign task baru:
- "ada task serupa yang pernah gagal?" → local mode
- "worker mana yang paling sukses untuk task type ini?" → global mode
- "apa pola kesalahan umum di project ini?" → hybrid mode
```

---

## Summary: Kapan Pakai Apa

| Ring | Storage | Latensi | Dipakai untuk |
|------|---------|---------|---------------|
| Ring 1 | DuckDB in-process | ~μs | SEMUA operational decisions — satu-satunya source of truth |
| Ring 2 | SQLite + Parquet | ~ms | Query offline, training data Unsloth |
| Ring 3 (Fase 3) | Cognee | ~ms-s | Prototype — simple, no PostgreSQL needed |
| Ring 3 (Fase 4+) | EdgeQuake | <200ms | Production GraphRAG — 6 modes, Rust speed |

**Aturan keras:** Orchestrator hanya query Ring 1 saat execute.
Ring 2/3 hanya di-query saat planning atau startup untuk load context.
