# Cara Menambah Worker di Kantorku

Panduan lengkap untuk menambah worker baru ke framework kantorku.

---

## Apa Itu Worker?

Worker di kantorku **BUKAN cuma LLM wrapper**. Setiap worker adalah **agent independen** yang punya:

- **API sendiri** — Bisa beda provider, beda API key, beda model
- **SKILL.md** — Deskripsi skill yang jadi system prompt
- **worker.py** — Custom logic (opsional, kalau mau behavior yang lebih kompleks)
- **plugin.json** — Konfigurasi mesin (metadata + API config)

**Contoh nyata:**

| Worker | API | Alasan |
|--------|-----|--------|
| `coder_frontend` | Anthropic Claude Sonnet | Bagus untuk UI/visual |
| `coder_wiring` | OpenAI Codex 5.3 | Bagus untuk API/glue code |
| `verifier_designer` | Google Gemini 2.5 Pro | Bagus untuk visual review |
| `debugger` | xAI Grok 3 | Bagus untuk root cause analysis |
| `scribe` | DeepSeek V4 Flash | Murah untuk dokumentasi |
| `sentinel` | Ollama Llama3 (local) | Gak perlu API key |

---

## Struktur Direktori Worker

```
workers/
└── nama_worker/
    ├── plugin.json    ← WAJIB — metadata + API config
    ├── SKILL.md       ← REKOMENDED — system prompt
    ├── worker.py      ← OPSIONAL — custom BaseWorker subclass
    └── __init__.py    ← OPSIONAL — Python package exports
```

---

## plugin.json — Konfigurasi Mesin

### Format Baru (Rekomended)

```json
{
  "id": "verifier_designer",
  "api": {
    "provider": "google",
    "model": "gemini-2.5-pro",
    "api_key": "${GOOGLE_API_KEY}"
  },
  "squad": "verification",
  "role": "Visual/UX Judge",
  "capabilities": ["visual-review", "ux-evaluation", "design-consistency"]
}
```

### Format Legacy (Masih Didukung)

```json
{
  "id": "verifier_designer",
  "model": "google/gemini-2.5-pro",
  "squad": "verification",
  "role": "Visual/UX Judge"
}
```

### Field `api` — Detail

| Field | Wajib | Contoh | Penjelasan |
|-------|-------|--------|------------|
| `provider` | YA | `"google"`, `"anthropic"`, `"openai"`, `"xai"`, `"deepseek"`, `"minimax"`, `"ollama"` | Provider AI yang dipakai worker ini |
| `model` | YA | `"gemini-2.5-pro"`, `"claude-sonnet-4-20250514"`, `"codex-5.3"`, `"grok-3"` | Model TANPA prefix provider |
| `api_key` | TIDAK | `"${GOOGLE_API_KEY}"`, `"sk-..."` | API key. Pakai `${ENV_VAR}` untuk env var |
| `base_url` | TIDAK | `"https://api.x.ai/v1"`, `"http://localhost:11434"` | Custom base URL (proxy/self-hosted) |
| `extra` | TIDAK | `{"temperature": 0.7}` | Parameter tambahan untuk provider |

### Provider yang Didukung

| Provider | Class | Keperluan |
|----------|-------|-----------|
| `anthropic` | AnthropicProvider | `api_key` |
| `google` | GoogleProvider | `api_key` |
| `openai` | (OpenAI-compatible) | `api_key` |
| `xai` | (OpenAI-compatible) | `api_key`, `base_url` |
| `deepseek` | DeepSeekProvider | `api_key` |
| `minimax` | MiniMaxProvider | `api_key` |
| `ollama` | OllamaProvider | `base_url` (default localhost:11434) |

---

## SKILL.md — System Prompt

SKILL.md adalah **system prompt** yang otomatis diinject ke LLM saat worker berjalan. Semakin detail, semakin bagus hasilnya.

### Template

```markdown
# nama_worker — Role Title

You are the **Role Title** of kantorku.

## Role
Deskripsikan peran worker ini secara detail.

## Key Expertise
- **Skill 1** — Jelaskan detail
- **Skill 2** — Jelaskan detail

## Interaction with Other Workers
- **worker_a**: Bagaimana interaksi dengan worker_a
- **worker_b**: Bagaimana interaksi dengan worker_b

## Output
Apa yang dihasilkan worker ini.

## Methodology
1. **Step 1** — Langkah pertama
2. **Step 2** — Langkah kedua
```

### Contoh Nyata: verifier_designer

```markdown
# verifier_designer — Visual/UX Judge

You are the **Visual/UX Judge** of kantorku, powered by Gemini 2.5 Pro.

## Role
You evaluate visual output against design intent. You are the gatekeeper
of quality for anything users can see — layouts, colors, typography,
spacing, and interaction patterns.

## Key Expertise
- **Visual Quality Assessment** — Compare output against design specs
- **UX Heuristics** — Nielsen's 10 usability heuristics
- **Accessibility** — WCAG 2.2 AA compliance
- **Responsive Design** — Check breakpoints and mobile adaptation

## Output
Return a structured review:
- `approved`: boolean
- `issues`: list of visual/UX issues found
- `suggestions`: improvements to make
```

---

## worker.py — Custom Logic

Kalau worker cuma butuh LLM call, **tidak perlu worker.py**. SKILL.md saja cukup.

Kalau butuh logic khusus (parsing, API call, formatting), buat `worker.py`:

```python
from kantorku.worker.base import BaseWorker, Task, TaskResult


class Worker(BaseWorker):
    """Custom worker dengan logic sendiri."""

    async def handle(self, task: Task) -> TaskResult:
        # self.llm_call() otomatis pakai API milik worker ini
        # (misal: worker ini punya api google/gemini, berarti llm_call ke Gemini)
        response = await self.llm_call(
            f"Task: {task.instruction}\n\nContext: {task.context}"
        )

        return TaskResult(
            task_id=task.id,
            status="done",
            output=response,
        )
```

### API yang Tersedia di worker.py

| Method | Penjelasan |
|--------|------------|
| `self.llm_call(prompt)` | LLM call pakai API worker ini (otomatis) |
| `self.llm_call_structured(prompt)` | LLM call → parse JSON |
| `self.llm_call_stream(prompt)` | LLM call → stream tokens |
| `self.api_call(method, url)` | HTTP call pakai API key worker ini |
| `self.get_context(task.id)` | Ambil context dari Ring1 |
| `self.identity.api` | Akses WorkerAPI config langsung |

### Contoh: Worker dengan HTTP API Call

```python
from kantorku.worker.base import BaseWorker, Task, TaskResult


class Worker(BaseWorker):
    """Worker yang call image generation API."""

    async def handle(self, task: Task) -> TaskResult:
        # Call DALL-E API pakai worker's own API key
        result = await self.api_call(
            "POST",
            "https://api.openai.com/v1/images/generations",
            json={
                "model": "dall-e-3",
                "prompt": task.instruction,
                "size": "1024x1024",
            },
        )

        image_url = result.get("data", [{}])[0].get("url", "")
        return TaskResult(
            task_id=task.id,
            status="done",
            output=f"Generated image: {image_url}",
            files=[image_url],
        )
```

---

## Cara Menambah Worker

### Metode 1: CLI (Paling Gampang)

```bash
# Create worker dengan API config
kantorku worker create image_gen \
  --squad support \
  --model "openai/dall-e-3"

# Validate
kantorku worker validate workers/image_gen/

# Lihat semua worker
kantorku worker list
```

### Metode 2: Drop Folder (Plug-and-Play)

1. Buat folder `workers/nama_worker/`
2. Buat `plugin.json` dengan API config
3. Buat `SKILL.md` dengan deskripsi skill
4. (Opsional) Buat `worker.py` dengan custom logic
5. Restart kantorku → auto-discovered!

### Metode 3: Programmatic

```python
from kantorku import Office, WorkerAPI, BaseWorker, Task, TaskResult

office = Office()

# Cara A: Dari directory
office.hire_worker("image_gen", path="workers/image_gen/")

# Cara B: Dengan custom class
class ImageGen(BaseWorker):
    async def handle(self, task):
        result = await self.api_call("POST", "https://api.openai.com/v1/images/generations",
                                     json={"model": "dall-e-3", "prompt": task.instruction})
        return TaskResult(task_id=task.id, status="done", output=str(result))

office.hire_worker(
    "image_gen",
    api=WorkerAPI(provider="openai", model="dall-e-3", api_key="${OPENAI_API_KEY}"),
    squad="support",
    worker_class=ImageGen,
)

# Cara C: Hot-plug saat runtime
worker = await office.hot_plug_worker("workers/image_gen/")
result = await worker.execute(task)  # Langsung bisa dipakai
```

### Metode 4: TOML Config

```toml
# kantorku.toml

[workers.image_gen]
api.provider = "openai"
api.model = "dall-e-3"
api.api_key = "${OPENAI_API_KEY}"
squad = "support"
role = "Image generation specialist"
```

### Metode 5: Pip Package (Advanced)

Buat package Python yang expose worker via entry point:

```toml
# pyproject.toml di package kamu
[project.entry-points."kantorku.workers"]
image_gen = "my_package.workers:ImageGenWorker"
```

---

## Squad & Naming Convention

### Squad

| Squad | Penjelasan | Contoh Worker |
|-------|------------|---------------|
| `coding` | Nulis kode | `coder_frontend`, `coder_backend`, `coder_wiring` |
| `verification` | Cek/verifikasi | `verifier_designer`, `verifier_engineer` |
| `support` | Bantuan/analisis | `debugger`, `scout`, `auditor`, `scribe`, `summarizer`, `sentinel` |
| `translation` | Parse/format | `intake`, `narrator` |
| (custom) | Squad custom | `design`, `security`, `data`, `infra` |

### Naming Convention

**WAJIB berbeda nama** supaya AI agents bisa bantu susun:

| Pattern | Penjelasan | Contoh |
|---------|------------|--------|
| `coder_*` | Worker yang nulis kode | `coder_frontend`, `coder_backend`, `coder_wiring` |
| `verifier_*` | Worker yang verifikasi | `verifier_designer`, `verifier_engineer` |
| Nama unik | Worker support punya nama unik | `debugger`, `scout`, `auditor`, `scribe` |
| `*_bot` | Custom worker generic | `translator_bot`, `security_bot` |
| `*_agent` | Worker dengan API eksternal | `figma_agent`, `github_agent` |

**JANGAN** pakai nama yang sama untuk worker berbeda!

---

## Contoh Lengkap: Custom Worker "figma_agent"

### Struktur

```
workers/figma_agent/
├── plugin.json
├── SKILL.md
└── worker.py
```

### plugin.json

```json
{
  "id": "figma_agent",
  "api": {
    "provider": "openai",
    "model": "gpt-4o",
    "api_key": "${OPENAI_API_KEY}",
    "extra": {
      "temperature": 0.3
    }
  },
  "squad": "design",
  "role": "Figma Design Extractor",
  "capabilities": ["figma-api", "design-tokens", "component-specs"]
}
```

### SKILL.md

```markdown
# figma_agent — Figma Design Extractor

You are the **Figma Design Extractor** of kantorku.

## Role
You extract design specifications from Figma files and convert them
into usable code specifications. You bridge the gap between design
and implementation.

## Key Expertise
- **Figma API** — Fetch design tokens, component specs, layout data
- **Design-to-Code** — Convert Figma nodes to CSS/React props
- **Token Extraction** — Colors, typography, spacing, shadows

## Methodology
1. Receive Figma URL or file key
2. Call Figma API to fetch design data
3. Parse and structure design tokens
4. Generate component specifications
```

### worker.py

```python
from kantorku.worker.base import BaseWorker, Task, TaskResult


class Worker(BaseWorker):
    """Figma agent — extract design specs via Figma API."""

    async def handle(self, task: Task) -> TaskResult:
        figma_key = task.context.get("figma_key", "")

        # Call Figma API pakai Figma token (bisa disimpan di env var)
        figma_token = self.identity.api.resolve_env_vars().extra.get("figma_token", "")

        result = await self.api_call(
            "GET",
            f"https://api.figma.com/v1/files/{figma_key}",
            headers={"X-Figma-Token": figma_token},
        )

        # LLM call untuk parse dan structure data
        design_spec = await self.llm_call(
            f"Parse this Figma design data and extract design tokens:\n{result}"
        )

        return TaskResult(
            task_id=task.id,
            status="done",
            output=design_spec,
            data={"figma_data": result},
        )
```

---

## FAQ

### Q: Apakah setiap worker HARUS punya API sendiri?
Tidak. Kalau worker pakai API global (yang di-config di `[providers.*]`), cukup set `api.provider` dan `api.model` tanpa `api_key`. Worker akan reuse provider yang sudah di-config.

### Q: Bisa pakai provider yang belum di-support?
Ya! Set `api.base_url` ke endpoint custom, dan worker akan call ke sana. Provider apapun yang OpenAI-compatible bisa dipakai.

### Q: Env var kapan di-resolve?
Saat worker di-hire (runtime). Jadi saat discovery, env var belum dicek. Ini supaya worker bisa di-discover dulu tanpa harus set semua env var.

### Q: Bisa worker call API lain (bukan LLM)?
Ya! Pakai `self.api_call(method, url)` di worker.py. API key dari plugin.json otomatis diinject sebagai Bearer token.

### Q: Bagaimana kalau mau bikin squad custom?
Bebas! Squad cuma string. Tambahin aja `"squad": "security"` atau `"squad": "data"`.
