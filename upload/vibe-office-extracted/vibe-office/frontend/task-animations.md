# Frontend — Task Animations & Meeting Behaviors (Fase 3)

> **Konteks untuk session baru:**
> Dua sistem animasi:
>   1. Walk-to-desk: saat kamu klik ruangan tertentu (conductor, scout, trainer,
>      curator, designer), worker harus jalan dulu ke mejanya, duduk, buka laptop,
>      BARU overlay fade in. Immersive entry sequence.
>   2. Task animations: saat vibe coding berjalan, workers yang terlibat
>      melakukan animasi berbeda berdasarkan event type (meeting, argue, hacking, dll).
>      Semua rule-based — zero LLM calls.
> File terkait:
>   - `frontend/ui-overlays.md` → overlay FectTral yang di-trigger setelah walk-to-desk
>   - `frontend/fsm-rooms.md` → room tile positions

---

## Sistem 1 — Walk-to-Desk Entry Sequence

### Ruangan yang Punya Walk-to-Desk

```typescript
// Hanya ruangan "khusus" yang punya entry sequence
// Ruangan biasa (workstation, break room) → langsung buka overlay

const WALK_TO_DESK_ROOMS = new Set([
  'ceo_office',      // conductor
  'server_room',     // scout
  'lab_room',        // trainer
  'library_room',    // curator
  'design_studio',   // designer
])
```

### Sequence Flow

```
USER klik tile ruangan (mis. library_room)
  ↓
frontend: cek apakah room ada di WALK_TO_DESK_ROOMS
  ↓ YA
game emit event: "entry_requested" { room_id: 'library_room' }
  ↓
worker yang bersangkutan (curator) dapat target: desk_position[room_id]
  ↓
BFS pathfinding dari posisi curator sekarang → desk tile
  ↓
animasi berjalan: walk frames (sudah ada di pixel-agents)
  ↓ (tiba di desk — ~500–1500ms tergantung jarak)
animasi duduk: sit_down frame (1 frame, 300ms)
  ↓
animasi buka laptop: open_laptop frames (2 frames, 400ms)
  ↓
fade out game canvas: opacity 1→0 (300ms)
  ↓
fade in FectTral overlay: opacity 0→1 (300ms)
  ↓
overlay aktif — interaksi dimulai
```

### Implementasi

```typescript
// src/systems/room-entry.ts

interface DeskPosition {
  x: number
  y: number
  facing: 'up' | 'down' | 'left' | 'right'
}

// Posisi meja per ruangan — ini harus match tile map
const DESK_POSITIONS: Record<string, DeskPosition> = {
  'ceo_office':    { x: 12, y: 8,  facing: 'down' },
  'server_room':   { x: 28, y: 15, facing: 'right' },
  'lab_room':      { x: 42, y: 20, facing: 'left' },
  'library_room':  { x: 18, y: 30, facing: 'up' },
  'design_studio': { x: 35, y: 8,  facing: 'down' },
}

const ROOM_WORKER: Record<string, string> = {
  'ceo_office':    'conductor',
  'server_room':   'scout',
  'lab_room':      'trainer',
  'library_room':  'curator',
  'design_studio': 'designer',
}

export async function triggerRoomEntry(roomId: string): Promise<void> {
  if (!WALK_TO_DESK_ROOMS.has(roomId)) {
    // Langsung buka overlay tanpa walk sequence
    openOverlay(roomId)
    return
  }

  const workerId = ROOM_WORKER[roomId]
  const desk = DESK_POSITIONS[roomId]

  // 1. Worker jalan ke meja
  await walkWorkerTo(workerId, desk)

  // 2. Animasi duduk + buka laptop
  await playAnimation(workerId, 'sit_down', 300)
  await playAnimation(workerId, 'open_laptop', 400)

  // 3. Transition ke overlay
  await fadeOutCanvas(300)
  openOverlay(roomId)
  await fadeInOverlay(300)
}

async function walkWorkerTo(workerId: string, target: DeskPosition): Promise<void> {
  return new Promise((resolve) => {
    // Kirim ke pathfinding system
    emitWorkerMove(workerId, target.x, target.y, target.facing)

    // Listen untuk arrived event
    once(`worker_arrived_${workerId}`, resolve)

    // Timeout fallback: kalau 3 detik belum arrive (misal worker blocking)
    setTimeout(resolve, 3000)
  })
}
```

### Close Sequence (keluar overlay)

```typescript
// Saat user tutup overlay FectTral

export async function closeRoomOverlay(roomId: string): Promise<void> {
  // 1. Fade out overlay
  await fadeOutOverlay(200)

  // 2. Fade in game canvas
  await fadeInCanvas(300)

  // 3. Worker animasi tutup laptop + berdiri
  const workerId = ROOM_WORKER[roomId]
  if (workerId) {
    await playAnimation(workerId, 'close_laptop', 300)
    await playAnimation(workerId, 'stand_up', 200)
    // Worker kembali ke idle state
    setWorkerState(workerId, 'idle')
  }
}
```

---

## Sistem 2 — Task Animations saat Vibe Coding

### Event → Animasi Mapping

```typescript
// src/systems/task-animations.ts
// Semua rule-based — tidak ada LLM calls

interface AnimationEvent {
  workers: string[]       // siapa yang animasi
  animation: string       // animasi yang dimainkan
  room: string            // di ruangan mana
  duration_ms: number
  speech?: string         // speech bubble opsional
}

const TASK_EVENT_ANIMATIONS: Record<string, () => AnimationEvent[]> = {

  // ── Task diterima conductor ──
  'task_received': () => [{
    workers: ['conductor'],
    animation: 'stand_at_whiteboard',
    room: 'meeting_room',
    duration_ms: 2000,
    speech: 'alright team, listen up.'
  }],

  // ── Semua workers yang terlibat di-brief ──
  'task_briefing': () => {
    const workers = getActiveWorkers()  // siapa yang dapat task ini
    return [{
      workers: ['conductor', ...workers.slice(0, 3)],
      animation: 'walk_to_meeting_room',
      room: 'meeting_room',
      duration_ms: 1500,
    }, {
      workers: ['conductor'],
      animation: 'point_at_tv',
      room: 'meeting_room',
      duration_ms: 3000,
    }, {
      workers: workers.slice(0, 3),
      animation: 'look_at_tv',
      room: 'meeting_room',
      duration_ms: 3000,
    }]
  },

  // ── Coder mulai kerja ──
  'coder_working': () => [{
    workers: ['coder_rust'],          // atau coder yang relevan
    animation: 'type_fast',
    room: 'workstation',
    duration_ms: -1,                  // -1 = sampai event berikutnya
  }],

  // ── Scout lookup / research ──
  'scout_researching': () => [{
    workers: ['scout'],
    animation: 'rapid_typing',        // animasi ketik sangat cepat
    room: 'server_room',
    duration_ms: -1,
    speech: 'scanning...'
  }],

  // ── Error terjadi ──
  'task_error': () => {
    const randomAngryWorker = pickRandom(['coder_rust', 'tester', 'conductor'])
    return [{
      workers: [randomAngryWorker],
      animation: 'frustrated_bounce', // lompat kecil dua kali
      room: getWorkerRoom(randomAngryWorker),
      duration_ms: 1000,
      speech: pickRandom([
        'bruh.',
        'again???',
        'what the—',
        '...',
        'no no no',
      ])
    }, {
      workers: ['conductor'],
      animation: 'facepalm',
      room: getWorkerRoom('conductor'),
      duration_ms: 800,
    }]
  },

  // ── Security issue ditemukan sentinel ──
  'security_issue': () => [{
    workers: ['sentinel'],
    animation: 'rapid_typing',        // "hacking" vibe
    room: 'server_room',
    duration_ms: 2000,
    speech: '⚠ vulnerability detected'
  }, {
    workers: ['conductor'],
    animation: 'alarmed_walk',        // jalan cepat ke server room
    room: 'server_room',
    duration_ms: 1500,
  }],

  // ── Audit sedang berjalan ──
  'auditor_reviewing': () => [{
    workers: ['auditor'],
    animation: 'read_carefully',      // lean forward, tilt head
    room: 'workstation',
    duration_ms: -1,
    speech: 'hmm...'
  }],

  // ── Auditor dan coder argue (audit ada issue) ──
  'audit_issue': () => [{
    workers: ['auditor', 'coder_rust'],
    animation: 'face_each_other',
    room: 'meeting_room',
    duration_ms: 500,
  }, {
    workers: ['auditor'],
    animation: 'point_accusingly',
    room: 'meeting_room',
    duration_ms: 1200,
    speech: 'this is wrong.'
  }, {
    workers: ['coder_rust'],
    animation: 'defensive_gesture',
    room: 'meeting_room',
    duration_ms: 1200,
    speech: 'it compiled!'
  }],

  // ── Designer bekerja ──
  'designer_working': () => [{
    workers: ['designer', 'compositor'],
    animation: 'paint_on_tablet',    // tablet digital animasi
    room: 'design_studio',
    duration_ms: -1,
  }, {
    workers: ['stylist'],
    animation: 'study_mood_board',
    room: 'design_studio',
    duration_ms: -1,
  }],

  // ── Task selesai sukses ──
  'task_complete': () => {
    const involved = getCurrentTaskWorkers()
    return [{
      workers: involved,
      animation: 'celebrate_small',  // satu frame jump
      room: 'workstation',
      duration_ms: 600,
    }, {
      workers: ['conductor'],
      animation: 'thumbs_up',
      room: 'ceo_office',
      duration_ms: 800,
      speech: 'nice.'
    }]
  },

  // ── LoRA baru selesai di-train ──
  'lora_ready': () => [{
    workers: ['trainer', 'curator'],
    animation: 'high_five',          // dua worker saling high five
    room: 'lab_room',
    duration_ms: 800,
    speech: 'new upgrade ready 🧪'
  }, {
    workers: getActiveCoders(),
    animation: 'level_up_flash',     // flash efek di atas kepala
    room: 'workstation',
    duration_ms: 1000,
  }],

  // ── life_manager generate rules (pagi/session start) ──
  'daily_rules_ready': () => [{
    workers: ['life_manager'],
    animation: 'look_around_room',   // sweep pandang ke seluruh kantor
    room: 'library_room',
    duration_ms: 2000,
    speech: 'the office knows its rhythm.'
  }],
}
```

### Eksekusi Animasi

```typescript
export async function playTaskAnimation(eventType: string, context: dict = {}): Promise<void> {
  const factory = TASK_EVENT_ANIMATIONS[eventType]
  if (!factory) return

  const events = factory()

  // Jalankan sequential (pakai await) atau parallel (Promise.all)
  // Sequential untuk events yang berurutan (briefing, argue)
  // Parallel untuk events yang bersamaan (semua worker celebrate)
  for (const anim of events) {
    if (anim.animation === 'walk_to_meeting_room') {
      // Walk dulu sebelum animasi lain
      await Promise.all(
        anim.workers.map(w => walkWorkerTo(w, getMeetingRoomSpot(w)))
      )
    } else {
      // Play animasi untuk semua workers sekaligus
      anim.workers.forEach(w => {
        setWorkerAnimation(w, anim.animation)
        if (anim.speech) {
          emitSpeechBubble(w, anim.speech, 'auto', anim.duration_ms)
        }
      })

      if (anim.duration_ms > 0) {
        await sleep(anim.duration_ms)
      }
    }
  }
}
```

### Integrasi ke WebSocket Handler

```python
# backend/main.py — setiap event yang trigger animasi

ANIMATION_EVENT_MAP = {
    'task_received':     'task_received',
    'worker_assigned':   'task_briefing',
    'coder_started':     'coder_working',
    'scout_started':     'scout_researching',
    'task_error':        'task_error',
    'security_alert':    'security_issue',
    'audit_started':     'auditor_reviewing',
    'audit_issue_found': 'audit_issue',
    'task_complete':     'task_complete',
    'lora_activated':    'lora_ready',
    'daily_rules_ready': 'daily_rules_ready',
}

async def broadcast_with_animation(event: dict):
    """Setiap event yang dikirim ke frontend, cek apakah perlu trigger animasi."""
    await ws_broadcast(event)

    anim_type = ANIMATION_EVENT_MAP.get(event['type'])
    if anim_type:
        await ws_broadcast({
            'type': 'play_animation',
            'animation_event': anim_type,
            'context': event,
        })
```

---

## Sprite Frames yang Dibutuhkan (Fase 5)

```
Base (sudah ada di pixel-agents):
  walk_up, walk_down, walk_left, walk_right (4 frame tiap arah)
  idle_down (default)

Baru — perlu ditambah ke sprite sheet:
  sit_down           → 1 frame
  open_laptop        → 2 frame
  close_laptop       → 2 frame (reverse open_laptop)
  stand_up           → 1 frame (reverse sit_down)
  type_fast          → 3 frame loop
  rapid_typing       → 4 frame loop (lebih cepat)
  stand_at_whiteboard → 2 frame
  point_at_tv        → 2 frame
  look_at_tv         → 1 frame
  frustrated_bounce  → 3 frame (idle → jump kecil → idle)
  facepalm           → 1 frame
  alarmed_walk       → sama dengan walk tapi fps 2x
  read_carefully     → 2 frame
  point_accusingly   → 1 frame
  defensive_gesture  → 1 frame
  paint_on_tablet    → 3 frame loop
  study_mood_board   → 2 frame
  celebrate_small    → 2 frame
  thumbs_up          → 1 frame
  high_five          → 3 frame (dua worker)
  level_up_flash     → 2 frame (efek di atas kepala)
  look_around_room   → 4 frame pan kiri-kanan

Untuk Fase 2 (MVP): cukup type_fast, frustrated_bounce, celebrate_small
Fase 3: tambah whiteboard, look_at_tv, facepalm
Fase 5: semua lengkap
```

---

## Checklist

```
Fase 2:
[ ] triggerRoomEntry() dengan walk-to-desk sequence
[ ] walkWorkerTo() via BFS pathfinding
[ ] fadeOutCanvas / fadeInOverlay transitions
[ ] closeRoomOverlay() dengan close_laptop + stand_up
[ ] 3 animasi MVP: type_fast, frustrated_bounce, celebrate_small

Fase 3:
[ ] TASK_EVENT_ANIMATIONS semua events terdaftar
[ ] playTaskAnimation() dipanggil dari WebSocket 'play_animation' event
[ ] broadcast_with_animation() di semua backend event broadcasts
[ ] Meeting room walk sequence saat task_briefing
[ ] Argue sequence saat audit_issue_found

Fase 5:
[ ] Semua sprite frames lengkap di sprite sheet
[ ] high_five: sync dua worker ke titik yang sama
[ ] level_up_flash: particle effect di atas kepala
```

---

## Rooftop Ceremony — LoRA Presentation Event

> Scene ini terjadi di pixel art world — tidak ada FectTral overlay.
> Rooftop adalah satu-satunya "event besar" yang fully in-game world.
> Ini yang bikin special dibanding semua overlay lainnya.

### Trigger

```python
# Di backend: setelah trainer eval passed (delta > 5%)
# broadcast_with_animation() emit event ini

{
  "type": "lora_ceremony",
  "worker_id": "coder_rust",
  "domain": "borrow_checker",
  "delta": "+23%",
  "lora_name": "lora_borrow_checker_v2"
}
```

### Full Sequence

```typescript
// src/systems/task-animations.ts — tambah ke TASK_EVENT_ANIMATIONS

'lora_ceremony': (ctx) => [

  // Beat 1 — Lab room: trainer + curator react
  {
    workers: ['trainer', 'curator'],
    animation: 'high_five',
    room: 'lab_room',
    duration_ms: 800,
  },

  // Beat 2 — Narrator announce ke TV + chat panel
  // (parallel dengan beat 3, tidak await)
  {
    type: 'narrator',
    message: `🧪 upgrade complete: ${ctx.worker_id}.${ctx.domain} ${ctx.delta}`,
    duration_ms: 0,  // fire and forget
  },

  // Beat 3 — trainer + curator jalan ke tangga → naik ke rooftop
  {
    workers: ['trainer', 'curator'],
    animation: 'walk_to_stairs',
    room: 'lab_room',
    duration_ms: 1200,
  },
  {
    workers: ['trainer', 'curator'],
    animation: 'climb_stairs',        // animasi naik tangga (2 frame)
    room: 'staircase',
    duration_ms: 600,
  },

  // Beat 4 — semua workers IDLE walk ke rooftop
  // (hanya yang tidak sedang task aktif)
  {
    workers: getIdleWorkers(),         // filter: state !== 'working'
    animation: 'walk_to_rooftop',
    room: 'rooftop',
    duration_ms: 2000,                 // jalan dari mana aja, waktu bervariasi
  },

  // Beat 5 — trainer animasi "present" di tengah rooftop
  {
    workers: ['trainer'],
    animation: 'present_to_crowd',     // angkat tangan, sedikit jump
    room: 'rooftop',
    duration_ms: 1000,
    speech: `${ctx.domain}: ${ctx.delta} 🧪`
  },

  // Beat 6 — worker yang dapat upgrade: level_up_flash
  {
    workers: [ctx.worker_id],          // misal: coder_rust
    animation: 'level_up_flash',       // glow burst di atas kepala
    room: 'rooftop',                   // dia juga sudah di rooftop
    duration_ms: 1200,
  },

  // Beat 7 — crowd reaction
  // workers lain animasi kecil bersamaan (random dari list)
  {
    workers: getIdleWorkers().filter(w => w !== ctx.worker_id && w !== 'trainer'),
    animation: pickRandom(['celebrate_small', 'thumbs_up', 'clap']),
    room: 'rooftop',
    duration_ms: 800,
  },

  // Beat 8 — curator speech bubble
  {
    workers: ['curator'],
    animation: 'idle_down',
    room: 'rooftop',
    duration_ms: 500,
    speech: 'the office grows. 🌱'
  },

  // Beat 9 — semua diam sejenak (cinematic pause)
  {
    type: 'pause',
    duration_ms: 1500,
  },

  // Beat 10 — semua workers balik ke ruangan masing-masing
  {
    workers: getIdleWorkers(),
    animation: 'walk_to_home_room',    // balik ke home_room masing-masing
    room: 'various',
    duration_ms: 2000,
  },
]
```

### Total Duration

```
Beat 1:  0.8s  — high five
Beat 2:  0s    — narrator (instant)
Beat 3:  1.2s  — jalan ke tangga
Beat 4:  0.6s  — naik tangga
Beat 5:  2.0s  — workers idle jalan ke rooftop
Beat 6:  1.0s  — trainer present
Beat 7:  1.2s  — level up flash
Beat 8:  0.8s  — crowd react
Beat 9:  0.5s  — curator speech
Beat 10: 1.5s  — cinematic pause
Beat 11: 2.0s  — semua pulang
─────────────────
Total:  ~11.6 detik — cukup singkat tapi memorable
```

### Kalau User Tidak Lihat (Minimize / Tab Lain)

```python
# Ceremony tetap terjadi di game world (workers bergerak)
# Tapi juga ada notifikasi di chat panel:

{
  "type": "output_card",
  "variant": "success",
  "worker_id": "trainer",
  "title": "LoRA Ceremony Complete",
  "body": "coder_rust.borrow_checker upgraded +23%\nAll workers gathered on the rooftop.",
  "timestamp": "..."
}
```

### Sprite Frames Baru yang Dibutuhkan

```
present_to_crowd   → 3 frame: stand → raise arms → hold
climb_stairs       → 2 frame: step up loop
clap               → 2 frame: hands together loop
walk_to_stairs     → pakai walk biasa, target tile = staircase
walk_to_rooftop    → pakai walk biasa, target tile = rooftop entrance
```

Fase 2: skip ceremony, hanya narrator announce + speech bubble di lab room.
Fase 3: ceremony berjalan tapi animasi placeholder (celebrate_small semua).
Fase 5: semua sprite baru di atas diimplementasikan.

### Checklist

```
Fase 3:
[ ] lora_ceremony event di-broadcast dari trainer worker
[ ] getIdleWorkers() filter workers yang tidak sedang task
[ ] walk_to_rooftop: semua idle workers pathfind ke rooftop tile
[ ] trainer speech bubble di rooftop
[ ] ctx.worker_id dapat level_up_flash
[ ] semua pulang ke home_room setelah ceremony

Fase 5:
[ ] present_to_crowd sprite
[ ] climb_stairs sprite
[ ] clap sprite
[ ] cinematic pause (camera subtle zoom out saat beat 9)
```
