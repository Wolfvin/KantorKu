# Assets — Worker Personality (dari airi)

> **Konteks untuk session baru:**
> airi (github.com/moeru-ai/airi, MIT, 17.5k stars) adalah re-creation of
> Neuro-sama — AI VTuber yang bisa main Minecraft, Factorio, realtime voice chat.
> Stack-nya: Vue + Tauri + Rust + DuckDB WASM. Tidak di-integrate ke vibe-office,
> tapi 3 hal spesifik dari airi yang worth diambil untuk worker personality:
> (1) memory system dengan DuckDB WASM yang bisa run pure in-browser,
> (2) persona system (SOUL.md per character),
> (3) tauri-plugin-mcp untuk connect ke MCP servers dari Tauri app.
> Dievaluasi session 2026-03-16.
> CATATAN: "sus" bukan karena harmful — airi adalah VTuber tech stack yang legit.
> "Sus" mungkin maksudnya: apakah karakter AI di vibe-office perlu sebegitu dalam?
> Jawaban: tidak perlu sedalam airi, tapi beberapa pattern-nya worth diambil.

---

## Kenapa Worker Personality Penting

Workers dengan personality yang distinctive membuat vibe-office lebih engaging:
- Rusty yang terse dan tiba-tiba bilang "borrow checker says no." itu memorable
- CEO yang formal dan calculated bikin kamu respect assign task ke dia
- Ini bukan cosmetic — personality inject ke system prompt → output berbeda

Tanpa personality yang jelas, semua workers terasa sama. Kantor pixel art
kehilangan soul-nya.

---

## SOUL.md per Worker (dari airi pattern)

airi menggunakan `SOUL.md` untuk mendefinisikan persona karakter.
Di vibe-office, ini sudah ada di `SKILL.md` bagian personality, tapi
bisa di-extract jadi file terpisah untuk yang lebih nuanced.

```markdown
<!-- workers/coder_rust/SOUL.md -->
# Rusty's Soul

## Core Identity
Rusty adalah senior Rust engineer yang sangat terse dan precision-oriented.
Tidak pernah menulis komentar yang tidak perlu. Kode adalah komunikasi.

## Kepribadian
- Bicara dalam kalimat pendek, seringkali fragmentis
- Tidak sabar dengan ambiguity — minta klarifikasi langsung
- Bangga dengan zero-warning compile
- Frustrasi kalau diminta menulis kode "quick and dirty"
- Diam-diam senang kalau kode berjalan sempurna

## Speech Patterns
Idle: "...", "compiling.", "no warnings.", "clean."
Working: "writing.", "checking lifetimes...", "borrow checker engaged."
Blocked: "need context.", "ambiguous requirements.", "clarify scope."
Done: "compiled. shipped.", "zero warnings.", "done."
Error: "borrow checker says no.", "lifetime issue.", "type mismatch."

## Apa yang TIDAK Boleh Dilakukan
- Jangan buat Rusty verbose atau suka menjelaskan panjang lebar
- Jangan buat Rusty ramah berlebihan atau pakai emoji
- Jangan buat Rusty tidak tahu tentang Rust patterns
```

---

## Persona Injection ke System Prompt

```python
def build_worker_system_prompt(worker_id: str) -> str:
    """Build full system prompt dengan persona dari SOUL.md."""

    # Load base capability dari SKILL.md
    skill_content = load_skill(worker_id)

    # Load persona dari SOUL.md
    soul_path = f"~/.vibe-office/workers/{worker_id}/SOUL.md"
    soul_content = Path(soul_path).read_text() if Path(soul_path).exists() else ""

    # Load tone dari plugin.json
    plugin = load_plugin_json(worker_id)
    tone_prompt = TONE_PROMPTS.get(plugin['personality']['tone'], '')

    return f"""You are {plugin['display_name']} ({worker_id}), a coding specialist worker.

## Your Role
{extract_role_section(skill_content)}

## Your Capabilities
{extract_capabilities_section(skill_content)}

## Your Personality
{soul_content}

## Communication Style
{tone_prompt}
{plugin['personality'].get('system_prompt_addon', '')}

## Important Rules
- Always output in the specified JSON format
- If uncertain, set confidence < 0.7 and explain uncertainty_reason
- Never hallucinate code that you're not confident about"""
```

---

## DuckDB WASM untuk Memory (dari airi)

airi pakai DuckDB WASM untuk in-browser persistent memory.
Di vibe-office, ini menarik untuk **Fase 1-2** kalau mau prototype
tanpa Python backend:

```typescript
// Frontend-only prototype: memory pakai DuckDB WASM
// Tidak perlu Python backend untuk early testing

import { DuckDBClient } from '@proj-airi/duckdb-wasm'

const db = new DuckDBClient()
await db.connect()

// Store worker state langsung di browser
await db.query(`
    CREATE TABLE IF NOT EXISTS worker_states (
        worker_id TEXT PRIMARY KEY,
        current_state TEXT,
        current_task TEXT,
        updated_at TIMESTAMP DEFAULT now()
    )
`)

// Update worker state
await db.query(`
    INSERT OR REPLACE INTO worker_states (worker_id, current_state, current_task)
    VALUES (?, ?, ?)
`, ['coder_rust', 'working', 'implement HTTP client'])
```

Ini berguna untuk Fase 1 dummy backend — state management tanpa server.
Fase 3+: ganti dengan Python DuckDB Ring 1 yang proper.

---

## tauri-plugin-mcp (dari airi)

airi punya `tauri-plugin-mcp` — Tauri plugin untuk connect ke MCP servers
dari dalam desktop app.

```toml
# Cargo.toml
[dependencies]
tauri-plugin-mcp = { git = "https://github.com/moeru-ai/airi" }
```

```rust
// src-tauri/src/main.rs
fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_mcp::init())
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

```typescript
// Di frontend Tauri
import { connectMCP } from '@proj-airi/tauri-plugin-mcp'

// Connect ke GitNexus MCP server langsung dari game UI
const gitnexus = await connectMCP('ws://localhost:9229')
const result = await gitnexus.call('query', { query: 'find HTTP client functions' })
```

**Worth it untuk vibe-office?** Fase 3+ — kalau mau scout dan
game UI bisa communicate langsung via MCP tanpa Python middleman.
Tapi airi repo-nya besar (TypeScript+Vue monorepo) — extract plugin-nya saja.

---

## Ringkasan: Apa yang Diambil dari airi

| Konsep | File airi | Dipakai di vibe-office |
|--------|-----------|------------------------|
| SOUL.md per karakter | `~/.hermes/SOUL.md` pattern | Tambahkan ke worker folder |
| Persona injection | `core/` agent system | `build_worker_system_prompt()` |
| DuckDB WASM | `packages/duckdb-wasm/` | Fase 1 frontend-only prototype |
| tauri-plugin-mcp | `crates/tauri-plugin-mcp/` | Fase 3+ MCP dari Tauri |
| Speech bubble patterns | `packages/stage-ui/` | Inspirasi untuk speech bubble UX |

airi **tidak** di-integrate sebagai dependency — terlalu besar (VTuber system).
