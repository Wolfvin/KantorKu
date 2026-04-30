# Backend — Agent Loop (dari learn-claude-code)

**Sumber:** https://github.com/shareAI-lab/learn-claude-code
MIT license, 23.1k stars. Baca ini sebelum mulai coding AI backend.

Repo ini adalah blueprint implementasi yang nyaris sempurna untuk AI backend
vibe-office. 12 sesi progressif, setiap sesi tambah satu mekanisme.

---

## Sesi yang Paling Relevan untuk Vibe-Office

### s01 — The Agent Loop (fondasi semua workers)
```python
def agent_loop(messages):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM,
            messages=messages, tools=TOOLS,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return  # selesai

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = TOOL_HANDLERS[block.name](**block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        messages.append({"role": "user", "content": results})
```
Setiap worker di vibe-office pakai loop ini. Tool handlers berbeda per worker.

### s03 — TodoWrite (task planning)
AR Orchestrator pakai pola ini: list steps dulu, baru execute.
Tanpa plan, agent drift. Ini kenapa CEO bikin execution_plan sebelum assign.

### s04 — Subagents (workers sebagai subagent)
```python
# Orchestrator spawn subagent untuk setiap worker
def spawn_worker(worker_id: str, task: dict):
    worker_messages = [{"role": "user", "content": format_task(task)}]
    # Fresh messages[] per worker — tidak campur context orchestrator
    return agent_loop(worker_messages, tools=WORKER_TOOLS[worker_id])
```
Setiap worker punya `messages[]` sendiri yang bersih — tidak mewarisi
context orchestrator. Ini yang bikin workers bisa fokus pada task-nya.

### s05 — Skill Loading (PENTING untuk context_worker)
```python
# Jangan inject knowledge ke system prompt di awal — terlalu mahal
# Inject via tool_result saat dibutuhkan
def load_skill(skill_name: str) -> str:
    with open(f"skills/{skill_name}.md") as f:
        return f.read()

# Tool handler
def get_skill(name: str):
    return load_skill(name)  # return ke LLM via tool_result
```
Pattern ini dipakai `context_worker` untuk inject GitNexus output
ke context rust_worker — load on demand, bukan semuanya di awal.

### s06 — Context Compact (wajib untuk long-running sessions)
Tiga-layer compression saat context mendekati limit:
1. Summarize messages[] yang lama jadi ringkasan singkat
2. Pertahankan system prompt dan N messages terakhir
3. Inject summary sebagai synthetic message
Tanpa ini, vibe-office tidak bisa jalan lebih dari ~20 task.

### s07 — Task System (DuckDB Ring 1 pattern)
```
file-based task graph dengan dependencies
→ kita ganti dengan DuckDB checkpoints
tapi dependency graph logic-nya sama persis
```

### s08 — Background Tasks
```python
# Daemon thread untuk background operations
# Kita pakai ini untuk: Ring 1→Ring 2 flush, Cognee sync
import threading

def background_flush():
    while True:
        time.sleep(5)
        flush_ring1_to_ring2()

threading.Thread(target=background_flush, daemon=True).start()
```

### s09-s10 — Agent Teams & Protocols
Orchestrator + workers = implementation dari s09-s10.
JSONL mailbox protocol untuk komunikasi antar agent.
Shutdown + plan approval FSM.

### s11 — Autonomous Agents
Workers bisa "scan the board" dan claim task sendiri kalau idle.
Di vibe-office: worker yang done ke break room, lalu scan pending tasks,
kalau ada yang match capability → request ke orchestrator.

### s12 — Worktree Isolation
Setiap project punya directory sendiri + DuckDB sendiri.
`task.id` bound ke `worktree_path` — tidak ada interference.

---

## Mapping learn-claude-code → Vibe-Office

| Session | Mekanisme | Dipakai di |
|---------|-----------|------------|
| s01 | Agent loop | Semua workers |
| s03 | TodoWrite / planning | AR Orchestrator |
| s04 | Subagents | Worker spawning |
| s05 | Skill loading | context_worker + GitNexus inject |
| s06 | Context compact | Long session management |
| s07 | Task graph | DuckDB Ring 1 checkpoint |
| s08 | Background tasks | Ring flush, Cognee sync |
| s09-s10 | Teams + protocols | Orchestrator ↔ workers |
| s11 | Autonomous | Workers claim tasks sendiri |
| s12 | Worktree isolation | Multi-project session |

---

## Quick Start (baca repo ini dulu!)

```bash
git clone https://github.com/shareAI-lab/learn-claude-code
cd learn-claude-code
pip install -r requirements.txt
cp .env.example .env  # isi ANTHROPIC_API_KEY

python agents/s01_agent_loop.py   # mulai dari sini
python agents/s09_agent_teams.py  # paling relevan untuk vibe-office
python agents/s12_worktree_task_isolation.py
```

Web platform interaktif: https://learn-claude-agents.vercel.app/en/s01/
