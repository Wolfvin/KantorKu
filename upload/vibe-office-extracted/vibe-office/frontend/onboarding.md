# Frontend — Onboarding (Fase 2)

> Target: dari buka pertama kali → workers jalan dalam < 5 menit.

---

## Decision Tree Saat Buka App

```typescript
async function onAppStart() {
  const projects = await loadProjects()  // ~/.vibe-office/projects.json

  if (projects.length > 0) {
    // Langsung load session terakhir
    const last = projects.sort((a,b) => b.last_opened - a.last_opened)[0]
    await loadSession(last.id)
    showGame()
  } else {
    // Pertama kali — tampilkan wizard
    showWelcomeScreen()
  }
}
```

---

## Welcome Screen (Sebelum Wizard)

```
┌──────────────────────────────────────────────┐
│                                              │
│     ██╗   ██╗██╗██████╗ ███████╗            │
│     ██║   ██║██║██╔══██╗██╔════╝            │
│     ██║   ██║██║██████╔╝█████╗              │
│     ╚██╗ ██╔╝██║██╔══██╗██╔══╝              │
│      ╚████╔╝ ██║██████╔╝███████╗            │
│       ╚═══╝  ╚═╝╚═════╝ ╚══════╝            │
│          OFFICE                              │
│                                              │
│   AI workers that actually code for you.    │
│                                              │
│         [ GET STARTED → ]                   │
│                                              │
└──────────────────────────────────────────────┘
```

FectTral style: `--bg-void` background, glitch text effect pada "VIBE OFFICE",
starfield canvas, scan beam. Tombol GET STARTED → 4-step wizard.

---

## 4-Step Wizard

### Step 1 — Project Directory

```typescript
function Step1({ onNext }: StepProps) {
  const [path, setPath] = useState('')
  const [valid, setValid] = useState<null | 'rust' | 'js' | 'python' | 'unknown'>(null)

  async function browse() {
    // Tauri dialog
    const selected = await open({ directory: true })
    if (!selected) return
    setPath(selected as string)

    // Detect project type
    const hasCargo  = await exists(`${selected}/Cargo.toml`)
    const hasPkg    = await exists(`${selected}/package.json`)
    const hasPyproj = await exists(`${selected}/pyproject.toml`)

    setValid(hasCargo ? 'rust' : hasPkg ? 'js' : hasPyproj ? 'python' : 'unknown')
  }

  return (
    <div className="wizard-step">
      <div className="wizard-step-num">01 / 04</div>
      <h2 className="wizard-title">SELECT PROJECT</h2>
      <p className="wizard-desc">Where is your codebase?</p>

      <div className="wizard-path-row">
        <input className="fectral-input" value={path} readOnly placeholder="/path/to/your/project" />
        <button className="paper-btn-primary" onClick={browse}>browse</button>
      </div>

      {valid === 'rust'    && <div className="wizard-ok">✓ Rust project detected (Cargo.toml)</div>}
      {valid === 'js'      && <div className="wizard-ok">✓ JS/TS project detected (package.json)</div>}
      {valid === 'python'  && <div className="wizard-ok">✓ Python project detected (pyproject.toml)</div>}
      {valid === 'unknown' && (
        <div className="wizard-warn">
          ⚠ No known project file found — workers will still work but without project context
        </div>
      )}

      <button className="paper-btn-primary wizard-next"
        disabled={!path} onClick={() => onNext({ project_path: path, project_type: valid })}>
        next →
      </button>
    </div>
  )
}
```

### Step 2 — Project Name

```typescript
function Step2({ data, onNext }: StepProps) {
  // Auto-suggest dari folder name
  const suggested = data.project_path.split('/').pop() ?? 'my-project'
  const [name, setName] = useState(suggested)

  return (
    <div className="wizard-step">
      <div className="wizard-step-num">02 / 04</div>
      <h2 className="wizard-title">PROJECT NAME</h2>
      <input className="fectral-input" value={name}
        onChange={e => setName(e.target.value)} />
      <button className="paper-btn-primary wizard-next"
        disabled={!name.trim()} onClick={() => onNext({ project_name: name })}>
        next →
      </button>
    </div>
  )
}
```

### Step 3 — Meet the Team

```typescript
function Step3({ onNext }: StepProps) {
  // Tampilkan 6 workers utama sebagai preview
  const preview = [
    { id: 'conductor',   emoji: '👔', role: 'CEO — orchestrates everything' },
    { id: 'coder_rust',  emoji: '🦀', role: 'writes & debugs Rust code' },
    { id: 'tester',      emoji: '🧪', role: 'writes & runs tests' },
    { id: 'auditor',     emoji: '🔍', role: 'reviews code quality' },
    { id: 'scout',       emoji: '🔭', role: 'researches codebase context' },
    { id: 'chronicler',  emoji: '📚', role: 'manages git commits' },
  ]

  return (
    <div className="wizard-step">
      <div className="wizard-step-num">03 / 04</div>
      <h2 className="wizard-title">MEET THE TEAM</h2>
      <p className="wizard-desc">Your default workers. Customize names & personalities later in CEO office.</p>

      <div className="wizard-team-grid">
        {preview.map(w => (
          <div key={w.id} className="wizard-worker-card">
            <span className="wizard-worker-emoji">{w.emoji}</span>
            <span className="wizard-worker-id">{w.id}</span>
            <span className="wizard-worker-role">{w.role}</span>
          </div>
        ))}
      </div>

      <p className="wizard-footnote">+{25 - preview.length} more workers available to hire</p>

      <div className="wizard-nav">
        <button className="paper-btn-secondary" onClick={() => onNext({})}>skip</button>
        <button className="paper-btn-primary" onClick={() => onNext({})}>nice, let's go →</button>
      </div>
    </div>
  )
}
```

### Step 4 — LLM Backend

```typescript
function Step4({ onFinish }: StepProps) {
  const [backend, setBackend] = useState<'ollama' | 'api'>('ollama')
  const [ollamaOk, setOllamaOk] = useState<null | boolean>(null)
  const [apiKey, setApiKey] = useState('')

  async function checkOllama() {
    try {
      const res = await fetch('http://localhost:11434/api/tags')
      setOllamaOk(res.ok)
    } catch {
      setOllamaOk(false)
    }
  }

  useEffect(() => { if (backend === 'ollama') checkOllama() }, [backend])

  return (
    <div className="wizard-step">
      <div className="wizard-step-num">04 / 04</div>
      <h2 className="wizard-title">LLM BACKEND</h2>

      <div className="wizard-radio-group">
        <label className={`wizard-radio ${backend === 'ollama' ? 'selected' : ''}`}>
          <input type="radio" value="ollama" checked={backend === 'ollama'}
            onChange={() => setBackend('ollama')} />
          <div>
            <strong>Ollama</strong> — local, free, private
            {ollamaOk === true  && <span className="wizard-ok"> ✓ running</span>}
            {ollamaOk === false && (
              <span className="wizard-warn">
                {' '}⚠ not detected —{' '}
                <a href="https://ollama.ai" target="_blank">install at ollama.ai</a>
                {' '}then run: <code>ollama pull qwen2.5-coder:7b</code>
              </span>
            )}
          </div>
        </label>

        <label className={`wizard-radio ${backend === 'api' ? 'selected' : ''}`}>
          <input type="radio" value="api" checked={backend === 'api'}
            onChange={() => setBackend('api')} />
          <div>
            <strong>API Key</strong> — faster, smarter (Anthropic/OpenRouter)
            {backend === 'api' && (
              <input className="fectral-input" type="password"
                placeholder="sk-..." value={apiKey}
                onChange={e => setApiKey(e.target.value)} />
            )}
          </div>
        </label>
      </div>

      <button
        className="paper-btn-primary wizard-next"
        disabled={backend === 'ollama' && ollamaOk !== true && !apiKey}
        onClick={() => onFinish({ backend, apiKey })}
      >
        launch vibe-office →
      </button>
    </div>
  )
}
```

---

## Post-Wizard: Worker Spawn Sequence

```typescript
async function spawnWorkersSequentially(workers: WorkerProfile[]) {
  for (const w of workers) {
    // Kirim ke backend via WebSocket
    sendToBackend({ type: 'spawn_worker', worker: w })

    // Animasi: worker muncul di pintu, jalan ke room default
    await animateWorkerEntry(w)

    // Speech bubble: catchphrase
    setTimeout(() => {
      showSpeechBubble(w.id, w.catchphrase, '#00aaff', 2000)
    }, 500)

    await sleep(200)  // stagger antar spawn
  }

  // Setelah semua spawn: mulai tutorial tooltips
  startTutorialFlow()
}

async function animateWorkerEntry(w: WorkerProfile) {
  // Worker muncul di entrance tile (x:0, y: map_height/2)
  spawnAt(w.id, { x: 0, y: Math.floor(MAP_H / 2) })

  // Jalan ke default room
  const target = findSpawnTileInZone(DEFAULT_ROOMS[w.id] ?? 'break_room')
  await walkTo(w.id, target)
}
```

---

## Tutorial Tooltips (3 Langkah Berurutan)

```typescript
const TUTORIALS = [
  {
    target: '#chat-input',
    text: 'type a task here to get started →',
    position: 'above',
    arrow: 'right',
  },
  {
    target: null,  // highlight random worker
    text: 'click any worker to see what they\'re up to',
    position: 'center',
  },
  {
    target: '#tv-screen',
    text: 'watch the TV for live updates 📺',
    position: 'below',
    arrow: 'up',
  },
]

function TutorialTooltip({ step, onDismiss }: { step: number; onDismiss: () => void }) {
  const t = TUTORIALS[step]
  if (!t) return null

  return (
    <div className="tutorial-tooltip" data-position={t.position}>
      <span>{t.text}</span>
      <button onClick={onDismiss}>got it</button>
    </div>
  )
}
// Setiap user interact (klik, ketik) → dismiss tooltip saat ini → tampilkan berikutnya
// Setelah tooltip ke-3 dismiss → konfetti pixel art
```

---

## Empty State

Saat kantor idle (tidak ada task aktif):
- TV screen: `"waiting for your next task..."`
- Chat input placeholder: `"what should the team work on?"`
- Workers wander random di break room (idle state, jalan pelan)
- Setiap 10-20 detik, satu worker random tampilkan speech bubble dari `idle_phrases`
- Jika kantor sudah lama idle (>5 menit), satu worker tidur di dormitory

---

## Checklist Fase 2 Onboarding

```
[ ] Welcome screen tampil saat pertama kali buka
[ ] 4-step wizard berjalan dengan benar
[ ] Step 1: detect project type (Rust/JS/Python/unknown)
[ ] Step 4: cek Ollama running, tampilkan link install kalau tidak ada
[ ] Workers spawn satu per satu dengan animasi masuk dari pintu
[ ] Speech bubble catchphrase saat spawn
[ ] 3 tutorial tooltips dismiss berurutan
[ ] Konfetti setelah tooltip terakhir
[ ] Empty state: workers wander, TV placeholder, chat placeholder
```
