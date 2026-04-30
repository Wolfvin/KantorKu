# Backend — Training Landscape

> **Konteks untuk session baru yang baca file ini:**
> Vibe-office butuh workers yang di-fine-tune pada coding tasks spesifik.
> File ini menjelaskan KAPAN pakai tool mana, bukan tutorial masing-masing.
> Keputusan akhir: Unsloth untuk fine-tuning, BitNet untuk inference tanpa GPU.
> Sumber: evaluasi 5 repos session 2026-03-16.

---

## Dua Masalah yang Berbeda

```
MASALAH 1: Bagaimana TRAIN model agar worker lebih pintar?
           → Unsloth (fine-tuning QLoRA/DoRA)

MASALAH 2: Bagaimana RUN model kecepatan tinggi di hardware terbatas?
           → BitNet (CPU inference untuk 1-bit LLMs)
           → atau Ollama/vLLM (untuk model biasa)
```

Ini dua masalah berbeda. Jangan campur aduk.

---

## Unsloth — Fine-tuning Workers

**Repo:** https://github.com/unslothai/unsloth
MIT license. Untuk QLoRA dan DoRA fine-tuning.

**Kapan pakai:** Fase 4 — saat mau fine-tune Qwen2.5-Coder-7B agar
rust_worker / tester_worker lebih akurat pada task spesifik vibe-office.

**Kenapa Unsloth bukan vanilla PEFT:**
- 2x lebih hemat VRAM (fine-tune 7B di GPU 8GB bisa)
- 2x lebih cepat training
- Kompatibel penuh dengan HuggingFace ecosystem

**Setup dasar:**
```python
from unsloth import FastLanguageModel
import torch

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="Qwen/Qwen2.5-Coder-7B-Instruct",
    max_seq_length=4096,
    dtype=torch.bfloat16,       # BF16 — lebih stabil dari FP16 untuk Qwen
    load_in_4bit=True,          # QLoRA: 4-bit base weights
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,                       # LoRA rank — 16 cukup untuk task spesifik
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",   # hemat VRAM ekstra
    random_state=42,            # reproducibility
)
```

**Training data untuk workers:**
Data training diambil dari Ring 2 (Parquet episodes) yang sudah terkumpul.
Format: instruction → ideal output pairs dari task-task yang berhasil.

```python
# Format dataset dari Ring 2 episodes
def format_episode_for_training(episode: dict) -> dict:
    return {
        "instruction": episode["instruction"],
        "input": json.dumps(episode["context"]),
        "output": episode["result"]["code"],  # untuk rust_worker
    }
```

**Pipeline training (Fase 4):**
```
Ring 2 Parquet episodes
  ↓ filter: success=True, task_type=write_code
  ↓ format ke instruction-output pairs
  ↓ Unsloth fine-tune Qwen2.5-Coder-7B
  ↓ export ke GGUF (untuk Ollama) atau safetensors (untuk vLLM)
  ↓ replace model di rust_worker plugin.json
```

---

## BitNet — CPU Inference Tanpa GPU

**Repo:** https://github.com/microsoft/BitNet
MIT license, 25.8k stars. Official inference framework untuk 1-bit LLMs.

**Kapan pakai:** Ketika tidak ada GPU dan perlu run model lokal dengan cepat.
- Speedup 1.37x–5.07x di ARM CPU
- Energy reduction 55–70%
- Bisa run 100B model di single CPU (kecepatan ~5-7 token/detik)

**Kapan TIDAK pakai:**
- Kalau mau fine-tune model → pakai Unsloth
- Kalau punya GPU → Ollama/vLLM lebih fleksibel
- BitNet hanya support model yang sudah di-train dengan arsitektur 1-bit

**Model tersedia di HuggingFace:**
```
microsoft/BitNet-b1.58-2B-4T     ← model resmi Microsoft (2.4B params)
1bitLLM/bitnet_b1_58-3B          ← community 3B
HF1BitLLM/Llama3-8B-1.58-100B-tokens  ← Llama3 versi BitNet
```

**Setup:**
```bash
git clone --recursive https://github.com/microsoft/BitNet.git
cd BitNet

conda create -n bitnet-cpp python=3.9
conda activate bitnet-cpp
pip install -r requirements.txt

# Download model
huggingface-cli download microsoft/BitNet-b1.58-2B-4T-gguf \
    --local-dir models/BitNet-b1.58-2B-4T

# Build dan setup
python setup_env.py -md models/BitNet-b1.58-2B-4T -q i2_s

# Run inference
python run_inference.py \
    -m models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf \
    -p "You are rust_worker. Write a Rust HTTP GET function." \
    -cnv
```

**Sebagai inference server (kompatibel OpenAI API):**
```bash
python run_inference_server.py \
    -m models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf \
    --host 127.0.0.1 --port 8080
# Kemudian backend Python-nya panggil http://127.0.0.1:8080/v1/chat/completions
```

---

## Perbandingan Lengkap

| Aspek | Unsloth | BitNet | Ollama | vLLM |
|-------|---------|--------|--------|------|
| Tujuan | Fine-tuning | CPU inference | Local dev | Production inference |
| GPU diperlukan | Ya (8GB+ untuk 7B) | **Tidak** | Opsional | Ya (lebih baik) |
| Model flexibility | Semua HF models | Hanya 1-bit models | Semua GGUF | Semua |
| Untuk training | ✅ utama | ❌ bukan | ❌ | ❌ |
| Untuk inference | ❌ bukan | ✅ CPU only | ✅ dev | ✅ production |
| Fase vibe-office | Fase 4 | Fase 3-4 (fallback) | Fase 1-3 | Fase 4 prod |

---

## Decision Tree untuk Vibe-Office

```
Mau train workers lebih pintar?
  → Unsloth (Fase 4)

Mau run workers secara lokal?
  Punya GPU?
    Ya  → Ollama (dev) atau vLLM (production)
    Tidak → BitNet (kalau pakai 1-bit model)
           atau Ollama dengan model kecil (3B-7B GGUF)

Mau fine-tune LALU run?
  → Fine-tune dengan Unsloth → export GGUF → load di Ollama/BitNet
```

---

## Gradient Checkpointing & Reproducibility

Dua hal penting saat training di hardware terbatas (dari v2.9 skill):

```python
# Gradient checkpointing — hemat VRAM dengan tradeoff sedikit lebih lambat
# Sudah di-handle Unsloth via: use_gradient_checkpointing="unsloth"

# Reproducibility — seed harus konsisten agar hasil training bisa di-reproduce
import torch, random, numpy as np

def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

set_seed(42)  # panggil sebelum apapun
```

Kenapa reproducibility penting: kalau fine-tuning rust_worker gagal dan
mau coba ulang, seed yang sama = kondisi awal yang sama = debug lebih mudah.

---

## Anti-Forgetting: O-LoRA (Orthogonal LoRA)

> Dievaluasi session 2026-03-17. Worth sebagai konsep, tapi butuh adaptasi.

**Masalah:** Trainer membuat LoRA `lora_borrow_checker` untuk coder_rust.
Lalu trainer membuat LoRA `lora_async_patterns`. Yang kedua bisa mengganggu
yang pertama — weights bergerak ke arah yang sama, terjadi interference.

**Solusi O-LoRA:** Tiap LoRA domain belajar di **subspace yang orthogonal**
satu sama lain. Kalau `lora_borrow_checker` "menempati" arah vektor A,
maka `lora_async_patterns` harus belajar di arah vektor B yang tegak lurus
dengan A. Zero interference, zero forgetting antar domain.

```
Tanpa O-LoRA:
  lora_borrow_checker  →  vektor arah (0.8, 0.3, 0.5)
  lora_async_patterns  →  vektor arah (0.7, 0.4, 0.6)  ← hampir sama! conflict!

Dengan O-LoRA:
  lora_borrow_checker  →  vektor arah (1, 0, 0)
  lora_async_patterns  →  vektor arah (0, 1, 0)  ← orthogonal, no conflict
  lora_server_http     →  vektor arah (0, 0, 1)  ← orthogonal ke keduanya
```

**Repo referensi:**
- Paper + kode original: https://github.com/cmnfriend/O-LoRA (T5-large, butuh adaptasi)
- Paper arXiv: https://arxiv.org/abs/2309.01158

**Cara implement di Unsloth (constraint sederhana):**
```python
import torch
from unsloth import FastLanguageModel

def orthogonal_constraint(new_lora_weights: dict, existing_loras: list[dict]) -> float:
    """
    Regularization loss: paksa new LoRA weights orthogonal terhadap existing LoRAs.
    Tambahkan ke training loss: total_loss = task_loss + lambda_orth * orth_loss
    """
    orth_loss = 0.0
    for existing in existing_loras:
        for key in new_lora_weights:
            if key in existing:
                # Dot product mendekati 0 = orthogonal
                A = new_lora_weights[key].flatten()
                B = existing[key].flatten()
                # Normalize ke unit vectors dulu
                A_norm = A / (A.norm() + 1e-8)
                B_norm = B / (B.norm() + 1e-8)
                orth_loss += torch.abs(torch.dot(A_norm, B_norm))
    return orth_loss

# Di training loop trainer worker:
LAMBDA_ORTH = 0.1   # seberapa kuat constraint orthogonality

task_loss = compute_task_loss(outputs, labels)
orth_loss = orthogonal_constraint(
    new_lora_weights=get_current_lora_weights(model),
    existing_loras=load_all_existing_loras(worker_id)
)
total_loss = task_loss + LAMBDA_ORTH * orth_loss
total_loss.backward()
```

**Catatan praktis untuk trainer worker:**
- Load existing LoRAs sebagai reference (frozen, tidak di-train)
- Hitung orthogonality loss setiap step
- LAMBDA_ORTH = 0.1 adalah starting point — kalau model lupa terlalu cepat,
  naikkan. Kalau model tidak bisa belajar domain baru, turunkan.
- Tidak perlu implement dari nol — nanti bisa borrow logic dari
  `cmnfriend/O-LoRA` dan adapt untuk Qwen2.5

**Alternatif lebih sederhana (tidak perlu O-LoRA):**
Kalau O-LoRA terlalu complex, cukup pakai **LoRA sebagai file terpisah per domain**
dan JANGAN merge. Load hanya yang dibutuhkan saat inference (task router).
Ini bukan zero-forgetting tapi zero-interference karena weights tidak pernah overlap.

---

## Roadmap Training untuk Vibe-Office

```
Fase 1-2: Pakai API LLM biasa (Anthropic/OpenRouter) + Ollama
Fase 3:   Kumpulkan training data dari Ring 2 (episodes sukses)
Fase 4:   Fine-tune dengan Unsloth → deploy ke Ollama/vLLM
          Opsional: BitNet untuk CPU-only deployment
```

Jangan terburu fine-tune di Fase 1-3 — data belum cukup dan
model baseline sudah bagus untuk development awal.

---

## Evaluation Module — lm-evaluation-harness (Fase 4)

> Extend trainer worker evaluation — lebih granular dari "delta > 5%".
> Repo: https://github.com/EleutherAI/lm-evaluation-harness
> Disebutkan di Open-dLLM sebagai evaluation framework standard.
> Tidak butuh dLLM — bisa langsung dipakai dengan Qwen2.5 + vLLM.

### Masalah dengan Evaluasi Sekarang

```python
# SEKARANG (terlalu sederhana):
delta = eval_result['score'] - eval_result['baseline']
if delta > 0.05:
    activate_lora()   # cukup 5% improvement → aktifkan

# Masalah:
# - Tidak tahu improvement di aspek apa
# - Tidak tahu apakah ada regresi di domain lain
# - Tidak ada benchmark standar → tidak bisa compare antar session
```

### Evaluation dengan lm-evaluation-harness

```python
# backend/training/eval_harness.py

from lm_eval import evaluator, tasks

# Benchmark per worker type
WORKER_BENCHMARKS = {
    'coder_rust': [
        'humaneval',           # standard code gen benchmark
        'mbpp',                # mostly basic programming problems
        'multiple_rust',       # HumanEval ported ke Rust (komunitas)
    ],
    'coder_python': [
        'humaneval',
        'mbpp',
        'ds1000',              # data science tasks
    ],
    'coder_js': [
        'humaneval_js',
        'mbpp_js',
    ],
    'tester': [
        'humaneval',           # bisa generate test yang pass
        'mbpp',
    ],
    'auditor': [
        'truthfulqa',          # seberapa "jujur" audit-nya
        'hellaswag',           # reasoning quality
    ],
}

async def evaluate_lora_full(worker_id: str, lora_path: str) -> dict:
    """
    Full evaluation sebelum decide apakah LoRA di-activate.
    Lebih granular dari sekadar delta score.
    """
    benchmarks = WORKER_BENCHMARKS.get(worker_id, ['humaneval'])

    # Load model + LoRA
    results = evaluator.simple_evaluate(
        model="vllm",
        model_args=f"pretrained={get_worker_base_model(worker_id)},lora={lora_path}",
        tasks=benchmarks,
        num_fewshot=0,
        batch_size=4,
    )

    # Load baseline (tanpa LoRA) untuk compare
    baseline = evaluator.simple_evaluate(
        model="vllm",
        model_args=f"pretrained={get_worker_base_model(worker_id)}",
        tasks=benchmarks,
        num_fewshot=0,
        batch_size=4,
    )

    # Compute per-benchmark delta
    deltas = {}
    regressions = []
    improvements = []

    for task_name in benchmarks:
        lora_score     = results['results'][task_name].get('acc,none', 0)
        baseline_score = baseline['results'][task_name].get('acc,none', 0)
        delta          = lora_score - baseline_score
        deltas[task_name] = {
            'lora':     round(lora_score, 4),
            'baseline': round(baseline_score, 4),
            'delta':    round(delta, 4),
        }
        if delta < -0.02:   regressions.append(task_name)
        if delta > 0.05:    improvements.append(task_name)

    # Decision logic
    has_improvement  = len(improvements) > 0
    no_big_regression = all(
        deltas[t]['delta'] > -0.05 for t in benchmarks
    )

    return {
        'worker_id':      worker_id,
        'lora_path':      lora_path,
        'benchmarks':     deltas,
        'improvements':   improvements,
        'regressions':    regressions,
        'recommend':      has_improvement and no_big_regression,
        'summary':        _build_summary(deltas, improvements, regressions),
    }

def _build_summary(deltas, improvements, regressions) -> str:
    parts = []
    for t, d in deltas.items():
        sign = '+' if d['delta'] >= 0 else ''
        parts.append(f"{t}: {sign}{d['delta']*100:.1f}%")
    return ' · '.join(parts)
```

### Integration ke trainer Worker

```python
# Di backend/workers.py — trainer worker, ganti eval sederhana

async def train_new_lora(request: dict) -> dict:
    # ... training code (tidak berubah) ...

    # GANTI: eval sederhana → eval harness
    eval_result = await evaluate_lora_full(worker_id, result['lora_path'])

    # Update metadata dengan full eval results
    update_lora_metadata(worker_id, result['lora_name'], {
        'status':        'active' if eval_result['recommend'] else 'discarded',
        'eval_scores':   eval_result['benchmarks'],
        'improvements':  eval_result['improvements'],
        'regressions':   eval_result['regressions'],
        'performance_delta': eval_result['summary'],
    })

    if eval_result['recommend']:
        activate_lora(worker_id, result['lora_name'])
        # Rooftop ceremony (lihat task-animations.md)
        await ws_broadcast({
            'type': 'lora_ceremony',
            'worker_id': worker_id,
            'domain': request['domain'],
            'delta': eval_result['summary'],
            'lora_name': result['lora_name'],
        })
    else:
        import shutil
        shutil.rmtree(result['lora_path'])
        reason = f"regressions: {eval_result['regressions']}" if eval_result['regressions'] else "no improvement"
        await ws_broadcast({
            'type': 'speech_bubble',
            'worker_id': 'trainer',
            'text': f'LoRA discarded: {reason}',
            'color': '#FF5252',
            'duration_ms': 4000,
        })

    return eval_result
```

### Hasil Eval di Brain Visualization

```typescript
// Tab LoRA Manager — extend LoRAMetadata untuk tampilkan per-benchmark scores

// Expand row LoRA card → tampilkan benchmark breakdown:
{Object.entries(lora.eval_scores ?? {}).map(([benchmark, scores]) => (
  <div key={benchmark} className="benchmark-row">
    <span className="bench-name">{benchmark}</span>
    <span className="bench-baseline">{(scores.baseline * 100).toFixed(1)}%</span>
    <span className="bench-arrow">→</span>
    <span
      className="bench-lora"
      style={{ color: scores.delta > 0 ? '#44ff88' : '#FF5252' }}
    >
      {(scores.lora * 100).toFixed(1)}%
    </span>
    <span
      className="bench-delta"
      style={{ color: scores.delta > 0 ? '#44ff88' : '#FF5252' }}
    >
      {scores.delta > 0 ? '+' : ''}{(scores.delta * 100).toFixed(1)}%
    </span>
  </div>
))}
```

### Install

```bash
pip install lm-eval --break-system-packages
# Atau dari source (lebih up to date):
git clone https://github.com/EleutherAI/lm-evaluation-harness
pip install -e . --break-system-packages
```

### Checklist Fase 4

```
[ ] lm-eval install di environment trainer
[ ] evaluate_lora_full() berjalan tanpa error untuk coder_rust
[ ] WORKER_BENCHMARKS defined untuk semua worker types
[ ] trainer pakai evaluate_lora_full() bukan eval sederhana
[ ] LoRAMetadata extended: eval_scores, improvements, regressions
[ ] Brain Visualization: benchmark breakdown di expanded LoRA card
[ ] Regressions → jangan activate LoRA meskipun ada improvement di benchmark lain
```

---

## dLLM sebagai "Penyusun" — Fase 5 Experimental

> Ide dari diskusi 2026-03-17. Dokumentasikan sekarang agar tidak terlupa.
> Jangan implementasikan sebelum ada model dLLM yang cukup kuat (>7B, production-ready).
> Track: Dream 7B (dari Qwen2.5 weights), DiffuLLaMA 7B, Mercury Coder (commercial).

### Konsep

```
Sekarang (sequential assembly via bridge):
  coder_rust → bridge → tester → bridge → auditor → output

Dengan dLLM "Penyusun" (Fase 5):
  coder_rust output ──┐
  tester output    ───┤→ Aggregator → dLLM "denoise" → final output koheren
  auditor notes    ───┘

Keunggulan: dLLM bisa lihat semua fragmen sekaligus (bidirectional),
isi bagian yang kosong, fix inkonsistensi antar output workers.
```

### Kandidat Model

```
Dream 7B         → diinisialisasi dari Qwen2.5 7B, masih experimental
DiffuLLaMA 7B    → scale dari paper, belum ada release publik
Open-dCoder 0.5B → ada sekarang tapi terlalu lemah untuk production
Mercury Coder    → commercial, tidak open source

Target: model yang HumanEval Pass@1 > 60% sebelum worth diintegrasikan.
Open-dCoder sekarang: ~20% — belum.
```

### Bila Saatnya Tiba — Integrasi ke Bridge

```python
# Extension bridge.py — tambah route baru saja, tidak ubah yang existing

# Route baru: multi_worker_output → dLLM assembler
('*_multi', 'dllm_assembler'): lambda outputs: {
    'task_type': 'assemble',
    'fragments': [
        {'worker': o['worker_id'], 'content': o['output'], 'confidence': o['confidence']}
        for o in outputs
    ],
    'task_context': outputs[0].get('original_task'),
}
```

### Kapan Revisit

```
Cek setiap 3 bulan: apakah ada dLLM open-source yang:
  [ ] Parameter ≥ 7B
  [ ] HumanEval Pass@1 ≥ 60%
  [ ] Bisa run di vLLM atau Ollama
  [ ] License: Apache / MIT

Kalau semua centang → mulai Fase 5 dLLM integration.
```

---

## Grokking Detection — Trainer Integration (Fase 4)

> **Berdasarkan:** Nanda et al. "Progress measures for grokking via mechanistic
> interpretability" — ICLR 2023.
> **Paper:** https://arxiv.org/abs/2301.05217
> **Analysis:** https://www.alignmentforum.org/posts/N6WM6hs7RQMKDhYjB/
>
> **Konteks:** Grokking adalah fenomena di mana model awalnya hafal data training,
> tapi setelah training yang cukup lama, tiba-tiba "paham" dan bisa generalize dengan
> sempurna. Ini bukan magic — ini adalah 3 fase training yang continuous:
>
> ```
> FASE 1: MEMORIZATION
>   → Model hafal training data (train loss turun cepat)
>   → Val loss masih tinggi — model belum generalize
>   → Memorization circuits terbentuk dan dominan
>
> FASE 2: CIRCUIT FORMATION
>   → Generalizing circuits mulai terbentuk di background
>   → Val loss mulai turun, tapi lambat
>   → Dua jenis circuits berlomba: memorization vs generalizing
>
> FASE 3: GROKKED (CLEANUP)
>   → Weight decay secara bertahap membersihkan memorization circuits
>   → Generalizing circuits menjadi dominan
>   → Val loss drop tajam — ini yang terlihat sebagai "sudden grokking"
>   → Train/val loss gap menjadi kecil dan stabil
> ```
>
> **Untuk vibe-office trainer:** deteksi fase ini dari loss curve shape.
> Jangan aktifkan LoRA yang masih di fase memorization — dia hafal, tidak generalize.
> Full UI visualization ada di `frontend/brain-visualization.md` Tab 4.

### Trainer: Simpan Loss Curve ke Ring 2

```python
# Extend trainer di workers.md — tambahkan snapshot logging

LOSS_CURVE_SNAPSHOT_INTERVAL = 50  # simpan setiap 50 training steps

async def unsloth_finetune_with_tracking(
    base_model: str,
    dataset: list,
    output_path: str,
    rank: int = 16,
    alpha: int = 32,
    seed: int = 42,
    max_minutes: int = MAX_TRAIN_MINUTES,
) -> dict:
    """
    Extend unsloth_finetune() dengan loss curve tracking.
    Simpan snapshots ke Ring 2 experiments.parquet setiap N steps.
    """
    from unsloth import FastLanguageModel
    import torch

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model,
        max_seq_length=4096,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model, r=rank, lora_alpha=alpha, random_state=seed,
        use_gradient_checkpointing="unsloth",
    )

    trainer = SFTTrainer(model=model, train_dataset=dataset, ...)

    # Tracking state
    loss_curve = {
        "steps": [], "train_loss": [], "val_loss": [], "val_bpb": []
    }

    start_time = time.time()
    step = 0

    for batch in trainer.get_train_dataloader():
        if (time.time() - start_time) / 60 > max_minutes:
            break  # Fixed time budget (Karpathy pattern)

        train_loss = trainer.training_step(batch)

        if step % LOSS_CURVE_SNAPSHOT_INTERVAL == 0:
            val_loss = trainer.evaluate()['eval_loss']
            val_bpb  = val_loss / 0.693147  # ln(2)

            loss_curve["steps"].append(step)
            loss_curve["train_loss"].append(float(train_loss))
            loss_curve["val_loss"].append(float(val_loss))
            loss_curve["val_bpb"].append(float(val_bpb))

        step += 1

    # Simpan loss curve ke Ring 2
    append_to_parquet('loss_curves', {
        'worker_id':  output_path.split('/')[-2],  # dari path
        'lora_name':  output_path.split('/')[-1],
        'loss_curve': json.dumps(loss_curve),
        'trained_at': datetime.now().isoformat(),
    })

    return {
        'model':      model,
        'loss_curve': loss_curve,
        'steps_run':  step,
    }
```

### Trainer: Auto-Run Grokking Analysis

```python
# Setelah setiap training run — sebelum decide activate/discard

async def train_new_lora(request: dict) -> dict:
    worker_id = request['worker_id']
    domain    = request['domain']

    # ... (existing training code dari workers.md) ...

    # BARU: Auto-run grokking analysis setelah training
    grokking = await analyze_grokking_phase(
        worker_id=worker_id,
        lora_name=lora_name,
        loss_curve=result['loss_curve'],
    )

    # Update LoRA metadata dengan training phase
    update_lora_metadata(worker_id, lora_name,
        training_phase=grokking['training_phase'],
        grokking_confidence=grokking['grokking_confidence'],
        loss_curve=result['loss_curve'],
    )

    # PENTING: Jangan aktifkan kalau masih memorizing
    if grokking['training_phase'] == 'memorizing':
        # Jangan discard — bisa jadi grokking kalau training lebih lama
        return {
            'status':         'pending_more_training',
            'training_phase': 'memorizing',
            'recommendation': (
                'Model masih memorizing. Pertimbangkan training lebih lama '
                'atau naikkan weight decay untuk percepat cleanup phase.'
            ),
        }

    if grokking['grokking_confidence'] < 0.4:
        return {
            'status':         'pending_more_training',
            'training_phase': grokking['training_phase'],
            'grokking_confidence': grokking['grokking_confidence'],
        }

    # Lanjut ke eval val_bpb normal (dari workers.md trainer section)
    eval_result = eval_lora_val_bpb(worker_id, lora_path, domain)
    if eval_result['improvement'] > IMPROVEMENT_THRESHOLD:
        activate_lora(worker_id, lora_name, weight=0.8)
        return {
            'status':         'activated',
            'lora':           lora_name,
            'val_bpb_delta':  eval_result['improvement'],
            'training_phase': grokking['training_phase'],
            'grokking_confidence': grokking['grokking_confidence'],
        }
    else:
        discard_lora(lora_path)
        return {'status': 'discarded', 'reason': 'no_improvement'}
```

### Grokking Analysis Function

```python
# backend/api/brain.py — full implementation (referenced dari brain-visualization.md)

def analyze_grokking_phase_local(loss_curve: dict) -> dict:
    """
    Local version untuk trainer (tidak butuh HTTP call ke API).
    Sama dengan GET /brain/{worker_id}/grokking-phase/{lora_name}
    tapi dipanggil langsung dari trainer function.
    """
    train_loss = loss_curve["train_loss"]
    val_loss   = loss_curve["val_loss"]

    if not train_loss or not val_loss:
        return {"training_phase": "unknown", "grokking_confidence": 0.0}

    final_train = train_loss[-1]
    final_val   = val_loss[-1]
    gap         = (final_val - final_train) / max(final_train, 1e-8)

    # Detect grokking events: val_loss drop >15% dalam window 10 steps
    events = []
    window = min(10, len(val_loss) // 3)
    for i in range(window, len(val_loss)):
        prev = val_loss[i - window]
        curr = val_loss[i]
        if prev > 0 and (prev - curr) / prev > 0.15:
            events.append({"step": loss_curve["steps"][i], "drop": (prev-curr)/prev})

    # Classify phase
    if len(events) > 0 and gap < 0.15:
        phase      = "grokked"
        confidence = min(0.95, 0.7 + (0.15 - gap) * 2 + len(events) * 0.05)
    elif gap < 0.3 or len(events) > 0:
        phase      = "circuit_forming"
        confidence = 0.5 + max(0, 0.3 - gap) * 0.5
    else:
        phase      = "memorizing"
        confidence = min(0.9, 0.5 + gap * 0.3)

    return {
        "training_phase":      phase,
        "grokking_confidence": round(confidence, 3),
        "train_val_gap":       round(gap, 4),
        "grokking_events":     events,
        "recommendation": {
            "grokked":         "✅ Safe to activate.",
            "circuit_forming": "⚠️ Monitor side effects after activate.",
            "memorizing":      "❌ Train longer or increase weight decay.",
            "unknown":         "ℹ️ Need more training steps.",
        }[phase],
    }
```

### Aturan Grokking untuk Trainer

```
WAJIB: Trainer simpan loss_curve ke Ring 2 setiap training run
WAJIB: Trainer run grokking analysis setelah setiap training run
WAJIB: Jangan activate LoRA kalau training_phase == 'memorizing'
WAJIB: Jangan activate LoRA kalau grokking_confidence < 0.4

BOLEH activate dengan monitoring kalau:
  - training_phase == 'circuit_forming' AND grokking_confidence >= 0.4
  - Tambah monitoring: narrator announce tiap 24 jam apakah phase berubah

IDEAL: training_phase == 'grokked' AND grokking_confidence >= 0.7
```

---

## KARL — Knowledge Agents via Reinforcement Learning (Fase 4-5 Blueprint)

> **Konteks:** KARL adalah paper dari Databricks (Maret 2026) yang mendokumentasikan
> sistem RL untuk knowledge agents. Ini bukan tool yang di-install sekarang — ini
> adalah **roadmap evolution** dari SKILL.md static yang kita pakai hari ini menuju
> weights yang benar-benar internalize reasoning pattern.
>
> **Paper:** https://www.databricks.com/blog/karl-knowledge-agents-via-reinforcement-learning
> **Relevansi:** Trainer + curator Fase 4-5. Baca paper ini sebelum design
> trainer overnight loop di Fase 4.

---

### Masalah yang KARL Solve

**Masalah kita hari ini (Fase 1-3):**
SKILL.md adalah "latent representation of logic in text." Setiap kali worker run,
dia harus parse SKILL.md, understand instruksi, lalu apply ke context yang ada.
Ini ada dua cost tersembunyi:
1. Token overhead — ribuan baris SKILL.md di-inject ke context setiap run
2. Comprehension gap — LLM tidak selalu apply instruksi dengan benar,
   terutama edge cases yang tidak ter-cover dalam SKILL.md

Analogi KARL: mengajar manusia nyetir dengan memberikan manual 100 halaman
setiap kali duduk di mobil. Kondisi ideal: skills terinternalisasi.
Driver react instinctively karena learned, bukan karena baca rules.

**Apa yang KARL prove:**
- Match performa Claude 4.6 dan GPT 5.2 pada enterprise knowledge tasks
- ~33% biaya lebih murah, ~47% latency lebih rendah
- Ditraining hanya dengan beberapa ribu GPU hours dan entirely synthetic data
- Iterative RL: 53% → 64% → 71% accuracy melalui tiga iterasi training

---

### KARL Patterns untuk Vibe-Office

**Hybrid Approach (bukan replace SKILL.md, tapi complement):**
```
Fase 1-3: SKILL.md sebagai primary — reliable, auditable, easy to update
Fase 4:   SKILL.md + LoRA (Unsloth) — workers mulai internalize patterns
Fase 5:   SKILL.md + LoRA + KARL RL — workers internalize reasoning strategy
```

SKILL.md tidak hilang di Fase 5 — dia tetap ada untuk reliability dan auditability.
RL layer adalah optimization di atasnya. Kalau RL model error, SKILL.md
masih jadi ground truth untuk recovery.

**Pattern 1 — Iterative Bootstrapping (untuk trainer):**
```python
# KARL's key insight: improved model bisa generate better training data
# untuk iterasi berikutnya. Loop ini compound.

async def karl_iterative_loop(worker_id: str, domain: str):
    """
    Fase 5 extension untuk trainer overnight loop.
    Setelah base LoRA ada, model yang lebih baik generate synthetic episodes
    yang lebih baik → training data quality compound seiring iterasi.
    """
    for iteration in range(MAX_KARL_ITERATIONS):
        # 1. Model versi saat ini generate synthetic training episodes
        synthetic_episodes = await generate_synthetic_episodes(
            worker_id=worker_id,
            domain=domain,
            count=500,
            model=get_current_lora_model(worker_id)  # pakai model terbaik sejauh ini
        )

        # 2. Filter: hanya episode yang pass mechanical verification
        # KARL: multiple solver attempts per question, filter by pass rate
        verified = [ep for ep in synthetic_episodes if verify_episode(ep)]

        # 3. Train LoRA baru dari verified episodes (Unsloth)
        new_lora = await unsloth_finetune(
            base_model=get_worker_base_model(worker_id),
            dataset=verified,
            max_minutes=MAX_TRAIN_MINUTES  # Karpathy fixed budget tetap berlaku
        )

        # 4. Eval — kalau naik, ini jadi base untuk iterasi berikutnya
        eval_result = eval_lora_val_bpb(worker_id, new_lora, domain)
        if eval_result['improvement'] > IMPROVEMENT_THRESHOLD:
            activate_lora(worker_id, new_lora)
            # Loop: model yang lebih baik → synthetic data yang lebih baik
        else:
            break  # Convergence — tidak ada improvement lagi
```

**Pattern 2 — Search Efficiency Training (untuk scout):**
```python
# KARL reduce wasteful searches dramatically.
# Scout kita saat ini: search sampai context cukup, tapi tidak tau kapan berhenti.
# KARL's approach: train search strategy, bukan hanya search accuracy.

# Synthetic training data untuk scout:
# - Queries yang bisa dijawab dengan 1 search (teach: stop early)
# - Queries yang butuh 3 searches (teach: persevere)
# - Queries yang tidak bisa dijawab dari search apapun (teach: escalate ke conductor)

SCOUT_SEARCH_TRAINING_SCHEMA = {
    "query": str,
    "optimal_search_count": int,  # berapa kali search yang "benar"
    "stop_signal": str,           # kapan model harus stop
    "escalation_trigger": str,    # kapan harus escalate vs terus search
}
```

**Pattern 3 — Hard-to-Verify Task Handling (untuk auditor + curator):**
```python
# KARL solve: grounded reasoning tidak punya single correct answer.
# Untuk auditor dan curator, evaluation tidak selalu binary.
# KARL's approach: multiple solver attempts, filter by consensus pass rate.

async def multi_attempt_eval(task: dict, model, n_attempts: int = 5) -> dict:
    """
    Untuk tasks yang tidak punya ground truth (code review quality,
    knowledge classification) — jalankan N kali, ambil consensus.
    Hasil consensus yang masuk Ring 2 sebagai training data.
    """
    results = []
    for _ in range(n_attempts):
        result = await model.complete(task)
        results.append(result)

    # Filter: hanya masuk Ring 2 kalau ≥3/5 attempts agree
    consensus = find_consensus(results, threshold=0.6)
    if consensus['confidence'] >= 0.6:
        await ring2.store_episode({
            'task': task,
            'result': consensus['result'],
            'confidence': consensus['confidence'],
            'source': 'karl_multi_attempt'
        })
    return consensus
```

---

### Kapan Mulai Implement KARL

```
JANGAN mulai sebelum:
  [ ] Fase 3 selesai — workers hidup dan menghasilkan real episodes
  [ ] Ring 2 punya minimal 2000 episodes per domain
  [ ] Trainer overnight loop sudah stable (dari Karpathy patterns)
  [ ] Base LoRA per coder_* worker sudah ada dan proven

Tanda Fase 5 siap dimulai:
  [ ] trainer sudah proven: overnight loop jalan tanpa human intervention
  [ ] curator sudah proven: SKILL.md update otomatis dari episodes
  [ ] Ada cukup GPU resources untuk multi-iteration training
```

---

### Synthetic Data Generation untuk KARL

KARL pakai entirely synthetic data — tidak perlu label manual.
Untuk vibe-office, synthetic data bisa di-generate dari:

```python
SYNTHETIC_DATA_SOURCES = {
    'coder_rust': [
        'generate random Rust coding tasks dari SKILL.md domains',
        'mutate existing episodes dengan bug injection',
        'cross-domain kombinasi (async + server, unsafe + rayon)',
    ],
    'scout': [
        'generate research queries dengan known-answer dari GitNexus',
        'vary search depth: simple lookup vs multi-hop research',
        'inject dead-end queries untuk train escalation behavior',
    ],
    'auditor': [
        'generate code samples dengan known issues (dari Ring 2 failures)',
        'vary severity: critical vs minor vs false positive',
        'multi-attempt consensus untuk build training signal',
    ],
    'curator': [
        'generate knowledge classification tasks dari SKILL.md content',
        'vary document length: short snippet vs long NovaNotes doc (pakai RLM)',
        'domain boundary cases: knowledge yang overlap dua workers',
    ],
}
```
