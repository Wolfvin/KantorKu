# Backend — vLLM Setup (Fase 3, Production Inference)

> **Konteks untuk session baru:**
> Fase 1-3: Ollama untuk development (simple, satu request satu waktu).
> Fase 3+: vLLM untuk production — continuous batching, PagedAttention,
> bisa serve banyak workers paralel tanpa antrian panjang.
> Swap Ollama → vLLM = ganti satu URL, tidak ada perubahan kode workers.
> Repo: https://github.com/vllm-project/vllm (Apache-2.0, 47k stars)

---

## Kapan Switch dari Ollama ke vLLM

```
Tetap Ollama kalau:
  - Solo dev, testing, Fase 1-3
  - Satu worker jalan satu waktu
  - Hardware: laptop / PC tanpa GPU dedicated

Switch ke vLLM kalau:
  - Post-coding pipeline mulai: scribe + auditor + sentinel jalan paralel
  - Latency Ollama > 5 detik per response dan terasa lambat
  - Punya GPU 8GB+ dan mau maximize throughput
  - Siap masuk Fase 4 (trainer butuh vLLM untuk RL training)
```

---

## Setup vLLM

```bash
# Requirements: Python 3.9+, CUDA 11.8+ (kalau punya GPU)
pip install vllm

# Atau dengan versi pinned (lebih stable):
pip install vllm==0.6.0
```

**Serve Qwen2.5-Coder-7B (model utama coders):**
```bash
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-Coder-7B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --dtype bfloat16 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.85 \
    --tensor-parallel-size 1      # 1 GPU, naikkan kalau multi-GPU
```

**Serve Qwen2.5-32B (conductor model) — butuh GPU > 24GB atau multi-GPU:**
```bash
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-32B-Instruct \
    --host 0.0.0.0 \
    --port 8001 \
    --dtype bfloat16 \
    --max-model-len 16384 \
    --gpu-memory-utilization 0.90 \
    --tensor-parallel-size 2      # perlu 2 GPU kalau 32B
```

**Tanpa GPU (CPU mode, lambat tapi jalan):**
```bash
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-Coder-7B-Instruct \
    --device cpu \
    --dtype float32 \
    --max-model-len 4096
```

---

## Konfigurasi Backend Workers

Satu perubahan di config — semua workers langsung pakai vLLM:

```python
# config/llm_config.py

import os

# Ubah nilai ini saat switch Ollama → vLLM
LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama")  # "ollama" | "vllm"

LLM_ENDPOINTS = {
    "ollama": {
        "coder":     "http://localhost:11434/v1",   # semua coder_*
        "conductor": "http://localhost:11434/v1",
        "small":     "http://localhost:11434/v1",   # intake, narrator
    },
    "vllm": {
        "coder":     "http://localhost:8000/v1",    # vLLM port 8000
        "conductor": "http://localhost:8001/v1",    # vLLM port 8001 (32B)
        "small":     "http://localhost:8000/v1",    # pakai coder endpoint
    }
}

LLM_MODELS = {
    "ollama": {
        "coder":     "qwen2.5-coder:7b",
        "conductor": "qwen2.5:32b",
        "small":     "llama3.2:3b",
    },
    "vllm": {
        "coder":     "Qwen/Qwen2.5-Coder-7B-Instruct",
        "conductor": "Qwen/Qwen2.5-32B-Instruct",
        "small":     "Qwen/Qwen2.5-Coder-7B-Instruct",
    }
}

def get_llm_config(worker_type: str) -> dict:
    """
    worker_type: "coder" | "conductor" | "small"
    Return: {"base_url": ..., "model": ...}
    """
    backend = LLM_BACKEND
    return {
        "base_url": LLM_ENDPOINTS[backend][worker_type],
        "model":    LLM_MODELS[backend][worker_type],
    }
```

**Penggunaan di worker (identik untuk Ollama dan vLLM):**
```python
from openai import AsyncOpenAI
from config.llm_config import get_llm_config

async def run_coder(task: dict) -> dict:
    cfg = get_llm_config("coder")
    client = AsyncOpenAI(base_url=cfg["base_url"], api_key="none")

    response = await client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": CODER_SYSTEM_PROMPT},
            {"role": "user",   "content": format_task(task)},
        ],
        temperature=0.1,
        max_tokens=2048,
    )
    return parse_coder_output(response.choices[0].message.content)
```

`api_key="none"` — vLLM tidak butuh API key untuk local setup.

---

## Paralel Workers dengan vLLM

Keunggulan utama vLLM vs Ollama: **continuous batching**.
Saat scribe + auditor + sentinel jalan bersamaan, vLLM batch
request mereka secara otomatis — tidak ada antrian sequential.

```python
# Test parallelism — jalankan ini untuk verify vLLM handle concurrent requests

import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(base_url="http://localhost:8000/v1", api_key="none")

async def test_concurrent():
    tasks = [
        client.chat.completions.create(
            model="Qwen/Qwen2.5-Coder-7B-Instruct",
            messages=[{"role":"user","content":f"worker {i}: hello"}],
        )
        for i in range(5)  # 5 request sekaligus
    ]
    results = await asyncio.gather(*tasks)
    for i, r in enumerate(results):
        print(f"worker {i}: {r.choices[0].message.content[:50]}")

asyncio.run(test_concurrent())
# Dengan Ollama: 5 request = ~5x latency satu request (sequential)
# Dengan vLLM:  5 request = ~1.5x latency satu request (batched)
```

---

## Multi-Model Setup (Satu vLLM, Banyak Model)

Untuk hemat resource, bisa jalankan satu vLLM instance dengan
model switching (tapi ada cold-start ~5s saat ganti model):

```bash
# vLLM dengan model pool — experimental
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-Coder-7B-Instruct \
    --served-model-name coder \
    --port 8000

# Instance kedua untuk conductor (port beda)
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-32B-Instruct \
    --served-model-name conductor \
    --port 8001
```

Untuk sekarang: dua instance terpisah lebih reliable dari model pooling.

---

## LoRA Loading di vLLM (Fase 4)

Saat trainer mulai produce LoRA adapters, vLLM bisa load mereka
tanpa restart server:

```bash
# Start vLLM dengan LoRA support
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-Coder-7B-Instruct \
    --enable-lora \
    --max-lora-rank 64 \
    --max-loras 8 \
    --port 8000
```

```python
# Request dengan satu LoRA aktif
response = await client.chat.completions.create(
    model="Qwen/Qwen2.5-Coder-7B-Instruct",
    messages=[...],
    extra_body={
        "lora_request": {
            "lora_name": "borrow_checker",
            "lora_int_id": 1,
            "lora_local_path": "~/.vibe-office/loras/coder_rust/lora_borrow_checker_v2"
        }
    }
)
```

---

## LoRA Composition — Multiple LoRA Aktif Bersamaan (Fase 4)

> **Gap yang ada sebelumnya:** vLLM hanya dokumentasi satu LoRA per request.
> Tapi workers kita bisa punya 3-5 LoRA aktif bersamaan (borrow_checker +
> async + server untuk coder_rust). Brain viz Tab 2 weight slider hanya bermakna
> kalau composition system ini bekerja.

**Dua pendekatan yang bisa dipakai:**

### Opsi A — LoRA Merge (offline, sebelum serve)

Merge beberapa LoRA weights menjadi satu adapter sebelum load ke vLLM.
Cara paling simple dan reliable. Trainer run merge saat semua LoRA sudah grokked.

```python
# backend/workers/trainer.py — LoRA merge utility

from peft import PeftModel
import torch

def merge_active_loras(
    base_model_name: str,
    worker_id: str,
    lora_names: list[str],
    output_path: str,
    weights: dict[str, float] | None = None,
) -> str:
    """
    Merge beberapa LoRA adapters menjadi satu.
    Dipanggil saat: user ubah weight slider di brain viz, atau trainer activate LoRA baru.

    weights: {lora_name: weight} — dari LoRAMetadata.weight di brain viz
    Kalau weights=None → equal weights (1/n setiap LoRA)

    Return: path ke merged adapter
    """
    from transformers import AutoModelForCausalLM
    from peft import PeftModel

    n = len(lora_names)
    if weights is None:
        weights = {name: 1.0 / n for name in lora_names}

    # Load base model
    base = AutoModelForCausalLM.from_pretrained(
        base_model_name, torch_dtype=torch.float16, device_map='cpu'
    )

    # Iterative weighted merge
    merged = base
    for i, lora_name in enumerate(lora_names):
        lora_path = f"~/.vibe-office/loras/{worker_id}/{lora_name}"
        w = weights[lora_name]

        peft_model = PeftModel.from_pretrained(merged, lora_path)
        # Scale adapter weights
        for name, param in peft_model.named_parameters():
            if 'lora_' in name:
                param.data *= w
        merged = peft_model.merge_and_unload()

    # Save merged adapter
    os.makedirs(output_path, exist_ok=True)
    merged.save_pretrained(output_path)

    return output_path


def get_merged_lora_path(worker_id: str) -> str:
    """
    Return path ke merged LoRA yang saat ini aktif untuk worker.
    Di-update setiap kali user ubah weight atau enable/disable LoRA di brain viz.
    """
    return f"~/.vibe-office/loras/{worker_id}/merged_active"


async def rebuild_merged_lora(worker_id: str):
    """
    Dipanggil oleh backend API /brain/{worker_id}/toggle + /weight saat user
    ubah sesuatu di brain viz. Re-merge semua LoRA aktif dengan weights terbaru.
    Lalu hot-reload di vLLM via /reload endpoint.
    """
    active_loras = get_active_loras(worker_id)  # filter status='active'
    if not active_loras:
        # No active LoRA → pakai base model saja
        set_worker_lora(worker_id, None)
        return

    weights = {l.name: l.weight for l in active_loras}
    lora_names = [l.name for l in active_loras]

    merged_path = merge_active_loras(
        base_model_name=get_worker_base_model(worker_id),
        worker_id=worker_id,
        lora_names=lora_names,
        output_path=get_merged_lora_path(worker_id),
        weights=weights,
    )

    # Hot-reload merged LoRA di vLLM tanpa restart
    await reload_lora_in_vllm(worker_id, merged_path)
```

### Opsi B — Sequential Application (online, saat inference)

Tidak merge — apply setiap LoRA satu per satu ke output, weighted sum.
Lebih flexible tapi butuh custom inference loop. Tidak support di vLLM standard.
Gunakan hanya kalau Opsi A menghasilkan quality yang tidak memuaskan.

```python
# Opsi B — hanya kalau Opsi A insufficient
async def inference_with_lora_stack(
    prompt: str,
    worker_id: str,
    active_loras: list[LoRAMetadata],
) -> str:
    """
    Apply multiple LoRAs secara sequential dengan weighted interpolation.
    Jauh lebih lambat dari Opsi A — hanya sebagai fallback.
    """
    base_output = await call_base_model(prompt)

    lora_outputs = []
    for lora in active_loras:
        lora_output = await call_model_with_lora(prompt, lora.path)
        lora_outputs.append((lora_output, lora.weight))

    # Weighted interpolation di token probability space
    return weighted_merge_outputs(base_output, lora_outputs)
```

### vLLM Hot-reload LoRA

```python
# backend/utils/vllm_client.py

async def reload_lora_in_vllm(worker_id: str, lora_path: str):
    """
    Hot-reload merged LoRA di vLLM tanpa restart.
    Dipanggil setelah rebuild_merged_lora() selesai.
    Brain viz weight slider → toggle → rebuild → hot-reload dalam satu flow.
    """
    async with httpx.AsyncClient() as client:
        # vLLM load_lora endpoint (tersedia di vLLM >= 0.4.0)
        await client.post(
            f"http://localhost:8000/v1/load_lora_adapter",
            json={
                "lora_name":       f"{worker_id}_merged",
                "lora_path":       lora_path,
                "base_model_name": get_worker_base_model(worker_id),
            }
        )

async def unload_lora_in_vllm(worker_id: str):
    """Unload LoRA kalau user disable semua LoRA untuk worker ini."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"http://localhost:8000/v1/unload_lora_adapter",
            json={"lora_name": f"{worker_id}_merged"}
        )
```

### Aturan LoRA Composition

```
WAJIB:
  - Setiap LoRA yang di-toggle atau weight-nya diubah di brain viz
    → rebuild_merged_lora() → hot-reload vLLM
  - Jangan merge LoRA yang training_phase == 'memorizing'
    (grokking_confidence < 0.4) — ini sudah di-enforce di trainer

PERFORMA:
  - Merge dilakukan di CPU background thread — tidak block inference
  - Gunakan Opsi A (merge offline) secara default
  - Switch ke Opsi B hanya kalau ada conflict antar domains yang tidak bisa
    di-solve dengan weight tuning

CONFLICT MAP:
  - Brain viz Tab 3 Conflict Map sudah visualisasi orthogonality matrix
  - Kalau dua LoRA punya dot product > 0.3 → warning di brain viz
  - User bisa reduce weight salah satunya atau request trainer refactor
  - Merge dua LoRA yang highly conflicting tidak otomatis gagal —
    hanya perlu user approval via CEO office brain viz

STORAGE:
  merged_active/ selalu di-regenerate — bukan artifact permanen
  Actual LoRA adapters tetap di loras/{worker_id}/{lora_name}/
  Kalau merge gagal → fallback ke LoRA tunggal dengan eval_score tertinggi
```

---

## Monitoring vLLM

```bash
# vLLM expose metrics di /metrics (Prometheus format)
curl http://localhost:8000/metrics | grep vllm

# Metrics yang penting:
# vllm:gpu_cache_usage_perc    ← GPU memory usage (target < 90%)
# vllm:num_requests_running    ← concurrent requests aktif
# vllm:num_requests_waiting    ← requests di queue (target 0)
# vllm:avg_generation_throughput ← tokens/second
```

Di kantor pixel art: server_room tile bisa nampilin mini metrics
ini sebagai part dari scout's proactive monitoring.

---

## Checklist Setup vLLM

```
[ ] pip install vllm berhasil
[ ] vLLM serve Qwen2.5-Coder-7B (port 8000) berjalan
[ ] curl http://localhost:8000/v1/models mengembalikan model list
[ ] Test concurrent: 5 request paralel selesai lebih cepat dari sequential
[ ] LLM_BACKEND=vllm di .env → semua workers otomatis pakai vLLM
[ ] (Fase 4) --enable-lora flag aktif dan LoRA loading bekerja
```
