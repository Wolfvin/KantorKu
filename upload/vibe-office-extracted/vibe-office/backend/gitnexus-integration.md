# Backend — GitNexus Integration

**Repo:** https://github.com/abhigyanpatwari/GitNexus
PolyForm Noncommercial license (gratis untuk personal), 9.4k stars.

GitNexus adalah "mata" para workers. Sebelum nulis kode, context_worker
query GitNexus untuk tahu: apa yang di-call oleh fungsi ini, apa yang
akan break kalau diubah, dependencies apa yang perlu diperhatikan.

---

## Masalah yang Dipecahkan

Tanpa GitNexus:
```
rust_worker edit UserService.validate()
→ tidak tahu 47 fungsi depend pada return type-nya
→ breaking changes masuk ke production
```

Dengan GitNexus:
```
context_worker: impact({target: "UserService", direction: "upstream"})
→ "8 callers, 3 clusters, semua 90%+ confidence"
→ rust_worker dapat context lengkap sebelum mulai
```

---

## Setup

```bash
# Install sekali
npm install -g gitnexus

# Index project (jalankan dari root project)
npx gitnexus analyze

# Ini yang dijalankan: index codebase, install agent skills,
# buat AGENTS.md / CLAUDE.md context files
```

Index disimpan di `.gitnexus/` dalam project (gitignored).
Global registry di `~/.gitnexus/registry.json`.

---

## 7 MCP Tools yang Dipakai context_worker

```python
# context_worker memanggil tools ini via MCP

# 1. Impact analysis — blast radius sebelum ubah kode
impact(target="UserService", direction="upstream", minConfidence=0.8)
# → depth 1 (WILL BREAK), depth 2 (LIKELY AFFECTED)

# 2. Context — 360-degree view satu symbol
context(name="validateUser")
# → incoming calls, outgoing calls, process participation

# 3. Query — hybrid search (BM25 + semantic + RRF)
query(query="authentication middleware")
# → grouped by process, tidak flat

# 4. Detect changes — analisis git diff sebelum commit
detect_changes(scope="all")
# → changed symbols, affected processes, risk level

# 5. Rename — safe multi-file rename
rename(symbol_name="validateUser", new_name="verifyUser", dry_run=True)
# → files affected, total edits, graph edits vs text search edits

# 6. Cypher — raw graph query
cypher(query="MATCH (fn)-[:CALLS]->(dep) WHERE dep.name = 'unwrap' RETURN fn")

# 7. List repos — discovery semua indexed repos
list_repos()
```

---

## Integrasi dengan context_worker

Sebelum assign task ke rust_worker, context_worker selalu:

```python
async def enrich_task_with_context(task: dict) -> dict:
    """
    Inject GitNexus context ke task sebelum dikirim ke rust_worker.
    Pakai s05 skill-loading pattern dari learn-claude-code.
    """

    # 1. Cari symbols yang relevan dengan task
    search_result = await gitnexus.query(task["instruction"])

    # 2. Kalau task adalah edit fungsi existing, cek impact
    if task["task_type"] in ["debug", "refactor"]:
        affected_symbols = extract_symbols(task["instruction"])
        for sym in affected_symbols:
            impact_result = await gitnexus.impact(
                target=sym,
                direction="upstream",
                minConfidence=0.8
            )
            task["context"]["impact"] = impact_result

    # 3. Inject sebagai context ke task (bukan di system prompt)
    task["context"]["codebase_context"] = {
        "relevant_symbols": search_result["definitions"],
        "related_processes": search_result["processes"],
        "impact_analysis": task["context"].get("impact"),
    }

    return task
```

---

## Visualisasi di Server Room

Di kantor pixel art, server room menampilkan GitNexus knowledge graph
sebagai mini-visualization. context_worker yang "tinggal" di sini terlihat
sedang browse graph saat query.

Di TV meeting room, saat rust_worker di-assign task, tampil:
```
[context_worker] loaded 8 symbols, 2 processes, impact: medium
[CEO] assigned to rust_worker with full context
```

---

## MCP Setup untuk Vibe-Office Backend

```python
# Di Python backend, panggil GitNexus via subprocess atau MCP client
import subprocess
import json

class GitNexusClient:
    def __init__(self, project_path: str):
        self.project_path = project_path

    async def query(self, text: str) -> dict:
        result = subprocess.run(
            ["npx", "gitnexus", "mcp"],
            input=json.dumps({"method": "query", "params": {"query": text}}),
            capture_output=True, text=True, cwd=self.project_path
        )
        return json.loads(result.stdout)

    async def impact(self, target: str, direction: str = "upstream") -> dict:
        result = subprocess.run(
            ["npx", "gitnexus", "mcp"],
            input=json.dumps({
                "method": "impact",
                "params": {"target": target, "direction": direction}
            }),
            capture_output=True, text=True, cwd=self.project_path
        )
        return json.loads(result.stdout)
```

---

## Bahasa yang Didukung GitNexus

TypeScript, JavaScript, Python, Java, Kotlin, C, C++, C#, Go, **Rust**, PHP, Swift.

Rust support = context_worker bisa analyze project Rust kamu dengan benar —
tahu ownership patterns, trait implementations, lifetime dependencies.

---

## Re-index Setelah Worker Coding

Setiap kali rust_worker selesai coding, git_worker commit, context_worker
trigger re-index agar knowledge graph selalu fresh:

```bash
npx gitnexus analyze --force
```

Ini dijalankan sebagai background task setelah setiap commit (s08 pattern).
