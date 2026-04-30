# Frontend — Canvas Game (pixel-agents fork)

> **Konteks untuk session baru:**
> Game engine sudah ada — fork pixel-agents (MIT, 3.6k stars).
> Kita TIDAK build dari nol. Swap 2 file, extend 4 hal, reuse sisanya.
> File ini adalah panduan Fase 1: dari clone sampai dummy workers bergerak.

---

## Quick Start Fase 1

```bash
# 1. Fork pixel-agents
git clone https://github.com/pablodelucca/pixel-agents vibe-office
cd vibe-office

# 2. Install dependencies
cd webview-ui && npm install && cd ..

# 3. Setup Tauri v2
cargo install tauri-cli
# tambahkan ke webview-ui/package.json:
# "scripts": { "tauri": "tauri" }

# 4. Jalankan simulated backend (Python, Fase 1)
python3 backend/simulate.py   # lihat websocket-events.md

# 5. Dev server
cargo tauri dev
# → browser otomatis buka di http://localhost:1420
# → workers muncul, bergerak random berdasarkan WebSocket events
```

---

## Apa yang Diambil dari pixel-agents

**Repo:** https://github.com/pablodelucca/pixel-agents — MIT, 3.6k stars.

Lihat langsung struktur repo sebelum mulai:
```bash
git clone https://github.com/pablodelucca/pixel-agents /tmp/pixel-agents-ref
ls /tmp/pixel-agents-ref/webview-ui/src/
# tileMap.ts, renderer.ts, gameLoop.ts, layoutEditor/, sprites/, ...
```

### Reuse 100% (jangan diubah)
```
tileMap.ts          BFS pathfinding, walkability grid 16×16
renderer.ts         Canvas 2D, z-sort: y + TILE_SIZE/2 + 0.5
gameLoop.ts         requestAnimationFrame loop
layoutEditor/       paint/erase/place tiles, undo 50 level, JSON export/import
sprites/            sprite sheet loader, animation frame system
speechBubble.ts     speech bubble render + lifetime
zoomHandler.ts      mouse wheel zoom, clamp min/max
```

### Swap (2 file — ini yang berubah)

**File 1: `agentWatcher.ts` → `workerWatcher.ts`**

Pixel-agents watch file JSONL dari VS Code. Kita ganti dengan WebSocket:

```typescript
// webview-ui/src/workerWatcher.ts
import { workerManager } from './workerManager'

let ws: WebSocket | null = null
let retryDelay = 1000

export function connectWorkerBackend() {
  ws = new WebSocket('ws://localhost:8765/game')

  ws.onopen = () => {
    retryDelay = 1000
    console.log('[workerWatcher] connected to backend')
  }

  ws.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data)
      workerManager.handleEvent(event)
    } catch (err) {
      console.warn('[workerWatcher] bad event:', e.data)
    }
  }

  ws.onclose = () => {
    console.warn('[workerWatcher] disconnected, retry in', retryDelay, 'ms')
    setTimeout(connectWorkerBackend, retryDelay)
    retryDelay = Math.min(retryDelay * 1.5, 10_000)  // exponential backoff cap 10s
  }

  ws.onerror = () => ws?.close()
}
```

**File 2: `extension.ts` + `SquadPodViewProvider.ts` → dihapus**

Cabut seluruh VS Code extension host. Ganti semua `vscode.*` calls:

```typescript
// LAMA (pixel-agents):
vscode.postMessage({ type: 'saveLayout', data })
vscode.getState()
vscode.setState(data)
window.addEventListener('message', handler)

// BARU (vibe-office):
ws.send(JSON.stringify({ type: 'command', command: 'save_layout', data }))
localStorage.getItem('vibe-office-layout')
localStorage.setItem('vibe-office-layout', JSON.stringify(data))
ws.onmessage = (e) => handleBackendEvent(JSON.parse(e.data))
```

### Extend (4 hal)

**1. FSM: 3 states → 7 states**
Pixel-agents punya: idle, walking, talking.
Vibe-office butuh: idle, working, meeting, reviewing, resting, blocked, done.
Detail lengkap di `fsm-rooms.md`.

**2. Rooms: tambah preset layout JSON dengan 8 zona**
Pixel-agents punya free-form tile placement.
Vibe-office punya zona dengan nama dan access control.
Detail di `fsm-rooms.md`.

**3. Renderer: tambah overlay UI**
- TV screen di meeting room (posisi fixed relative ke tile tertentu)
- Progress bar di atas worker saat `working`/`reviewing`
- Name badge di bawah sprite
- Blocked visual: shake animation ±1px setiap 4 frame
Detail di `ui-overlays.md`.

**4. TileMap: zone-aware pathfinding**
Worker hanya bisa masuk zona yang diizinkan berdasarkan role.
`conductor` hanya bisa ke CEO office. `scout` hanya ke server room.
Detail di `fsm-rooms.md`.

---

## WorkerManager — State Machine Central

File baru yang tidak ada di pixel-agents. Ini yang connect WebSocket events
ke game state:

```typescript
// webview-ui/src/workerManager.ts
import type { WorkerEvent } from './types'

export interface WorkerState {
  id: string
  displayName: string
  role: string
  badgeEmoji: string
  fsm: 'idle'|'working'|'meeting'|'reviewing'|'resting'|'blocked'|'done'
  room: string
  tilePos: { x: number; y: number }
  progress: number           // 0.0–1.0, hanya relevan saat working/reviewing
  speechBubble: string|null
  taskName: string|null
}

const workers = new Map<string, WorkerState>()

export const workerManager = {
  handleEvent(event: WorkerEvent) {
    switch (event.type) {

      case 'state_change': {
        const w = workers.get(event.worker_id)
        if (w) w.fsm = event.new_state
        break
      }

      case 'move_to_room': {
        const w = workers.get(event.worker_id)
        if (w) {
          w.room = event.target_room
          // pathfinding akan handle animasi jalan ke tile tujuan
          requestMoveTo(w, getRoomEntryTile(event.target_room))
        }
        break
      }

      case 'progress': {
        const w = workers.get(event.worker_id)
        if (w) {
          w.progress = event.progress
          w.taskName = event.message
        }
        break
      }

      case 'speech_bubble': {
        const w = workers.get(event.worker_id)
        if (w) {
          w.speechBubble = event.text
          setTimeout(() => { if (w) w.speechBubble = null }, event.duration_ms)
        }
        break
      }

      case 'hire': {
        workers.set(event.worker_profile.id, {
          ...event.worker_profile,
          fsm: 'idle',
          room: 'break_room',
          tilePos: getDoorTile(),   // spawn di pintu kantor
          progress: 0,
          speechBubble: null,
          taskName: null,
        })
        break
      }

      case 'fire': {
        workers.delete(event.worker_id)
        break
      }
    }
  },

  getAll(): WorkerState[] {
    return Array.from(workers.values())
  },

  get(id: string): WorkerState|undefined {
    return workers.get(id)
  }
}
```

---

## Sprite Sheet Format

```
256×64px per worker (16px per tile × 4 tiles wide, 7 rows)
Row 0: walk_down   — 4 frames (pixel-agents original)
Row 1: walk_left   — 4 frames
Row 2: walk_right  — 4 frames
Row 3: walk_up     — 4 frames
Row 4: typing      — 4 frames (tambahan: saat state=working)
Row 5: reading     — 4 frames (tambahan: saat state=reviewing)
Row 6: sleeping    — 2 frames (tambahan: saat state=resting/blocked)
```

File naming: `workers/{worker_id}.png`
Contoh: `workers/coder_rust.png`, `workers/conductor.png`

Generate sprites: lihat `assets/sprite-pipeline.md`.

---

## Pixel-Perfect CSS (wajib)

```css
/* webview-ui/src/styles/global.css */
html, canvas {
  image-rendering: pixelated;
  image-rendering: crisp-edges;   /* Firefox */
}
```

Tanpa ini semua sprite blur saat di-zoom.

---

## Struktur File Final (setelah swap + extend)

```
webview-ui/src/
├── main.ts                  ← entry point, init semua
├── workerWatcher.ts         ← NEW: WebSocket → workerManager (ganti agentWatcher)
├── workerManager.ts         ← NEW: state machine central
├── tileMap.ts               ← REUSE dari pixel-agents
├── renderer.ts              ← EXTEND: tambah overlay renders
├── gameLoop.ts              ← REUSE dari pixel-agents
├── overlays/
│   ├── tvScreen.ts          ← NEW: TV overlay di meeting room
│   ├── statusPopup.ts       ← NEW: klik worker → popup
│   └── progressBar.ts       ← NEW: bar di atas worker saat working
├── layoutEditor/            ← REUSE dari pixel-agents (layout kantor)
├── sprites/                 ← REUSE dari pixel-agents (loader)
├── speechBubble.ts          ← REUSE dari pixel-agents
├── types.ts                 ← NEW: WebSocket event types
└── styles/
    └── global.css           ← pixelated rendering + base styles
```

---

## Troubleshooting Fase 1

**Workers tidak muncul setelah WebSocket connect:**
Cek apakah `simulate.py` running dan kirim event `hire` dulu sebelum `state_change`.

**Sprite blur:**
Pastikan CSS `image-rendering: pixelated` sudah ada. Cek juga canvas scale.

**WebSocket reconnect loop:**
Backend mungkin tidak jalan. Cek `python3 backend/simulate.py` di terminal terpisah.

**Pathfinding worker nyangkut:**
Cek zone bounds di `fsm-rooms.md` — tile target mungkin di luar walkable area.
