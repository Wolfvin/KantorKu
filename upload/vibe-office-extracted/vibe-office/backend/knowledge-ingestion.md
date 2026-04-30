# Backend — Knowledge Ingestion Pipeline (Fase 3)

> **Konteks untuk session baru:**
> Knowledge ingestion adalah cara user "mengajari" workers secara aktif.
> User tempel teks di NovaNotes → curator otomatis:
>   1. Rapikan dan klasifikasi konten
>   2. Update atau buat SKILL.md untuk domain yang terdeteksi
>   3. Kirim ke Ring 2 sebagai episode bertipe "knowledge_inject"
>   4. Flag ke trainer kalau domain sudah di atas threshold
> Trigger: manual (tombol "Send to Curator") atau auto (paste > 300 kata).
> File terkait:
>   - `frontend/nova-notes-integration.md` → UI NovaNotes + trigger
>   - `backend/workers.md` → curator worker definition
>   - `backend/memory.md` → Ring 2 Parquet episode storage

---

## WebSocket Event

```python
# Event masuk dari frontend:
{
  "type": "knowledge_ingest",
  "source": "nova_notes",           # atau "web_paste", "file_import"
  "note_id": 1234,
  "title": "Rust Lifetimes Deep Dive",
  "content": "# Rust Lifetimes\n\nLifetimes are..."
}

# Event balik ke frontend setelah selesai:
{
  "type": "knowledge_ingest_done",
  "note_id": 1234,
  "domains": ["coder_rust.lifetimes", "coder_rust.borrow_checker"],
  "skill_updated": true,
  "skill_created": false,
  "episode_id": "ep_20260317_abc123",
  "summary": "Detailed guide on Rust lifetime annotations and borrow checker patterns."
}
```

---

## Pipeline Lengkap

```python
# backend/workers/curator.py — fungsi knowledge_ingest

async def knowledge_ingest(event: dict) -> dict:
    """
    Pipeline 3 langkah: classify → skill_update → ring2_store
    Berjalan di background — tidak block WebSocket.
    """
    content = event['content']
    title   = event.get('title', 'Untitled')
    note_id = event.get('note_id')

    # Notify game: curator mulai kerja
    await ws_broadcast({
        'type': 'state_change',
        'worker_id': 'curator',
        'new_state': 'working'
    })
    await ws_broadcast({
        'type': 'speech_bubble',
        'worker_id': 'curator',
        'text': 'reading... classifying...',
        'color': '#89DDFF',
        'duration_ms': 3000,
    })

    # --- STEP 1: Classify & Clean ---
    classification = await classify_content(content, title)

    # --- STEP 2: Update SKILL.md ---
    skill_result = await update_skills(classification, content)

    # --- STEP 3: Store ke Ring 2 ---
    episode_id = await store_knowledge_episode(
        classification=classification,
        content=content,
        title=title,
        note_id=note_id,
    )

    # --- STEP 4: Check trainer threshold ---
    for domain in classification['domains']:
        await check_training_threshold(domain)

    # Notify game: curator selesai
    await ws_broadcast({
        'type': 'state_change',
        'worker_id': 'curator',
        'new_state': 'idle'
    })
    await ws_broadcast({
        'type': 'speech_bubble',
        'worker_id': 'curator',
        'text': f'filed under: {", ".join(classification["domains"])} ✓',
        'color': '#89DDFF',
        'duration_ms': 4000,
    })

    return {
        'type': 'knowledge_ingest_done',
        'note_id': note_id,
        'domains': classification['domains'],
        'skill_updated': skill_result['updated'],
        'skill_created': skill_result['created'],
        'episode_id': episode_id,
        'summary': classification['summary'],
    }
```

---

## Step 1: Classify & Clean

```python
CLASSIFY_SYSTEM = """
You are curator. You read raw text and extract structured knowledge.
Output ONLY valid JSON. No preamble, no explanation.
"""

CLASSIFY_PROMPT = """
Text title: {title}

Text content:
{content}

Classify this content and output JSON:
{{
  "summary": "<2-3 sentence summary of the key insights>",
  "domains": ["<worker_id>.<subdomain>", ...],
  "knowledge_type": "tutorial" | "reference" | "pattern" | "gotcha" | "comparison" | "other",
  "key_concepts": ["<concept1>", "<concept2>"],
  "actionable": true | false,
  "quality_score": <0.0–1.0>,
  "cleaned_content": "<reformatted clean markdown of the key content>"
}}

Domain format examples:
  "coder_rust.lifetimes"
  "coder_rust.async"
  "coder_python.ml_patterns"
  "coder_css.animations"
  "tester.property_testing"
  "auditor.security_patterns"
  "conductor.planning_patterns"

Only include domains where content is genuinely relevant.
Quality score: 0.0 = noise/spam, 0.5 = ok, 1.0 = excellent reference.
If quality_score < 0.3, set actionable: false.
"""

async def classify_content(content: str, title: str) -> dict:
    # Truncate kalau terlalu panjang (curator hanya butuh inti)
    truncated = content[:8000] if len(content) > 8000 else content

    response = await llm_call(
        model='conductor',  # pakai conductor untuk classification quality
        system=CLASSIFY_SYSTEM,
        prompt=CLASSIFY_PROMPT.format(title=title, content=truncated),
        temperature=0.2,
    )

    result = json.loads(response)

    # Safety: buang domain yang tidak valid
    valid_workers = get_all_worker_ids()
    result['domains'] = [
        d for d in result['domains']
        if d.split('.')[0] in valid_workers
    ]

    return result
```

---

## Step 2: Update SKILL.md

```python
async def update_skills(classification: dict, raw_content: str) -> dict:
    """
    Update atau buat SKILL.md untuk setiap domain yang terdeteksi.
    Hanya update kalau quality_score > 0.5 dan actionable = true.
    """
    if not classification.get('actionable') or classification.get('quality_score', 0) < 0.5:
        return {'updated': False, 'created': False, 'reason': 'low_quality'}

    updated = []
    created = []

    for domain_str in classification['domains']:
        worker_id, subdomain = domain_str.split('.', 1)
        skill_path = get_skill_path(worker_id, subdomain)

        if skill_path.exists():
            # Update existing SKILL.md — append ke "Lessons Learned" section
            await append_to_skill(
                path=skill_path,
                subdomain=subdomain,
                new_insight=classification['summary'],
                key_concepts=classification['key_concepts'],
                source_title=classification.get('title', 'NovaNotes'),
            )
            updated.append(domain_str)
        else:
            # Buat SKILL.md baru untuk subdomain ini
            await create_skill(
                worker_id=worker_id,
                subdomain=subdomain,
                content=classification['cleaned_content'],
                summary=classification['summary'],
                key_concepts=classification['key_concepts'],
            )
            created.append(domain_str)

    return {
        'updated': len(updated) > 0,
        'created': len(created) > 0,
        'updated_domains': updated,
        'created_domains': created,
    }

async def append_to_skill(path, subdomain, new_insight, key_concepts, source_title):
    """Append insight ke section 'Lessons Learned' di SKILL.md."""
    existing = path.read_text()

    # Cari section atau buat baru
    section_header = "## Lessons Learned"
    new_entry = f"""
### {source_title} _{datetime.now().strftime('%Y-%m-%d')}_

{new_insight}

Key concepts: {', '.join(f'`{c}`' for c in key_concepts)}

---
"""
    if section_header in existing:
        updated = existing.replace(
            section_header,
            section_header + "\n" + new_entry
        )
    else:
        updated = existing + f"\n{section_header}\n{new_entry}"

    path.write_text(updated)
```

---

## Step 3: Store ke Ring 2

```python
async def store_knowledge_episode(classification, content, title, note_id) -> str:
    """
    Simpan ke Ring 2 Parquet sebagai episode tipe 'knowledge_inject'.
    Episode ini bisa dipakai oleh trainer untuk fine-tune workers.
    """
    episode_id = f"ep_{datetime.now().strftime('%Y%m%d')}_{uuid4().hex[:8]}"

    for domain_str in classification['domains']:
        worker_id, subdomain = domain_str.split('.', 1)

        episode = {
            'episode_id':    episode_id,
            'episode_type':  'knowledge_inject',
            'worker_id':     worker_id,
            'domain':        subdomain,
            'source':        'nova_notes',
            'note_id':       note_id,
            'title':         title,
            'instruction':   f"Understand and apply: {title}",
            'result_summary': classification['summary'],
            'key_concepts':  json.dumps(classification['key_concepts']),
            'quality_score': classification['quality_score'],
            'knowledge_type': classification['knowledge_type'],
            'raw_content':   classification['cleaned_content'][:2000],  # truncate
            'success':       True,
            'timestamp':     datetime.now().isoformat(),
        }

        # Tulis ke Ring 1 dulu (DuckDB), flush ke Ring 2 async
        await ring1_write_episode(episode)

    return episode_id
```

---

## Step 4: Check Training Threshold

```python
TRAINING_THRESHOLD = 200  # minimum episodes sebelum trainer bisa fire

async def check_training_threshold(domain_str: str):
    """
    Setelah episode baru masuk, cek apakah domain ini sudah cukup data.
    Kalau ya → notify trainer.
    """
    worker_id, subdomain = domain_str.split('.', 1)

    count = await ring2_count_episodes(
        worker_id=worker_id,
        domain=subdomain,
        min_quality=0.5,  # hanya episode yang berkualitas
    )

    if count >= TRAINING_THRESHOLD:
        # Flag ke trainer via conductor
        await conductor_queue.put({
            'type': 'training_ready',
            'worker_id': worker_id,
            'domain': subdomain,
            'episode_count': count,
        })

        await ws_broadcast({
            'type': 'speech_bubble',
            'worker_id': 'curator',
            'text': f'{worker_id}.{subdomain}: {count} episodes — training ready 🧪',
            'color': '#C792EA',
            'duration_ms': 5000,
        })
```

---

## Knowledge Browser — Ring 2 Visibility

> Jawaban untuk: "apakah saya bisa langsung lihat penyimpanannya?"

```python
# API endpoint untuk Knowledge Browser di Lab Room

@router.get("/api/knowledge/index")
async def get_knowledge_index() -> list[dict]:
    """
    Return semua domain knowledge yang ada di Ring 2.
    Ini adalah data yang ditampilkan di Knowledge Browser.
    """
    domains = await ring2_list_domains()
    result = []

    for worker_id, subdomain in domains:
        count       = await ring2_count_episodes(worker_id, subdomain)
        quality_avg = await ring2_avg_quality(worker_id, subdomain)
        latest      = await ring2_latest_episode(worker_id, subdomain)
        threshold_pct = min(count / TRAINING_THRESHOLD, 1.0)

        result.append({
            'worker_id':       worker_id,
            'domain':          subdomain,
            'episode_count':   count,
            'quality_avg':     quality_avg,
            'threshold_pct':   threshold_pct,  # 0.0–1.0, 1.0 = training ready
            'training_ready':  count >= TRAINING_THRESHOLD,
            'latest_title':    latest.get('title'),
            'latest_at':       latest.get('timestamp'),
            'skill_exists':    get_skill_path(worker_id, subdomain).exists(),
        })

    return sorted(result, key=lambda x: x['episode_count'], reverse=True)

@router.get("/api/knowledge/{worker_id}/{domain}/episodes")
async def get_domain_episodes(
    worker_id: str,
    domain: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """
    List episodes untuk domain tertentu — untuk Knowledge Browser detail view.
    Pagination: limit + offset.
    """
    return await ring2_list_episodes(worker_id, domain, limit, offset)

@router.post("/api/knowledge/{worker_id}/{domain}/episodes/{episode_id}/exclude")
async def exclude_episode(worker_id: str, domain: str, episode_id: str):
    """
    User bisa mark episode sebagai 'do not use for training'.
    Berguna kalau kamu tahu episode itu edge case atau salah.
    """
    await ring2_update_episode(episode_id, {'excluded': True})
    return {'excluded': True}
```

---

## Knowledge Browser UI (di Lab Room — komputer curator)

```typescript
// Komputer curator di Lab Room → klik → buka KnowledgeBrowser panel

function KnowledgeBrowser() {
  const [domains, setDomains] = useState<DomainSummary[]>([])
  const [selected, setSelected] = useState<{worker: string, domain: string} | null>(null)
  const [episodes, setEpisodes] = useState<Episode[]>([])

  return (
    <div className="knowledge-browser">
      {/* Left: domain list */}
      <div className="kb-domain-list">
        <div className="kb-title">KNOWLEDGE VAULT</div>
        {domains.map(d => (
          <div
            key={`${d.worker_id}.${d.domain}`}
            className={`kb-domain-row ${d.training_ready ? 'ready' : ''}`}
            onClick={() => setSelected({ worker: d.worker_id, domain: d.domain })}
          >
            <span className="kb-domain-name">{d.worker_id}.{d.domain}</span>
            <div className="kb-threshold-bar">
              <div
                className="kb-threshold-fill"
                style={{
                  width: `${d.threshold_pct * 100}%`,
                  background: d.training_ready ? '#44ff88' : '#2b7fff'
                }}
              />
            </div>
            <span className="kb-count">{d.episode_count}</span>
            {d.training_ready && <span className="kb-ready-badge">READY</span>}
          </div>
        ))}
      </div>

      {/* Right: episode list */}
      {selected && (
        <div className="kb-episode-list">
          <div className="kb-episode-header">
            {selected.worker}.{selected.domain} — {episodes.length} episodes
          </div>
          {episodes.map(ep => (
            <div key={ep.episode_id} className={`kb-episode-row ${ep.excluded ? 'excluded' : ''}`}>
              <span className="kb-ep-title">{ep.title}</span>
              <span className="kb-ep-quality">{(ep.quality_score * 100).toFixed(0)}%</span>
              <span className="kb-ep-type">{ep.knowledge_type}</span>
              <span className="kb-ep-date">{formatDate(ep.timestamp)}</span>
              <button
                className="kb-ep-exclude"
                onClick={() => excludeEpisode(ep.episode_id)}
                title={ep.excluded ? "Excluded from training" : "Exclude from training"}
              >
                {ep.excluded ? '✗' : '○'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

---

## Checklist

```
Fase 3 — Backend:
[ ] knowledge_ingest() handler di curator worker
[ ] classify_content() → JSON classification dengan domains
[ ] update_skills() → append/create SKILL.md per domain
[ ] store_knowledge_episode() → Ring 2 Parquet
[ ] check_training_threshold() → notify trainer saat ready

Fase 3 — Frontend:
[ ] Knowledge Browser panel di komputer curator (Lab Room)
[ ] Domain list dengan threshold progress bar
[ ] Episode list dengan exclude toggle
[ ] GET /api/knowledge/index endpoint
[ ] GET /api/knowledge/{worker}/{domain}/episodes endpoint
[ ] POST /api/knowledge/.../exclude endpoint
```
