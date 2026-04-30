# Desktop — Session Management

---

## File Structure

```
~/.vibe-office/
├── projects.json            ← daftar semua project
├── workers.json             ← worker profiles global
├── sessions/
│   └── {session_id}.json   ← state per session
├── rings/
│   └── {project_id}/
│       ├── ring1.duckdb     ← hot memory (satu per project!)
│       └── ring2/           ← warm storage
└── skins/                  ← custom sprite sheets
```

## Session Schema

```typescript
interface Session {
  id: string; project_id: string
  status: 'active'|'paused'|'completed'
  worker_positions: Record<string, TileCoord>
  worker_states: Record<string, WorkerState>
  pending_tasks: Task[]
  chat_history: Message[]
  ring1_path: string
}
```

## Save (Atomic Write — Wajib!)

```python
import os, json, tempfile

async def save_session(session: dict, path: str):
    # Tulis ke .tmp dulu — kalau crash di tengah, file lama masih intact
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(session, f)
    os.rename(tmp, path)  # atomic pada semua OS modern
```

## Resume

```python
async def resume_session(session: dict):
    pending = session['pending_tasks']
    for task in pending:
        if task['status'] == 'in_progress':
            task['status'] = 'pending'  # restart dari awal
        await task_queue.put(task)
```

## Multi-Project: Switch

```typescript
async function switchProject(newId: string) {
  await saveCurrentSession()
  await ws.send(JSON.stringify({ type: 'command', command: 'switch_project', args: [newId] }))
  const session = await loadLastSession(newId)
  if (session) { restoreCanvas(session); restoreChat(session.chat_history) }
  else resetToInitial()
}
```

**Aturan:** Satu DuckDB per project. Tidak boleh dua project pakai Ring 1 yang sama.
