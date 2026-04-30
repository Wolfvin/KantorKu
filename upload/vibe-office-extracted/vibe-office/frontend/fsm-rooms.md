# Frontend — FSM & Rooms

> **Konteks untuk session baru:**
> File ini define layout kantor (zone JSON) dan FSM 7 states.
> Semua nama worker sudah diupdate ke naming baru (2026-03-17).
> Design studio room ditambahkan. Vila rooms dikembangkan dengan unlock logic.

---

## FSM 7 States

| State | Ruangan Default | Animasi Sprite | Trigger Masuk |
|-------|----------------|----------------|---------------|
| `idle` | break_room / wander | walk pelan random | tidak ada task aktif |
| `working` | workstation / lab / design_studio | typing cepat (row 4) | task di-assign |
| `meeting` | meeting_room | seated bob | conductor briefing |
| `reviewing` | workstation | reading lambat (row 5) | post-coding pipeline |
| `resting` | dormitory | sleeping (row 6) | self-retry / timeout |
| `blocked` | posisi saat itu | gemetar ±1px + speech bubble merah | recovery tier 2 gagal |
| `done` | break_room | idle santai + speech bubble hijau | task selesai |

### Transisi State

```
idle ──task assigned──→ meeting ──briefed──→ working ──selesai──→ done ──reset──→ idle
                                                 ↓ error kecil
                                             resting (self-retry max 2x)
                                                 ↓ masih gagal
                                             blocked ──user respond──→ working
                                                 ↓ user skip
                                                idle
```

### Efek Visual per State

```typescript
function renderWorkerOverlay(worker: WorkerState, ctx: CanvasRenderingContext2D) {
  // Progress bar — hanya saat working atau reviewing
  if (worker.fsm === 'working' || worker.fsm === 'reviewing') {
    drawProgressBar(ctx, worker.tilePos, worker.progress)
  }

  // Shake effect — hanya saat blocked
  if (worker.fsm === 'blocked') {
    const shake = Math.sin(Date.now() / 80) * 1.2  // ±1.2px
    ctx.translate(shake, 0)
  }

  // State badge warna
  const BADGE_COLOR: Record<string, string> = {
    idle:      '#6b7280',  // abu
    working:   '#3b82f6',  // biru
    meeting:   '#8b5cf6',  // ungu
    reviewing: '#f59e0b',  // kuning
    resting:   '#6b7280',  // abu
    blocked:   '#ef4444',  // merah
    done:      '#10b981',  // hijau
  }
  drawStateBadge(ctx, worker.tilePos, BADGE_COLOR[worker.fsm])
}
```

---

## Zone Layout JSON (Updated — semua nama baru)

Zone adalah area tile dengan nama, batas, kapasitas, dan daftar worker yang boleh masuk.

```json
{
  "zones": {
    "meeting_room": {
      "bounds": {"x": 1,  "y": 1,  "w": 14, "h": 8},
      "capacity": 15,
      "allowed": ["all"],
      "description": "Semua workers bisa, TV screen di sini"
    },
    "workstation": {
      "bounds": {"x": 16, "y": 1,  "w": 12, "h": 10},
      "capacity": 8,
      "allowed": ["coder_rust","coder_css","coder_js","coder_python",
                  "tester","auditor","scribe"],
      "description": "Zona coding utama"
    },
    "break_room": {
      "bounds": {"x": 1,  "y": 10, "w": 10, "h": 8},
      "capacity": 20,
      "allowed": ["all"],
      "description": "Default saat idle, steward tinggal di sini"
    },
    "dormitory": {
      "bounds": {"x": 12, "y": 10, "w": 10, "h": 8},
      "capacity": 10,
      "allowed": ["all"],
      "description": "Workers blocked atau resting"
    },
    "server_room": {
      "bounds": {"x": 30, "y": 1,  "w": 8,  "h": 8},
      "capacity": 4,
      "allowed": ["sentinel","chronicler","scout"],
      "description": "Banyak monitor, scout tinggal di sini"
    },
    "ceo_office": {
      "bounds": {"x": 30, "y": 10, "w": 8,  "h": 8},
      "capacity": 1,
      "allowed": ["conductor"],
      "description": "Hanya conductor. Kamu bisa masuk sebagai client."
    },
    "library_room": {
      "bounds": {"x": 40, "y": 1,  "w": 8,  "h": 8},
      "capacity": 2,
      "allowed": ["curator"],
      "unlock_after": 10,
      "description": "Viola room. curator tinggal di sini."
    },
    "lab_room": {
      "bounds": {"x": 40, "y": 10, "w": 8,  "h": 8},
      "capacity": 1,
      "allowed": ["trainer"],
      "unlock_after": 50,
      "description": "Viola room. trainer di sini, ada GPU icon di dinding."
    },
    "design_studio": {
      "bounds": {"x": 50, "y": 1,  "w": 10, "h": 12},
      "capacity": 4,
      "allowed": ["designer","archivist","stylist","compositor"],
      "unlock_after": 10,
      "description": "Viola room. Ada monitor besar — klik untuk masuk FectTral UI."
    }
  }
}
```

### Zone-Aware Pathfinding

```typescript
function canWorkerEnterTile(
  worker: WorkerState,
  tile: TileCoord,
  zones: ZoneConfig
): boolean {
  const zone = getZoneForTile(tile, zones)
  if (!zone) return isWalkable(tile)  // tile di luar semua zone = bebas

  // Cek apakah zone sudah unlock
  if (zones[zone].unlock_after && getTotalTasksDone() < zones[zone].unlock_after) {
    return false
  }

  const allowed = zones[zone].allowed
  if (allowed.includes('all')) return isWalkable(tile)
  return allowed.includes(worker.role) && isWalkable(tile)
}

function getRoomEntryTile(roomId: string, zones: ZoneConfig): TileCoord {
  const b = zones[roomId].bounds
  // Entry tile = sisi bawah-tengah room
  return { x: Math.floor(b.x + b.w / 2), y: b.y + b.h - 1 }
}
```

---

## Vila Rooms — Unlock System

```typescript
interface VilaRoom {
  id: string
  unlock_after: number       // total tasks sukses
  name: string
  description: string
  unlock_animation: string   // 'confetti' | 'glow_pulse' | 'door_open'
  ambient_sound: string      // dari sound-design.md
}

const VILA_ROOMS: VilaRoom[] = [
  {
    id: 'library_room',
    unlock_after: 10,
    name: 'Library',
    description: 'curator pindah ke sini. Rak buku pixel art.',
    unlock_animation: 'door_open',
    ambient_sound: 'page_turn_ambient',
  },
  {
    id: 'design_studio',
    unlock_after: 10,
    name: 'Design Studio',
    description: 'designer dan kru design pindah ke sini.',
    unlock_animation: 'glow_pulse',
    ambient_sound: 'design_hum',
  },
  {
    id: 'lab_room',
    unlock_after: 50,
    name: 'Lab',
    description: 'trainer pindah ke sini. Ada GPU icon di dinding.',
    unlock_animation: 'confetti',
    ambient_sound: 'server_hum',
  },
  {
    id: 'rooftop',
    unlock_after: 100,
    name: 'Rooftop',
    description: 'Outdoor area lantai 2. Trainer present hasil LoRA baru. Celebration zone.',
    unlock_animation: 'confetti',
    ambient_sound: 'wind_ambient',
  },
]

function checkVilaUnlocks(tasksDone: number): VilaRoom[] {
  return VILA_ROOMS.filter(r => r.unlock_after === tasksDone)
  // Caller handle: play animation, send narrator event, update zone config
}
```

**Unlock flow:**
```
Task ke-10 selesai
  → checkVilaUnlocks(10) → [library_room, design_studio]
  → narrator: "🎉 Library Room unlocked! curator moved in."
  → play door_open animation pada tile pintu library
  → update zone config: library_room.unlocked = true
  → curator bergerak dari break_room ke library_room
```

---

## Design Studio — Monitor Interaction

Monitor besar di design studio adalah special tile. Ketika player (kamu) klik:

```typescript
// webview-ui/src/tileMap.ts — tambahkan ke handleClick
function handleTileClick(tile: TileCoord) {
  if (isMonitorTile(tile) && getZoneForTile(tile) === 'design_studio') {
    enterDesignStudio()
    return
  }
  // ... normal click handling
}

function isMonitorTile(tile: TileCoord): boolean {
  // Monitor besar = tile khusus yang ditandai di layout JSON
  return layoutData.special_tiles?.monitor === `${tile.x},${tile.y}`
}
```

Animasi transisi ke FectTral UI: lihat `design/design-system.md`.

---

## Rooftop Room

Fungsi final: lantai 2 viola zone — ceremony room untuk trainer present LoRA, outdoor meeting, project celebration. Lihat desktop/room-editor.md.
**Fungsi final (diputuskan v4.7):**
- Outdoor celebration zone — unlock saat 50 tasks selesai
- Trainer present hasil LoRA baru ke semua workers di sini
- Meeting informal yang lebih casual dari meeting room
- Bird's-eye project stats overlay saat di rooftop
- Lokasi di lantai 2 (lihat desktop/room-editor.md multi-lantai)


## Lab Room + Library Room — Visual Connection

Dua ruangan terpisah tapi terhubung secara visual:

```
┌─────────────────┐  shared wall  ┌─────────────────┐
│   LIBRARY ROOM  │───── kaca ────│    LAB ROOM      │
│                 │   (window     │                  │
│  📚 bookshelf   │    panel)     │  💊 stasis pods  │
│  🖥 komputer    │               │  🖥🖥🖥 servers  │
│     curator     │               │     trainer      │
└─────────────────┘               └─────────────────┘
```

**Kaca/jendela antar ruangan:**
- Tile khusus di shared wall: `window_panel` (tembus pandang)
- Dari library room kamu bisa lihat silhouette trainer di lab
- Dari lab room kamu bisa lihat curator di komputer
- Tidak bisa lewat — hanya visual connection
- Efek: slight transparency overlay di tile kaca

---

## Lab Room — Elemen Visual

**1. Stasis Chamber / Stasis Tank (kiri ruangan)**

```
Tile: 2×3 (lebar × tinggi)
Glow warna: berdasarkan status worker di dalamnya

Status visual:
  idle (data belum cukup):
    → kapsul gelap, worker frozen inside, minimal glow
    → tooltip hover: "coder_rust — 124/200 episodes"

  ready (data cukup, belum di-train):
    → kapsul berpendar biru-cyan, slow pulse animation
    → partikel kecil naik dari bawah kapsul
    → tooltip: "coder_rust — READY TO TRAIN ✓"
    → KLIK → modal: pilih domain LoRA → confirm → trainer mulai

  training (sedang di-train):
    → kapsul penuh glow, animasi bubble di dalam cairan
    → progress bar di luar kapsul (bawah)
    → warna shift: biru → ungu → biru (cycle)
    → TIDAK bisa diklik saat training

  complete (training selesai, menunggu eval):
    → kapsul hijau bright, worker pose berubah (pose "upgraded")
    → efek burst singkat saat pertama kali complete
```

**2. Server Machines (kanan ruangan)**

```
Tile: 1×2 per server, 4–6 server berjejer
Visual: blinking LED dots (animasi 2 frame flip)
KLIK salah satu server → buka NovaNotes panel (Knowledge Vault)
  Panel muncul sebagai windowed overlay (70% screen)
  Bisa di-maximize ke fullscreen
```

**3. Komputer Trainer (tengah ruangan)**

```
Trainer worker duduk di sini saat idle
KLIK → walk-to-desk sequence → fade in Lab overlay (FectTral)
Lab overlay: brain visualization + training monitor (lihat brain-visualization.md)
```

---

## Library Room — Elemen Visual

**1. Komputer Curator (meja tengah)**

```
Curator worker duduk di sini saat idle
KLIK → walk-to-desk sequence → fade in Library overlay
Library overlay: Knowledge Browser (lihat backend/knowledge-ingestion.md)
  - Domain list dengan threshold progress bar
  - Episode list dengan exclude toggle
  - SKILL.md viewer
```

**2. Bookshelf (dinding)**

```
Tile dekorasi — bisa diklik untuk flavor text
Juga dipakai sebagai "read_book" behavior saat needs.social rendah
```

**3. NovaNotes shortcut**

```
Di library room ada juga shortcut ke NovaNotes
(berbeda dari server machine di lab — ini lebih personal/curator's notes)
```
