# Backend — Knowledge Approval Pipeline (Fase 3)

> **Konteks untuk session baru:**
> Setiap knowledge yang curator klasifikasi TIDAK langsung masuk ke trainer.
> Harus lewat auditor dulu untuk approval.
> Flow: curator done → status "waiting_approval" → auditor review (otomatis LLM)
> → APPROVED: ke trainer | REJECTED: ke coder terkait untuk fix → loop sampai approved.
> Semua komunikasi antar worker melewati bridge (translation layer).
> File terkait:
>   - `backend/knowledge-ingestion.md` → curator pipeline sebelum approval
>   - `backend/workers.md` → auditor + bridge worker definitions

---

## Full Pipeline

```
curator selesai classify knowledge
  ↓
bridge.relay('curator', 'auditor', knowledge_review_request)
  ↓
status Ring 1: "waiting_approval"
  ↓
auditor review (LLM, otomatis):
  - domain classification benar?
  - quality score masuk akal?
  - content tidak misleading/berbahaya?
  ↓
  ┌─── APPROVED ──────────────────────────────────────┐
  │ bridge.relay('auditor', 'trainer', approved_data) │
  │ status → "approved"                               │
  │ trainer terima → threshold check                 │
  └────────────────────────────────────────────────────┘
  ┌─── REJECTED ──────────────────────────────────────┐
  │ bridge.relay('auditor', coder_terkait, fix_req)   │
  │ status → "needs_fix"                              │
  │ coder fix → bridge → auditor re-review            │
  │ loop sampai approved                              │
  └────────────────────────────────────────────────────┘
```

---

## Status States

```python
# Di Ring 1 DuckDB — field 'approval_status' di knowledge_queue table

APPROVAL_STATES = [
    'waiting_approval',   # curator selesai, menunggu auditor
    'under_review',       # auditor sedang review
    'approved',           # auditor OK → masuk ke trainer queue
    'rejected',           # auditor reject → kirim ke coder
    'needs_fix',          # coder sedang fix
    'fix_submitted',      # coder selesai fix → kembali ke auditor
    'discarded',          # reject berulang (> 3x) → curator buang
]
```

---

## Bridge Messages — Semua Lewat Sini

```python
# backend/bridge.py — extend ROUTE_HANDLERS dengan knowledge routes

KNOWLEDGE_ROUTES = {

  # Curator → Auditor
  ('curator', 'auditor'): lambda out: {
    'task_type': 'knowledge_review',
    'knowledge_id': out['episode_id'],
    'title': out['title'],
    'domains': out['domains'],               # curator's classification
    'quality_score': out['quality_score'],
    'knowledge_type': out['knowledge_type'],
    'summary': out['summary'],
    'cleaned_content': out['cleaned_content'],
    'source': out['source'],                 # "nova_notes" | "scout_web" | "file_import"
    'review_checklist': [
      'domain_classification_correct',
      'quality_score_reasonable',
      'content_not_misleading',
      'content_not_harmful',
      'actionable_for_workers',
    ],
  },

  # Auditor → Trainer (approved)
  ('auditor', 'trainer'): lambda out: {
    'task_type': 'knowledge_approved',
    'knowledge_id': out['knowledge_id'],
    'domains': out['approved_domains'],      # bisa berbeda dari curator's domains
    'quality_score': out['final_quality'],   # auditor bisa adjust score
    'episode_id': out['episode_id'],
    'ready_for_threshold_check': True,
  },

  # Auditor → Coder (rejected, needs fix)
  ('auditor', 'coder_*'): lambda out: {
    'task_type': 'knowledge_fix',
    'knowledge_id': out['knowledge_id'],
    'rejection_reason': out['rejection_reason'],
    'specific_issues': out['issues'],        # list masalah konkret
    'original_content': out['content'],
    'suggested_fixes': out['suggestions'],   # auditor kasih hint
    'return_to': 'auditor',                  # setelah fix, kirim balik ke auditor
  },

  # Coder → Auditor (fix submitted)
  ('coder_*', 'auditor'): lambda out: {
    'task_type': 'knowledge_recheck',
    'knowledge_id': out['knowledge_id'],
    'fix_description': out['what_was_fixed'],
    'updated_content': out['content'],
    'attempt_number': out['attempt'],
  },
}
```

---

## Auditor Review Logic

```python
# Di backend/workers.py — auditor worker, mode 3: knowledge_review

KNOWLEDGE_REVIEW_SYSTEM = """
You are auditor reviewing knowledge before it enters the training pipeline.
Be strict but fair. Output ONLY valid JSON.
"""

KNOWLEDGE_REVIEW_PROMPT = """
Review this knowledge submission:

Title: {title}
Source: {source}
Curator's domains: {domains}
Quality score (curator): {quality_score}
Knowledge type: {knowledge_type}
Summary: {summary}

Content:
{content}

Review checklist:
{checklist}

Output JSON:
{{
  "decision": "approved" | "rejected",
  "approved_domains": [...],          // dapat berbeda dari curator's domains
  "final_quality": <0.0-1.0>,
  "rejection_reason": "<string | null>",
  "issues": ["<issue1>", ...],        // kalau rejected
  "suggestions": ["<fix1>", ...],     // kalau rejected — hint untuk coder
  "confidence": <0.0-1.0>,            // seberapa yakin auditor dengan keputusannya
  "review_notes": "<brief notes>"
}}

REJECTION criteria:
- Domain classification clearly wrong (e.g., CSS tutorial classified as Rust)
- Content contains factual errors that could mislead workers
- Quality score inflated (curator gave 0.9 but content is shallow)
- Content is harmful, toxic, or promotes bad practices
- Not actionable for any worker

APPROVAL criteria:
- Domain makes sense even if slightly off
- Content is genuinely useful reference
- Quality score roughly accurate
"""

async def review_knowledge(request: dict) -> dict:
    attempt = request.get('attempt_number', 1)

    # Kalau sudah 3x reject → auto discard
    if attempt > 3:
        await update_knowledge_status(request['knowledge_id'], 'discarded')
        await ws_broadcast({
            'type': 'speech_bubble',
            'worker_id': 'auditor',
            'text': f'discarded after {attempt} attempts.',
            'color': '#FF5252',
            'duration_ms': 3000,
        })
        return {'decision': 'discarded'}

    response = await llm_call(
        model='auditor',
        system=KNOWLEDGE_REVIEW_SYSTEM,
        prompt=KNOWLEDGE_REVIEW_PROMPT.format(**request),
        temperature=0.1,  # sangat deterministik untuk review
    )

    result = json.loads(response)

    if result['decision'] == 'approved':
        await update_knowledge_status(request['knowledge_id'], 'approved')
        await bridge.relay('auditor', 'trainer', {**result, **request})
        await ws_broadcast({
            'type': 'speech_bubble',
            'worker_id': 'auditor',
            'text': f'approved: {", ".join(result["approved_domains"])} ✓',
            'color': '#44ff88',
            'duration_ms': 3000,
        })
    else:
        # Tentukan coder mana yang paling relevan untuk fix
        target_coder = pick_coder_for_domain(result['approved_domains'] or request['domains'])
        await update_knowledge_status(request['knowledge_id'], 'needs_fix')
        await bridge.relay('auditor', target_coder, {
            **result,
            'knowledge_id': request['knowledge_id'],
            'content': request['cleaned_content'],
            'attempt': attempt,
        })
        await ws_broadcast({
            'type': 'speech_bubble',
            'worker_id': 'auditor',
            'text': f'rejected → {target_coder}: {result["rejection_reason"]}',
            'color': '#FF9800',
            'duration_ms': 4000,
        })

    return result

def pick_coder_for_domain(domains: list[str]) -> str:
    """Pilih coder yang paling relevan berdasarkan domain."""
    for d in domains:
        if 'rust' in d:   return 'coder_rust'
        if 'python' in d: return 'coder_python'
        if 'css' in d:    return 'coder_css'
        if 'js' in d or 'ts' in d: return 'coder_js'
    return 'coder_rust'  # default
```

---

## UI — Waiting for Approval Status

```typescript
// Di Knowledge Browser (Tab All Episodes) dan chat panel

// Status badge di episode row:
const APPROVAL_STATUS_UI = {
  'waiting_approval': { label: 'waiting',    color: '#FFCB6B', icon: '⏳' },
  'under_review':     { label: 'reviewing',  color: '#89DDFF', icon: '🔍' },
  'approved':         { label: 'approved',   color: '#44ff88', icon: '✓'  },
  'rejected':         { label: 'rejected',   color: '#FF5252', icon: '✗'  },
  'needs_fix':        { label: 'fixing',     color: '#FF9800', icon: '🔧' },
  'fix_submitted':    { label: 'rechecking', color: '#C792EA', icon: '↩'  },
  'discarded':        { label: 'discarded',  color: '#555',    icon: '🗑'  },
}

// Chat panel notification saat status berubah:
// "⏳ curator: Rust Lifetimes Deep Dive — waiting for approval"
// "🔍 auditor: reviewing..."
// "✓ auditor: approved → trainer queue"
// "🔧 coder_rust: fixing domain classification issue..."
```

---

## Checklist Fase 3

```
[ ] knowledge_queue table di Ring 1 dengan approval_status field
[ ] bridge KNOWLEDGE_ROUTES terdaftar
[ ] auditor mode 3: knowledge_review handler
[ ] review_knowledge() dengan auto-discard setelah 3x reject
[ ] pick_coder_for_domain() routing logic
[ ] update_knowledge_status() update Ring 1
[ ] Status badges di Knowledge Browser Tab All Episodes
[ ] Chat panel notifications per status change
[ ] Speech bubbles auditor saat approve/reject
[ ] Animasi: auditor dan curator terlihat interact saat review berlangsung
```
