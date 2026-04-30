# Backend — EdgeQuake Setup (PostgreSQL + AGE + pgvector)

> **Konteks untuk session baru:**
> EdgeQuake adalah Ring 3 production (menggantikan Cognee Fase 3 prototype).
> EdgeQuake BUTUH PostgreSQL dengan dua extensions:
>   - Apache AGE  → graph database (knowledge graph entity/relationship)
>   - pgvector    → vector similarity search (semantic search)
> File ini: install PostgreSQL + kedua extensions + verify + EdgeQuake connect.
> Repos:
>   - EdgeQuake:  https://github.com/raphaelmansuy/edgequake (Apache-2.0)
>   - Apache AGE: https://github.com/apache/age (Apache-2.0, 3k stars)
>   - pgvector:   https://github.com/pgvector/pgvector (PostgreSQL License, 14k stars)

---

## Gambaran Arsitektur

```
Python backend workers
  ↓ HTTP POST /api/v1/documents (simpan episode)
  ↓ HTTP POST /api/v1/query (semantic + graph query)
EdgeQuake (Rust server, port 8080)
  ↓ entity extraction + graph building
  ↓ vector embedding + storage
PostgreSQL 15+
  ├── Apache AGE extension  → graph storage (nodes, edges, cypher queries)
  └── pgvector extension    → vector storage (embeddings, similarity search)
```

---

## Step 1 — Install PostgreSQL 15+

**Ubuntu/Debian:**
```bash
# Tambah PostgreSQL APT repository
sudo sh -c 'echo "deb https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget -qO- https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo tee /etc/apt/trusted.gpg.d/pgdg.asc

sudo apt update
sudo apt install -y postgresql-15 postgresql-server-dev-15

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify
psql --version  # harus 15.x
```

**macOS (Homebrew):**
```bash
brew install postgresql@15
brew services start postgresql@15
echo 'export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Docker (paling mudah, recommended untuk dev):**
```bash
# Jalankan PostgreSQL dengan AGE dan pgvector sudah include
docker run -d \
  --name vibe-postgres \
  -e POSTGRES_PASSWORD=vibeoffice \
  -e POSTGRES_DB=vibe_knowledge \
  -p 5432:5432 \
  -v vibe-pg-data:/var/lib/postgresql/data \
  apache/age:latest

# Verify
docker exec -it vibe-postgres psql -U postgres -c "SELECT version();"
```

> Docker image `apache/age:latest` sudah include AGE built-in.
> Untuk pgvector, perlu install terpisah (lihat Step 3).

---

## Step 2 — Install Apache AGE

**Dari package (Ubuntu, PostgreSQL 15):**
```bash
# Download AGE release
wget https://github.com/apache/age/releases/download/v1.5.0-rc0/apache-age-1.5.0-pg15-ubuntu-22.04-amd64.tar.gz
tar xzf apache-age-1.5.0-pg15-ubuntu-22.04-amd64.tar.gz

# Install
sudo cp apache-age-1.5.0/lib/age.so $(pg_config --pkglibdir)/
sudo cp apache-age-1.5.0/share/extension/age* $(pg_config --sharedir)/extension/
```

**Build dari source (lebih reliable):**
```bash
git clone https://github.com/apache/age.git
cd age

# Checkout versi stable
git checkout PG15/v1.5.0

# Build
make PG_CONFIG=$(which pg_config)
sudo make install
```

**Enable extension di database:**
```bash
# Connect ke PostgreSQL
psql -U postgres

# Buat database untuk vibe-office
CREATE DATABASE vibe_knowledge;
\c vibe_knowledge

-- Enable AGE
CREATE EXTENSION IF NOT EXISTS age;
LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- Verify
SELECT * FROM ag_graph;
-- Harus return: (0 rows) — tidak error = sukses
```

---

## Step 3 — Install pgvector

**Ubuntu/Debian:**
```bash
# Install build dependencies
sudo apt install -y build-essential git

# Clone dan build
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

**macOS:**
```bash
brew install pgvector
```

**Docker — tambah ke container yang sudah ada:**
```bash
# Kalau pakai Docker Apache AGE, install pgvector di dalamnya
docker exec -it vibe-postgres bash
apt-get install -y build-essential git
git clone https://github.com/pgvector/pgvector.git
cd pgvector && make && make install
exit
```

**Enable extension:**
```sql
-- Di database vibe_knowledge
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify
SELECT * FROM pg_extension WHERE extname = 'vector';
-- Harus return 1 row
```

---

## Step 4 — Verify Keduanya Berjalan

```sql
-- Connect ke vibe_knowledge
\c vibe_knowledge

-- Test AGE: buat graph sederhana
SELECT * FROM cypher('test_graph', $$
    CREATE (a:Entity {name: 'coder_rust', type: 'worker'})
    RETURN a
$$) AS (a agtype);

-- Test pgvector: buat tabel dengan vector column
CREATE TABLE IF NOT EXISTS test_embeddings (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding vector(1536)  -- 1536 = dimensi OpenAI embeddings
);

INSERT INTO test_embeddings (content, embedding)
VALUES ('test content', '[0.1, 0.2, 0.3, ...]'::vector);

-- Test similarity search
SELECT content, embedding <-> '[0.1, 0.2, 0.3, ...]'::vector AS distance
FROM test_embeddings
ORDER BY distance LIMIT 5;

-- Cleanup test
DROP TABLE test_embeddings;
SELECT drop_graph('test_graph', true);
```

Kalau tidak ada error: PostgreSQL + AGE + pgvector siap.

---

## Step 5 — Setup EdgeQuake

```bash
git clone https://github.com/raphaelmansuy/edgequake.git
cd edgequake

# Install dependencies
make install
# Ini install: Rust toolchain, Node.js deps, Python deps
```

**Configure `.env`:**
```bash
cp .env.example .env
```

```env
# .env — edit sesuai setup PostgreSQL kamu
DATABASE_URL=postgresql://postgres:vibeoffice@localhost:5432/vibe_knowledge

# LLM untuk entity extraction (pakai Ollama lokal)
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5-coder:7b
LLM_ENDPOINT=http://localhost:11434/v1

# Embedding model (bisa pakai Ollama juga)
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSIONS=768  # sesuaikan dengan model

# Server config
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
```

> **Catatan embedding dimensions:**
> `nomic-embed-text` (Ollama) = 768 dimensi
> `text-embedding-3-small` (OpenAI) = 1536 dimensi
> Pilih satu dan konsisten — tidak bisa campur.

**Pull embedding model:**
```bash
ollama pull nomic-embed-text
```

**Jalankan EdgeQuake:**
```bash
make dev
# Backend: http://localhost:8080
# Frontend: http://localhost:3000
# Swagger: http://localhost:8080/swagger-ui
```

---

## Step 6 — Integrasi dengan Python Backend Workers

```python
# backend/ring3_edgequake.py

import httpx
from typing import Any

EDGEQUAKE_URL = "http://localhost:8080"

class EdgeQuakeClient:
    """Ring 3 client — simpan episodes, query knowledge."""

    def __init__(self, base_url: str = EDGEQUAKE_URL):
        self.base_url = base_url

    async def store_episode(self, episode: dict) -> str:
        """Upload episode ke EdgeQuake untuk di-index ke knowledge graph."""
        # Format episode sebagai teks yang bisa di-extract entity-nya
        doc_text = self._format_episode(episode)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/documents",
                data={"text": doc_text},
                timeout=30.0
            )
            resp.raise_for_status()
            return resp.json()["id"]

    async def query(
        self,
        query: str,
        mode: str = "hybrid",
        worker_filter: str | None = None
    ) -> dict:
        """
        Query knowledge graph.
        mode: naive | local | global | hybrid | mix | bypass
        worker_filter: kalau diisi, filter hanya knowledge untuk worker ini
        """
        payload = {"query": query, "mode": mode}
        if worker_filter:
            payload["query"] = f"[{worker_filter}] {query}"

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/query",
                json=payload,
                timeout=60.0
            )
            resp.raise_for_status()
            return resp.json()

    async def get_stats(self) -> dict:
        """Ambil statistik knowledge graph — untuk DNA Report curator."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/api/v1/stats")
            resp.raise_for_status()
            return resp.json()

    def _format_episode(self, episode: dict) -> str:
        return f"""
Worker: {episode['worker_id']}
Task Type: {episode['task_type']}
Instruction: {episode['instruction']}
Result: {episode.get('result_summary', 'N/A')}
Success: {episode['success']}
Duration: {episode.get('duration_seconds', 'N/A')}s
Errors: {', '.join(episode.get('errors', [])) or 'none'}
Context: {episode.get('language', 'N/A')} project
"""

# Singleton untuk dipakai semua workers
ring3 = EdgeQuakeClient()
```

**Cara pakai di curator worker:**
```python
async def sync_episodes_to_ring3():
    """Background task: flush Ring 2 episodes ke EdgeQuake Ring 3."""
    episodes = load_parquet_episodes_pending_sync()
    for ep in episodes:
        doc_id = await ring3.store_episode(ep)
        mark_episode_synced(ep['id'], doc_id)
        await asyncio.sleep(0.1)  # rate limit

async def query_similar_failures(task: dict) -> str:
    """Sebelum assign task, cek apakah ada failure serupa di masa lalu."""
    result = await ring3.query(
        query=f"failed tasks similar to: {task['instruction']}",
        mode="local",
        worker_filter=task.get('preferred_worker')
    )
    return result.get('answer', '')
```

---

## Query Modes: Kapan Pakai Yang Mana

| Mode | Latensi | Pakai untuk |
|------|---------|-------------|
| `naive` | ~100ms | Keyword search cepat |
| `local` | ~200ms | Knowledge spesifik satu worker atau satu task type |
| `global` | ~400ms | Pattern lintas semua workers ("error apa yang paling sering?") |
| `hybrid` | ~600ms | Default — balanced, cocok untuk conductor planning |
| `bypass` | instant | Direct LLM tanpa RAG, untuk query yang tidak butuh history |

**Rekomendasi per use case:**
```python
# Conductor planning task baru
await ring3.query("strategi terbaik untuk task ini", mode="hybrid")

# Curator analisis knowledge gap
await ring3.query("domain mana yang paling banyak gagal?", mode="global")

# Uncertainty escalation — cari solusi serupa
await ring3.query(f"bagaimana solve {error_type}", mode="local", worker_filter="coder_rust")

# Scout proactive research summary
await ring3.query("update library terbaru yang relevan", mode="global")
```

---

## Troubleshooting Umum

**AGE tidak mau load:**
```sql
-- Pastikan AGE di shared_preload_libraries
SHOW shared_preload_libraries;
-- Kalau tidak ada 'age', edit postgresql.conf:
-- shared_preload_libraries = 'age'
-- Lalu restart PostgreSQL
```

**pgvector dimension mismatch:**
```
ERROR: expected 1536 dimensions, not 768
→ Embedding model kamu berubah. Drop dan recreate table embeddings.
→ Atau ubah EMBEDDING_DIMENSIONS di .env sesuai model yang dipakai.
```

**EdgeQuake gagal connect ke PostgreSQL:**
```bash
# Test koneksi manual
psql postgresql://postgres:vibeoffice@localhost:5432/vibe_knowledge -c "SELECT 1;"

# Kalau Docker, pastikan port 5432 ter-expose:
docker ps | grep vibe-postgres
# PORTS harus ada: 0.0.0.0:5432->5432/tcp
```

---

## Checklist Setup EdgeQuake

```
[ ] PostgreSQL 15+ berjalan (psql --version mengembalikan 15.x)
[ ] Apache AGE extension enabled (SELECT * FROM ag_graph; tidak error)
[ ] pgvector extension enabled (SELECT * FROM pg_extension WHERE extname='vector'; return 1 row)
[ ] EdgeQuake clone dan make install berhasil
[ ] .env dikonfigurasi: DATABASE_URL, LLM_PROVIDER, EMBEDDING_MODEL
[ ] ollama pull nomic-embed-text selesai
[ ] make dev berjalan: backend 8080, frontend 3000
[ ] Test upload document: curl -X POST http://localhost:8080/api/v1/documents
[ ] Test query: curl -X POST http://localhost:8080/api/v1/query -d '{"query":"test","mode":"hybrid"}'
[ ] ring3_edgequake.py terhubung dan store_episode() bekerja
```
