# Frontend — UI Overlays (Fase 2)

> **Konteks untuk session baru:**
> Semua overlay = HTML div di atas canvas — bukan canvas draw.
> FectTral adalah skin untuk semua overlay (lihat design/design-system.md untuk tokens).
> File ini: TV screen, status popup, progress bar, blocked visual, toast, connection overlay.
> Design Studio transition (pixel art → FectTral full UI) ada di bagian bawah.

---

## Layer Stack

```
z-index: 0    → canvas (pixel art game world)
z-index: 10   → TV screen overlay (di meeting room)
z-index: 20   → character status popup (klik worker)
z-index: 30   → CEO office paper stack
z-index: 40   → toast notifications (pojok kanan bawah)
z-index: 50   → tier 3 error card (blocking)
z-index: 60   → connection lost overlay
z-index: 100  → design studio FectTral takeover (full screen)
```

Semua overlay pakai FectTral tokens dari `:root` di `design/design-system.md`.

---

## TV Screen (Meeting Room)

Posisi absolute di atas canvas. Koordinat konversi world→screen setiap frame render.
Update setiap kali ada `tv_update` WebSocket event.

> **MassGen pattern (adopted 2026-03-18):**
> TV screen sebelumnya hanya tampilkan 3 log terakhir. MassGen punya "timeline view"
> — full scrollable event history. Kita adopt: TV punya dua mode yang bisa di-toggle.
> Ref: github.com/massgen/MassGen

```typescript
// src/overlays/TVScreen.tsx

type TVMode = 'live' | 'timeline'

interface TVEvent {
  id:        string
  time:      string
  worker_id: string
  type:      'task_start'|'task_done'|'blocked'|'lora_ready'|
             'skill_updated'|'review_blocking'|'security_block'|
             'training_start'|'tier3_escalate'|'grokked'
  text:      string
  severity?: 'info'|'warn'|'critical'|'success'
}

interface TVProps {
  currentTask:    string | null
  workerStatuses: { id: string; state: WorkerState; progress: number }[]
  events:         TVEvent[]       // full history, max 200
  tvWorldPos:     { x: number; y: number }
  mode:           TVMode
  onModeToggle:   () => void
}

const SEVERITY_COLOR: Record<string, string> = {
  info: 'var(--text-secondary)', warn: '#FF9800',
  critical: '#ff6b6b',           success: '#44ff88',
}

const EVENT_ICON: Record<TVEvent['type'], string> = {
  task_start: '▶', task_done: '✓', blocked: '⚠',
  lora_ready: '🧠', skill_updated: '📚', review_blocking: '🔴',
  security_block: '🔒', training_start: '⚡', tier3_escalate: '❗', grokked: '🟢',
}

export function TVScreen({ currentTask, workerStatuses, events, tvWorldPos, mode, onModeToggle }: TVProps) {
  const { screenX, screenY } = worldToScreen(tvWorldPos)
  const timelineRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    if (mode === 'timeline' && timelineRef.current) {
      timelineRef.current.scrollTop = timelineRef.current.scrollHeight
    }
  }, [events.length, mode])

  return (
    <div className="tv-screen" style={{ left: screenX, top: screenY }}>
      <div className="tv-header">
        <span className="tv-label">{mode === 'live' ? 'ACTIVE TASK' : 'EVENT TIMELINE'}</span>
        <span className="tv-status-dot" />
        <button className="tv-mode-toggle" onClick={onModeToggle}>
          {mode === 'live' ? '📋' : '⚡'}
        </button>
      </div>

      {mode === 'live' ? (
        <>
          <div className="tv-task">
            {currentTask ?? <span className="tv-idle">waiting for your next task...</span>}
          </div>
          <div className="tv-workers">
            {workerStatuses.map(w => (
              <div key={w.id} className="tv-worker-row">
                <span className="tv-worker-id">{w.id}</span>
                <div className="tv-bar-bg">
                  <div className="tv-bar-fill" style={{ width: `${w.progress*100}%`, backgroundColor: STATE_COLOR[w.state] }} />
                </div>
                <span className="tv-worker-state">{w.state}</span>
              </div>
            ))}
          </div>
          <div className="tv-log">
            {events.slice(-3).map(ev => (
              <div key={ev.id} className="tv-log-line">
                <span className="tv-log-time">{ev.time}</span>
                <span className="tv-log-text" style={{ color: SEVERITY_COLOR[ev.severity ?? 'info'] }}>
                  {EVENT_ICON[ev.type]} {ev.text}
                </span>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="tv-timeline" ref={timelineRef}>
          {events.map(ev => (
            <div key={ev.id} className="tv-timeline-event">
              <div className="tv-tl-meta">
                <span className="tv-tl-time">{ev.time}</span>
                <span className="tv-tl-worker">{ev.worker_id}</span>
              </div>
              <div className="tv-tl-content">
                <span className="tv-tl-icon">{EVENT_ICON[ev.type]}</span>
                <span className="tv-tl-text" style={{ color: SEVERITY_COLOR[ev.severity ?? 'info'] }}>
                  {ev.text}
                </span>
              </div>
            </div>
          ))}
          {events.length === 0 && <div className="tv-tl-empty">no events yet...</div>}
        </div>
      )}
    </div>
  )
}
```

**State management (workerManager.ts):**
```typescript
const MAX_TV_EVENTS = 200
export const tvEventStore = {
  events: [] as TVEvent[],
  add(event: TVEvent) {
    this.events.push(event)
    if (this.events.length > MAX_TV_EVENTS) this.events.shift()
  },
  clear() { this.events = [] },
}
```

```css
.tv-screen {
  position: absolute; width: 200px;
  background: var(--bg-card); border: 1px solid var(--border-mid);
  box-shadow: var(--glow-sm); border-radius: 3px; padding: 6px 8px;
  font-family: var(--font-mono); font-size: 8px; color: var(--text-primary);
  pointer-events: auto;
}
.tv-header { display: flex; align-items: center; gap: 4px; margin-bottom: 4px; border-bottom: 1px solid var(--border-dim); padding-bottom: 3px; }
.tv-label { font-family: var(--font-display); font-size: 6px; letter-spacing: 0.1em; color: var(--blue-core); text-shadow: var(--glow-text); flex: 1; }
.tv-status-dot { width: 4px; height: 4px; border-radius: 50%; background: #44ff88; box-shadow: 0 0 4px #44ff88; animation: pulse 2s ease-in-out infinite; }
.tv-mode-toggle { background: none; border: none; cursor: pointer; font-size: 8px; padding: 0; color: var(--text-muted); }
.tv-mode-toggle:hover { color: var(--blue-core); }
.tv-task { color: var(--text-primary); font-size: 7px; margin-bottom: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tv-idle { color: var(--text-muted); }
.tv-worker-row { display: grid; grid-template-columns: 55px 1fr 38px; gap: 3px; align-items: center; margin-bottom: 2px; }
.tv-worker-id { color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; }
.tv-bar-bg { background: var(--bg-panel); height: 3px; border-radius: 2px; }
.tv-bar-fill { height: 3px; border-radius: 2px; transition: width 0.3s ease; }
.tv-worker-state { color: var(--text-muted); font-size: 6px; }
.tv-log { margin-top: 4px; border-top: 1px solid var(--border-dim); padding-top: 3px; }
.tv-log-line { display: flex; gap: 4px; margin-bottom: 1px; }
.tv-log-time { color: var(--text-muted); min-width: 32px; }
.tv-log-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* Timeline mode */
.tv-timeline { max-height: 120px; overflow-y: auto; scrollbar-width: none; }
.tv-timeline::-webkit-scrollbar { display: none; }
.tv-timeline-event { display: grid; grid-template-columns: 52px 1fr; gap: 4px; padding: 2px 0; border-bottom: 1px solid var(--border-dim); }
.tv-timeline-event:last-child { border-bottom: none; }
.tv-tl-meta { display: flex; flex-direction: column; gap: 1px; }
.tv-tl-time { color: var(--text-muted); font-size: 6px; }
.tv-tl-worker { color: var(--blue-dim); font-size: 6px; overflow: hidden; text-overflow: ellipsis; }
.tv-tl-content { display: flex; align-items: flex-start; gap: 3px; }
.tv-tl-icon { font-size: 7px; min-width: 10px; }
.tv-tl-text { font-size: 7px; line-height: 1.3; word-break: break-word; }
.tv-tl-empty { color: var(--text-muted); font-size: 7px; text-align: center; padding: 8px 0; }
@keyframes pulse { 0%,100% { opacity:1 } 50% { opacity:0.4 } }
```

## Character Status Popup

Klik worker → popup muncul. Klik lagi atau area lain → tutup.
Live update: kalau terbuka dan event masuk untuk worker ini, update langsung.

```typescript
// src/overlays/WorkerPopup.tsx

interface PopupProps {
  worker: WorkerData
  onClose: () => void
  canvasPos: { x: number; y: number }  // posisi di canvas screen
  canvasSize: { w: number; h: number }
}

export function WorkerPopup({ worker, onClose, canvasPos, canvasSize }: PopupProps) {
  // Smart positioning: jangan keluar canvas
  const W = 200, H = 260
  let left = canvasPos.x + 12
  let top  = canvasPos.y - 20
  if (left + W > canvasSize.w) left = canvasPos.x - W - 12
  if (top + H > canvasSize.h) top = canvasSize.h - H - 8
  if (top < 0) top = 8

  return (
    <div className="worker-popup" style={{ left, top }} onClick={e => e.stopPropagation()}>
      {/* Header */}
      <div className="popup-header">
        <span className="popup-emoji">{worker.badge_emoji}</span>
        <div>
          <div className="popup-name">{worker.display_name}</div>
          <div className="popup-id">{worker.id}</div>
        </div>
        <button className="popup-close" onClick={onClose}>×</button>
      </div>

      {/* State badge */}
      <div className="popup-state" style={{ borderColor: STATE_COLOR[worker.state] }}>
        <span className="popup-state-dot" style={{ background: STATE_COLOR[worker.state] }} />
        {worker.state.toUpperCase()}
        {worker.room && <span className="popup-room"> · {worker.room.replace('_',' ')}</span>}
      </div>

      {/* Task aktif */}
      {worker.current_task && (
        <div className="popup-section">
          <div className="popup-label">CURRENT TASK</div>
          <div className="popup-task">{worker.current_task}</div>
          {(worker.state === 'working' || worker.state === 'reviewing') && (
            <div className="popup-progress-bg">
              <div
                className="popup-progress-fill"
                style={{
                  width: `${worker.progress * 100}%`,
                  background: STATE_COLOR[worker.state]
                }}
              />
              <span className="popup-progress-pct">{Math.round(worker.progress*100)}%</span>
            </div>
          )}
        </div>
      )}

      {/* Stats */}
      <div className="popup-stats">
        <div className="popup-stat">
          <span className="popup-stat-val">{worker.tasks_done}</span>
          <span className="popup-stat-label">done</span>
        </div>
        <div className="popup-stat">
          <span className="popup-stat-val" style={{ color: worker.errors > 0 ? '#ff6b6b' : 'inherit' }}>
            {worker.errors}
          </span>
          <span className="popup-stat-label">errors</span>
        </div>
        <div className="popup-stat">
          <span className="popup-stat-val">{formatUptime(worker.uptime_seconds)}</span>
          <span className="popup-stat-label">uptime</span>
        </div>
      </div>

      {/* LoRA badges — Fase 4, render kalau ada */}
      {worker.active_loras && worker.active_loras.length > 0 && (
        <div className="popup-loras">
          <div className="popup-label">ACTIVE LORAS</div>
          {worker.active_loras.map(l => (
            <span key={l.name} className="lora-badge" title={`${l.domain} · ${l.weight}`}>
              🧠 {l.domain}
            </span>
          ))}
          <button className="popup-brain-btn" onClick={() => openBrainViz(worker.id)}>
            view brain →
          </button>
        </div>
      )}
    </div>
  )
}
```

```css
.worker-popup {
  position: absolute;
  width: 200px;
  background: var(--bg-panel);
  border: 1px solid var(--border-mid);
  box-shadow: var(--glow-md);
  border-radius: 4px;
  padding: 10px;
  font-family: var(--font-body);
  font-size: 10px;
  color: var(--text-primary);
  z-index: 20;
}
.popup-header {
  display: flex; align-items: center; gap: 6px; margin-bottom: 8px;
}
.popup-emoji { font-size: 20px; }
.popup-name { font-family: var(--font-display); font-size: 11px; color: var(--blue-bright); }
.popup-id   { color: var(--text-muted); font-family: var(--font-mono); font-size: 8px; }
.popup-close {
  margin-left: auto; background: none; border: none;
  color: var(--text-muted); cursor: pointer; font-size: 14px;
}
.popup-state {
  display: flex; align-items: center; gap: 5px;
  border: 1px solid; border-radius: 3px; padding: 3px 6px;
  font-family: var(--font-mono); font-size: 8px; letter-spacing: 0.08em;
  margin-bottom: 8px;
}
.popup-state-dot { width: 5px; height: 5px; border-radius: 50%; }
.popup-room { color: var(--text-muted); }
.popup-section { margin-bottom: 8px; }
.popup-label {
  font-family: var(--font-display); font-size: 7px;
  letter-spacing: 0.12em; color: var(--text-muted); margin-bottom: 3px;
}
.popup-task { color: var(--text-secondary); line-height: 1.4; }
.popup-progress-bg {
  position: relative; height: 4px; background: var(--bg-card);
  border-radius: 2px; margin-top: 5px; overflow: visible;
}
.popup-progress-fill { height: 100%; border-radius: 2px; transition: width 0.4s ease; }
.popup-progress-pct {
  position: absolute; right: 0; top: -12px;
  font-size: 8px; font-family: var(--font-mono); color: var(--text-muted);
}
.popup-stats {
  display: grid; grid-template-columns: repeat(3, 1fr);
  text-align: center; gap: 4px; margin-bottom: 8px;
  border: 1px solid var(--border-dim); border-radius: 3px; padding: 5px;
}
.popup-stat-val { display: block; font-family: var(--font-display); font-size: 13px; }
.popup-stat-label { color: var(--text-muted); font-size: 7px; }
.popup-loras { border-top: 1px solid var(--border-dim); padding-top: 6px; }
.lora-badge {
  display: inline-block; background: rgba(0,170,255,0.1);
  border: 1px solid var(--border-mid); border-radius: 2px;
  padding: 1px 5px; margin: 2px; font-size: 8px; cursor: pointer;
}
.popup-brain-btn {
  display: block; width: 100%; margin-top: 5px;
  background: rgba(0,170,255,0.08); border: 1px solid var(--border-mid);
  color: var(--blue-core); font-family: var(--font-mono); font-size: 8px;
  letter-spacing: 0.06em; cursor: pointer; padding: 3px;
  border-radius: 2px; text-align: center;
}
.popup-brain-btn:hover { background: rgba(0,170,255,0.18); }
```

---

## Hit Test + Click Handler

```typescript
// Di App.tsx atau GameCanvas.tsx

canvas.addEventListener('click', (e) => {
  const rect = canvas.getBoundingClientRect()
  const scale = rect.width / CANVAS_W
  const wx = (e.clientX - rect.left) / scale
  const wy = (e.clientY - rect.top) / scale
  const T = TILE_SIZE

  // Cek hit worker
  const hit = workers.find(w =>
    wx >= w.position.x * T &&
    wx < (w.position.x + 1) * T &&
    wy >= w.position.y * T &&
    wy < (w.position.y + 1) * T
  )

  if (hit) {
    setActivePopup(hit.id)
    return
  }

  // Cek hit monitor design studio
  if (isMonitorTile(wx, wy)) {
    enterDesignStudio()
    return
  }

  // Cek hit meja conductor → CEO office papers
  if (isConductorDesk(wx, wy)) {
    openCEOOffice()
    return
  }

  // Klik area kosong → tutup popup
  setActivePopup(null)
})
```

---

## Notification Toast

```typescript
// src/overlays/ToastManager.tsx

type ToastType = 'success' | 'warning' | 'error' | 'info'

interface Toast {
  id: string; type: ToastType; message: string
  autoDismiss: boolean  // error = false, lainnya = true setelah 3s
}

const TOAST_COLORS: Record<ToastType, string> = {
  success: '#44ff88',
  warning: '#ffaa00',
  error:   '#ff4444',
  info:    '#00aaff',
}

// Toast stack di pojok kanan bawah
// Animasi: slide in dari kanan (300ms), slide out ke kanan (200ms)
```

---

## Design Studio Transition (Pixel Art → FectTral)

Klik monitor besar di design studio → seamless zoom in ke monitor → FectTral UI.

```typescript
// src/overlays/DesignStudioTransition.tsx

export function enterDesignStudio() {
  const monitorPos = getMonitorScreenPos()  // pixel coordinates di canvas
  const canvas = document.getElementById('game-canvas') as HTMLCanvasElement
  const overlay = document.getElementById('fectral-overlay') as HTMLDivElement

  // Step 1: Zoom canvas ke monitor (400ms)
  const scaleX = window.innerWidth / 16    // 16px tile → full screen
  const scaleY = window.innerHeight / 16
  const scale  = Math.min(scaleX, scaleY) * 1.2

  // Translate: bawa monitor ke tengah layar
  const tx = (window.innerWidth / 2 - monitorPos.x) / scale
  const ty = (window.innerHeight / 2 - monitorPos.y) / scale

  canvas.style.transition = 'transform 400ms cubic-bezier(0.4, 0, 0.2, 1)'
  canvas.style.transformOrigin = '0 0'
  canvas.style.transform = `scale(${scale}) translate(${tx}px, ${ty}px)`

  // Step 2: Fade in FectTral overlay setelah zoom selesai
  setTimeout(() => {
    overlay.style.display = 'flex'
    overlay.style.opacity = '0'
    overlay.style.transition = 'opacity 250ms ease'
    requestAnimationFrame(() => {
      overlay.style.opacity = '1'
    })
  }, 380)
}

export function exitDesignStudio() {
  const overlay = document.getElementById('fectral-overlay') as HTMLDivElement
  const canvas  = document.getElementById('game-canvas') as HTMLCanvasElement

  // Step 1: Fade out FectTral
  overlay.style.transition = 'opacity 200ms ease'
  overlay.style.opacity = '0'

  // Step 2: Zoom canvas kembali normal
  setTimeout(() => {
    overlay.style.display = 'none'
    canvas.style.transition = 'transform 350ms cubic-bezier(0.4, 0, 0.2, 1)'
    canvas.style.transform = 'scale(1) translate(0, 0)'
  }, 200)

  // Step 3: Clean up transition setelah selesai
  setTimeout(() => {
    canvas.style.transition = ''
  }, 600)
}
```

```css
/* FectTral overlay — full screen, z-index tertinggi */
#fectral-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: none;  /* default hidden */
  flex-direction: column;
  background: var(--bg-void);
  /* Semua FectTral styles dari SKILL-v3.md */
}

/* Monitor di pixel art glowing saat idle */
.monitor-glow {
  animation: monitorPulse 3s ease-in-out infinite;
}
@keyframes monitorPulse {
  0%,100% { filter: brightness(1); }
  50%      { filter: brightness(1.4) drop-shadow(0 0 4px #00aaff); }
}

/* Cursor berubah saat hover monitor */
.monitor-hover { cursor: pointer; }
```

---

## Blocked Worker Visual (Canvas Draw)

Ini tetap di canvas — bukan HTML overlay karena butuh sync dengan sprite position.

```typescript
// Di renderer.ts, tambahkan setelah drawSprite():

function drawBlockedEffects(ctx: CanvasRenderingContext2D, worker: WorkerData, screenX: number, screenY: number) {
  if (worker.state !== 'blocked') return

  // Gemetar: offset ±1px setiap 100ms
  const shakeOffset = Math.floor(Date.now() / 100) % 2 === 0 ? 1 : -1
  // (sudah di-apply saat drawSprite dengan shakeOffset)

  // "!" merah di atas kepala
  ctx.save()
  ctx.fillStyle = '#ff4444'
  ctx.font = 'bold 9px monospace'
  ctx.shadowColor = '#ff4444'
  ctx.shadowBlur = 4
  ctx.fillText('!', screenX + TILE_SIZE/2 - 3, screenY - 4)
  ctx.restore()

  // Exclamation berkedip (setiap 500ms)
  if (Math.floor(Date.now() / 500) % 2 === 0) {
    ctx.save()
    ctx.strokeStyle = 'rgba(255,68,68,0.4)'
    ctx.lineWidth = 1
    ctx.strokeRect(screenX - 2, screenY - 2, TILE_SIZE + 4, TILE_SIZE + 4)
    ctx.restore()
  }
}
```

---

## Connection Lost Overlay

```typescript
// src/overlays/ConnectionOverlay.tsx
// Muncul otomatis saat WebSocket disconnect

export function ConnectionOverlay({ isVisible, retryCount }: {
  isVisible: boolean; retryCount: number
}) {
  if (!isVisible) return null
  const delay = Math.min(1000 * Math.pow(1.5, retryCount), 30000)

  return (
    <div className="connection-overlay">
      <div className="connection-card">
        <div className="connection-icon">⚡</div>
        <div className="connection-title">CONNECTION LOST</div>
        <div className="connection-msg">workers paused — backend unreachable</div>
        <div className="connection-retry">
          reconnecting in {(delay/1000).toFixed(1)}s
          <span className="connection-dots">...</span>
        </div>
      </div>
    </div>
  )
}
```

```css
.connection-overlay {
  position: fixed; inset: 0; z-index: 60;
  background: rgba(2,4,8,0.85);
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(4px);
}
.connection-card {
  background: var(--bg-card);
  border: 1px solid var(--border-mid);
  box-shadow: var(--glow-md);
  border-radius: 6px;
  padding: 24px 32px;
  text-align: center;
  font-family: var(--font-mono);
}
.connection-icon  { font-size: 32px; margin-bottom: 8px; }
.connection-title {
  font-family: var(--font-display); font-size: 14px;
  color: var(--blue-bright); letter-spacing: 0.15em;
  text-shadow: var(--glow-text); margin-bottom: 6px;
}
.connection-msg   { color: var(--text-secondary); font-size: 10px; }
.connection-retry { color: var(--text-muted); font-size: 9px; margin-top: 10px; }
.connection-dots  { animation: blink 1s step-end infinite; }
@keyframes blink  { 50% { opacity: 0; } }
```
