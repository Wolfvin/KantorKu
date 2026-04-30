# Frontend — Brain Visualization (Fase 4)

> **Konteks untuk session baru:**
> "Isi otak" setiap AI worker = koleksi LoRA adapters yang aktif.
> Kamu bisa lihat, toggle aktif/nonaktif, adjust weight, dan minta trainer refactor.
> Dua entry point:
>   1. Tab "brain" di CEO office worker paper → popup kecil inline
>   2. Tombol "view brain →" → buka Brain Viz full page (FectTral Template 5D)
> Brain Viz adalah DNA Report style dari FectTral — sudah ada templatenya.
> File ini mendokumentasikan keduanya beserta semua interaksi.

---

## LoRAMetadata Interface (Single Source of Truth)

> **Konteks Mechanistic Interpretability (update 2026-03-18):**
> Interface ini di-extend dengan `training_phase` dan `grokking_detected` fields
> berdasarkan temuan Neel Nanda et al. (ICLR 2023) tentang Grokking phenomenon.
> Paper: https://arxiv.org/abs/2301.05217
> Analysis detail: https://www.alignmentforum.org/posts/N6WM6hs7RQMKDhYjB/a-mechanistic-interpretability-analysis-of-grokking
>
> Key insight: training terbagi tiga fase — memorization → circuit formation → cleanup.
> "Grokking" yang terlihat tiba-tiba sebenarnya adalah fase cleanup yang
> buang memorization circuits dan tinggalkan generalizing circuits.
> Trainer bisa detect fase ini dari loss curve shape dan activasi patterns.
> Brain viz bisa tampilkan posisi LoRA dalam fase ini — signal nyata apakah
> LoRA sudah generalize atau masih hafal.

```typescript
// src/types/lora.ts

export interface LoRAMetadata {
  name: string              // "lora_borrow_checker_v2"
  version: number           // 2
  domain: string            // "borrow_checker" | "async" | "server" | "unsafe" | "rayon"
  worker_id: string         // "coder_rust"

  // Training provenance
  trained_at: string        // "2026-03-17"
  episodes_count: number    // 847
  success_rate: number      // 0.89

  // Performance
  performance_delta: string  // "+23% val_bpb"
  eval_score: number         // 0.87 (0-1)
  baseline_score: number     // 0.71 (score sebelum LoRA ini)

  // Runtime
  status: 'active' | 'disabled' | 'pending_eval'
  weight: number             // 0.0–1.0, berapa kuat LoRA ini di-apply
  rank: number               // 16 (LoRA rank saat training)

  // Side effects (hasil eval terhadap domain lain)
  side_effects: Record<string, string>  // { "async_accuracy": "-2%" }

  // Storage
  path: string              // "~/.vibe-office/loras/coder_rust/lora_borrow_checker_v2"
  size_mb: number

  // === MECHANISTIC INTERPRETABILITY FIELDS (Fase 4) ===
  // Berdasarkan Grokking paper: Nanda et al. ICLR 2023
  // https://arxiv.org/abs/2301.05217
  //
  // Tiga fase training yang trainer detect dari loss curve:
  // 'memorizing'    → model hafal training data, belum generalize
  //                   signal: train loss turun, val loss masih tinggi
  // 'circuit_forming' → generalizing circuits mulai terbentuk
  //                   signal: val loss mulai turun, tapi lambat
  // 'grokked'       → memorization circuits dibersihkan oleh weight decay
  //                   generalizing circuits dominan, val loss drop tajam
  //                   signal: val loss plateau rendah, train/val gap minimal
  training_phase: 'memorizing' | 'circuit_forming' | 'grokked' | 'unknown'

  // Confidence score bahwa LoRA sudah grokked (0.0-1.0)
  // Dicompute trainer dari: train/val loss gap + activation pattern analysis
  // < 0.4 → masih memorizing, tidak direkomendasikan untuk aktifkan
  // 0.4-0.7 → circuit forming, bisa aktif tapi monitor side effects
  // > 0.7 → grokked, aman untuk aktif di production
  grokking_confidence: number

  // Raw loss curve data untuk visualisasi di brain viz
  // Trainer simpan snapshot setiap N steps
  loss_curve: {
    steps: number[]
    train_loss: number[]
    val_loss: number[]
    val_bpb: number[]         // primary metric (Karpathy pattern)
  } | null

  // Circuit complexity estimate (opsional, Fase 5)
  // Berapa banyak "circuits" yang terbentuk — lebih sedikit = lebih clean
  // Didapat dari activation pattern clustering
  circuit_count: number | null
}

export interface WorkerBrainState {
  worker_id: string
  display_name: string
  badge_emoji: string
  base_model: string         // "Qwen2.5-Coder-7B"
  loras: LoRAMetadata[]

  // Computed
  total_domains: number
  strongest_domain: string   // domain dengan eval_score tertinggi
  weakest_domain: string     // domain dengan gap terbesar vs baseline
  total_lora_params: number  // jumlah trainable params dari semua LoRA aktif

  // === MECHANISTIC INTERPRETABILITY COMPUTED ===
  grokked_count: number      // berapa LoRA yang sudah confirmed grokked
  memorizing_count: number   // berapa yang masih memorizing (warning signal)
  overall_health: 'healthy' | 'warning' | 'critical'
  // healthy  → semua active LoRA sudah grokked
  // warning  → ada LoRA active yang masih circuit_forming
  // critical → ada LoRA active yang masih memorizing
}
```

---

## Entry Point 1 — Tab Brain di CEO Office Paper

Sudah ada di `frontend/ceo-office.md` (`BrainSection` component).
Ini adalah preview ringkas — tidak semua detail ditampilkan.

```typescript
// Sudah ada di ceo-office.md, ini adalah extensi-nya

function BrainSection({ loras, workerId }: { loras: LoRAMetadata[]; workerId: string }) {
  if (loras.length === 0) {
    return <BrainEmptyState workerId={workerId} />
  }

  return (
    <div className="brain-section">
      {/* Summary bar */}
      <div className="brain-summary">
        <span>{loras.filter(l => l.status === 'active').length} active</span>
        <span>·</span>
        <span>{loras.length} total</span>
        <span>·</span>
        <span>{loras.reduce((s, l) => s + l.size_mb, 0).toFixed(1)} MB</span>
      </div>

      {/* LoRA list — compact */}
      {loras.map(lora => (
        <LoRARow key={lora.name} lora={lora} workerId={workerId} compact />
      ))}

      {/* Link ke full brain viz */}
      <button
        className="brain-open-full"
        onClick={() => openBrainVisualization(workerId)}
      >
        open brain visualization →
      </button>
    </div>
  )
}
```

---

## Entry Point 2 — Full Brain Visualization (FectTral Template 5D)

Buka via "open brain visualization →" dari tab brain CEO office,
atau via "view brain →" dari status popup worker.

Ini adalah FectTral full-screen overlay (z-index 90, di bawah design studio 100).

```typescript
// src/overlays/BrainVisualization.tsx

interface BrainVizProps {
  workerId: string
  onClose: () => void
}

export function BrainVisualization({ workerId, onClose }: BrainVizProps) {
  const brain = useBrainState(workerId)   // dari backend API
  const [selectedLora, setSelectedLora] = useState<LoRAMetadata | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'loras' | 'conflicts'>('overview')

  return (
    <div className="brain-viz-overlay">
      {/* FectTral background (dari design-system.md) */}
      <div className="bg-root">
        <div className="bg-space" />
        <div className="bg-grid" />
        <canvas id="starCanvas" />
        <div className="scan-beam" />
        <div className="scanlines" />
        <div className="vignette" />
      </div>

      {/* App shell */}
      <div id="app" className="app">
        {/* Topbar */}
        <header className="topbar">
          <div className="topbar-logo">
            <span>{brain.badge_emoji}</span>
            <span className="glitch-text" data-text={brain.display_name.toUpperCase()}>
              {brain.display_name.toUpperCase()}
            </span>
            <span className="topbar-sub">BRAIN VISUALIZATION</span>
          </div>
          <div className="topbar-meta">
            <span className="meta-pill">{brain.base_model}</span>
            <span className="meta-pill">{brain.loras.length} adapters</span>
            <span className="meta-pill">{brain.total_lora_params.toLocaleString()} params</span>
          </div>
          <button className="topbar-close" onClick={onClose}>✕ EXIT</button>
        </header>

        {/* Main layout */}
        <div className="main-layout">
          {/* Sidebar */}
          <nav className="sidebar">
            <div className="sidebar-section">
              <div className="sidebar-label">BRAIN</div>
              {[
                { key: 'overview',  icon: '🧬', label: 'DNA Overview' },
                { key: 'loras',     icon: '🔧', label: 'LoRA Adapters' },
                { key: 'conflicts', icon: '⚡', label: 'Conflict Map' },
              ].map(item => (
                <button
                  key={item.key}
                  className={`sidebar-item ${activeTab === item.key ? 'active' : ''}`}
                  onClick={() => setActiveTab(item.key as any)}
                >
                  <span>{item.icon}</span>
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
            <div className="sidebar-section">
              <div className="sidebar-label">ACTIONS</div>
              <button className="sidebar-item" onClick={() => requestTrainerRefactor(workerId)}>
                <span>🧪</span>
                <span>Request Refactor</span>
              </button>
              <button className="sidebar-item" onClick={() => disableAllLoras(workerId)}>
                <span>🔕</span>
                <span>Disable All</span>
              </button>
            </div>
          </nav>

          {/* Content */}
          <main className="content">
            {activeTab === 'overview'  && <DNAOverview brain={brain} />}
            {activeTab === 'loras'     && <LoRAManager brain={brain} onSelect={setSelectedLora} />}
            {activeTab === 'conflicts' && <ConflictMap brain={brain} />}
          </main>
        </div>
      </div>

      {/* Detail panel — muncul saat LoRA dipilih */}
      {selectedLora && (
        <LoRADetailPanel
          lora={selectedLora}
          workerId={workerId}
          onClose={() => setSelectedLora(null)}
        />
      )}
    </div>
  )
}
```

---

## Tab 1 — DNA Overview

```typescript
function DNAOverview({ brain }: { brain: WorkerBrainState }) {
  return (
    <div className="dna-overview">
      {/* Section: Identity + Health */}
      <div className="dna-card">
        <div className="dna-card-title">DESIGN IDENTITY</div>
        <div className="dna-subtitle">Based on {brain.loras.length} LoRA adapters</div>

        {/* Health indicator dari Mechanistic Interpretability */}
        <div className={`brain-health brain-health-${brain.overall_health}`}>
          <span className="health-icon">
            {brain.overall_health === 'healthy'  ? '🟢' :
             brain.overall_health === 'warning'  ? '🟡' : '🔴'}
          </span>
          <span className="health-label">
            {brain.overall_health === 'healthy'
              ? `${brain.grokked_count} LoRAs fully grokked — generalizing, not memorizing`
              : brain.overall_health === 'warning'
              ? `${brain.memorizing_count + (brain.loras.length - brain.grokked_count - brain.memorizing_count)} LoRAs still forming circuits`
              : `⚠ ${brain.memorizing_count} LoRAs still memorizing — risky to activate`}
          </span>
        </div>

        {/* Strongest / Weakest */}
        <div className="dna-highlights">
          <div className="dna-highlight green">
            <span className="dna-hl-label">STRONGEST</span>
            <span className="dna-hl-val">{brain.strongest_domain}</span>
          </div>
          <div className="dna-highlight red">
            <span className="dna-hl-label">NEEDS WORK</span>
            <span className="dna-hl-val">{brain.weakest_domain}</span>
          </div>
        </div>
      </div>

      {/* Section: Training Phase Overview (Mechanistic Interpretability) */}
      <div className="dna-card">
        <div className="dna-card-title">TRAINING PHASES</div>
        <div className="dna-subtitle">
          Based on Grokking research — Nanda et al. ICLR 2023
        </div>
        <TrainingPhaseOverview loras={brain.loras} />
      </div>

      {/* Section: Domain Strength Bars */}
      <div className="dna-card">
        <div className="dna-card-title">DOMAIN STRENGTH</div>
        <DomainStrengthBars loras={brain.loras} />
      </div>

      {/* Section: Stats Grid */}
      <div className="dna-stats-grid">
        {[
          { label: 'Total LoRAs',   value: brain.loras.length },
          { label: 'Active',        value: brain.loras.filter(l => l.status === 'active').length },
          { label: 'Grokked',       value: brain.grokked_count },
          { label: 'Avg Score',     value: (brain.loras.reduce((s,l) => s+l.eval_score,0) / brain.loras.length).toFixed(2) },
          { label: 'Total Params',  value: `${(brain.total_lora_params/1000).toFixed(0)}K` },
          { label: 'Total Episodes',value: brain.loras.reduce((s,l) => s+l.episodes_count,0).toLocaleString() },
          { label: 'Storage',       value: `${brain.loras.reduce((s,l) => s+l.size_mb,0).toFixed(0)} MB` },
        ].map(stat => (
          <div key={stat.label} className="dna-stat-cell">
            <span className="dna-stat-val">{stat.value}</span>
            <span className="dna-stat-label">{stat.label}</span>
          </div>
        ))}
      </div>

      {/* Section: Recommendation Cards */}
      <RecommendationCards brain={brain} />
    </div>
  )
}

// === KOMPONEN BARU: Training Phase Overview ===
// Berdasarkan Grokking paper — 3 fase training yang trainer detect

function TrainingPhaseOverview({ loras }: { loras: LoRAMetadata[] }) {
  const phases = {
    memorizing:      loras.filter(l => l.training_phase === 'memorizing'),
    circuit_forming: loras.filter(l => l.training_phase === 'circuit_forming'),
    grokked:         loras.filter(l => l.training_phase === 'grokked'),
    unknown:         loras.filter(l => l.training_phase === 'unknown'),
  }

  const PHASE_INFO = {
    memorizing: {
      icon: '🔴', label: 'Memorizing',
      desc: 'Hafal training data, belum generalize. Tidak direkomendasikan untuk aktif.',
      color: 'rgba(255,68,68,0.15)', border: 'rgba(255,68,68,0.4)'
    },
    circuit_forming: {
      icon: '🟡', label: 'Circuit Forming',
      desc: 'Generalizing circuits mulai terbentuk. Bisa aktif, tapi monitor side effects.',
      color: 'rgba(255,170,0,0.15)', border: 'rgba(255,170,0,0.4)'
    },
    grokked: {
      icon: '🟢', label: 'Grokked',
      desc: 'Memorization circuits sudah dibersihkan. Generalizing dominan. Aman untuk produksi.',
      color: 'rgba(68,255,136,0.15)', border: 'rgba(68,255,136,0.4)'
    },
    unknown: {
      icon: '⚪', label: 'Unknown',
      desc: 'Belum ada data interpretability. Jalankan trainer analysis untuk detect.',
      color: 'rgba(136,135,128,0.15)', border: 'rgba(136,135,128,0.3)'
    },
  }

  return (
    <div className="phase-overview">
      {(Object.entries(phases) as [keyof typeof phases, LoRAMetadata[]][])
        .filter(([, group]) => group.length > 0)
        .map(([phase, group]) => {
          const info = PHASE_INFO[phase]
          return (
            <div key={phase} className="phase-row"
              style={{ background: info.color, border: `1px solid ${info.border}` }}>
              <div className="phase-header">
                <span>{info.icon}</span>
                <span className="phase-label">{info.label}</span>
                <span className="phase-count">{group.length} LoRA</span>
              </div>
              <div className="phase-desc">{info.desc}</div>
              <div className="phase-loras">
                {group.map(l => (
                  <span key={l.name} className="phase-lora-chip">
                    {l.domain}
                    {l.grokking_confidence > 0
                      ? ` (${(l.grokking_confidence * 100).toFixed(0)}%)`
                      : ''}
                  </span>
                ))}
              </div>
            </div>
          )
        })}

      {/* Tooltip edukasi tentang Grokking */}
      <div className="phase-footnote">
        <span className="phase-footnote-icon">ℹ</span>
        <span>
          Grokking: model awalnya menghafal, lalu weight decay secara bertahap
          membersihkan memorization circuits — tinggalkan generalizing circuits yang bersih.
          Proses ini bisa terjadi jauh setelah training terlihat "selesai."
        </span>
      </div>
    </div>
  )
}

function DomainStrengthBars({ loras }: { loras: LoRAMetadata[] }) {
  const active = loras.filter(l => l.status === 'active')
  const maxScore = Math.max(...active.map(l => l.eval_score))

  return (
    <div className="domain-bars">
      {active.sort((a,b) => b.eval_score - a.eval_score).map(lora => (
        <div key={lora.domain} className="domain-bar-row">
          <span className="domain-bar-label">{lora.domain}</span>

          {/* Phase indicator di samping nama */}
          <span className="domain-phase-dot" title={`Training phase: ${lora.training_phase}`}>
            {lora.training_phase === 'grokked'         ? '🟢' :
             lora.training_phase === 'circuit_forming' ? '🟡' :
             lora.training_phase === 'memorizing'      ? '🔴' : '⚪'}
          </span>

          <div className="domain-bar-track">
            <div
              className="domain-bar-fill"
              style={{
                width: `${(lora.eval_score / maxScore) * 100}%`,
                background: lora.training_phase === 'grokked'
                  ? 'var(--blue-core)'
                  : lora.training_phase === 'circuit_forming'
                  ? '#EF9F27'
                  : '#E24B4A'
              }}
            />
          </div>
          <span className="domain-bar-score">{(lora.eval_score * 100).toFixed(0)}%</span>
          <span className="domain-bar-delta" style={{
            color: lora.eval_score > lora.baseline_score ? '#44ff88' : '#ff6b6b'
          }}>
            {lora.eval_score > lora.baseline_score ? '▲' : '▼'}
            {Math.abs(lora.eval_score - lora.baseline_score * 100).toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  )
}              className="domain-bar-fill"
              style={{
                width: `${(lora.eval_score / maxScore) * 100}%`,
                // Warna berdasarkan improvement dari baseline
                background: lora.eval_score - lora.baseline_score > 0.1
                  ? 'var(--blue-core)'
                  : 'var(--blue-dim)'
              }}
            />
          </div>
          <span className="domain-bar-score">{(lora.eval_score * 100).toFixed(0)}%</span>
          <span className="domain-bar-delta" style={{
            color: lora.eval_score > lora.baseline_score ? '#44ff88' : '#ff6b6b'
          }}>
            {lora.eval_score > lora.baseline_score ? '▲' : '▼'}
            {Math.abs(lora.eval_score - lora.baseline_score * 100).toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  )
}

function RecommendationCards({ brain }: { brain: WorkerBrainState }) {
  const allDomains = ['borrow_checker', 'async', 'server', 'unsafe', 'rayon']
  const coveredDomains = brain.loras.map(l => l.domain)
  const missingDomains = allDomains.filter(d => !coveredDomains.includes(d))

  return (
    <div className="dna-card">
      <div className="dna-card-title">RECOMMENDATIONS</div>
      <div className="rec-cards">
        {/* Missing domains */}
        {missingDomains.slice(0,2).map(d => (
          <div key={d} className="rec-card rec-missing">
            <span className="rec-icon">🔴</span>
            <div>
              <div className="rec-title">MISSING</div>
              <div className="rec-body">No LoRA for <strong>{d}</strong> domain</div>
              <button
                className="rec-action"
                onClick={() => requestTrainerForDomain(brain.worker_id, d)}
              >
                train now →
              </button>
            </div>
          </div>
        ))}

        {/* Weak LoRA */}
        {brain.loras
          .filter(l => l.eval_score - l.baseline_score < 0.05)
          .slice(0,1)
          .map(l => (
            <div key={l.name} className="rec-card rec-warn">
              <span className="rec-icon">🟡</span>
              <div>
                <div className="rec-title">UNDERPERFORMING</div>
                <div className="rec-body"><strong>{l.domain}</strong> — low improvement ({l.performance_delta})</div>
                <button className="rec-action" onClick={() => retrainLora(brain.worker_id, l.name)}>
                  retrain →
                </button>
              </div>
            </div>
          ))}

        {/* Strong LoRA */}
        {brain.loras
          .filter(l => l.eval_score - l.baseline_score > 0.15)
          .slice(0,1)
          .map(l => (
            <div key={l.name} className="rec-card rec-good">
              <span className="rec-icon">🟢</span>
              <div>
                <div className="rec-title">STRENGTH</div>
                <div className="rec-body"><strong>{l.domain}</strong> — {l.performance_delta}</div>
              </div>
            </div>
          ))}
      </div>
    </div>
  )
}
```

---

## Tab 2 — LoRA Manager

```typescript
function LoRAManager({ brain, onSelect }: {
  brain: WorkerBrainState
  onSelect: (lora: LoRAMetadata) => void
}) {
  return (
    <div className="lora-manager">
      {brain.loras.map(lora => (
        <div
          key={lora.name}
          className={`lora-card ${lora.status === 'disabled' ? 'disabled' : ''}`}
          onClick={() => onSelect(lora)}
        >
          {/* Header */}
          <div className="lora-card-header">
            <div>
              <span className="lora-card-name">{lora.name}</span>
              <span className="lora-card-domain">{lora.domain}</span>
            </div>
            <span
              className="lora-status-badge"
              style={{ color: lora.status === 'active' ? '#44ff88' : '#ff6b6b' }}
            >
              {lora.status.toUpperCase()}
            </span>
          </div>

          {/* Score bar */}
          <div className="lora-score-row">
            <span>Score</span>
            <div className="lora-score-track">
              <div
                className="lora-score-baseline"
                style={{ width: `${lora.baseline_score * 100}%` }}
              />
              <div
                className="lora-score-fill"
                style={{ width: `${lora.eval_score * 100}%` }}
              />
            </div>
            <span className="lora-score-val">{(lora.eval_score * 100).toFixed(0)}%</span>
            <span className="lora-delta" style={{
              color: lora.eval_score > lora.baseline_score ? '#44ff88' : '#ff6b6b'
            }}>
              {lora.performance_delta}
            </span>
          </div>

          {/* Weight slider */}
          <div className="lora-weight-row" onClick={e => e.stopPropagation()}>
            <span>Weight</span>
            <input
              type="range" min="0" max="1" step="0.05"
              value={lora.weight}
              onChange={e => updateLoRAWeight(brain.worker_id, lora.name, parseFloat(e.target.value))}
              disabled={lora.status === 'disabled'}
            />
            <span className="lora-weight-val">{lora.weight.toFixed(2)}</span>
          </div>

          {/* Side effects */}
          {Object.keys(lora.side_effects).length > 0 && (
            <div className="lora-side-effects">
              ⚠ {Object.entries(lora.side_effects).map(([k,v]) => `${k}: ${v}`).join(' · ')}
            </div>
          )}

          {/* Toggle button */}
          <div className="lora-actions" onClick={e => e.stopPropagation()}>
            <button
              className={`lora-toggle-btn ${lora.status === 'active' ? 'active' : ''}`}
              onClick={() => toggleLoRA(brain.worker_id, lora.name)}
            >
              {lora.status === 'active' ? '● ACTIVE' : '○ DISABLED'}
            </button>
            <button
              className="lora-delete-btn"
              onClick={() => deleteLoRAConfirm(brain.worker_id, lora.name)}
            >
              🗑
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
```

---

## Tab 3 — Conflict Map

Visualisasi orthogonality antar LoRAs. Kalau dua LoRA punya dot product tinggi
→ interference risk → tampilkan warning.

```typescript
function ConflictMap({ brain }: { brain: WorkerBrainState }) {
  const [matrix, setMatrix] = useState<number[][]>([])
  const active = brain.loras.filter(l => l.status === 'active')

  useEffect(() => {
    // Request orthogonality matrix dari backend
    fetchOrthogonalityMatrix(brain.worker_id).then(setMatrix)
  }, [brain.worker_id])

  return (
    <div className="conflict-map">
      <div className="dna-card-title">ORTHOGONALITY MATRIX</div>
      <p className="conflict-desc">
        Nilai mendekati 0 = LoRAs orthogonal (baik).
        Nilai mendekati 1 = ada interference (perlu perhatian).
      </p>

      {/* Heatmap grid */}
      <div
        className="conflict-grid"
        style={{ gridTemplateColumns: `120px repeat(${active.length}, 1fr)` }}
      >
        {/* Header row */}
        <div />
        {active.map(l => (
          <div key={l.domain} className="conflict-header">{l.domain}</div>
        ))}

        {/* Data rows */}
        {active.map((rowLora, i) => (
          <>
            <div key={rowLora.domain} className="conflict-row-label">{rowLora.domain}</div>
            {active.map((colLora, j) => {
              const val = matrix[i]?.[j] ?? 0
              const isDiag = i === j
              return (
                <div
                  key={colLora.domain}
                  className="conflict-cell"
                  style={{
                    background: isDiag
                      ? 'var(--bg-deep)'
                      : val > 0.3
                        ? `rgba(255,68,68,${val * 0.7})`   // merah kalau tinggi
                        : `rgba(0,170,255,${(1-val) * 0.3})`, // biru kalau rendah
                  }}
                  title={isDiag ? '-' : `${rowLora.domain} ↔ ${colLora.domain}: ${val.toFixed(3)}`}
                >
                  {isDiag ? '—' : val.toFixed(2)}
                </div>
              )
            })}
          </>
        ))}
      </div>

      {/* Warning list */}
      {active.some((_, i) => active.some((_, j) => i < j && (matrix[i]?.[j] ?? 0) > 0.3)) && (
        <div className="conflict-warnings">
          <div className="conflict-warn-title">⚠ HIGH INTERFERENCE DETECTED</div>
          {active.flatMap((l1, i) =>
            active.slice(i+1).map((l2, jj) => {
              const j = i + 1 + jj
              const val = matrix[i]?.[j] ?? 0
              if (val <= 0.3) return null
              return (
                <div key={`${l1.domain}-${l2.domain}`} className="conflict-warn-item">
                  <span>{l1.domain} ↔ {l2.domain}</span>
                  <span className="conflict-warn-score">{(val * 100).toFixed(0)}% overlap</span>
                  <button
                    onClick={() => requestTrainerRefactor(brain.worker_id, [l1.name, l2.name])}
                  >
                    fix →
                  </button>
                </div>
              )
            }).filter(Boolean)
          )}
        </div>
      )}
    </div>
  )
}
```

---

## Backend API untuk Brain Visualization

```python
# backend/api/brain.py — endpoint yang dibutuhkan frontend

from fastapi import APIRouter
router = APIRouter(prefix="/api/brain")

@router.get("/{worker_id}")
async def get_brain_state(worker_id: str) -> WorkerBrainState:
    """Return semua LoRA metadata untuk worker."""
    loras = load_all_lora_metadata(worker_id)
    return WorkerBrainState(
        worker_id=worker_id,
        display_name=get_worker_display_name(worker_id),
        badge_emoji=get_worker_badge(worker_id),
        base_model=get_worker_base_model(worker_id),
        loras=loras,
        total_domains=len(set(l.domain for l in loras)),
        strongest_domain=max(loras, key=lambda l: l.eval_score).domain if loras else "",
        weakest_domain=min(loras, key=lambda l: l.eval_score - l.baseline_score).domain if loras else "",
        total_lora_params=sum(compute_lora_params(l) for l in loras if l.status == 'active'),
    )

@router.post("/{worker_id}/toggle/{lora_name}")
async def toggle_lora(worker_id: str, lora_name: str):
    """Toggle LoRA aktif/nonaktif."""
    lora = load_lora_metadata(worker_id, lora_name)
    new_status = 'disabled' if lora.status == 'active' else 'active'
    update_lora_metadata(worker_id, lora_name, status=new_status)
    return {"status": new_status}

@router.post("/{worker_id}/weight/{lora_name}")
async def update_weight(worker_id: str, lora_name: str, weight: float):
    """Update weight LoRA (0.0–1.0)."""
    update_lora_metadata(worker_id, lora_name, weight=max(0.0, min(1.0, weight)))
    return {"weight": weight}

@router.get("/{worker_id}/orthogonality")
async def get_orthogonality_matrix(worker_id: str) -> list[list[float]]:
    """
    Hitung dot product antar semua LoRAs aktif.
    Return NxN matrix — diagonal = 1.0, off-diagonal = interference score.
    Dipakai oleh Conflict Map tab.
    """
    loras = [l for l in load_all_lora_metadata(worker_id) if l.status == 'active']
    weights = [load_lora_weights(worker_id, l.name) for l in loras]
    n = len(loras)
    matrix = [[0.0] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i == j:
                matrix[i][j] = 1.0
                continue
            # Dot product antara dua LoRA weight matrices
            score = compute_dot_product(weights[i], weights[j])
            matrix[i][j] = float(score)

    return matrix

@router.post("/{worker_id}/delete/{lora_name}")
async def delete_lora(worker_id: str, lora_name: str):
    """Hapus LoRA dari disk dan metadata."""
    lora_path = get_lora_path(worker_id, lora_name)
    import shutil
    shutil.rmtree(lora_path, ignore_errors=True)
    delete_lora_metadata(worker_id, lora_name)
    return {"deleted": True}
```

---

## CSS — FectTral Brain Viz Style

```css
/* brain-viz.css — extends FectTral base dari design-system.md */

.brain-viz-overlay {
  position: fixed; inset: 0; z-index: 90;
  /* Semua FectTral bg layers */
}

/* DNA Cards */
.dna-card {
  background: var(--bg-card);
  border: 1px solid var(--border-mid);
  border-radius: 4px;
  padding: 16px;
  margin-bottom: 12px;
}
.dna-card-title {
  font-family: var(--font-display);
  font-size: 10px; letter-spacing: 0.15em;
  color: var(--blue-core);
  text-shadow: var(--glow-text);
  margin-bottom: 12px;
}

/* Stats Grid */
.dna-stats-grid {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 8px; margin-bottom: 12px;
}
.dna-stat-cell {
  background: var(--bg-panel);
  border: 1px solid var(--border-dim);
  border-radius: 3px;
  padding: 10px; text-align: center;
}
.dna-stat-val {
  display: block;
  font-family: var(--font-display); font-size: 20px;
  color: var(--blue-bright);
  text-shadow: var(--glow-text);
}
.dna-stat-label {
  font-size: 8px; color: var(--text-muted);
  font-family: var(--font-mono); letter-spacing: 0.08em;
}

/* LoRA cards */
.lora-card {
  background: var(--bg-panel);
  border: 1px solid var(--border-dim);
  border-radius: 3px; padding: 12px;
  margin-bottom: 8px; cursor: pointer;
  transition: border-color 0.2s;
}
.lora-card:hover { border-color: var(--border-mid); }
.lora-card.disabled { opacity: 0.5; }

/* Conflict heatmap */
.conflict-grid {
  display: grid; gap: 2px;
  font-family: var(--font-mono); font-size: 9px;
  margin: 12px 0;
}
.conflict-cell {
  padding: 5px 2px; text-align: center;
  border-radius: 2px; min-width: 40px;
  color: var(--text-primary);
}

/* Recommendation cards */
.rec-cards { display: flex; gap: 8px; flex-wrap: wrap; }
.rec-card {
  flex: 1; min-width: 180px;
  background: var(--bg-panel);
  border-radius: 3px; padding: 10px;
  display: flex; gap: 8px; align-items: flex-start;
}
.rec-missing { border: 1px solid rgba(255,68,68,0.3); }
.rec-warn    { border: 1px solid rgba(255,170,0,0.3); }
.rec-good    { border: 1px solid rgba(68,255,136,0.3); }
.rec-action  {
  margin-top: 6px; background: none;
  border: 1px solid var(--border-mid);
  color: var(--blue-core); font-family: var(--font-mono);
  font-size: 8px; cursor: pointer; padding: 2px 6px;
}
```

---

## Tab 4 — Loss Curve & Grokking Analysis (BARU — Fase 4)

```typescript
// Tab baru di brain visualization — visualisasi training curve per LoRA
// Berdasarkan insight dari Grokking paper: loss curve shape reveal training phase

function LossCurveTab({ brain, selectedLora }: {
  brain: WorkerBrainState
  selectedLora: LoRAMetadata | null
}) {
  const lora = selectedLora ?? brain.loras.find(l => l.status === 'active') ?? brain.loras[0]

  if (!lora || !lora.loss_curve) {
    return (
      <div className="dna-card">
        <div className="dna-card-title">LOSS CURVE</div>
        <div className="phase-footnote">
          Belum ada data loss curve. Trainer akan simpan snapshot saat overnight loop.
        </div>
      </div>
    )
  }

  const { steps, train_loss, val_loss, val_bpb } = lora.loss_curve

  return (
    <div className="loss-curve-tab">
      {/* LoRA selector */}
      <div className="lora-selector">
        {brain.loras.map(l => (
          <button
            key={l.name}
            className={`lora-chip ${l.name === lora.name ? 'active' : ''}`}
            onClick={() => setSelectedLora(l)}
          >
            {l.domain}
            <span className="lora-chip-phase">
              {l.training_phase === 'grokked'         ? '🟢' :
               l.training_phase === 'circuit_forming' ? '🟡' :
               l.training_phase === 'memorizing'      ? '🔴' : '⚪'}
            </span>
          </button>
        ))}
      </div>

      {/* Phase annotation */}
      <div className={`phase-banner phase-banner-${lora.training_phase}`}>
        <strong>
          {lora.training_phase === 'grokked'
            ? '🟢 GROKKED — Generalizing circuits dominant. Weight decay cleaned memorization.'
            : lora.training_phase === 'circuit_forming'
            ? '🟡 CIRCUIT FORMING — Generalizing circuits emerging. Monitor closely.'
            : lora.training_phase === 'memorizing'
            ? '🔴 MEMORIZING — Model still overfitting. Not recommended for production.'
            : '⚪ UNKNOWN — Run trainer analysis to detect phase.'}
        </strong>
        <span className="phase-confidence">
          Confidence: {(lora.grokking_confidence * 100).toFixed(0)}%
        </span>
      </div>

      {/* Loss curve chart — pakai Chart.js (sudah ada di design system) */}
      <div style={{ position: 'relative', height: '220px', marginBottom: '16px' }}>
        <canvas id="lossCurveChart" />
        {/* Chart.js render di sini — train_loss (orange) + val_loss (blue) + val_bpb (teal) */}
        {/* Grokking event ditandai dengan vertical line saat val_loss drop tajam */}
      </div>

      {/* Grokking event detector annotation */}
      <div className="grok-events">
        <div className="dna-card-title">GROKKING EVENTS DETECTED</div>
        <GrokEventAnnotations lossCurve={lora.loss_curve} />
      </div>

      {/* Interpretability note */}
      <div className="phase-footnote" style={{ marginTop: '12px' }}>
        <span>ℹ</span>
        <span>
          Train/val loss gap yang kecil dan stabil = generalizing circuits dominant.
          Gap yang besar = masih memorizing. Sudden val_loss drop = grokking event.
          Ref: Nanda et al. "Progress measures for grokking via mechanistic interpretability"
          — <a href="https://arxiv.org/abs/2301.05217" style={{ color: 'var(--blue-core)' }}>
            arxiv.org/abs/2301.05217
          </a>
        </span>
      </div>
    </div>
  )
}

function GrokEventAnnotations({ lossCurve }: { lossCurve: LoRAMetadata['loss_curve'] }) {
  if (!lossCurve) return null

  // Detect grokking events: step di mana val_loss drop > 15% dalam window kecil
  const events: { step: number; drop: number }[] = []
  const WINDOW = 10
  const THRESHOLD = 0.15

  for (let i = WINDOW; i < lossCurve.val_loss.length; i++) {
    const prev = lossCurve.val_loss[i - WINDOW]
    const curr = lossCurve.val_loss[i]
    const drop = (prev - curr) / prev
    if (drop > THRESHOLD) {
      events.push({ step: lossCurve.steps[i], drop })
    }
  }

  if (events.length === 0) {
    return (
      <div className="phase-footnote">
        Belum ada grokking event terdeteksi. Training mungkin masih di fase memorization
        atau circuit formation.
      </div>
    )
  }

  return (
    <div className="grok-event-list">
      {events.map((ev, i) => (
        <div key={i} className="grok-event-item">
          <span className="grok-event-step">Step {ev.step.toLocaleString()}</span>
          <span className="grok-event-drop" style={{ color: '#44ff88' }}>
            val_loss ↓ {(ev.drop * 100).toFixed(1)}%
          </span>
          <span className="grok-event-label">
            {i === 0 ? '← probable grokking onset' : '← continued generalization'}
          </span>
        </div>
      ))}
    </div>
  )
}
```

---

## Backend API — Tambahan untuk Grokking Support

```python
# backend/api/brain.py — extend API yang sudah ada

@router.get("/{worker_id}/loss-curve/{lora_name}")
async def get_loss_curve(worker_id: str, lora_name: str) -> dict:
    """
    Return loss curve data untuk visualisasi di Tab 4.
    Trainer simpan snapshot setiap N steps ke Ring 2 experiments.parquet.
    """
    curve_data = load_loss_curve_from_ring2(worker_id, lora_name)
    return {
        "steps":      curve_data["steps"],
        "train_loss": curve_data["train_loss"],
        "val_loss":   curve_data["val_loss"],
        "val_bpb":    curve_data["val_bpb"],
    }


@router.get("/{worker_id}/grokking-phase/{lora_name}")
async def analyze_grokking_phase(worker_id: str, lora_name: str) -> dict:
    """
    Detect training phase dari loss curve shape.
    Dipanggil saat:
    - Trainer selesai training → auto-detect phase sebelum activate/discard
    - User klik "Analyze" di brain viz Tab 4
    - Scheduled: trainer run analysis setiap pagi

    Return:
    - training_phase: 'memorizing' | 'circuit_forming' | 'grokked' | 'unknown'
    - grokking_confidence: float 0-1
    - grokking_events: list of {step, val_loss_drop} events
    - recommendation: string penjelasan apa yang harus dilakukan
    """
    curve = load_loss_curve_from_ring2(worker_id, lora_name)

    if curve is None:
        return {"training_phase": "unknown", "grokking_confidence": 0.0}

    # Phase detection algorithm:
    # 1. Hitung train/val loss gap di akhir training
    # 2. Detect apakah ada sudden val_loss drop (grokking event)
    # 3. Check apakah val_loss sudah plateau di level rendah

    final_train = curve["train_loss"][-1]
    final_val   = curve["val_loss"][-1]
    gap         = (final_val - final_train) / final_train

    # Detect grokking events
    events = detect_grokking_events(
        curve["val_loss"], curve["steps"], threshold=0.15, window=10
    )

    # Classify phase
    if len(events) > 0 and gap < 0.15:
        phase      = "grokked"
        confidence = min(0.95, 0.7 + (0.15 - gap) * 2 + len(events) * 0.05)
    elif gap < 0.3 or len(events) > 0:
        phase      = "circuit_forming"
        confidence = 0.5 + (0.3 - gap) * 0.5 if gap < 0.3 else 0.4
    else:
        phase      = "memorizing"
        confidence = min(0.9, 0.5 + gap * 0.3)

    # Simpan ke LoRA metadata untuk brain viz
    update_lora_metadata(worker_id, lora_name,
        training_phase=phase,
        grokking_confidence=confidence
    )

    recommendation = {
        "grokked":         "✅ Safe to activate. Circuits clean, generalizing.",
        "circuit_forming": "⚠️ Can activate with monitoring. Check side effects.",
        "memorizing":      "❌ Not recommended. Continue training or increase weight decay.",
        "unknown":         "ℹ️ Run more training steps and re-analyze.",
    }[phase]

    return {
        "training_phase":      phase,
        "grokking_confidence": confidence,
        "train_val_gap":       gap,
        "grokking_events":     events,
        "recommendation":      recommendation,
    }


def detect_grokking_events(
    val_loss: list[float],
    steps: list[int],
    threshold: float = 0.15,
    window: int = 10
) -> list[dict]:
    """
    Detect sudden drops di val_loss — signature grokking event.
    Threshold: val_loss drop > 15% dalam window 10 steps = probable grokking.
    """
    events = []
    for i in range(window, len(val_loss)):
        prev = val_loss[i - window]
        curr = val_loss[i]
        if prev > 0:
            drop = (prev - curr) / prev
            if drop > threshold:
                events.append({
                    "step":           steps[i],
                    "val_loss_before": prev,
                    "val_loss_after":  curr,
                    "drop_pct":        drop,
                })
    return events
```

---

## CSS — Training Phase Styles

```css
/* Tambahan ke brain-viz.css */

/* Health indicator */
.brain-health {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; border-radius: 3px; margin: 10px 0;
  font-size: 12px; font-family: var(--font-mono);
}
.brain-health-healthy  { background: rgba(68,255,136,0.1); border: 1px solid rgba(68,255,136,0.3); }
.brain-health-warning  { background: rgba(255,170,0,0.1);  border: 1px solid rgba(255,170,0,0.3);  }
.brain-health-critical { background: rgba(255,68,68,0.1);  border: 1px solid rgba(255,68,68,0.3);  }

/* Training phase overview */
.phase-row {
  border-radius: 3px; padding: 10px 12px; margin-bottom: 6px;
}
.phase-header {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 4px;
}
.phase-label { font-weight: 500; font-size: 12px; color: var(--text-primary); }
.phase-count {
  margin-left: auto; font-size: 10px;
  color: var(--text-muted); font-family: var(--font-mono);
}
.phase-desc { font-size: 11px; color: var(--text-secondary); margin-bottom: 6px; }
.phase-loras { display: flex; flex-wrap: wrap; gap: 4px; }
.phase-lora-chip {
  background: var(--bg-deep); border: 1px solid var(--border-dim);
  border-radius: 2px; padding: 2px 6px;
  font-size: 10px; font-family: var(--font-mono); color: var(--text-secondary);
}
.phase-footnote {
  display: flex; gap: 6px; align-items: flex-start;
  font-size: 10px; color: var(--text-muted);
  margin-top: 8px; line-height: 1.5;
}

/* Loss curve tab */
.phase-banner {
  padding: 8px 12px; border-radius: 3px; margin-bottom: 12px;
  display: flex; justify-content: space-between; align-items: center;
  font-size: 11px; font-family: var(--font-mono);
}
.phase-banner-grokked         { background: rgba(68,255,136,0.1); border: 1px solid rgba(68,255,136,0.3); }
.phase-banner-circuit_forming { background: rgba(255,170,0,0.1);  border: 1px solid rgba(255,170,0,0.3);  }
.phase-banner-memorizing      { background: rgba(255,68,68,0.1);  border: 1px solid rgba(255,68,68,0.3);  }
.phase-banner-unknown         { background: var(--bg-panel);      border: 1px solid var(--border-dim);     }
.phase-confidence { font-size: 10px; color: var(--text-muted); white-space: nowrap; }

/* Grokking events */
.grok-event-list { display: flex; flex-direction: column; gap: 4px; }
.grok-event-item {
  display: flex; gap: 12px; align-items: center;
  font-size: 11px; font-family: var(--font-mono);
  padding: 4px 8px; background: var(--bg-deep); border-radius: 2px;
}
.grok-event-step  { color: var(--text-secondary); min-width: 80px; }
.grok-event-drop  { min-width: 80px; }
.grok-event-label { color: var(--text-muted); }

/* Lora selector chips */
.lora-selector {
  display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px;
}
.lora-chip {
  background: var(--bg-panel); border: 1px solid var(--border-dim);
  border-radius: 2px; padding: 4px 10px;
  font-size: 11px; font-family: var(--font-mono); cursor: pointer;
  display: flex; align-items: center; gap: 4px;
  color: var(--text-secondary);
}
.lora-chip.active { border-color: var(--blue-core); color: var(--text-primary); }
.domain-phase-dot { font-size: 8px; }
```

---

## Checklist Fase 4 Brain Visualization

```
[ ] LoRAMetadata interface — fields baru: training_phase, grokking_confidence,
    loss_curve, circuit_count (Mechanistic Interpretability)
[ ] WorkerBrainState — fields baru: grokked_count, memorizing_count, overall_health
[ ] Tab brain di CEO office: compact view + health dot + tombol "open brain viz"
[ ] BrainVisualization full page terbuka sebagai overlay
[ ] Tab 1 Overview: brain health indicator, training phase overview, domain strength
    bars dengan phase color coding, stats grid dengan Grokked count
[ ] Tab 2 LoRA Manager: list semua LoRA, weight slider, toggle, delete
[ ] Tab 3 Conflict Map: orthogonality matrix heatmap, warning list
[ ] Tab 4 Loss Curve: LoRA selector, phase banner, loss curve chart (Chart.js),
    grokking event annotations, interpretability footnote
[ ] Backend API: GET /brain/{worker_id}, POST toggle, POST weight, GET orthogonality
[ ] Backend API BARU: GET /brain/{worker_id}/loss-curve/{lora_name}
[ ] Backend API BARU: GET /brain/{worker_id}/grokking-phase/{lora_name}
[ ] Trainer auto-run grokking analysis setelah setiap training run
[ ] Trainer simpan loss curve snapshots ke Ring 2 experiments.parquet
[ ] Toggle LoRA langsung update inference di vLLM (tanpa restart)
[ ] "Request Refactor" kirim task ke trainer worker via conductor
[ ] "Train now" dari recommendation card → trigger trainer untuk domain baru
[ ] Health indicator di CEO office worker paper (compact — hanya warna dot)
```
