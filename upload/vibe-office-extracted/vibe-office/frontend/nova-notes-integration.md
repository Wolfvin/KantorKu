# Frontend — NovaNotes Integration (Fase 2+)

> **Konteks untuk session baru:**
> NovaNotes adalah markdown editor dengan enkripsi AES-256-GCM yang di-embed
> ke dalam vibe-office sebagai panel di server machine di Lab Room.
> Source: NovaNotes.jsx (file asli dari Wolfvin) — dimodifikasi untuk:
>   1. Lazy load: sidebar hanya tampilkan judul, isi di-load saat dibuka
>   2. Disk persist: simpan ke ~/.vibe-office/notes/ via Tauri fs plugin
>   3. Enkripsi OFF by default, bisa di-enable per-note
>   4. "Send to Curator" button — trigger knowledge ingestion pipeline
> File terkait:
>   - `backend/knowledge-ingestion.md` → curator auto-process paste
>   - `frontend/fsm-rooms.md` → Lab Room + server machine tile

---

## Cara Akses

```
Lab Room → klik salah satu server machine tile
  ↓
Panel NovaNotes muncul (tidak full screen, ~70% width)
  tombol maximize → full screen
  tombol X → tutup panel
  game tetap berjalan di background (tidak di-pause)
```

---

## Perubahan dari NovaNotes.jsx Asli

### 1. Lazy Load Notes

```typescript
// SEBELUM (NovaNotes.jsx asli):
// Semua notes ada di state dengan full content — load semua sekaligus

// SESUDAH:
interface NoteIndex {
  id: number
  title: string
  updatedAt: Date
  wordCount: number
  domain?: string[]       // dari curator — terisi setelah di-process
  encrypted: boolean
  // TIDAK ada content di sini
}

interface NoteContent {
  id: number
  content: string         // di-load on demand
}

// State:
const [noteIndex, setNoteIndex] = useState<NoteIndex[]>([])  // load saat panel buka
const [loadedContent, setLoadedContent] = useState<Record<number, string>>({})  // cache

async function loadNoteContent(id: number): Promise<string> {
  if (loadedContent[id]) return loadedContent[id]  // cache hit

  const content = await invoke('read_note_content', { id })
  setLoadedContent(prev => ({ ...prev, [id]: content }))
  return content
}

// Saat user klik note di sidebar:
const handleSelectNote = async (id: number) => {
  setActiveId(id)
  await loadNoteContent(id)  // load baru saat dibutuhkan
}
```

### 2. Disk Persist via Tauri

```typescript
// Struktur file di disk:
// ~/.vibe-office/notes/
//   index.json          ← NoteIndex[] — judul, metadata, NO content
//   content/
//     {id}.md           ← raw content (kalau tidak terenkripsi)
//     {id}.nova         ← encrypted content (kalau per-note enkripsi ON)

// Tauri commands (src-tauri/src/commands.rs):
// invoke('load_notes_index')       → NoteIndex[]
// invoke('read_note_content', {id}) → string
// invoke('save_note_content', {id, content, encrypted, password?}) → void
// invoke('delete_note', {id})      → void
```

### 3. Enkripsi Per-Note

```typescript
// Di NoteIndex, field: encrypted: boolean (default false)
// Enkripsi AES-256-GCM sudah ada di NovaNotes.jsx asli — tinggal pakai

// UI di note item (sidebar):
<div className="note-item" onClick={() => handleSelectNote(note.id)}>
  <div className="note-item-title">
    {note.encrypted && <span className="note-lock-icon">🔒</span>}
    {note.title}
  </div>
  <div className="note-item-meta">
    {note.domain?.map(d => (
      <span key={d} className="domain-badge">{d}</span>  // dari curator
    ))}
  </div>
  <div className="note-item-date">{formatDate(note.updatedAt)}</div>
</div>

// Kalau note.encrypted = true → saat load content → minta password dulu (modal)
// Toggle enkripsi: settings icon di note → "Enable Encryption for this note"
```

### 4. "Send to Curator" Button

```typescript
// Di topbar NovaNotes, tombol baru:
<button
  className="btn btn-curator"
  onClick={() => handleSendToCurator()}
  disabled={curatorProcessing}
>
  {curatorProcessing ? '🔍 Processing...' : '🧠 Send to Curator'}
</button>

// Handler:
async function handleSendToCurator() {
  if (!activeNote) return
  setCuratorProcessing(true)

  // Kirim via WebSocket ke backend
  wsClient.send({
    type: 'knowledge_ingest',
    source: 'nova_notes',
    note_id: activeNote.id,
    title: activeNote.title,
    content: loadedContent[activeNote.id],
  })

  // Listen untuk response
  wsClient.once('knowledge_ingest_done', (data) => {
    setCuratorProcessing(false)

    // Update domain badges di note index
    updateNoteIndex(activeNote.id, { domain: data.domains })

    showToast(`✓ Curator: ${data.domains.join(', ')} — ${data.skill_updated ? 'SKILL.md updated' : 'logged'}`, 'success')
  })
}
```

---

## Auto-Trigger saat Paste Panjang

```typescript
// Di textarea onChange handler (modifikasi dari updateContent asli):

const updateContent = useCallback((value: string) => {
  // Update content seperti biasa
  setNotes(ns => ns.map(n => n.id === activeId ? { ...n, content: value } : n))
  setCharCount(value.length)

  // Auto-trigger curator kalau paste besar (> 300 kata baru)
  const wordsBefore = (loadedContent[activeId] ?? '').trim().split(/\s+/).length
  const wordsAfter = value.trim().split(/\s+/).length
  const wordsAdded = wordsAfter - wordsBefore

  if (wordsAdded > 300 && !curatorProcessing) {
    // Delay 2 detik — pastikan user sudah selesai paste
    clearTimeout(curatorDebounceRef.current)
    curatorDebounceRef.current = setTimeout(() => {
      showToast('🔍 Curator detected large paste — processing...', 'info')
      handleSendToCurator()
    }, 2000)
  }
}, [activeId, loadedContent, curatorProcessing])
```

---

## UI Additions — Domain Badges

```css
/* Tambahan CSS ke STYLES di NovaNotes */

.domain-badge {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 9px;
  font-family: var(--font-mono);
  letter-spacing: 0.08em;
  background: rgba(26,95,212,0.2);
  border: 1px solid rgba(43,127,255,0.3);
  color: var(--blue-glow);
  margin-right: 3px;
}

.note-lock-icon {
  font-size: 10px;
  margin-right: 4px;
  opacity: 0.7;
}

.btn-curator {
  background: rgba(0,229,255,0.1);
  color: var(--cyan);
  border: 1px solid rgba(0,229,255,0.3);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 600;
}
.btn-curator:hover {
  background: rgba(0,229,255,0.2);
  border-color: var(--cyan);
  box-shadow: 0 0 12px rgba(0,229,255,0.2);
}
.btn-curator:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Curator processing indicator di status bar */
.curator-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  color: var(--cyan-dim);
  animation: pulse 1.5s ease-in-out infinite;
}
```

---

## Panel di Lab Room — Embed

```typescript
// src/overlays/LabRoomPanel.tsx
// Buka saat klik server machine tile di Lab Room

export function ServerMachinePanel({ onClose }: { onClose: () => void }) {
  const [isFullscreen, setIsFullscreen] = useState(false)

  return (
    <div className={`server-panel ${isFullscreen ? 'fullscreen' : 'windowed'}`}>
      {/* Panel header */}
      <div className="panel-header">
        <span className="panel-title">🖥 SERVER — KNOWLEDGE VAULT</span>
        <div className="panel-actions">
          <button onClick={() => setIsFullscreen(f => !f)}>
            {isFullscreen ? '⊡' : '⊞'}
          </button>
          <button onClick={onClose}>✕</button>
        </div>
      </div>

      {/* NovaNotes embedded */}
      <div className="panel-content">
        <NovaNotes embedded />
        {/* embedded prop: sembunyikan topbar logo, pakai panel header sebagai pengganti */}
      </div>
    </div>
  )
}

/* CSS */
.server-panel.windowed {
  position: fixed;
  top: 60px; right: 20px;
  width: 70vw; height: 80vh;
  z-index: 50;
  border: 1px solid var(--border-bright);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 0 40px rgba(43,127,255,0.15);
}
.server-panel.fullscreen {
  position: fixed;
  inset: 0;
  z-index: 80;
}
```

---

## Checklist Fase 2

```
[ ] NoteIndex interface — sidebar render judul only
[ ] loadNoteContent() — load on demand + cache
[ ] Disk persist: Tauri commands read/write ~/.vibe-office/notes/
[ ] Enkripsi per-note toggle (default OFF)
[ ] "Send to Curator" button di topbar
[ ] Auto-trigger curator saat paste > 300 kata (debounce 2s)
[ ] Domain badges di sidebar setelah curator process
[ ] ServerMachinePanel embed NovaNotes (windowed + fullscreen)
[ ] Server machine tile di Lab Room bisa diklik → buka panel

Fase 3 (curator live):
[ ] handleSendToCurator() kirim via WebSocket ke backend
[ ] knowledge_ingest_done response update badges
[ ] SKILL.md update dari curator terefleksi di domain badge
```
