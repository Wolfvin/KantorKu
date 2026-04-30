# Frontend — Chat Panel (Fase 2)

> Sidebar kanan. Satu-satunya cara kamu komunikasi dengan sistem.
> Di Fase 2: UI lengkap dengan FectTral style. Di Fase 3: terhubung ke backend AI.
> Di Fase 2, hanya command `/status`, `/workers`, dan `/pause` yang fungsional.
> Sisanya echo balik sebagai placeholder.

---

## Layout

```
┌─────────────────────────────────────────────┐
│  VIBE-OFFICE         🟢 connected    ≡ menu │  ← topbar
├─────────────────────────────────────────────┤
│                                             │
│  [system]  session started                  │
│                                             │
│  [conductor]  I'll assign that to Rusty.    │
│               ─────────────────────────     │
│                                             │
│  [you]  buatin fungsi parse JSON dari file  │
│                                             │
│  [output]  ┌─ coder_rust ──────────────┐   │
│            │ fn parse_json(path: &str)  │   │
│            │ → Result<Value, Error> {   │   │
│            │ ...                        │   │
│            │ [expand ↓] [copy]          │   │
│            └────────────────────────────┘   │
│                                             │
├─────────────────────────────────────────────┤
│  [input area]                    [send →]   │
└─────────────────────────────────────────────┘
```

Width: 300px fixed. Background: `--bg-panel`. Topbar: 40px. Input area: 60px.

---

## Message Types

```typescript
type MessageType =
  | 'client'   // kamu kirim — bubble kanan, --blue-core border
  | 'system'   // info sistem — teks muted di tengah
  | 'worker'   // worker kirim — bubble kiri + badge emoji
  | 'output'   // kode output — card collapsible
  | 'error'    // error card — merah, ada action buttons

interface Message {
  id: string
  type: MessageType
  content: string
  worker_id?: string     // untuk tipe 'worker' dan 'output'
  code?: string          // untuk tipe 'output' — kode lengkap
  timestamp: string      // "HH:MM"
  collapsed?: boolean    // untuk tipe 'output', default true kalau >10 baris
}
```

```typescript
// Rendering per type
function MessageBubble({ msg }: { msg: Message }) {
  switch (msg.type) {
    case 'client':
      return <div className="msg-client">{msg.content}</div>

    case 'system':
      return <div className="msg-system">{msg.content}</div>

    case 'worker':
      const w = getWorker(msg.worker_id!)
      return (
        <div className="msg-worker">
          <span className="msg-badge">{w?.badge_emoji}</span>
          <div>
            <span className="msg-worker-name">{w?.display_name ?? msg.worker_id}</span>
            <div className="msg-content">{msg.content}</div>
          </div>
        </div>
      )

    case 'output':
      return <OutputCard msg={msg} />

    case 'error':
      return <ErrorCard msg={msg} />
  }
}
```

---

## Output Card (Kode Collapsible)

```typescript
function OutputCard({ msg }: { msg: Message }) {
  const [collapsed, setCollapsed] = useState(
    (msg.code?.split('\n').length ?? 0) > 10
  )
  const lines = msg.code?.split('\n') ?? []

  return (
    <div className="output-card">
      <div className="output-header">
        <span className="output-worker">{msg.worker_id}</span>
        <span className="output-lines">{lines.length} lines</span>
        <button className="output-copy" onClick={() => copyToClipboard(msg.code!)}>
          copy
        </button>
      </div>
      <pre className={`output-code ${collapsed ? 'collapsed' : ''}`}>
        <code>{collapsed ? lines.slice(0,8).join('\n') + '\n...' : msg.code}</code>
      </pre>
      {lines.length > 10 && (
        <button className="output-toggle" onClick={() => setCollapsed(!collapsed)}>
          {collapsed ? `expand ↓ (${lines.length} lines)` : 'collapse ↑'}
        </button>
      )}
    </div>
  )
}
```

```css
.output-card {
  background: var(--bg-void);
  border: 1px solid var(--border-mid);
  border-radius: 3px;
  margin: 4px 0;
  overflow: hidden;
}
.output-header {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 8px;
  background: var(--bg-deep);
  border-bottom: 1px solid var(--border-dim);
  font-family: var(--font-mono); font-size: 9px;
}
.output-worker { color: var(--blue-core); }
.output-lines  { color: var(--text-muted); margin-left: auto; }
.output-copy   {
  background: none; border: 1px solid var(--border-dim);
  color: var(--text-secondary); cursor: pointer;
  font-family: var(--font-mono); font-size: 8px; padding: 1px 5px;
}
.output-copy:hover { border-color: var(--blue-core); color: var(--blue-core); }
.output-code {
  padding: 8px; font-family: var(--font-mono); font-size: 9px;
  color: var(--text-primary); white-space: pre-wrap; overflow-x: auto;
  margin: 0; max-height: 300px; overflow-y: auto;
}
.output-code.collapsed { max-height: 120px; }
.output-toggle {
  display: block; width: 100%;
  background: none; border: none; border-top: 1px solid var(--border-dim);
  color: var(--blue-dim); cursor: pointer;
  font-family: var(--font-mono); font-size: 8px; padding: 4px;
}
.output-toggle:hover { color: var(--blue-core); }
```

---

## Error Card (Tier 3 Escalation)

```typescript
function ErrorCard({ msg }: { msg: Message }) {
  return (
    <div className="error-card">
      <div className="error-header">
        <span>{getWorker(msg.worker_id!)?.badge_emoji} {getWorker(msg.worker_id!)?.display_name} needs help</span>
        <span className="error-time">{msg.timestamp}</span>
      </div>
      <div className="error-body">
        <div className="error-line"><span className="error-label">Task:</span> {msg.task}</div>
        <div className="error-line"><span className="error-label">Tried:</span> {msg.tried} × {msg.retries}</div>
        <div className="error-line"><span className="error-label">Blocker:</span> {msg.blocker}</div>
      </div>
      <div className="error-actions">
        <button
          className="error-btn-primary"
          onClick={() => prefillInput(`@${msg.worker_id} re: `)}
        >
          give new instruction
        </button>
        <button className="error-btn-secondary" onClick={() => skipTask(msg.task_id)}>
          skip
        </button>
        <button className="error-btn-secondary error-btn-stop" onClick={pausePipeline}>
          stop
        </button>
      </div>
    </div>
  )
}
```

```css
.error-card {
  background: rgba(255, 68, 68, 0.08);
  border: 1px solid rgba(255, 68, 68, 0.4);
  border-radius: 4px;
  padding: 10px;
  box-shadow: 0 0 12px rgba(255,68,68,0.2);
}
.error-header {
  display: flex; justify-content: space-between;
  font-family: var(--font-display); font-size: 10px;
  color: #ff6b6b; margin-bottom: 8px;
}
.error-time { color: var(--text-muted); }
.error-body { font-size: 9px; color: var(--text-secondary); margin-bottom: 10px; }
.error-line { margin-bottom: 3px; }
.error-label { color: var(--text-muted); }
.error-actions { display: flex; gap: 6px; }
.error-btn-primary {
  flex: 1; background: rgba(0,170,255,0.1);
  border: 1px solid var(--blue-core); color: var(--blue-bright);
  font-family: var(--font-mono); font-size: 8px; cursor: pointer;
  padding: 5px; border-radius: 2px;
}
.error-btn-secondary {
  background: none; border: 1px solid var(--border-mid);
  color: var(--text-muted); font-family: var(--font-mono);
  font-size: 8px; cursor: pointer; padding: 5px; border-radius: 2px;
}
.error-btn-stop { border-color: rgba(255,68,68,0.4); color: #ff6b6b; }
```

---

## Command System

```typescript
// Ketik "/" → command palette muncul di atas input
const COMMANDS = [
  { cmd: '/status',          args: '[worker_id]', desc: 'lihat status satu atau semua workers' },
  { cmd: '/workers',         args: '',            desc: 'list semua workers + state + room' },
  { cmd: '/assign',          args: '[worker] [task]', desc: 'force assign task ke worker' },
  { cmd: '/pause',           args: '',            desc: 'pause semua workers' },
  { cmd: '/resume',          args: '',            desc: 'resume workers' },
  { cmd: '/cancel',          args: '[task_id]',   desc: 'cancel task pending' },
  { cmd: '/history',         args: '[n]',         desc: 'n task terakhir (default 10)' },
  { cmd: '/log',             args: '',            desc: 'activity log penuh' },
  { cmd: '/switch',          args: '[project]',   desc: 'ganti project' },
  { cmd: '/save',            args: '',            desc: 'force save session' },
  { cmd: '/clear',           args: '',            desc: 'clear chat display' },
]

function CommandPalette({ query, onSelect }: { query: string; onSelect: (cmd: string) => void }) {
  const filtered = COMMANDS.filter(c => c.cmd.includes(query))
  if (filtered.length === 0) return null

  return (
    <div className="cmd-palette">
      {filtered.map(c => (
        <button key={c.cmd} className="cmd-item" onClick={() => onSelect(c.cmd + ' ')}>
          <span className="cmd-name">{c.cmd}</span>
          <span className="cmd-args">{c.args}</span>
          <span className="cmd-desc">{c.desc}</span>
        </button>
      ))}
    </div>
  )
}
```

---

## Input Area

```typescript
function ChatInput({ onSend }: { onSend: (msg: string) => void }) {
  const [value, setValue] = useState('')
  const [showPalette, setShowPalette] = useState(false)
  const [history, setHistory] = useState<string[]>([])
  const [histIdx, setHistIdx] = useState(-1)

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (value.trim()) {
        onSend(value.trim())
        setHistory(h => [value, ...h.slice(0, 49)])
        setHistIdx(-1)
        setValue('')
      }
    }
    if (e.key === 'ArrowUp' && !value) {
      // Recall history
      const idx = histIdx + 1
      if (idx < history.length) {
        setHistIdx(idx)
        setValue(history[idx])
      }
    }
    if (e.key === 'Escape') {
      setShowPalette(false)
    }
    if (e.key === '/' && !value) {
      setShowPalette(true)
    }
  }

  return (
    <div className="chat-input-area">
      {showPalette && (
        <CommandPalette
          query={value}
          onSelect={cmd => { setValue(cmd); setShowPalette(false) }}
        />
      )}
      <textarea
        className="fectral-textarea"
        value={value}
        placeholder="what should the team work on?"
        onKeyDown={handleKeyDown}
        onChange={e => {
          setValue(e.target.value)
          setShowPalette(e.target.value.startsWith('/'))
        }}
        rows={2}
      />
      <button
        className="chat-send-btn"
        disabled={!value.trim()}
        onClick={() => { onSend(value.trim()); setValue('') }}
      >
        send →
      </button>
    </div>
  )
}
```

---

## Checklist Fase 2 Chat Panel

```
[ ] Semua message types render dengan benar (client/system/worker/output/error)
[ ] Output card: collapsible kalau > 10 baris, copy button bekerja
[ ] Error card: 3 buttons bekerja (new instruction, skip, stop)
[ ] "/" trigger command palette
[ ] Keyboard: Enter kirim, Shift+Enter newline, ↑ recall history, Esc tutup palette
[ ] Scroll otomatis ke bawah saat pesan baru masuk
[ ] Pesan tidak hilang saat resize window
```
