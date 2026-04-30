# Frontend — Knowledge Browser (Fase 3)

> **Konteks untuk session baru:**
> Knowledge Browser adalah UI untuk lihat semua data Ring 2 — bukan hanya
> dari NovaNotes, tapi SEMUA episodes: coding, testing, auditing, knowledge_inject.
> Lokasi: komputer curator di Library Room → walk-to-desk → fade in overlay.
> Tiga tab: Domains (aggregate view), All Episodes (raw browser), SKILL Files.
> File terkait:
>   - `backend/knowledge-ingestion.md` → API endpoints
>   - `frontend/nova-notes-integration.md` → NovaNotes yang feed data ke sini
>   - `backend/memory.md` → Ring 2 Parquet schema

---

## Entry Point

```
Library Room → klik komputer curator
  ↓ walk-to-desk sequence (lihat task-animations.md)
  ↓ fade in Knowledge Browser overlay (FectTral, z-index 70)
```

---

## Layout — Tiga Tab

```
┌─────────────────────────────────────────────────────────┐
│  🧠 KNOWLEDGE BROWSER                          [✕ EXIT] │
├──────────┬──────────────────────────────────────────────┤
│ SIDEBAR  │  [Domains] [All Episodes] [SKILL Files]      │
│          ├──────────────────────────────────────────────┤
│ Workers  │                                              │
│ ──────── │  TAB CONTENT (lihat bawah)                  │
│ All      │                                              │
│ curator  │                                              │
│ coder_*  │                                              │
│ tester   │                                              │
│ auditor  │                                              │
│ ...      │                                              │
│          │                                              │
│ Filter   │                                              │
│ ──────── │                                              │
│ Type     │                                              │
│ Quality  │                                              │
│ Date     │                                              │
└──────────┴──────────────────────────────────────────────┘
```

Sidebar filter apply ke semua tiga tab sekaligus.

---

## Tab 1 — Domains

Aggregate view per domain — training readiness di satu pandang.

```typescript
function DomainsTab({ domains }: { domains: DomainSummary[] }) {
  return (
    <div className="domains-tab">
      {domains.map(d => (
        <div
          key={`${d.worker_id}.${d.domain}`}
          className={`domain-card ${d.training_ready ? 'ready' : ''}`}
        >
          {/* Header */}
          <div className="domain-card-header">
            <span className="domain-worker">{d.worker_id}</span>
            <span className="domain-dot">·</span>
            <span className="domain-name">{d.domain}</span>
            {d.training_ready && (
              <span className="training-ready-badge">⚡ READY</span>
            )}
            {d.skill_exists && (
              <span className="skill-badge">📄 SKILL</span>
            )}
          </div>

          {/* Threshold progress bar */}
          <div className="threshold-track">
            <div
              className="threshold-fill"
              style={{
                width: `${d.threshold_pct * 100}%`,
                background: d.training_ready
                  ? '#44ff88'
                  : d.threshold_pct > 0.6
                    ? '#FFCB6B'
                    : '#2b7fff'
              }}
            />
            <span className="threshold-label">
              {d.episode_count} / {TRAINING_THRESHOLD} episodes
            </span>
          </div>

          {/* Stats row */}
          <div className="domain-stats">
            <span>avg quality: {(d.quality_avg * 100).toFixed(0)}%</span>
            <span>·</span>
            <span>latest: {formatDate(d.latest_at)}</span>
            <span>·</span>
            <span>{d.latest_title}</span>
          </div>

          {/* Actions */}
          {d.training_ready && (
            <button
              className="train-now-btn"
              onClick={() => requestTraining(d.worker_id, d.domain)}
            >
              request training →
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
```

---

## Tab 2 — All Episodes

Raw browser semua episodes Ring 2. Filter sidebar apply di sini.

```typescript
function AllEpisodesTab() {
  const [episodes, setEpisodes] = useState<Episode[]>([])
  const [expanded, setExpanded] = useState<string | null>(null)
  const [page, setPage] = useState(0)
  const filters = useFilters()  // dari sidebar

  useEffect(() => {
    fetchEpisodes(filters, page).then(setEpisodes)
  }, [filters, page])

  return (
    <div className="episodes-tab">
      {/* Episode count header */}
      <div className="episodes-header">
        <span className="episodes-count">{filters.total} episodes</span>
        <span className="episodes-filter-summary">
          {filters.worker_id !== 'all' && `worker: ${filters.worker_id}`}
          {filters.type !== 'all' && ` · type: ${filters.type}`}
          {filters.quality_min > 0 && ` · quality ≥ ${filters.quality_min * 100}%`}
        </span>
      </div>

      {/* Episode rows */}
      {episodes.map(ep => (
        <div key={ep.episode_id} className={`episode-row ${ep.excluded ? 'excluded' : ''}`}>

          {/* Collapsed view */}
          <div
            className="episode-row-header"
            onClick={() => setExpanded(e => e === ep.episode_id ? null : ep.episode_id)}
          >
            <span className="ep-type-badge" style={{ color: TYPE_COLORS[ep.episode_type] }}>
              {ep.episode_type}
            </span>
            <span className="ep-worker">{ep.worker_id}</span>
            <span className="ep-domain">{ep.domain}</span>
            <span className="ep-title">{ep.title ?? ep.instruction?.slice(0, 50)}</span>
            <span className="ep-quality" style={{
              color: ep.quality_score > 0.7 ? '#44ff88'
                   : ep.quality_score > 0.4 ? '#FFCB6B' : '#ff6b6b'
            }}>
              {(ep.quality_score * 100).toFixed(0)}%
            </span>
            <span className={`ep-success ${ep.success ? 'ok' : 'fail'}`}>
              {ep.success ? '✓' : '✗'}
            </span>
            <span className="ep-date">{formatDate(ep.timestamp)}</span>
            <button
              className="ep-exclude-btn"
              title={ep.excluded ? 'excluded from training' : 'exclude from training'}
              onClick={e => { e.stopPropagation(); toggleExclude(ep.episode_id) }}
            >
              {ep.excluded ? '🚫' : '○'}
            </button>
          </div>

          {/* Expanded view */}
          {expanded === ep.episode_id && (
            <div className="episode-detail">
              <div className="ep-detail-section">
                <div className="ep-detail-label">INSTRUCTION</div>
                <div className="ep-detail-body">{ep.instruction}</div>
              </div>
              {ep.result_summary && (
                <div className="ep-detail-section">
                  <div className="ep-detail-label">RESULT</div>
                  <div className="ep-detail-body">{ep.result_summary}</div>
                </div>
              )}
              {ep.raw_content && (
                <div className="ep-detail-section">
                  <div className="ep-detail-label">CONTENT</div>
                  <pre className="ep-detail-code">{ep.raw_content.slice(0, 500)}</pre>
                </div>
              )}
              {ep.key_concepts && (
                <div className="ep-detail-section">
                  <div className="ep-detail-label">KEY CONCEPTS</div>
                  <div className="ep-concepts">
                    {JSON.parse(ep.key_concepts).map((c: string) => (
                      <span key={c} className="concept-tag">{c}</span>
                    ))}
                  </div>
                </div>
              )}
              <div className="ep-detail-meta">
                ID: {ep.episode_id} · source: {ep.source}
              </div>
            </div>
          )}
        </div>
      ))}

      {/* Pagination */}
      <div className="episodes-pagination">
        <button disabled={page === 0} onClick={() => setPage(p => p - 1)}>← prev</button>
        <span>page {page + 1}</span>
        <button onClick={() => setPage(p => p + 1)}>next →</button>
      </div>
    </div>
  )
}

const TYPE_COLORS: Record<string, string> = {
  'coding':           '#C792EA',
  'testing':          '#FFCB6B',
  'audit':            '#FF9800',
  'knowledge_inject': '#89DDFF',
  'security':         '#FF5252',
  'planning':         '#C3E88D',
}
```

---

## Tab 3 — SKILL Files

Lihat semua SKILL.md yang sudah ada, termasuk yang di-generate dari knowledge ingestion.

```typescript
function SkillFilesTab() {
  const [skills, setSkills] = useState<SkillFile[]>([])
  const [activeSkill, setActiveSkill] = useState<SkillFile | null>(null)

  return (
    <div className="skills-tab">
      {/* Skill list */}
      <div className="skill-list">
        {skills.map(s => (
          <div
            key={s.path}
            className={`skill-item ${activeSkill?.path === s.path ? 'active' : ''}`}
            onClick={() => setActiveSkill(s)}
          >
            <span className="skill-worker">{s.worker_id}</span>
            <span className="skill-domain">{s.subdomain}</span>
            <span className="skill-updated">{formatDate(s.updated_at)}</span>
            <span className="skill-size">{s.word_count}w</span>
          </div>
        ))}
      </div>

      {/* Skill content viewer */}
      {activeSkill && (
        <div className="skill-viewer">
          <div className="skill-viewer-header">
            {activeSkill.worker_id}/{activeSkill.subdomain}
            <span className="skill-viewer-meta">
              last updated: {formatDate(activeSkill.updated_at)}
            </span>
          </div>
          {/* Render markdown */}
          <div
            className="skill-content rendered"
            dangerouslySetInnerHTML={{ __html: parseMarkdown(activeSkill.content) }}
          />
        </div>
      )}
    </div>
  )
}
```

---

## Sidebar Filter

```typescript
function KnowledgeBrowserSidebar({ onChange }: { onChange: (f: Filters) => void }) {
  const [workerFilter, setWorkerFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')
  const [qualityMin, setQualityMin] = useState(0)

  const workers = ['all', ...getWorkerIds()]
  const types = ['all', 'coding', 'testing', 'audit', 'knowledge_inject', 'security', 'planning']

  return (
    <div className="kb-sidebar">
      <div className="kb-filter-section">
        <div className="kb-filter-label">WORKER</div>
        {workers.map(w => (
          <button
            key={w}
            className={`kb-filter-btn ${workerFilter === w ? 'active' : ''}`}
            onClick={() => { setWorkerFilter(w); onChange({ ...filters, worker_id: w }) }}
          >
            {w}
          </button>
        ))}
      </div>

      <div className="kb-filter-section">
        <div className="kb-filter-label">TYPE</div>
        {types.map(t => (
          <button
            key={t}
            className={`kb-filter-btn ${typeFilter === t ? 'active' : ''}`}
            style={{ color: t !== 'all' ? TYPE_COLORS[t] : undefined }}
            onClick={() => { setTypeFilter(t); onChange({ ...filters, type: t }) }}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="kb-filter-section">
        <div className="kb-filter-label">MIN QUALITY</div>
        <input
          type="range" min="0" max="1" step="0.1"
          value={qualityMin}
          onChange={e => {
            const v = parseFloat(e.target.value)
            setQualityMin(v)
            onChange({ ...filters, quality_min: v })
          }}
        />
        <span>{(qualityMin * 100).toFixed(0)}%</span>
      </div>
    </div>
  )
}
```

---

## Checklist Fase 3

```
[ ] KnowledgeBrowser overlay FectTral bisa dibuka dari komputer curator
[ ] Tab Domains: domain cards dengan threshold bar + train now button
[ ] Tab All Episodes: list dengan filter sidebar
[ ] Tab All Episodes: expand row untuk lihat detail episode
[ ] Tab All Episodes: exclude toggle per episode
[ ] Tab SKILL Files: list + markdown viewer
[ ] Sidebar filter: by worker, by type, by quality
[ ] Pagination (50 episodes per page)
[ ] requestTraining() kirim event ke trainer worker via WebSocket
[ ] GET /api/knowledge/episodes endpoint support filter params
```
