# Frontend — CEO Office (Fase 2)

> **Konteks untuk session baru:**
> CEO office = satu-satunya tempat manage workers. Klik meja conductor →
> kertas-kertas muncul. Flip next/prev. Kertas terakhir = Job Application.
> Fase 2 tambahan: kertas identitas sekarang include LoRA badges (render tapi
> disabled — aktif Fase 4 saat trainer ada). FectTral card style untuk semua kertas.

---

## Flow Lengkap

```
Klik meja conductor di CEO office tile
  ↓
Paper stack muncul di tengah layar (z-index 30)
  ↓
Satu kertas aktif, sisanya menumpuk di belakang
Tekan next/prev (atau tombol keyboard ← →) → animasi flip
  ↓
Kertas terakhir = Job Application (form hire worker baru)
Klik di luar paper stack → tutup
```

---

## Paper Stack Component

```typescript
// src/overlays/CEOOffice.tsx

interface WorkerPaper {
  workerId: string
  profile: WorkerProfile
  loras: LoRAMetadata[]      // kosong di Fase 1-3, terisi Fase 4
  stats: WorkerStats
}

export function CEOOffice({ workers, onClose }: {
  workers: WorkerProfile[]
  onClose: () => void
}) {
  const papers: WorkerPaper[] = [
    ...workers.map(w => ({ workerId: w.id, profile: w, loras: [], stats: getStats(w.id) })),
    { workerId: '__job_application', profile: null, loras: [], stats: null }
  ]

  const [currentIdx, setCurrentIdx] = useState(0)
  const [animating, setAnimating]   = useState(false)
  const [direction, setDirection]   = useState<'next'|'prev'>('next')

  const navigate = (dir: 'next' | 'prev') => {
    if (animating) return  // block double-tap
    setDirection(dir)
    setAnimating(true)
    setTimeout(() => {
      setCurrentIdx(i =>
        dir === 'next'
          ? (i + 1) % papers.length
          : (i - 1 + papers.length) % papers.length
      )
      setAnimating(false)
    }, 225)  // half of 450ms total
  }

  // Keyboard nav
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') navigate('next')
      if (e.key === 'ArrowLeft')  navigate('prev')
      if (e.key === 'Escape')     onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [animating])

  return (
    <div className="ceo-overlay" onClick={onClose}>
      <div className="paper-stack" onClick={e => e.stopPropagation()}>
        {/* Stack visual di belakang (2-3 kertas placeholder) */}
        <div className="paper-bg paper-bg-2" />
        <div className="paper-bg paper-bg-1" />

        {/* Kertas aktif */}
        <div className={`paper-active ${animating ? `paper-flip-${direction}` : ''}`}>
          {papers[currentIdx].workerId === '__job_application'
            ? <JobApplication onHire={handleHire} />
            : <WorkerPaper paper={papers[currentIdx]} />
          }
        </div>

        {/* Navigation */}
        <div className="paper-nav">
          <button onClick={() => navigate('prev')}>←</button>
          <span className="paper-counter">{currentIdx + 1} / {papers.length}</span>
          <button onClick={() => navigate('next')}>→</button>
        </div>

        {/* Close button */}
        <button className="paper-close" onClick={onClose}>×</button>
      </div>
    </div>
  )
}
```

---

## Animasi Kertas

```css
/* Flip ke belakang: 450ms total */
@keyframes paper-flip-next {
  0%   { transform: translateY(0) rotateX(0deg) scale(1);
         z-index: 10; opacity: 1; }
  20%  { transform: translateY(-24px) rotateX(-15deg) scale(1.04); }
  50%  { transform: translateY(-28px) rotateX(-90deg) scale(1);
         z-index: 0; opacity: 0; }
  75%  { transform: translateY(-8px) rotateX(10deg) scale(0.96); opacity: 0.8; }
  100% { transform: translateY(0) rotateX(0deg) scale(1);
         z-index: 0; opacity: 1; }
}

/* Flip ke depan */
@keyframes paper-flip-prev {
  0%   { transform: translateY(0) rotateX(0deg) scale(1); opacity: 1; }
  20%  { transform: translateY(24px) rotateX(15deg) scale(1.04); }
  50%  { transform: translateY(28px) rotateX(90deg) scale(1); opacity: 0; }
  75%  { transform: translateY(8px) rotateX(-10deg) scale(0.96); opacity: 0.8; }
  100% { transform: translateY(0) rotateX(0deg) scale(1); opacity: 1; }
}

.paper-flip-next { animation: paper-flip-next 450ms ease-in-out; }
.paper-flip-prev { animation: paper-flip-prev 450ms ease-in-out; }

/* Paper styling — FectTral dark card */
.paper-stack {
  position: relative;
  width: 320px;
  perspective: 800px;
}
.paper-active, .paper-bg {
  background: var(--bg-card);
  border: 1px solid var(--border-mid);
  border-radius: 4px;
  padding: 20px;
  width: 100%;
}
.paper-bg {
  position: absolute;
  pointer-events: none;
}
.paper-bg-1 {
  top: -4px; left: -4px; right: -4px;
  opacity: 0.7;
  transform: rotate(-1deg);
}
.paper-bg-2 {
  top: -8px; left: -8px; right: -8px;
  opacity: 0.4;
  transform: rotate(-2deg);
}
```

---

## Isi Kertas Worker (WorkerPaper Component)

```typescript
function WorkerPaper({ paper }: { paper: WorkerPaper }) {
  const { profile, loras, stats } = paper
  const [section, setSection] = useState<'identity'|'personality'|'stats'|'brain'>('identity')
  const [confirmFire, setConfirmFire] = useState(false)

  return (
    <div className="worker-paper">
      {/* Header */}
      <div className="paper-header">
        <span className="paper-emoji">{profile.badge_emoji}</span>
        <div>
          <div className="paper-display-name">{profile.display_name}</div>
          <div className="paper-role">{profile.id}</div>
        </div>
        <span className="paper-status-badge" style={{ color: profile.status === 'active' ? '#44ff88' : '#ffaa00' }}>
          {profile.status.toUpperCase()}
        </span>
      </div>

      {/* Tab nav */}
      <div className="paper-tabs">
        {(['identity','personality','stats','brain'] as const).map(t => (
          <button
            key={t}
            className={`paper-tab ${section === t ? 'active' : ''}`}
            onClick={() => setSection(t)}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Section content */}
      {section === 'identity' && <IdentitySection profile={profile} />}
      {section === 'personality' && <PersonalitySection profile={profile} />}
      {section === 'stats' && <StatsSection stats={stats} />}
      {section === 'brain' && <BrainSection loras={loras} workerId={profile.id} />}

      {/* Actions */}
      <div className="paper-actions">
        {!confirmFire ? (
          <>
            <button
              className="paper-btn-secondary"
              onClick={() => toggleActivation(profile.id)}
            >
              {profile.status === 'active' ? 'deactivate' : 'activate'}
            </button>
            <button
              className="paper-btn-danger"
              onClick={() => setConfirmFire(true)}
            >
              fire
            </button>
          </>
        ) : (
          <div className="paper-fire-confirm">
            <span>are you sure? {profile.display_name} will leave permanently.</span>
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button className="paper-btn-danger" onClick={() => fireWorker(profile.id)}>
                yes, fire
              </button>
              <button className="paper-btn-secondary" onClick={() => setConfirmFire(false)}>
                cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
```

---

## Brain Section (Tab di Worker Paper)

Visible Fase 2 tapi placeholder — aktif Fase 4 saat trainer ada.

```typescript
function BrainSection({ loras, workerId }: { loras: LoRAMetadata[]; workerId: string }) {
  if (loras.length === 0) {
    return (
      <div className="brain-empty">
        <div className="brain-empty-icon">🧠</div>
        <div className="brain-empty-msg">no LoRA adapters yet</div>
        <div className="brain-empty-sub">
          available after trainer collects enough episodes
        </div>
      </div>
    )
  }

  return (
    <div className="brain-section">
      {loras.map(lora => (
        <div key={lora.name} className="lora-row">
          <div className="lora-info">
            <span className="lora-name">{lora.name}</span>
            <span className="lora-domain">{lora.domain}</span>
            <span className="lora-delta" style={{ color: '#44ff88' }}>
              {lora.performance_delta}
            </span>
          </div>
          <div className="lora-controls">
            {/* Weight slider */}
            <input
              type="range" min="0" max="1" step="0.1"
              value={lora.weight}
              onChange={e => updateLoRAWeight(workerId, lora.name, parseFloat(e.target.value))}
            />
            <span className="lora-weight">{lora.weight}</span>
            {/* Toggle */}
            <button
              className={`lora-toggle ${lora.status === 'active' ? 'on' : 'off'}`}
              onClick={() => toggleLoRA(workerId, lora.name)}
            >
              {lora.status === 'active' ? 'ON' : 'OFF'}
            </button>
          </div>
          {/* Side effects warning */}
          {lora.side_effects && Object.keys(lora.side_effects).length > 0 && (
            <div className="lora-side-effects">
              ⚠ side effects: {Object.entries(lora.side_effects)
                .map(([k,v]) => `${k}: ${v}`)
                .join(', ')}
            </div>
          )}
        </div>
      ))}

      <button
        className="paper-btn-secondary"
        onClick={() => requestTrainerRefactor(workerId)}
        style={{ marginTop: 8, width: '100%' }}
      >
        🧪 request trainer to refactor
      </button>
    </div>
  )
}
```

---

## Fire Animation

```css
@keyframes paper-tear {
  0%   { clip-path: inset(0 0 0 0); transform: rotate(0deg); }
  30%  { transform: rotate(-1.5deg); }
  45%  { clip-path: inset(0 0 50% 0); transform: rotate(-2deg); }
  60%  { clip-path: inset(50% 0 0 0); transform: rotate(1deg); }
  100% { clip-path: inset(50% 0 0 0); opacity: 0; transform: rotate(2deg); }
}

.paper-firing { animation: paper-tear 500ms ease-in forwards; }
```

Di pixel art, worker yang di-fire:
1. Jalan ke pintu entrance (tile paling kiri / bawah map)
2. Wave animation: sprite row 0, speed lambat, posisi X terus berkurang
3. `opacity` turun dari 1 → 0 dalam 1 detik
4. Hapus dari workers map

---

## Hire Flow (Job Application)

```typescript
function JobApplication({ onHire }: { onHire: (profile: WorkerProfile) => void }) {
  const [form, setForm] = useState({
    id: '', display_name: '', badge_emoji: '🤖',
    role: 'coder_rust' as WorkerRole,
    model: 'qwen2.5-coder:7b',
    tone: 'casual' as Tone,
    catchphrase: '',
  })

  return (
    <div className="job-application">
      <div className="paper-header">
        <span>📋</span>
        <div>
          <div className="paper-display-name">JOB APPLICATION</div>
          <div className="paper-role">hire a new worker</div>
        </div>
      </div>

      {/* Form fields — FectTral glow input style */}
      <div className="form-group">
        <label>Worker ID</label>
        <input className="fectral-input" placeholder="e.g. coder_go"
          value={form.id} onChange={e => setForm({...form, id: e.target.value})} />
      </div>
      <div className="form-group">
        <label>Display Name</label>
        <input className="fectral-input" placeholder="e.g. Gopher"
          value={form.display_name} onChange={e => setForm({...form, display_name: e.target.value})} />
      </div>
      <div className="form-group">
        <label>Role</label>
        <select className="fectral-select" value={form.role}
          onChange={e => setForm({...form, role: e.target.value as WorkerRole})}>
          <option value="coder_rust">coder_rust</option>
          <option value="coder_css">coder_css</option>
          <option value="coder_js">coder_js</option>
          <option value="coder_python">coder_python</option>
          <option value="tester">tester</option>
          <option value="scribe">scribe</option>
          {/* tambahkan sesuai workers.md */}
        </select>
      </div>
      <div className="form-group">
        <label>Catchphrase</label>
        <input className="fectral-input" placeholder="e.g. no bugs, only features."
          value={form.catchphrase} onChange={e => setForm({...form, catchphrase: e.target.value})} />
      </div>

      <button
        className="paper-btn-primary"
        disabled={!form.id || !form.display_name}
        onClick={() => onHire(form)}
      >
        hire →
      </button>
    </div>
  )
}
```

Animasi hire: kertas fold + fade → masuk laci (200ms) → toast "joined!" →
worker spawn di pintu kantor, jalan ke break room, catchphrase speech bubble.

---

## Auto-save

Setiap kali: navigasi ke kertas lain, tutup overlay, atau edit field.
Atomic write: tulis `workers.tmp.json` → rename ke `workers.json`.

```typescript
function autoSave(workers: WorkerProfile[]) {
  const tmp  = '~/.vibe-office/workers.tmp.json'
  const dest = '~/.vibe-office/workers.json'
  writeFile(tmp, JSON.stringify(workers, null, 2))
  rename(tmp, dest)  // atomic
}
```

---

## Checklist Fase 2 CEO Office

```
[ ] Klik meja conductor → paper stack muncul
[ ] Flip next/prev bekerja (keyboard ← → juga)
[ ] Animasi 450ms tidak bisa di-interrupt
[ ] Setiap worker punya kertas sendiri
[ ] Tab: identity / personality / stats / brain
[ ] Brain tab: placeholder "no LoRA yet" untuk Fase 1-3
[ ] Fire: konfirmasi inline (bukan popup), animasi tear
[ ] Worker di-fire jalan ke pintu dan fade out
[ ] Job Application form bisa hire worker baru
[ ] Worker hire spawn di pintu, jalan ke break room
[ ] Auto-save setiap navigasi / edit
```
