# Backend — Uncertainty & Escalation System

> **CATATAN PENTING (v5.0):**
> "dLLM" di file ini BUKAN Diffusion LLM (Open-dLLM).
> Ini adalah "detection layer" — logic di conductor untuk detect task ambiguity.
> Diffusion LLM (inference method) didokumentasikan terpisah di training-landscape.md.
> Nama di file ini akan direfactor ke "uncertainty_detector" untuk menghindari konflik.

> **Konteks untuk session baru:**
> File ini menggabungkan dua sumber:
> 1. Say-I-Dont-Know (github.com/OpenMOSS/Say-I-Dont-Know, ICML 2024) —
>    paper riset tentang "knowledge quadrant" AI: kapan harus bilang tidak tahu
> 2. Ide yang diusulkan: kalau worker bilang tidak tahu → oper ke context_worker
>    yang search → inject knowledge → update SKILL.md via Cognee
> Ini adalah sistem self-improving yang terintegrasi dengan Three-Ring Memory.
> Dievaluasi dan dirancang session 2026-03-16.

---

## Knowledge Quadrant (dari Say-I-Dont-Know)

Paper ICML 2024 dari OpenMOSS membagi pengetahuan AI ke 4 kuadran:

```
                  TAHU JAWABANNYA
                  (model confident)
        ┌─────────────┬─────────────┐
  TAHU  │  Known      │  Unknown    │
  BATAS │  Known ✅   │  Known ⚠️  │
  DIRI  ├─────────────┼─────────────┤
        │  Known      │  Unknown    │
  TIDAK │  Unknown ❌ │  Unknown ❌ │
  TAHU  └─────────────┴─────────────┘
                  TIDAK TAHU JAWABANNYA
```

- **Known-Known (KK)**: Tahu dan tahu bahwa tahu → jawab dengan benar ✅
- **Known-Unknown (KU)**: Tidak tahu dan tahu tidak tahu → bilang "tidak tahu" ⚠️
- **Unknown-Known (UK)**: Tahu tapi tidak tahu bahwa tahu → mungkin jawab salah ❌
- **Unknown-Unknown (UU)**: Tidak tahu dan tidak tahu tidak tahu → hallucinate ❌

**Goal sistem ini:** Transform UK dan UU → KK dan KU.
Caranya: worker yang detect UU/UK → eskalasi → context_worker inject knowledge
→ worker sekarang jadi KK atau KU → SKILL.md di-update dengan lesson.

---

## Alur Escalation di Vibe-Office

```
Worker dapat task
  ↓
Worker assess confidence (sebelum execute):
  "Apakah saya punya knowledge yang cukup untuk ini?"
  
  confidence HIGH (KK) → execute langsung
  confidence LOW (KU)  → trigger uncertainty_escalation()
  
  Selama execute:
  Worker detect output tidak reliable (UK/UU)?
    → trigger post_execution_escalation()
```

**Uncertainty signal yang detectable:**
- Worker menghasilkan kode dengan banyak `// TODO: not sure about this`
- Output mengandung pola "I'm not certain", "might be", "should work"
- Kode tidak compile setelah 2 retry (strong signal: wrong approach)
- review_worker flag `confidence: low` pada output

---

## Implementation: Uncertainty Escalation Flow

```python
# Di worker agent loop — tambahkan sebelum dan sesudah execute

class UncertaintyDetector:
    """Detect apakah worker KK, KU, UK, atau UU untuk task ini."""

    UNCERTAINTY_PHRASES = [
        "i'm not sure", "might work", "should be",
        "not certain", "possibly", "// todo", "// fixme",
        "approximately", "i think", "probably"
    ]

    def assess_output(self, output: dict) -> float:
        """Return confidence score 0.0–1.0."""
        code = output.get('code', '')
        explanation = output.get('explanation', '')
        text = (code + explanation).lower()

        uncertainty_count = sum(
            1 for phrase in self.UNCERTAINTY_PHRASES
            if phrase in text
        )
        warnings_count = len(output.get('warnings', []))

        # Hitung: lebih banyak uncertainty signals = confidence lebih rendah
        raw_score = 1.0 - (uncertainty_count * 0.15) - (warnings_count * 0.10)
        return max(0.0, min(1.0, raw_score))

    def should_escalate(self, score: float, threshold: float = 0.6) -> bool:
        return score < threshold


async def worker_execute_with_uncertainty(
    worker_id: str,
    task: dict,
    messages: list
) -> dict:
    """Worker execute dengan uncertainty detection built-in."""

    # Execute task
    output = await agent_loop(messages, tools=WORKER_TOOLS[worker_id])

    # Assess confidence
    detector = UncertaintyDetector()
    confidence = detector.assess_output(output)

    if detector.should_escalate(confidence):
        # ESKALASI: oper ke context_worker untuk knowledge injection
        enriched = await uncertainty_escalation(
            worker_id=worker_id,
            task=task,
            failed_output=output,
            confidence=confidence
        )
        return enriched

    return output


async def uncertainty_escalation(
    worker_id: str,
    task: dict,
    failed_output: dict,
    confidence: float
) -> dict:
    """
    Ketika worker tidak yakin:
    1. context_worker search untuk knowledge yang relevan
    2. Knowledge di-inject ke task context
    3. Worker re-execute dengan context yang lebih kaya
    4. Lesson di-update ke SKILL.md via Cognee
    """

    # Notify game UI: worker sedang escalate
    await ws_broadcast({
        'type': 'state_change',
        'worker_id': worker_id,
        'new_state': 'blocked',
    })
    await ws_broadcast({
        'type': 'speech_bubble',
        'worker_id': worker_id,
        'text': f"uncertain ({confidence:.0%}), getting help...",
        'color': '#FFB300',  # kuning
        'duration_ms': 3000
    })

    # context_worker search untuk knowledge tambahan
    search_queries = extract_knowledge_gaps(task, failed_output)
    new_knowledge = []
    for query in search_queries:
        # Query GitNexus untuk codebase context
        gitnexus_result = await gitnexus.query(query)
        new_knowledge.append(gitnexus_result)

        # Kalau butuh external docs, Lightpanda scrape
        if needs_external_docs(query):
            docs = await lightpanda.scrape(f"https://docs.rs/{query}")
            new_knowledge.append(docs)

    # Inject knowledge baru ke task context
    task['context']['injected_knowledge'] = new_knowledge
    task['context']['uncertainty_note'] = (
        f"Previous attempt had confidence {confidence:.0%}. "
        f"Additional context injected. Please try again with this knowledge."
    )

    # Re-execute dengan knowledge yang lebih kaya
    enriched_output = await agent_loop(
        messages=build_messages(task),
        tools=WORKER_TOOLS[worker_id]
    )

    # Update Cognee Ring 3 dengan lesson
    await update_worker_knowledge(
        worker_id=worker_id,
        gap=search_queries,
        knowledge=new_knowledge,
        success=(UncertaintyDetector().assess_output(enriched_output) > 0.7)
    )

    return enriched_output


async def update_worker_knowledge(
    worker_id: str,
    gap: list,
    knowledge: list,
    success: bool
):
    """
    Update SKILL.md worker dengan lesson yang dipelajari dari escalation.
    Ini yang membuat workers makin pintar seiring waktu.
    """
    if not success:
        return  # tidak update kalau masih gagal

    lesson = f"When facing {', '.join(gap)}, inject context from: {summarize(knowledge)}"

    # Update via Cognee (Ring 3 eventual)
    await cognee.add(f"Lesson for {worker_id}: {lesson}")
    await cognee.cognify()

    # Langsung patch SKILL.md juga (immediate)
    await patch_worker_skill(
        worker_id=worker_id,
        section="Lessons Learned",
        new_entry=lesson
    )
```

---

## Integration dengan dLLM (Noise Detection)

dLLM (dari v2.9) sekarang punya tambahan responsibility:
selain detect noise/hallucination dari orchestrator,
juga monitor uncertainty signals dari workers.

```python
# dLLM tambahan check: uncertainty pattern
DLLM_UNCERTAINTY_CHECKS = {
    'worker_output': [
        lambda o: o.get('confidence_score', 1.0) < 0.5,  # worker self-report
        lambda o: len(o.get('warnings', [])) > 3,
        lambda o: 'TODO' in o.get('code', '') and count_todos(o['code']) > 5,
    ]
}
```

dLLM tidak auto-correct (aturan kritis #4) — tapi bisa trigger
uncertainty_escalation flow sebagai alternative ke blocking.

---

## Say-I-Dont-Know: Kapan Code-nya Relevan

Paper ini punya training approach (SFT/DPO/PPO) untuk membuat LLM yang
secara intrinsic bisa detect batas pengetahuannya sendiri.

**Relevansi untuk vibe-office:** Fase 4+, saat fine-tuning workers.
Idk dataset dari paper ini bisa jadi tambahan training signal:
train rust_worker untuk bilang "gak tau" dengan benar, bukan hallucinate.

```bash
# Download Idk dataset dari paper (untuk Fase 4 training)
# Dataset: Triviaqa-based Idk pairs untuk Llama-2-7b, Mistral-7b, dll

# Bisa adaptasi dengan curating vibe-office specific Idk pairs:
# "apakah fungsi ini thread-safe?" → "I don't have enough context to be certain"
# vs hallucinating "yes it is thread-safe" yang salah
```

**Training approach yang paling mudah untuk vibe-office:**
Tidak perlu full SFT/DPO dari paper. Cukup tambahkan contoh dalam
training data Unsloth (Fase 4):
```
Input: [task yang di luar kemampuan worker]
Output: {"confidence": 0.3, "uncertainty_reason": "...", "escalate": true}
```

Ini lebih sederhana dari paper tapi effective untuk production use case.
