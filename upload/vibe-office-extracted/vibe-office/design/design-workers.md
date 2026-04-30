# Design — Workers & Design Studio

> **Konteks untuk session baru:**
> FectTral punya 5 AI roles (curator, tagger, reviewer, selector, generator) +
> MCP server TypeScript. Wolfvin memutuskan: integrasikan PENUH sebagai satu
> sistem terpadu ke vibe-office, bukan terpisah.
> File ini mendokumentasikan workers design baru + design studio room.
> Keputusan tech stack (TypeScript vs Python) belum final — didokumentasikan di bawah.
>
> **Impeccable Integration (update 2026-03-17):**
> Impeccable (https://github.com/pbakaus/impeccable) — open-source plugin Claude Code
> yang solve AI slop problem di frontend. TIDAK di-install sebagai dependency.
> Yang diadopsi ke file ini:
> - Command vocabulary (/audit /polish /distill /bolder /quieter /animate /typeset
>   /colorize /critique /delight /overdrive) → masuk SKILL.md stylist + compositor
> - Anti-pattern catalog → masuk archivist reject_patterns list
> - Aesthetic direction framework (Brutal, Maximalist, Retro-futuristic, Luxury Editorial)
>   → masuk designer system prompt
> - Project aesthetic context (teach-impeccable pattern) → aesthetic-context.json
> Source of truth untuk command vocabulary + anti-patterns ada di workers.md
> design workers section — file ini tidak duplikasi, hanya reference.

---

## Design Workers (5 Workers Baru)

Semua tinggal di **design studio room**. Mereka tidak pernah di workstation
utama — domain mereka berbeda dari coder_*.

### archivist
**Merge dari:** FectTral `curator` + `tagger`
**Fungsi:** Fetch URL → ekstrak elemen design → beri nama/mood/tags otomatis
**Model:** LLM medium + web-extractor.ts logic
**Tools:** Lightpanda (scrape) + claude-generator.ts (generate tanpa URL)
**Tinggal di:** Design studio, meja dengan banyak tab browser

```
Flow archivist:
  1. Terima URL atau keyword dari kamu
  2. Fetch URL via Lightpanda → ambil HTML/CSS/JS
  3. Parse → pisahkan ke 6 kategori:
     animations | hover-effects | design-systems |
     components | gradients | micro-interactions
  4. Clean up kode: hapus selector spesifik, buat reusable
  5. Tagging otomatis (dari tagger logic):
     - nama: "elegant-fade-hero", "brutal-hover-button"
     - mood: elegant | playful | brutal | minimal | luxury |
             editorial | futuristic | organic | corporate | experimental
     - speed: fast | medium | slow (untuk animasi)
     - context: hero | card | button | nav | form | ...
     - compatible_with, clash_with
  6. Simpan ke design library dengan status: "pending"
  7. Notify stylist ada item baru untuk di-review
```

**Proactive mode** (seperti scout): saat idle, archivist watch URL watchlist
yang kamu set — Dribbble, Awwwards, atau URL custom. Auto-extract, masuk queue.

```typescript
// Database schema (dari database.ts FectTral)
interface DesignElement {
  id: number
  name: string
  category: 'animation'|'hover-effect'|'gradient'|'design-system'|
            'component'|'micro-interaction'|'css'|'tailwind'|
            'react-component'|'nextjs-pattern'|'typescript'|'framer-motion'
  source: 'web' | 'claude'
  source_url: string | null
  code: string
  mood: string        // JSON: ["elegant","minimal"]
  context: string     // JSON: ["hero","card"]
  compatible_with: string  // JSON: ["elemen-lain"]
  clash_with: string       // JSON: ["elemen-yang-tidak-cocok"]
  tags: string             // JSON: free tags
  framework: string        // JSON: ["react","tailwind"]
  status: 'pending' | 'approved' | 'rejected'
  used_count: number
  rating: number | null
  extracted_at: string
}
```

---

### stylist
**Merge dari:** FectTral `reviewer` + `selector`
**Fungsi:** Quality gate (approve/reject) + pilih kombinasi terbaik untuk project
**Model:** LLM medium — butuh judgment estetika
**Tinggal di:** Design studio, meja dengan banyak elemen design tertempel di dinding

**Mode 1 — review** (quality gate):
```
Tampilkan elemen pending satu per satu:
  [3/12] animation › elegant-fade-hero
  Mood: elegant | Speed: slow | Context: hero
  Source: https://linear.app
  
  [preview kode 20 baris]
  
  Simpan? (ya / tidak / rename [nama] / skip)
```

Batch mode: "approve semua futuristic" → approve semua dengan mood futuristic.

**Mode 2 — select** (dipanggil coder_css atau kamu langsung):
```python
async def select_combination(context: dict) -> dict:
    """
    Baca semua elemen approved, pilih kombinasi terbaik.
    Bukan hanya satu elemen — tapi "resep design" yang harmonis.
    """
    project_type = context['type']   # landing, dashboard, portfolio
    target_mood  = context['mood']   # futuristic, minimal, dll
    
    # Filter per kategori berdasarkan mood + context
    # Cek compatibility (compatible_with vs clash_with)
    # Return kombinasi: 1 elemen per kategori yang relevan
    
    return {
        'animation': 'neon-pulse-card',
        'hover-effect': 'electric-lift-button',
        'design-system': 'fectral-cyberpunk-tokens',
        'gradient': 'deep-space-hero',
        'micro-interaction': 'glitch-reveal-scroll',
        'reasoning': '...',
    }
```

---

### compositor
**Merge dari:** FectTral `generator`
**Fungsi:** Generate kode frontend lengkap dari kombinasi design terpilih
**Model:** LLM kuat (Qwen2.5-Coder-7B atau API) — butuh code generation yang bagus
**Tinggal di:** Design studio, workstation dengan dual monitor

Berbeda dari `coder_css`: compositor tidak nulis CSS dari instruksi teknis.
compositor **merakit** elemen dari library menjadi halaman/komponen yang kohesif.
coder_css yang nulis CSS baru. compositor yang compose yang sudah ada.

```
Flow compositor:
  1. stylist.select_combination(context) → dapat "resep"
  2. Load kode aktual tiap elemen dari database
  3. Plan struktur halaman (landing: hero→features→CTA→footer)
  4. Integrate:
     - design-system → CSS variables di :root
     - animations → keyframes
     - hover-effects → applied ke elemen interaktif
     - gradients → background layers
     - micro-interactions → scroll/click enhancements
  5. Output: single HTML file atau React component
     Setiap bagian dari library diberi komentar:
     /* === DARI LIBRARY: elegant-fade-hero === */
```

Output bisa langsung dilihat di design studio FectTral preview panel.
Juga bisa di-send ke coder_js untuk dijadikan bagian dari vibe-office sendiri.

---

### designer (1 WORKER BARU, tidak dari FectTral)
**Fungsi:** Orchestrator untuk semua design workers. Kamu berinteraksi dengannya.
**Model:** LLM medium
**Tinggal di:** Design studio, meja utama di tengah ruangan (ada "kursi bos" pixel art)

Designer adalah "pintu masuk" ke semua hal design. Tanpa designer, kamu harus
tahu harus bicara ke archivist, stylist, atau compositor. Dengan designer,
cukup bilang apa yang mau kamu capai.

```python
async def design(instruction: str) -> dict:
    """
    Orchestrate design pipeline berdasarkan instruksi natural.
    
    "ambil design dari linear.app" → archivist
    "review yang pending" → stylist (review mode)
    "buat landing page untuk project X, pakai library gue" → stylist → compositor
    "generate button dengan mood futuristic" → compositor langsung (pakai library)
    "lihat DNA library gue" → query stats → generate DNA Report
    "archivist idle, watch dribbble.com" → set archivist watchlist
    """
    intent = classify_intent(instruction)
    
    if intent == 'fetch':
        return await archivist.fetch(extract_url(instruction))
    elif intent == 'review':
        return await stylist.review()
    elif intent == 'generate':
        combo = await stylist.select(extract_context(instruction))
        return await compositor.generate(combo)
    elif intent == 'stats':
        return generate_dna_report(get_library_stats())
```

---

## Design Studio Room

Room khusus di kantor. Unlock Fase 2 (sama seperti library room curator).

```
LAYOUT DESIGN STUDIO (tiles):
┌────────────────────────────────────┐
│  [archivist desk]  [stylist desk]  │
│                                    │
│       [compositor workstation]     │
│                                    │
│     [designer desk — CENTER]       │
│                                    │
│  [big monitor — klik untuk enter]  │
└────────────────────────────────────┘
```

**Klik monitor besar** → pixel art zoom in → fade in FectTral full UI.

Di dalam FectTral UI ada 4 halaman (sidebar navigation):
```
DESIGN STUDIO — FectTral UI
├── 📊 Library        → semua elemen approved, filter/search
├── ⏳ Review Queue   → elemen pending (approve/reject/rename)
├── 🧬 DNA Report     → visualisasi "otak" design library
│   ├── mood distribution bar chart
│   ├── top elements dengan star rating
│   ├── category breakdown
│   ├── canvas sparkline (elemen ditambah per waktu)
│   └── recommendation cards (missing/explore/strength)
└── ⚡ Generate       → form untuk minta compositor generate
    ├── project type (dropdown)
    ├── mood preference (multi-select)
    ├── output format (HTML / React)
    └── [GENERATE] button → hasil tampil di right panel
```

---

## DNA Report — "Isi Otak" coder_css

FectTral v3.0 sudah punya template DNA Report (Template 5D).
Di vibe-office, ini menjadi visualisasi "otak" coder_css — bukan LoRA
(karena LoRA untuk coders bahasa pemrograman), tapi design library.

```
DNA REPORT — coder_css
┌──────────────────────────────────────────────────────┐
│  DESIGN IDENTITY                                      │
│  Based on 127 approved elements                      │
│                                                      │
│  MOOD DISTRIBUTION                                   │
│  futuristic ████████████████ 42%                    │
│  minimal    ████████ 22%                             │
│  elegant    ██████ 16%                               │
│  ...                                                 │
│                                                      │
│  TOP ELEMENTS                           ★ RATING    │
│  1. neon-pulse-card          animation  ★★★★★       │
│  2. electric-lift-button     hover      ★★★★☆       │
│  3. deep-space-hero          gradient   ★★★★★       │
│                                                      │
│  RECOMMENDATIONS                                     │
│  🔴 MISSING: organic mood (0 elements)              │
│  🟡 EXPLORE: micro-interactions (only 3)            │
│  🟢 STRENGTH: animations (47 elements)              │
└──────────────────────────────────────────────────────┘
```

Klik elemen mana saja di DNA Report → lihat kode, toggle aktif/nonaktif,
minta compositor untuk generate contoh pakai elemen itu.

---

## Tech Stack: Python (Diputuskan v4.9)

> **Keputusan final:** Opsi B — Python workers, konsisten dengan semua workers lain.
> Alasan: design workers hanya dipakai internal oleh conductor, tidak perlu MCP protocol.
> Room editor sudah file-based (room-config.json) — tidak butuh direct call ke design workers.
> Kalau suatu hari mau expose sebagai MCP: bisa di-wrap nanti.

## Tech Stack Detail (archived — sudah diputuskan)

**Situasi saat ini:**
- FectTral MCP server sudah ditulis TypeScript + SQLite (better-sqlite3)
- Semua workers lain di vibe-office pakai Python + DuckDB/SQLite

**Opsi A — Pakai TypeScript MCP server yang sudah ada:**
```
Pro:  Sudah jalan, sudah teruji, langsung bisa dipakai
      MCP protocol support built-in
      better-sqlite3 sangat cepat (synchronous)
Con:  Dua bahasa di backend (Python + TypeScript)
      Harus maintain dua runtime
      Design workers isolated dari Python AI loop
```

**Opsi B — Port ke Python:**
```
Pro:  Satu bahasa, satu runtime
      Design workers bisa langsung akses DuckDB Ring 1
      Lebih mudah integrate dengan conductor dan bridge
Con:  Harus rewrite web-extractor.ts (cheerio → BeautifulSoup)
      Harus rewrite generator (TypeScript pattern → Python)
      SQLite schema sudah proven, tapi perlu port
```

**Opsi C — Hybrid (rekomendasi gua):**
```
TypeScript MCP server → tetap untuk web-extractor (Node.js fetch lebih
                         bagus untuk web scraping browser compatibility)
Python wrapper → archivist, stylist, compositor, designer
                 panggil MCP tools via subprocess atau HTTP
Design library → tetap SQLite (bukan DuckDB — design elements
                 tidak butuh analytical query, lebih ke CRUD)

Ini memisahkan concerns:
  TypeScript = web layer (fetch, parse HTML/CSS)
  Python = AI layer (LLM calls, orchestration)
  SQLite = design storage (terpisah dari Ring 1 DuckDB)
```

**Belum diputuskan** — Wolfvin perlu baca ini dan decide. Gua sarankan mulai
dengan Opsi A dulu (langsung jalan), port ke Python kalau integrasi jadi
terlalu awkward.

---

## MCP Tools yang Sudah Ada (dari design-tools/index.ts)

Semua ini bisa langsung dipakai oleh designer/archivist/stylist/compositor:

| Tool | Fungsi | Dipakai oleh |
|------|--------|-------------|
| `fetch_web_design` | Fetch URL → ekstrak CSS, Tailwind, animasi | archivist |
| `generate_from_claude` | Generate design element dari Claude knowledge | archivist, compositor |
| `save_design_element` | Simpan elemen manual ke library | archivist |
| `review_library` | Tampilkan pending elements | stylist |
| `approve_element` | Approve → masuk library aktif | stylist |
| `reject_element` | Hapus dari library | stylist |
| `rename_element` | Rename elemen | stylist |
| `query_library` | Search & filter library | stylist, compositor, designer |
| `get_element_code` | Ambil kode lengkap elemen | compositor |
| `library_stats` | Statistik per kategori (untuk DNA Report) | designer |

Setup MCP server:
```bash
cd frontend/fectral/design-tools
npm install
npm run dev   # dev mode

# Atau tambahkan ke claude_desktop_config.json:
{
  "mcpServers": {
    "design-library": {
      "command": "node",
      "args": ["/path/to/design-tools/dist/index.js"]
    }
  }
}
```
