# Backend — DeerFlow Patterns

> **Konteks untuk session baru:**
> DeerFlow (github.com/bytedance/deer-flow, MIT, 22.7k stars, bytedance) adalah
> implementasi production yang paling mirip arsitektur vibe-office dari semua
> repo yang pernah dievaluasi. Bukan untuk di-integrate, tapi ini adalah
> referensi implementasi terlengkap untuk Fase 3.
> Key insight: DeerFlow v2.0 adalah ground-up rewrite dari Deep Research framework
> menjadi SuperAgent harness — persis jalur evolusi yang sama dengan vibe-office.
> Dievaluasi session 2026-03-16.

---

## Kenapa DeerFlow Paling Relevan

Lihat perbandingan ini:

| Fitur | DeerFlow | Vibe-Office |
|-------|----------|-------------|
| Skills system | `/mnt/skills/public/*.SKILL.md`, load on demand | `~/.vibe-office/workers/*/SKILL.md` |
| Sub-agents paralel | Lead agent spawn N sub-agents | post-coding pipeline paralel |
| Context compression | Summarize, offload ke filesystem | s06 pattern + hermes compression |
| Long-term memory | Persistent across sessions | Cognee Ring 3 |
| Sandbox | Docker isolated per task | OpenSandbox (Fase 3+) |
| Orchestration | LangGraph state machine | AR Orchestrator + DuckDB |

DeerFlow sudah solve masalah yang sama. Baca kodenya sebelum implement dari nol.

**Quickstart untuk self-study:**
```bash
git clone https://github.com/bytedance/deer-flow.git
cd deer-flow
make config          # buat config.yaml + .env dari templates
make docker-init     # pull sandbox image
make docker-start    # start semua services
# buka http://localhost:2026
```

---

## Pelajaran 1 — Skills Loading On-Demand (PENTING)

DeerFlow punya satu insight paling penting untuk vibe-office:
**skills di-load progressively, hanya saat task butuhkan, bukan semua di awal.**

```
/mnt/skills/public/
├── research/SKILL.md
├── report-generation/SKILL.md
├── slide-creation/SKILL.md
└── image-generation/SKILL.md

/mnt/skills/custom/
└── your-custom-skill/SKILL.md     ← user-added skills
```

```python
# DeerFlow pattern: skill loader on-demand
# (direkonstruksi dari arsitektur mereka)

class SkillLoader:
    def __init__(self, skills_dir: str):
        self.registry = self._scan_registry(skills_dir)

    def _scan_registry(self, path: str) -> dict:
        """Scan semua SKILL.md, simpan path-nya (bukan kontennya!)."""
        registry = {}
        for skill_dir in Path(path).iterdir():
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                # Parse hanya frontmatter untuk description + triggers
                meta = parse_frontmatter(skill_md)
                registry[meta['name']] = {
                    'path': skill_md,
                    'description': meta['description'],
                    'triggers': meta.get('triggers', [])
                }
        return registry

    def load(self, skill_name: str) -> str:
        """Load full content saat benar-benar dibutuhkan."""
        if skill_name not in self.registry:
            raise KeyError(f"Skill not found: {skill_name}")
        return self.registry[skill_name]['path'].read_text()

    def find_relevant(self, task: dict) -> list[str]:
        """Cari skills yang relevan — return names saja, belum load."""
        relevant = []
        for name, meta in self.registry.items():
            for trigger in meta['triggers']:
                if trigger.lower() in task['instruction'].lower():
                    relevant.append(name)
                    break
        return relevant
```

**Adapatasi untuk vibe-office:**
- Scan `~/.vibe-office/workers/*/SKILL.md` saat startup
- Simpan hanya frontmatter + path di registry (tidak full content)
- Load full SKILL.md hanya saat orchestrator butuh evaluate worker itu
- Hemat: ~500 tokens vs ~5000 tokens kalau semua di-inject ke system prompt

---

## Pelajaran 2 — Sub-Agent Context Isolation

DeerFlow eksplisit: **setiap sub-agent punya context terisolasi.**
Sub-agent tidak bisa lihat context main agent atau sub-agent lain.

```python
# DeerFlow architecture (LangGraph StateGraph)
# Lead agent → spawn sub-agents via StateGraph

from langgraph.graph import StateGraph, END

def build_agent_graph():
    graph = StateGraph(AgentState)

    graph.add_node("lead_agent", lead_agent_node)
    graph.add_node("sub_agent_research", sub_agent_node("research"))
    graph.add_node("sub_agent_code", sub_agent_node("code"))
    graph.add_node("synthesize", synthesize_node)

    graph.add_conditional_edges(
        "lead_agent",
        decide_next_step,
        {
            "spawn_research": "sub_agent_research",
            "spawn_code": "sub_agent_code",
            "synthesize": "synthesize",
            "done": END,
        }
    )

    return graph.compile()
```

Kenapa LangGraph menarik untuk vibe-office:
- **State machine yang bisa di-resume** — crash di tengah, state tersimpan
- **Visualisasi graph** — debug flow orchestrator lebih mudah
- **Parallel execution** built-in — `graph.add_node` dengan async nodes

**Apakah vibe-office perlu LangGraph?** Tidak wajib untuk Fase 1-3.
AR Orchestrator bisa pakai DuckDB checkpoint yang sudah kita design.
Tapi kalau di Fase 4 orchestrator makin kompleks, LangGraph bisa jadi backbone.

---

## Pelajaran 3 — Context Engineering Agresif

DeerFlow manage context sangat agresif untuk long-running tasks:

```python
# Pattern dari DeerFlow context engineering:

class ContextManager:
    def __init__(self, max_tokens: int = 100_000):
        self.max_tokens = max_tokens
        self.compression_threshold = 0.80

    async def manage(self, messages: list, workspace_path: str) -> list:
        current_tokens = count_tokens(messages)

        if current_tokens > self.max_tokens * self.compression_threshold:
            # 1. Identify completed sub-tasks
            completed = [m for m in messages if is_completed_subtask(m)]

            # 2. Summarize dan offload ke filesystem
            for task in completed:
                summary = await llm.summarize(task)
                summary_path = workspace_path / f"summary_{task['id']}.md"
                summary_path.write_text(summary)

                # Replace dengan reference, bukan full content
                task['content'] = f"[Completed: see {summary_path}]"

            # 3. Kalau masih terlalu besar, compress lebih agresif
            if count_tokens(messages) > self.max_tokens * 0.60:
                messages = compress_to_summary(messages)

        return messages
```

Perbedaan dari hermes compression (yang kita sudah dokument):
- DeerFlow offload ke **filesystem** (bukan cuma summarize in-memory)
- Summaries disimpan di `/mnt/user-data/workspace/` yang persisten
- Agent bisa reference kembali summary files kalau butuh detail

Adaptasi untuk vibe-office: simpan summaries ke Ring 2 (SQLite), bukan filesystem — lebih structured dan bisa di-query.

---

## Pelajaran 4 — Embedded Python Client

DeerFlow bisa dipakai sebagai library tanpa full HTTP server:

```python
from src.client import DeerFlowClient

client = DeerFlowClient()

# Ini relevan untuk vibe-office backend:
# Kalau mau embed DeerFlow sebagai orchestration engine
# tanpa setup HTTP server terpisah

response = client.chat("buatin fungsi HTTP GET", thread_id="session-123")

# Streaming responses (SSE protocol)
for event in client.stream("implement async retry logic"):
    if event.type == "messages-tuple" and event.data.get("type") == "ai":
        print(event.data["content"])
        # → kirim ke WebSocket sebagai tv_update event

# List available skills
skills = client.list_skills()  # {"skills": [...]}

# Update skill status
client.update_skill("rust-coding", enabled=True)
```

Ini menarik untuk Fase 3: vibe-office backend tidak perlu implement
orchestration dari nol — bisa embed DeerFlow client sebagai engine,
lalu wrapper-nya yang kirim WebSocket events ke game UI.

---

## Pelajaran 5 — Sandbox Integration (Preview untuk OpenSandbox)

DeerFlow sandbox structure:
```
/mnt/user-data/
├── uploads/      ← user uploads files here
├── workspace/    ← agents' working directory (Docker isolated)
└── outputs/      ← final deliverables
```

Setiap task runs di Docker container terisolasi. Agent read/write/execute
di dalam container, tidak bisa touch host system.

DeerFlow support tiga sandbox modes:
- Local (langsung di host — dev only)
- Docker (isolated containers — recommended)
- Docker + Kubernetes (distributed, production scale)

Ini langsung connect ke OpenSandbox (file terpisah) untuk vibe-office.

---

## Decision: Pakai DeerFlow atau Bangun Sendiri?

**Fase 1-2:** Bangun sendiri — game shell + dummy backend cukup sederhana
**Fase 3:** Baca DeerFlow source dalam-dalam sebelum implement orchestrator
**Fase 4:** Evaluasi apakah embed DeerFlow client worth it vs custom

Endpoint yang paling worth dibaca di DeerFlow source:
```
backend/src/         ← Python FastAPI backend
backend/src/agents/  ← agent loop implementation
backend/src/skills/  ← skill loader logic
backend/CLAUDE.md    ← arsitektur overview (baca ini dulu)
```
