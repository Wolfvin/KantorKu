# Frontend — Needs System & Worker Life (Fase 2+)

> **Konteks untuk session baru:**
> Workers bukan hanya coding machine — mereka punya kebutuhan sehari-hari.
> Sistem ini rule-based (zero LLM calls real-time), tapi rules-nya di-generate
> oleh `life_manager` worker setiap session start / room config berubah.
> Dekorasi dari room editor langsung mempengaruhi rules yang di-generate.
> File terkait:
>   - `backend/life-manager.md` → life_manager worker + daily_rules.json generation
>   - `desktop/room-editor.md` → Tauri app terpisah untuk edit ruangan + dekorasi
>   - `frontend/fsm-rooms.md` → multi-lantai, room sizing

---

## Needs System — 4 Bar

Setiap worker punya 4 needs yang update secara real-time:

```typescript
interface WorkerNeeds {
  energy:  number  // 0.0–1.0 | drain saat kerja, restore saat tidur/istirahat
  social:  number  // 0.0–1.0 | drain saat kerja solo, restore saat interaksi worker lain
  focus:   number  // 0.0–1.0 | drain karena interupsi, restore saat di meja kerja tenang
  hunger:  number  // 0.0–1.0 | drain konstan, restore saat di break room / ada food decoration
}
```

**Rate update:** setiap 60 detik real-time = satu "needs tick."
Nilai di atas bisa dikonfigurasi per-worker via `daily_rules.json` dari life_manager.

---

## Visibility Settings

```typescript
// settings.json
{
  "needs_bar_visible": boolean  // default: true
}
```

**Kalau `needs_bar_visible: true`:**
- Mini bar muncul di atas kepala worker saat worker sedang dilihat / area terdekat kamera
- 4 bar kecil (16px wide tiap bar) stacked horizontal, warna berbeda per need
- Fade in saat kamera zoom ke area worker, fade out saat zoom out

**Kalau `needs_bar_visible: false`:**
- Bar tidak muncul di dunia game sama sekali
- Tapi TETAP ada di **status popup** saat hover/tekan worker
- Behavior tetap terpengaruh needs — hanya visualnya yang disembunyikan

---

## Status Popup — Needs Section

Saat user hover atau tap worker (bisa dari setting visible on/off):

```typescript
// Extension dari status popup yang sudah ada di ui-overlays.md

function NeedsSection({ needs, worker }: { needs: WorkerNeeds; worker: WorkerProfile }) {
  return (
    <div className="needs-section">
      <div className="needs-title">NEEDS</div>
      {[
        { key: 'energy',  label: 'Energy',  icon: '⚡', color: '#FFCB6B' },
        { key: 'social',  label: 'Social',  icon: '💬', color: '#89DDFF' },
        { key: 'focus',   label: 'Focus',   icon: '🎯', color: '#C792EA' },
        { key: 'hunger',  label: 'Hunger',  icon: '🍜', color: '#C3E88D' },
      ].map(({ key, label, icon, color }) => {
        const val = needs[key as keyof WorkerNeeds]
        const status = val > 0.6 ? 'good' : val > 0.3 ? 'warn' : 'low'
        return (
          <div key={key} className="need-row">
            <span className="need-icon">{icon}</span>
            <span className="need-label">{label}</span>
            <div className="need-track">
              <div
                className="need-fill"
                style={{
                  width: `${val * 100}%`,
                  background: status === 'good' ? color
                            : status === 'warn' ? '#FF9800'
                            : '#FF5252'
                }}
              />
            </div>
            <span className="need-val">{Math.round(val * 100)}%</span>
          </div>
        )
      })}

      {/* Current behavior label */}
      <div className="need-behavior">
        doing: <strong>{worker.current_behavior ?? 'working'}</strong>
      </div>
    </div>
  )
}
```

---

## Behavior Trigger Logic

```typescript
// src/systems/needs-engine.ts

interface DailyRules {
  energy_drain_rate:  number          // 0.0–1.0 multiplier
  social_tendency:    number          // seberapa cepat social drain
  break_behaviors:    string[]        // animasi yang bisa dilakukan saat break
  idle_animations:    string[]        // animasi saat duduk idle
  stress_threshold:   number          // kalau focus < ini → worker visible stressed
  sleep_hour:         number          // jam tidur (0–23)
  wake_hour:          number          // jam bangun (0–23)
  food_behaviors:     string[]        // animasi makan yang tersedia (dari dekorasi)
  exercise_behaviors: string[]        // animasi olahraga yang tersedia (dari dekorasi)
}

function evaluateNeeds(worker: WorkerProfile, needs: WorkerNeeds, rules: DailyRules): string | null {
  /**
   * Cek needs dan return behavior yang harus di-trigger.
   * Return null kalau tidak ada yang perlu di-trigger (worker tetap di task).
   * Priority: energy > hunger > social > focus
   */

  // ENERGY habis → tidur / break
  if (needs.energy < 0.15) {
    return Math.random() < 0.7 ? 'go_dormitory' : 'go_break_room'
  }

  // HUNGER rendah → cari makan
  if (needs.hunger < 0.2) {
    const foodBehavior = rules.food_behaviors[
      Math.floor(Math.random() * rules.food_behaviors.length)
    ]
    return foodBehavior ?? 'go_break_room'
  }

  // SOCIAL rendah → jalan ke worker lain / break room
  if (needs.social < 0.25 && rules.social_tendency > 0.3) {
    return 'seek_social'
  }

  // FOCUS rendah → stretch / walk around sebentar
  if (needs.focus < 0.2) {
    return rules.break_behaviors[Math.floor(Math.random() * rules.break_behaviors.length)]
      ?? 'stretch'
  }

  return null  // semua OK, lanjut kerja
}

// Dipanggil setiap needs tick (60 detik)
function needsTick(workers: WorkerProfile[], dailyRules: Record<string, DailyRules>) {
  for (const worker of workers) {
    if (worker.state === 'working' || worker.state === 'idle') {
      const rules = dailyRules[worker.id]
      const triggered = evaluateNeeds(worker, worker.needs, rules)
      if (triggered) {
        emitBehavior(worker.id, triggered)
      }
    }
    // Update needs values
    drainNeeds(worker, rules)
  }
}
```

---

## Behavior → Animasi

Behavior string dari `daily_rules.json` map ke sprite animasi:

```typescript
// Animasi yang selalu ada (built-in, tidak butuh dekorasi)
const BASE_ANIMATIONS: Record<string, SpriteAnim> = {
  'stretch':        { frames: [40,41,42,43], fps: 4 },
  'stare_monitor':  { frames: [44,45], fps: 2 },
  'walk_idle':      { frames: [0,1,2,3], fps: 8 },  // default movement
}

// Animasi yang unlock berdasarkan dekorasi di room-config.json
// Room editor export dekorasi → vibe-office baca → unlock animasi
const DECORATION_ANIMATIONS: Record<string, SpriteAnim> = {
  'sit_at_sofa':       { frames: [50,51,52], fps: 3, requires: 'sofa' },
  'drink_coffee':      { frames: [53,54,55,56], fps: 4, requires: 'coffee_machine' },
  'use_treadmill':     { frames: [57,58,59,60,61], fps: 8, requires: 'treadmill' },
  'write_whiteboard':  { frames: [62,63,64], fps: 3, requires: 'whiteboard' },
  'make_coffee':       { frames: [65,66,67,68], fps: 4, requires: 'coffee_machine' },
  'read_book':         { frames: [69,70,71], fps: 3, requires: 'bookshelf' },
  'look_out_window':   { frames: [72,73], fps: 2, requires: 'window' },
  'eat_at_table':      { frames: [74,75,76,77], fps: 4, requires: 'dining_table' },
  'play_ping_pong':    { frames: [78,79,80,81,82,83], fps: 8, requires: 'ping_pong_table' },
  'pace_room':         { frames: [0,1,2,3], fps: 6 },  // conductor trait
}
```

**Fase rollout animasi:**
- Fase 2: base animations saja
- Fase 3: 4–5 dekorasi paling common (sofa, coffee_machine, whiteboard)
- Fase 5 Polish: semua animasi dekorasi lengkap

---

## Worker Social — Interaksi Antar Workers

Saat `seek_social` di-trigger:

```typescript
async function workerSeekSocial(workerId: string, allWorkers: WorkerProfile[]) {
  // Cari worker lain yang sedang idle / di break room
  const targets = allWorkers.filter(w =>
    w.id !== workerId &&
    (w.state === 'idle' || w.room === 'break_room') &&
    w.needs.social < 0.5  // dia juga butuh social
  )

  if (targets.length === 0) {
    // Tidak ada yang available → jalan sendiri ke break room
    emitMoveToRoom(workerId, 'break_room')
    return
  }

  const target = targets[Math.floor(Math.random() * targets.length)]

  // Keduanya jalan ke posisi yang sama
  emitMoveTo(workerId, target.position)

  // Speech bubble — dari idle_phrases di SOUL.md, bukan LLM
  const phrase = getRandomIdlePhrase(workerId)
  const response = getRandomIdlePhrase(target.id)

  await sleep(800)  // jalan dulu
  emitSpeechBubble(workerId, phrase)
  await sleep(1200)
  emitSpeechBubble(target.id, response)

  // Restore social needs keduanya
  restoreNeed(workerId, 'social', 0.2)
  restoreNeed(target.id, 'social', 0.15)
}
```

---

## In-World Needs Bar (kalau `needs_bar_visible: true`)

```
Di atas kepala worker, 4 bar kecil:
  [⚡████░░] [💬██████] [🎯███░░░] [🍜█░░░░░]

Layout:
  - Width: 4 × 14px = 56px total
  - Height: 4px per bar
  - Gap: 1px antar bar
  - Posisi: y = worker_tile_y - 8px
  - Fade: opacity 0→1 saat zoom > 2x, 1→0 saat zoom < 1.5x

Warna:
  > 60%: warna normal (kuning/biru/ungu/hijau)
  30–60%: oranye
  < 30%: merah + shimmer animation (warning)
```

---

## Checklist Fase 2 (Needs System Dasar)

```
[ ] WorkerNeeds interface di types/worker.ts
[ ] needs-engine.ts: drainNeeds, restoreNeed, evaluateNeeds, needsTick
[ ] needsTick dipanggil setiap 60 detik via setInterval
[ ] evaluateNeeds trigger behavior: go_dormitory, go_break_room, seek_social, stretch
[ ] Status popup: NeedsSection component dengan 4 bar
[ ] Settings: needs_bar_visible toggle
[ ] In-world bar: render di atas worker kalau setting ON, fade berdasarkan zoom
[ ] seek_social: dua workers bisa saling approach + speech bubble exchange

Fase 3 (life_manager live):
[ ] daily_rules.json di-generate oleh life_manager setiap session start
[ ] drainNeeds pakai rates dari daily_rules.json per worker
[ ] break_behaviors dari daily_rules.json → pilih animasi random

Fase 5 (dekorasi animasi penuh):
[ ] DECORATION_ANIMATIONS semua di-implement di sprite sheet
[ ] room-config.json di-read → unlock animasi yang sesuai dekorasi
```
