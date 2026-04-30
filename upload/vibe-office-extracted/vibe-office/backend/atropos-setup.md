# Backend — Atropos Setup (RL Training, Fase 4+)

> **Konteks untuk session baru:**
> Atropos adalah RL training framework dari NousResearch, dipakai di hermes-agent.
> Repo: https://github.com/NousResearch/atropos (Apache-2.0)
> Fungsi: train model pakai reinforcement learning — bukan SFT (tiru contoh).
> RL workers belajar dari feedback nyata: "kode compile = reward +1, gagal = 0".
> FASE: ini Fase 4+ — hanya setelah SFT fine-tuning (Unsloth) sudah jalan.
> File ini: install, arsitektur, custom environment untuk setiap worker type.

---

## SFT dulu, RL kemudian

```
Fase 4a — SFT via Unsloth (sudah di training-landscape.md):
  Data: Ring 2 episodes sukses
  Hasil: model yang bisa "tiru" contoh sukses
  Keterbatasan: tidak generalize ke situasi baru

Fase 4b — RL via Atropos (file ini):
  Reward: dari hasil nyata (compile success, test pass)
  Hasil: model yang bisa "reason" tentang apa yang benar
  Butuh: SFT baseline yang sudah bagus sebagai starting point
```

Jangan jalankan RL dari zero — mulai dari SFT checkpoint.

---

## Install Atropos

```bash
# Atropos terintegrasi dengan hermes-agent
# Clone hermes dengan submodules (Atropos ada sebagai submodule)
git clone --recurse-submodules https://github.com/NousResearch/hermes-agent
cd hermes-agent

# Install Atropos
uv pip install -e "./tinker-atropos"

# Install tools lain yang dibutuhkan
uv pip install -e ".[all]"

# Verify
python -c "from environments.hermes_base_env import HermesAgentBaseEnv; print('ok')"
```

**Atau install Atropos standalone:**
```bash
git clone https://github.com/NousResearch/atropos
cd atropos
pip install -e .

# Start Atropos API server
run-api
# Berjalan di http://localhost:8000 (Atropos port — berbeda dari vLLM!)
```

---

## Arsitektur Lengkap

```
┌─────────────────────────────────────────────────────────────────┐
│                    VIBE-OFFICE RL TRAINING STACK                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  trainer worker (Python)                                        │
│    ↓ request training                                           │
│  Atropos API (http://localhost:7999)                            │
│    ↓ distribute rollouts                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Custom Environments (satu per worker type)               │   │
│  │   CoderRustEnv, TesterEnv, AuditorEnv, ...              │   │
│  │     ↓ rollout: LLM generate response                    │   │
│  │     ↓ compute_reward() dengan real tools                │   │
│  │        → compile Rust → test → lint → reward score      │   │
│  └──────────────────────────────────────────────────────────┘   │
│    ↓ reward signals                                             │
│  vLLM (http://localhost:8000) ← model yang di-train            │
│    ↓ token IDs + logprobs                                       │
│  GRPO/PPO update                                                │
│    ↓                                                            │
│  Updated LoRA weights → ~/.vibe-office/loras/                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Port summary:**
- vLLM: `localhost:8000` (inference + training target)
- Atropos API: `localhost:7999` (RL orchestrator)
- Vibe-office backend: `localhost:8765` (WebSocket game)
- EdgeQuake: `localhost:8080` (Ring 3)

---

## Base Environment untuk Vibe-Office Workers

```python
# backend/training/vibe_base_env.py

from environments.hermes_base_env import HermesAgentBaseEnv
from typing import Any
import json

class VibeWorkerBaseEnv(HermesAgentBaseEnv):
    """
    Base class untuk semua vibe-office RL environments.
    Extend ini untuk setiap worker type.
    """

    def __init__(self, worker_id: str, **kwargs):
        super().__init__(**kwargs)
        self.worker_id = worker_id

    async def setup(self):
        """Load training tasks dari Ring 2."""
        from backend.memory import load_parquet_episodes
        # Ambil episodes dari Ring 2 — ini adalah "gym" untuk RL
        self.tasks = load_parquet_episodes(
            worker_id=self.worker_id,
            min_success_rate=0.0,  # RL butuh gagal juga untuk belajar
            limit=1000
        )
        print(f"[{self.worker_id}_env] loaded {len(self.tasks)} tasks")

    async def get_next_item(self) -> dict:
        import random
        return random.choice(self.tasks)

    def format_prompt(self, item: dict) -> str:
        """Format task sebagai prompt untuk model."""
        raise NotImplementedError("Implement di subclass")

    async def compute_reward(self, item: dict, result: Any, ctx) -> float:
        """Hitung reward dari hasil. ctx punya akses ke real tools."""
        raise NotImplementedError("Implement di subclass")

    async def evaluate(self, *args, **kwargs):
        """Jalankan evaluation set untuk monitor progress."""
        pass
```

---

## Environment: CoderRustEnv

```python
# backend/training/envs/coder_rust_env.py

from backend.training.vibe_base_env import VibeWorkerBaseEnv
import json
import re

class CoderRustEnv(VibeWorkerBaseEnv):
    """
    RL environment untuk coder_rust.
    Reward: compile success × test pass × code quality
    """
    name = "coder_rust"

    def format_prompt(self, item: dict) -> str:
        context = item.get('context', {})
        return f"""You are coder_rust, a Rust specialist.

Task: {item['instruction']}

Project context:
{json.dumps(context.get('codebase_context', {}), indent=2)}

Respond with valid JSON:
{{
  "code": "<complete Rust code>",
  "explanation": "<brief explanation>",
  "files_modified": ["<file paths>"]
}}"""

    async def compute_reward(self, item: dict, result: Any, ctx) -> float:
        """
        Multi-component reward:
        - compile_success: 0.5 (paling penting)
        - test_pass:       0.3 (kalau ada test)
        - no_warnings:     0.1
        - code_quality:    0.1
        Total max: 1.0
        """
        # Parse output
        try:
            if hasattr(result, 'content'):
                output = json.loads(result.content)
            else:
                output = json.loads(str(result))
            code = output.get('code', '')
        except (json.JSONDecodeError, AttributeError):
            return 0.0  # Parse gagal = reward 0

        if not code.strip():
            return 0.0

        reward = 0.0

        # 1. Compile check (0.5 reward)
        ctx.terminal(f"cat > /tmp/vibe_test.rs << 'RUSTEOF'\n{code}\nRUSTEOF")
        compile_result = ctx.terminal(
            "rustc /tmp/vibe_test.rs -o /tmp/vibe_test 2>&1"
        )

        if compile_result['exit_code'] == 0:
            reward += 0.5
        else:
            # Compile gagal — return early, tidak perlu cek yang lain
            # Tapi berikan partial reward kalau error yang diketahui
            stderr = compile_result.get('stdout', '')
            if 'error[E' in stderr:
                # Ada error yang jelas — model setidaknya nulis Rust valid
                reward += 0.05
            return reward

        # 2. Warning check (0.1 reward)
        warn_result = ctx.terminal("rustc /tmp/vibe_test.rs -o /tmp/vibe_test 2>&1 | grep -c warning")
        warning_count = int(warn_result.get('stdout', '99').strip() or '99')
        if warning_count == 0:
            reward += 0.1

        # 3. Test (0.3 reward) — kalau ada expected output di task
        if item.get('expected_output'):
            run_result = ctx.terminal("/tmp/vibe_test 2>&1")
            if item['expected_output'] in run_result.get('stdout', ''):
                reward += 0.3
            elif run_result['exit_code'] == 0:
                reward += 0.1  # Run berhasil tapi output beda
        else:
            # Tidak ada expected output — berikan partial
            reward += 0.2

        # 4. Code quality (0.1 reward) — pakai clippy
        clippy_result = ctx.terminal(
            "cd /tmp && rustc --edition 2021 /tmp/vibe_test.rs -o /tmp/vibe_test_q 2>&1"
        )
        # Simplified: tidak ada clippy warnings = quality OK
        if 'warning' not in clippy_result.get('stdout', ''):
            reward += 0.1

        return min(reward, 1.0)

if __name__ == "__main__":
    CoderRustEnv.cli()
```

---

## Environment: TesterEnv

```python
# backend/training/envs/tester_env.py

from backend.training.vibe_base_env import VibeWorkerBaseEnv
import json

class TesterEnv(VibeWorkerBaseEnv):
    name = "tester"

    def format_prompt(self, item: dict) -> str:
        return f"""You are tester, a Rust testing specialist.

Code to test:
{item.get('code_to_test', '')}

Write comprehensive unit tests. Respond with JSON:
{{
  "tests": "<complete #[cfg(test)] module>",
  "test_count": <number>,
  "coverage_areas": ["<what is tested>"]
}}"""

    async def compute_reward(self, item: dict, result: Any, ctx) -> float:
        try:
            output = json.loads(result.content if hasattr(result,'content') else str(result))
            tests = output.get('tests', '')
        except:
            return 0.0

        if '#[test]' not in tests:
            return 0.0  # Tidak ada test function

        # Gabungkan kode asli + tests
        combined = f"{item.get('code_to_test', '')}\n\n{tests}"
        ctx.terminal(f"cat > /tmp/test_combined.rs << 'EOF'\n{combined}\nEOF")

        # Run tests
        test_result = ctx.terminal("rustc --test /tmp/test_combined.rs -o /tmp/test_bin && /tmp/test_bin 2>&1")

        if test_result['exit_code'] != 0:
            output_text = test_result.get('stdout', '')
            if 'test result: FAILED' in output_text:
                # Test berjalan tapi ada yang gagal
                # Hitung berapa yang pass
                passed = output_text.count('... ok')
                failed = output_text.count('... FAILED')
                total = passed + failed
                return (passed / total) * 0.7 if total > 0 else 0.0
            return 0.0

        # Semua test pass — bonus untuk coverage
        output_text = test_result.get('stdout', '')
        test_count = output_text.count('... ok')
        coverage_bonus = min(test_count / 5, 0.3)  # max 0.3 untuk 5+ tests

        return 0.7 + coverage_bonus

if __name__ == "__main__":
    TesterEnv.cli()
```

---

## Jalankan RL Training

```bash
# 1. Pastikan vLLM jalan dengan tool parser
python -m vllm.entrypoints.openai.api_server \
    --model ~/.vibe-office/loras/coder_rust/sft_checkpoint \
    --tool-parser hermes \
    --enable-lora \
    --port 8000

# 2. Start Atropos API
run-api  # port 7999

# 3. Jalankan environment
python backend/training/envs/coder_rust_env.py serve \
    --openai.base_url http://localhost:8000/v1 \
    --openai.model_name coder_rust_sft \
    --openai.server_type openai \
    --env.num_rollouts 64 \
    --env.max_steps 5
```

---

## Integrasi ke trainer Worker

```python
# Di backend/workers.py, trainer worker tambahkan mode RL:

async def train_rl(request: dict) -> dict:
    """
    Jalankan RL training setelah SFT baseline sudah cukup bagus.
    Prerequisite: eval_score dari SFT > 0.7
    """
    worker_id = request['worker_id']
    domain    = request['domain']

    # Cek apakah SFT baseline sudah cukup
    sft_lora = get_best_sft_lora(worker_id, domain)
    if not sft_lora or sft_lora['eval_score'] < 0.7:
        return {
            'status': 'skipped',
            'reason': f'SFT baseline score {sft_lora["eval_score"]:.2f} < 0.7 threshold'
        }

    # Pilih environment berdasarkan worker_id
    env_map = {
        'coder_rust':   'backend.training.envs.coder_rust_env:CoderRustEnv',
        'coder_python': 'backend.training.envs.coder_python_env:CoderPythonEnv',
        'tester':       'backend.training.envs.tester_env:TesterEnv',
    }

    env_class = env_map.get(worker_id)
    if not env_class:
        return {'status': 'skipped', 'reason': f'No RL env for {worker_id}'}

    # Notify game UI
    await ws_broadcast({
        'type': 'state_change',
        'worker_id': 'trainer',
        'new_state': 'working'
    })
    await ws_broadcast({
        'type': 'speech_bubble',
        'worker_id': 'trainer',
        'text': f'RL training {domain}...',
        'color': '#C792EA',
        'duration_ms': 5000
    })

    # Launch RL via subprocess (training bisa berjam-jam)
    import subprocess
    proc = subprocess.Popen([
        'python', '-m', env_class.split(':')[0],
        'serve',
        '--openai.base_url', 'http://localhost:8000/v1',
        '--openai.model_name', f'{worker_id}_sft',
        '--env.num_rollouts', '128',
    ])

    return {'status': 'launched', 'pid': proc.pid}
```

---

## Reward Function Design Guidelines

```
PRINSIP:
1. Reward harus bisa dihitung secara otomatis (tidak butuh human judgment)
2. Reward harus binary atau kontinyu — tidak ada "sometimes right"
3. Jangan beri reward untuk prose explanation — hanya untuk hasil nyata

GOOD rewards:
  ✅ cargo compile berhasil (0 atau 1)
  ✅ cargo test semua pass (0, 0.5, atau 1 berdasarkan pass ratio)
  ✅ cargo clippy zero warnings (0 atau 1)
  ✅ output program sama dengan expected (0 atau 1)

BAD rewards:
  ❌ "kode terlihat bersih" (subjektif)
  ❌ "penjelasan lengkap" (tidak terukur)
  ❌ "pakai patterns yang benar" (perlu human judgment)

REWARD SHAPING:
  Kalau reward terlalu sparse (hampir selalu 0 atau 1):
  Tambahkan partial rewards untuk progress menuju tujuan.
  Contoh: partial reward 0.2 kalau compile tapi test gagal.
```

---

## Checklist Atropos Fase 4

```
[ ] Atropos install berhasil (run-api berjalan)
[ ] CoderRustEnv bisa setup() dan get_next_item() tanpa error
[ ] compute_reward() berjalan dengan ctx.terminal()
[ ] Satu rollout selesai end-to-end tanpa crash
[ ] Training loop: reward meningkat setelah beberapa epoch
[ ] trainer worker bisa launch RL job via subprocess
[ ] Game UI menampilkan progress trainer saat RL berjalan
[ ] Hasil RL LoRA ter-save ke ~/.vibe-office/loras/
[ ] Eval post-RL menunjukkan improvement vs SFT baseline
```
