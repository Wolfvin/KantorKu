# Backend — O-LoRA Adaptasi untuk Qwen2.5 (Fase 4)

> **Konteks untuk session baru:**
> O-LoRA (Orthogonal LoRA) mencegah catastrophic forgetting dengan memastikan
> setiap LoRA domain belajar di subspace orthogonal satu sama lain.
> Paper: https://arxiv.org/abs/2309.01158
> Repo referensi (T5-large): https://github.com/cmnfriend/O-LoRA
> File ini: adaptasi konkret untuk Qwen2.5-Coder-7B + integrasi ke trainer worker.
> Diimplementasikan sebagai custom training loop di atas Unsloth.

---

## Mengapa Perlu Diadaptasi

Repo O-LoRA asli ditulis untuk T5-large (encoder-decoder, 250M params).
Qwen2.5-Coder-7B adalah decoder-only (7B params). Perbedaan kritis:

| Aspek | T5 (paper) | Qwen2.5 (kita) |
|-------|-----------|-----------------|
| Arsitektur | Encoder-decoder | Decoder-only |
| Target modules | attention + FF di encoder + decoder | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
| Loss computation | Seq2seq cross-entropy | Causal LM cross-entropy |
| Jumlah layers | 12 encoder + 12 decoder | 32 decoder layers |
| Framework | HuggingFace Trainer | Unsloth FastLanguageModel |

Constraint orthogonality-nya sama — yang berbeda adalah cara access weights
dan cara integrate ke training loop.

---

## Cara Kerja O-LoRA (Ringkas)

LoRA decompose weight update sebagai: `ΔW = B × A`
Di mana `A` dan `B` adalah low-rank matrices (rank r << d).

O-LoRA constraint: untuk dua LoRA yang berbeda domain,
matrix `A` mereka harus orthogonal satu sama lain.

```
Tanpa constraint:
  LoRA_1: A1 = [[0.8, 0.2], [0.3, 0.7]]
  LoRA_2: A2 = [[0.7, 0.3], [0.4, 0.6]]  ← mirip A1! dot product tinggi

Dengan O-LoRA constraint:
  LoRA_1: A1 = [[1.0, 0.0], [0.0, 0.0]]
  LoRA_2: A2 = [[0.0, 0.0], [0.0, 1.0]]  ← A1·A2 = 0, orthogonal
```

Implementasinya: tambahkan regularization loss ke training:
`total_loss = task_loss + λ × orthogonality_loss`

---

## Implementasi Lengkap untuk Qwen2.5

```python
# backend/training/olora_trainer.py

import torch
import torch.nn.functional as F
from unsloth import FastLanguageModel
from transformers import TrainingArguments
from trl import SFTTrainer
from pathlib import Path
import json

# Target modules Qwen2.5 — WAJIB konsisten dengan Unsloth setup
QWEN_LORA_TARGETS = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj"
]


class OrthogonalLoRATrainer:
    """
    Custom trainer yang enforce orthogonality constraint antar LoRA domains.
    Dipakai oleh trainer worker saat fine-tune domain baru.
    """

    def __init__(
        self,
        worker_id: str,
        base_model_path: str,
        loras_dir: str,
        lambda_orth: float = 0.1,
        rank: int = 16,
        alpha: int = 32,
    ):
        self.worker_id = worker_id
        self.base_model_path = base_model_path
        self.loras_dir = Path(loras_dir)
        self.lambda_orth = lambda_orth
        self.rank = rank
        self.alpha = alpha

    def load_model_with_new_lora(self, domain: str) -> tuple:
        """Load base model + tambahkan LoRA baru untuk domain yang akan di-train."""
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=self.base_model_path,
            max_seq_length=4096,
            dtype=torch.bfloat16,
            load_in_4bit=True,
        )

        model = FastLanguageModel.get_peft_model(
            model,
            r=self.rank,
            target_modules=QWEN_LORA_TARGETS,
            lora_alpha=self.alpha,
            lora_dropout=0,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=42,
        )

        return model, tokenizer

    def load_existing_lora_weights(self) -> dict[str, dict[str, torch.Tensor]]:
        """
        Load A matrices dari semua LoRA existing untuk worker ini.
        Hanya butuh A matrix (bukan B) untuk orthogonality check.
        Return: {domain: {module_name: A_tensor}}
        """
        existing = {}
        worker_lora_dir = self.loras_dir / self.worker_id

        if not worker_lora_dir.exists():
            return existing

        for lora_dir in worker_lora_dir.iterdir():
            if not lora_dir.is_dir():
                continue

            # Load metadata
            meta_path = lora_dir / "metadata.json"
            if not meta_path.exists():
                continue
            meta = json.loads(meta_path.read_text())

            if meta.get("status") != "active":
                continue  # Skip disabled LoRAs

            domain = meta["domain"]
            existing[domain] = {}

            # Load adapter weights
            adapter_path = lora_dir / "adapter_model.safetensors"
            if adapter_path.exists():
                from safetensors.torch import load_file
                weights = load_file(str(adapter_path))

                # Ambil hanya lora_A weights
                for key, tensor in weights.items():
                    if "lora_A" in key:
                        # Key format: "base_model.model.model.layers.0.self_attn.q_proj.lora_A.weight"
                        # Simpan dengan key yang lebih pendek
                        short_key = self._extract_module_key(key)
                        existing[domain][short_key] = tensor.to(torch.float32)

        return existing

    def compute_orthogonality_loss(
        self,
        new_lora_A_weights: dict[str, torch.Tensor],
        existing_weights: dict[str, dict[str, torch.Tensor]]
    ) -> torch.Tensor:
        """
        Hitung orthogonality loss antara LoRA A baru dengan semua existing LoRA A.

        Loss = sum over existing domains and modules:
               |dot(normalize(A_new), normalize(A_existing))|²

        Target: loss mendekati 0 = perfectly orthogonal.
        """
        total_loss = torch.tensor(0.0, requires_grad=True)

        for domain, existing_A in existing_weights.items():
            domain_loss = torch.tensor(0.0, requires_grad=True)

            for module_key in new_lora_A_weights:
                if module_key not in existing_A:
                    continue

                A_new = new_lora_A_weights[module_key]
                A_old = existing_A[module_key].to(A_new.device)

                # Flatten ke vectors
                a_new_flat = A_new.view(-1).float()
                a_old_flat = A_old.view(-1).float()

                # Normalize (unit vectors)
                a_new_norm = F.normalize(a_new_flat, dim=0)
                a_old_norm = F.normalize(a_old_flat, dim=0)

                # Squared dot product — target: 0
                dot = torch.dot(a_new_norm, a_old_norm)
                domain_loss = domain_loss + dot.pow(2)

            # Average across modules per domain
            if existing_A:
                domain_loss = domain_loss / len(existing_A)

            total_loss = total_loss + domain_loss

        # Average across domains
        if existing_weights:
            total_loss = total_loss / len(existing_weights)

        return total_loss

    def get_current_lora_A_weights(self, model) -> dict[str, torch.Tensor]:
        """Extract lora_A weights dari model yang sedang di-train."""
        lora_weights = {}
        for name, param in model.named_parameters():
            if "lora_A" in name and param.requires_grad:
                short_key = self._extract_module_key(name)
                lora_weights[short_key] = param
        return lora_weights

    def train(
        self,
        domain: str,
        dataset,
        output_dir: str,
        num_epochs: int = 3,
        batch_size: int = 4,
    ) -> dict:
        """
        Train LoRA baru untuk domain dengan orthogonality constraint.
        """
        print(f"[trainer] loading model for domain: {domain}")
        model, tokenizer = self.load_model_with_new_lora(domain)

        print(f"[trainer] loading existing LoRA weights for orthogonality check")
        existing_weights = self.load_existing_lora_weights()
        print(f"[trainer] found {len(existing_weights)} existing domains: {list(existing_weights.keys())}")

        # Custom training step dengan orthogonality constraint
        original_compute_loss = None

        def custom_compute_loss(model, inputs, return_outputs=False, **kwargs):
            """
            Override SFTTrainer.compute_loss untuk tambahkan orth constraint.
            """
            # Task loss (standard causal LM)
            outputs = model(**inputs)
            task_loss = outputs.loss

            # Orthogonality loss (hanya kalau ada LoRA lain)
            orth_loss = torch.tensor(0.0, device=task_loss.device)
            if existing_weights:
                current_A = self.get_current_lora_A_weights(model)
                orth_loss = self.compute_orthogonality_loss(current_A, existing_weights)

            total_loss = task_loss + self.lambda_orth * orth_loss

            # Log untuk monitoring
            if hasattr(trainer, 'log'):
                trainer.log({
                    "task_loss": task_loss.item(),
                    "orth_loss": orth_loss.item(),
                    "total_loss": total_loss.item(),
                })

            return (total_loss, outputs) if return_outputs else total_loss

        # Setup trainer
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=4,
            warmup_steps=10,
            learning_rate=2e-4,
            bf16=True,
            logging_steps=10,
            save_strategy="epoch",
            seed=42,
        )

        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset,
            dataset_text_field="text",
            max_seq_length=4096,
            args=training_args,
        )

        # Patch compute_loss
        trainer.compute_loss = custom_compute_loss

        # Train
        print(f"[trainer] starting O-LoRA training for {domain}")
        train_result = trainer.train()

        # Save LoRA
        lora_name = f"lora_{domain}_v{self._get_next_version(domain)}"
        lora_path = self.loras_dir / self.worker_id / lora_name
        model.save_pretrained(str(lora_path))

        # Save metadata
        metadata = {
            "name": lora_name,
            "domain": domain,
            "worker_id": self.worker_id,
            "version": self._get_next_version(domain),
            "trained_at": str(torch.datetime.now()),
            "episodes_count": len(dataset),
            "lambda_orth": self.lambda_orth,
            "rank": self.rank,
            "alpha": self.alpha,
            "train_loss": train_result.training_loss,
            "status": "pending_eval",
        }
        (lora_path / "metadata.json").write_text(json.dumps(metadata, indent=2))

        print(f"[trainer] saved LoRA to {lora_path}")
        return {"lora_name": lora_name, "lora_path": str(lora_path), "metadata": metadata}

    def _extract_module_key(self, full_key: str) -> str:
        """
        Ekstrak nama modul yang pendek dari full parameter key.
        "base_model.model.model.layers.0.self_attn.q_proj.lora_A.weight"
        → "layers.0.self_attn.q_proj"
        """
        parts = full_key.split(".")
        # Cari index "layers" dan ambil sampai sebelum "lora_A"
        try:
            layers_idx = parts.index("layers")
            lora_idx = parts.index("lora_A")
            return ".".join(parts[layers_idx:lora_idx])
        except ValueError:
            return full_key

    def _get_next_version(self, domain: str) -> int:
        worker_dir = self.loras_dir / self.worker_id
        if not worker_dir.exists():
            return 1
        existing = [d.name for d in worker_dir.iterdir()
                    if d.is_dir() and d.name.startswith(f"lora_{domain}_v")]
        if not existing:
            return 1
        versions = [int(n.split("_v")[-1]) for n in existing if n.split("_v")[-1].isdigit()]
        return max(versions) + 1 if versions else 1
```

---

## Integrasi ke trainer Worker

```python
# Di backend/workers.py, bagian trainer worker:

async def train_new_lora(request: dict) -> dict:
    worker_id = request['worker_id']
    domain    = request['domain']

    # 1. Ambil episodes dari Ring 2
    episodes = load_parquet_episodes(worker_id, domain, min_success_rate=0.8)
    if len(episodes) < TRAINING_THRESHOLD:
        return {'status': 'skipped', 'reason': 'insufficient_data', 'count': len(episodes)}

    # 2. Compress (hermes pattern)
    compressed = compress_trajectories(episodes, target_max_tokens=6000)

    # 3. Format untuk SFTTrainer
    dataset = format_episodes_for_sft(compressed, worker_id)

    # 4. Train dengan O-LoRA
    trainer_obj = OrthogonalLoRATrainer(
        worker_id=worker_id,
        base_model_path=get_worker_base_model(worker_id),
        loras_dir="~/.vibe-office/loras",
        lambda_orth=0.1,    # constraint strength — tuning kalau perlu
        rank=16,
        alpha=32,
    )

    result = trainer_obj.train(
        domain=domain,
        dataset=dataset,
        output_dir=f"/tmp/vibe-training/{worker_id}-{domain}",
        num_epochs=3,
    )

    # 5. Eval LoRA baru
    eval_result = await eval_lora(worker_id, result['lora_path'], domain)
    delta = eval_result['score'] - eval_result['baseline']

    # 6. Keputusan: aktifkan atau discard
    if delta > 0.05:
        activate_lora(worker_id, result['lora_name'])
        update_lora_metadata(worker_id, result['lora_name'], {
            'status': 'active',
            'eval_score': eval_result['score'],
            'baseline_score': eval_result['baseline'],
            'performance_delta': f"+{delta*100:.1f}% {domain}",
        })
        return {'status': 'activated', 'lora': result['lora_name'], 'delta': delta}
    else:
        # Hapus LoRA yang tidak berguna
        import shutil
        shutil.rmtree(result['lora_path'])
        return {'status': 'discarded', 'reason': f'delta {delta:.3f} < threshold 0.05'}
```

---

## Tuning lambda_orth

```
lambda_orth = 0.0   → tidak ada constraint (sama seperti regular LoRA)
lambda_orth = 0.01  → constraint sangat lemah, hampir tidak ada efek
lambda_orth = 0.1   → STARTING POINT — balance antara plasticity dan stability
lambda_orth = 0.5   → constraint kuat, model mungkin susah belajar domain baru
lambda_orth = 1.0   → constraint sangat kuat, mungkin training tidak converge

Kalau domain baru tidak improve:   turunkan lambda_orth
Kalau domain lama mulai forgetting: naikkan lambda_orth

Cara monitor: lihat task_loss vs orth_loss di training logs.
Kalau orth_loss sangat tinggi tapi task_loss tidak turun → lambda terlalu besar.
```

---

## Alternatif: Separate LoRA Files (Tanpa O-LoRA)

Kalau O-LoRA terasa terlalu complex untuk implementasi awal, mulai dengan ini:

```python
# Tidak ada orthogonality constraint.
# Cukup simpan setiap LoRA sebagai file terpisah.
# Load hanya LoRA yang relevan berdasarkan task type.

async def inference_with_lora_routing(task: dict, worker_id: str) -> str:
    """Load LoRA yang paling relevan untuk task ini."""
    domain = classify_task_domain(task)
    lora_path = find_best_lora(worker_id, domain)

    response = await vllm_client.chat.completions.create(
        model=get_worker_base_model(worker_id),
        messages=build_messages(task),
        extra_body={
            "lora_request": {
                "lora_name": domain,
                "lora_int_id": get_lora_id(domain),
                "lora_local_path": lora_path
            }
        }
    )
    return response.choices[0].message.content
```

Ini tidak ada catastrophic forgetting karena LoRA tidak pernah di-merge —
tapi juga tidak ada cross-domain generalization.
Mulai dengan ini, switch ke O-LoRA kalau ada bukti forgetting.

---

## Checklist O-LoRA Fase 4

```
[ ] OrthogonalLoRATrainer bisa load existing LoRA weights tanpa error
[ ] compute_orthogonality_loss return 0 untuk weights yang orthogonal
[ ] Training loop dengan custom_compute_loss berjalan tanpa error
[ ] Training log menampilkan task_loss, orth_loss, total_loss terpisah
[ ] LoRA hasil training tersimpan dengan metadata.json lengkap
[ ] Eval pipeline mengukur score sebelum dan sesudah LoRA baru
[ ] Trainer worker auto-discard kalau delta < 0.05
[ ] Conflict map di brain visualization menampilkan orthogonality matrix
[ ] lambda_orth = 0.1 sebagai default, bisa dikonfigurasi via plugin.json trainer
```
