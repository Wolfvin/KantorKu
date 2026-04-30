# Backend — WebSocket Events

> **Konteks untuk session baru:**
> Fase 1-2 pakai simulated Python backend (tidak ada AI).
> Fase 3+ backend Python yang nyata dengan AI workers.
> File ini berisi: schema event, simulated backend lengkap, dan reconnect logic.
>
> **REFERENSI PENTING sebelum implement (Fase 1):**
> Baca `src/gateway/event-parser.ts` dari openclaw-office sebelum finalize schema:
> `git clone https://github.com/WW-AI-Lab/openclaw-office /tmp/openclaw-office-ref`
> Mereka sudah proven lifecycle event → visual state mapping production-ready.
> Schema kita di bawah sudah terinspirasi pattern yang sama, tapi cross-check
> dengan event-parser.ts mereka untuk edge cases yang mungkin kita miss.
> Juga baca `mock-adapter.ts` untuk cara simulate data yang clean — langsung
> applicable untuk Fase 1 simulated backend kita.

---

## Dua Endpoints

```
ws://localhost:8765/game    ← Python PUSH ke game UI (satu arah)
ws://localhost:8765/client  ← Terima pesan dari chat panel (bidirectional)
```

---

## Event Types: Backend → Game UI

```typescript
// webview-ui/src/types.ts

export type WorkerFSM =
  | 'idle' | 'working' | 'meeting' | 'reviewing'
  | 'resting' | 'blocked' | 'done'

export type RoomId =
  | 'meeting_room' | 'workstation' | 'break_room' | 'dormitory'
  | 'server_room' | 'ceo_office' | 'library_room' | 'lab_room'
  | 'design_studio' | 'rooftop'

export type WorkerEvent =
  | { type: 'state_change';   worker_id: string; new_state: WorkerFSM }
  | { type: 'move_to_room';   worker_id: string; target_room: RoomId; reason: string }
  | { type: 'progress';       worker_id: string; progress: number; message: string }
  | { type: 'speech_bubble';  worker_id: string; text: string; color: string; duration_ms: number }
  | { type: 'tv_update';      task_name: string|null; worker_statuses: WorkerStatus[]; log_entry: string|null }
  | { type: 'blocked';        worker_id: string; reason: string; tier: 1|2|3 }
  | { type: 'hire';           worker_profile: WorkerProfile }
  | { type: 'fire';           worker_id: string }
  | { type: 'deactivate';     worker_id: string }
  | { type: 'activate';       worker_id: string }
  | { type: 'vila_unlock';    room_id: RoomId; room_name: string }
  | { type: 'lora_activated'; worker_id: string; lora_name: string; delta: string }
  | { type: 'skill_updated';  worker_id: string; what_changed: string }
  | { type: 'connection_lost' }

export interface WorkerStatus {
  worker_id: string
  fsm: WorkerFSM
  task: string|null
  progress: number
}

export interface WorkerProfile {
  id: string
  display_name: string
  role: string
  badge_emoji: string
  personality: { tone: string; catchphrase: string }
}
```

## Event Types: Chat Panel → Backend

```typescript
export type ClientMessage =
  | { type: 'new_task';       message: string }
  | { type: 'command';        command: string; args: string[] }
  | { type: 'tier3_response'; task_id: string; action: 'new_instruction'|'skip'|'stop'; instruction?: string }
```

---

## Simulated Backend (Fase 1-2) — Lengkap

Simpan sebagai `backend/simulate.py`. Jalankan sebelum `cargo tauri dev`.

```python
# backend/simulate.py
import asyncio, websockets, json, random, time

# Semua workers dengan naming baru
WORKERS = [
    {'id': 'conductor',    'display_name': 'The Boss',  'badge_emoji': '👔', 'role': 'conductor'},
    {'id': 'coder_rust',   'display_name': 'Rusty',     'badge_emoji': '🦀', 'role': 'coder_rust'},
    {'id': 'coder_css',    'display_name': 'Pixel',     'badge_emoji': '🎨', 'role': 'coder_css'},
    {'id': 'coder_js',     'display_name': 'Spark',     'badge_emoji': '⚡', 'role': 'coder_js'},
    {'id': 'tester',       'display_name': 'T-Rex',     'badge_emoji': '🧪', 'role': 'tester'},
    {'id': 'auditor',      'display_name': 'Eagle',     'badge_emoji': '🔍', 'role': 'auditor'},
    {'id': 'scribe',       'display_name': 'Quill',     'badge_emoji': '📝', 'role': 'scribe'},
    {'id': 'sentinel',     'display_name': 'Shield',    'badge_emoji': '🛡️', 'role': 'sentinel'},
    {'id': 'chronicler',   'display_name': 'Archive',   'badge_emoji': '📚', 'role': 'chronicler'},
    {'id': 'scout',        'display_name': 'Radar',     'badge_emoji': '📡', 'role': 'scout'},
    {'id': 'intake',       'display_name': 'Gate',      'badge_emoji': '🚪', 'role': 'intake'},
    {'id': 'curator',      'display_name': 'Sage',      'badge_emoji': '🧙', 'role': 'curator'},
    {'id': 'trainer',      'display_name': 'Forge',     'badge_emoji': '⚙️', 'role': 'trainer'},
    {'id': 'steward',      'display_name': 'Tidy',      'badge_emoji': '🧹', 'role': 'steward'},
    {'id': 'designer',     'display_name': 'Vision',    'badge_emoji': '✏️', 'role': 'designer'},
]

ROOMS  = ['workstation', 'meeting_room', 'break_room', 'dormitory', 'server_room']
STATES = ['idle', 'working', 'meeting', 'reviewing', 'resting', 'done']

connected_clients: set = set()

async def handler(websocket):
    connected_clients.add(websocket)
    try:
        # 1. Hire semua workers saat connect
        for w in WORKERS:
            await websocket.send(json.dumps({'type': 'hire', 'worker_profile': w}))
            await asyncio.sleep(0.1)

        # 2. Simulate activity loop
        while True:
            worker = random.choice(WORKERS)
            events = [
                {
                    'type': 'state_change',
                    'worker_id': worker['id'],
                    'new_state': random.choice(STATES),
                },
                {
                    'type': 'move_to_room',
                    'worker_id': worker['id'],
                    'target_room': random.choice(ROOMS),
                    'reason': 'simulated',
                },
                {
                    'type': 'progress',
                    'worker_id': worker['id'],
                    'progress': random.random(),
                    'message': random.choice([
                        'writing HTTP client...',
                        'checking borrow checker...',
                        'running tests...',
                        'generating docs...',
                        'analyzing codebase...',
                    ]),
                },
                {
                    'type': 'speech_bubble',
                    'worker_id': worker['id'],
                    'text': random.choice([
                        'borrow checker says no.',
                        'all green.',
                        'compiled. shipped.',
                        'researching...',
                        '...',
                    ]),
                    'color': random.choice(['#00aaff', '#10b981', '#f59e0b']),
                    'duration_ms': 3000,
                },
                {
                    'type': 'tv_update',
                    'task_name': 'implement async HTTP client',
                    'worker_statuses': [
                        {'worker_id': w['id'], 'fsm': 'idle', 'task': None, 'progress': 0}
                        for w in WORKERS[:4]
                    ],
                    'log_entry': f'[{worker["display_name"]}] {random.choice(["started task", "task done", "reviewing"])}',
                },
            ]
            await websocket.send(json.dumps(random.choice(events)))
            await asyncio.sleep(random.uniform(0.8, 2.5))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)

async def main():
    async with websockets.serve(handler, 'localhost', 8765):
        print('Simulated backend running on ws://localhost:8765')
        print('Press Ctrl+C to stop')
        await asyncio.Future()

if __name__ == '__main__':
    asyncio.run(main())
```

**Install requirements:**
```bash
pip install websockets
python3 backend/simulate.py
```

---

## Reconnect dengan Exponential Backoff (webview-ui)

Sudah ada di `canvas-game.md` — `workerWatcher.ts` handle ini.
Cap: 1s → 1.5s → 2.25s → ... → max 10s.

---

## Dari Simulated ke Real Backend (Fase 3)

Saat backend Python AI sudah jalan, cukup ganti `simulate.py` dengan `server.py`.
Tidak ada perubahan di frontend — schema event sama persis.

```bash
# Fase 1-2:
python3 backend/simulate.py

# Fase 3+:
python3 backend/server.py   # real AI workers
```

`server.py` implement schema yang sama, tapi events datang dari AI yang nyata.
