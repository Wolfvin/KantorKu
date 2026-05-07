---
title: Rust AI Worker System Skill
kategori: Rust, Tauri & Desktop Development
tags: [Rust, AI-Worker, Multi-Agent, PDF-Extraction, Parallel-Pipeline, Excel-Output, Dataset, Fine-Tuning]
---

# Rust AI Worker System — Knowledge Skill

Pengetahuan terkristalisasi dari sistem PDF extraction + multi-agent AI + dataset
engineering. Gunakan sebagai referensi lengkap untuk membangun komponen sistem.

---

## 1. PDF TABLE EXTRACTION (Image-Based)

### Pipeline Utama
```
PDF → pdftoppm (DPI=220) → PNG
    → replace_white([0,255,0]) → isolasi background
    → flood_fill BFS → Vec<CellBox>
    → group_rows (toleransi dinamis, max 6px)
    → filter_separator (tipis ≤4px atau lebar ≥70% & tinggi ≤60px)
    → pdftotext -bbox-layout → WordBoxPt
    → scale pt→px → WordBoxPx
    → best_fit_overlap_assign → Vec<Vec<String>>
    → write_xlsx
```

### Konstanta Teruji (BNI Statement)
```rust
const RENDER_DPI: u32 = 220;
const COLOR_REGION_MIN_AREA_PX: usize = 2_000;
const SEP_THIN_PX: u32 = 4;
const SEP_INFO_H_PX: u32 = 60;
const SEP_INFO_W_PCT: u32 = 70;
const ROW_TOL_MAX: u32 = 6;
```

### Token Assignment — Best-Fit Overlap
```rust
fn overlap_area(cell: CellBox, w: &WordBoxPx) -> u32 {
    let ix = cell.right.min(w.right).saturating_sub(cell.x.max(w.left));
    let iy = cell.bottom.min(w.bottom).saturating_sub(cell.y.max(w.top));
    ix * iy
}
// Assign ke cell dengan overlap_area TERBESAR — bukan any-overlap
```

### Incomplete Row Merging
- Hitung mode cell count per row → `normal_col_count`
- Row dengan cell < normal → snap ke kolom terdekat berdasarkan X-boundary median
- Append ke row sebelumnya

### Banner Extraction (Header PDF)
- Anchor: token "Account" atau "Period"
- Col 1 = sebelum anchor, Col 2 = anchor+label, Col 3 = 2 token (Account) / 1 token (Period), Col 4 = sisa

### EOM Extraction (Totals)
- Anchor: "ending" atau "total" (case-insensitive)
- Token tanpa digit → label, token dengan digit sorted by X → amount/count

---

## 2. RUST PARALLEL PIPELINE

### Pilih Pola Berdasarkan Karakteristik

**Pola 1 — Flat** (satu jenis task):
```rust
items.par_iter().map(|x| process(x)).collect()
// JANGAN nested par_iter → oversubscription
// Flatten semua task ke satu level
```

**Pola 2 — Split Pool** (dua fase berbeda):
```rust
let n = available_parallelism().map(|n| n.get()).unwrap_or(4);
let render_pool  = ThreadPoolBuilder::new().num_threads(n/2).build()?;
let process_pool = ThreadPoolBuilder::new().num_threads(n-n/2).build()?;
// JANGAN build_global() → pakai build() pool lokal
// JANGAN * 2 jika ada subprocess
```

**Pola 3 — Pipeline Channel** (dua fase overlap):
```rust
let (tx, rx) = mpsc::sync_channel::<Msg>(64); // bounded = backpressure

// KRITIS: tx HARUS move ke OS thread — JANGAN Arc<Mutex<Sender>>
let render_thread = std::thread::spawn(move || {
    render_pool.install(|| {
        items.par_iter().for_each(|item| { let _ = tx.send(render(item)); });
    });
    // tx di-drop otomatis → rx.into_iter() selesai
});

let messages: Vec<Msg> = rx.into_iter().collect();
render_thread.join().ok();
let results = process_pool.install(|| messages.par_iter().map(process).collect());
```

### Deadlock Diagnosis
| Gejala | Penyebab | Fix |
|--------|----------|-----|
| Hang tidak bergerak | tx tidak di-drop (Arc masih hidup) | Move tx ke OS thread |
| Memory naik | channel() unbounded | Ganti sync_channel(N) |
| "already initialized" | build_global() dipanggil 2× | Pakai build() lokal |

### Pre-create Folders (hindari race condition)
```rust
// Buat semua folder SEBELUM par_iter dimulai
for idx in 0..n { fs::create_dir_all(dir.join(format!("pdf_{idx}")))?; }
```

---

## 3. EXCEL OUTPUT (rust_xlsxwriter)

### Format Lengkap
```rust
let rp_fmt = Format::new().set_num_format("#,##0.00").set_border(FormatBorder::Thin);
let hdr_fmt = Format::new()
    .set_bold()
    .set_background_color(Color::RGB(0x4472C4))
    .set_font_color(Color::White)
    .set_border(FormatBorder::Thin)
    .set_align(FormatAlign::Center);
let cell_fmt = Format::new().set_border(FormatBorder::Thin);
let wrap_fmt = Format::new().set_border(FormatBorder::Thin).set_text_wrap();
```

### Parse Angka Indonesia → f64
```rust
fn parse_id_number(s: &str) -> Option<f64> {
    let base = s.replace(',', "").replace('.', ",");
    let trimmed = base.trim_end();
    let clean = if trimmed.ends_with(" 0,00") { &trimmed[..trimmed.len()-5] } else { trimmed };
    clean.replace(',', ".").parse::<f64>().ok()
}
// Tulis ke cell: ws.write_number_with_format(row, col, value, &rp_fmt)?
```

### Formula dan Text Wrap
```rust
// Quote dalam format string Rust harus di-escape
let formula = format!("=IF(G{}=\"D\",F{},0)", row_1, row_1);
ws.write_formula_with_format(row, col, formula.as_str(), &rp_fmt)?; // .as_str() WAJIB

// Pipe → newline (Alt+Enter)
let wrapped = description.replace(" | ", " |\n");
ws.write_string_with_format(row, col, &wrapped, &wrap_fmt)?;
```

### Autofit
```rust
ws.autofit();
ws.set_column_width(4, 60.0)?;   // cap kolom deskripsi
ws.set_row_height(header_row, 20.0)?;
// Row height: (pipe_count + 1) * 15.0, max 150.0
```

---

## 4. MULTI-AGENT AI SYSTEM

### Arsitektur
```
USER → AR ORCHESTRATOR → dLLM CLARIFICATION LAYER → WORKER REGISTRY
                          (deteksi noise, tanya AR,       (extensible,
                           bukan perbaiki sendiri)         JSON file)
         ↓                                                    ↓
     [Mode: Planning|Execution|Consultation]      [Workers: Rust|Tester|Context|...]
```

### Communication Protocol
```json
// Orchestrator → Worker
{"task_id":"...", "type":"write_code|debug|refactor",
 "instruction":"...", "context":{"dependencies":[], "project_state":"..."}}

// Worker → Orchestrator (success)
{"task_id":"...", "status":"success", "result":
  {"code":"...", "explanation":"...", "files_modified":[], "warnings":[]}}

// Worker → Orchestrator (error)
{"task_id":"...", "status":"error", "error":
  {"error_type":"...", "message":"...", "recovery_suggestion":"..."}}
```

### Confidence Gate
```python
confidence = sum(checks.values()) / len(checks)
# confidence == 1.0 → PASS (langsung ke worker)
# confidence >= 0.7 → CLARIFY (kirim ke dLLM)
# confidence < 0.7  → REGENERATE (AR buat ulang)

checks = ["json_valid", "schema_valid", "workers_exist",
          "no_circular_deps", "logical_order", "context_consistent"]
```

### 5 Level Error Recovery
```
L1 RETRY    → timeout/network, maks 3×
L2 REPHRASE → instruksi tidak jelas → ubah lebih spesifik
L3 DECOMPOSE → gagal 3× → pecah task jadi sub-tasks
L4 ESCALATE → semua gagal → tanya user
L5 SKIP&LOG → deadline ketat → skip, catat di memory
```

### Worker Registry (Tambah Tanpa Retrain)
```python
registry["workers"]["new_worker"] = {
    "id": "new_worker",
    "description": "...",
    "capabilities": ["task_type_1", "task_type_2"],
    "status": "active"
}
save_registry(registry)
# Orchestrator baca saat startup → worker langsung tersedia
```

---

## 5. DATASET ENGINEERING (Rust Worker)

### Target & Distribusi
```
3000–5000 sampel total
40% write_code | 35% debug | 25% refactor
Format: ChatML JSONL
```

### Kategori Wajib
```
A. Ownership/Borrowing (200+ sampel) — paling penting untuk model kecil
B. Lifetimes, Traits, Generics
C. Result/Option, Error Handling (thiserror, anyhow)
D. Async/Tokio, reqwest, axum
E. serde/serde_json
F. Compiler Errors (borrow checker, move, type mismatch)
G. Idiomatic Refactor (iterator chains, match, Builder, enum vs dyn)
H. Worker JSON I/O — kritis untuk sistem multi-agent
```

### Format Sampel
```json
{"messages": [
  {"role": "system", "content": "Kamu adalah Rust AI Worker... output HARUS JSON valid."},
  {"role": "user",   "content": "{\"task_id\":\"001\",\"type\":\"write_code\",...}"},
  {"role": "assistant", "content": "{\"task_id\":\"001\",\"status\":\"success\",...}"}
]}
```

### Training Config (Unsloth)
```python
# Model: unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit
# r=16, lora_alpha=16, load_in_4bit=True
# 3 epochs, lr=2e-4, batch_size=2, grad_accum=4
# Export: GGUF Q4_K_M untuk Ollama deployment
```

### Strategi Orchestrator (BERBEDA dari Worker)
```
1. Jalankan rule-based orchestrator dulu (1-2 bulan)
2. LOG SEMUA interaksi → successful trajectories
3. Fine-tune DARI trajectories nyata (bukan synthetic)
4. Referensi: Cosine AI → 31% SWE-bench gain dari approach ini
```

---

## 6. PRINSIP SISTEM (Quick Reference)

| Prinsip | Aturan | Alasan |
|---------|--------|--------|
| PDF visual | Render dulu, analisis pixel | PDF tidak selalu punya struktur data |
| Paralel flat | 1 level, tidak nested | Nested = oversubscription |
| Channel ownership | tx MOVE ke OS thread | Arc<Mutex<tx>> = deadlock |
| Angka sebagai f64 | write_number bukan write_string | String tidak bisa dihitung Excel |
| Separation of concerns | dLLM deteksi, AR putuskan | Mencampur peran = kompleksitas O(n²) |
| Data nyata dulu | Log → fine-tune Orchestrator | Synthetic bisa ajarkan pola tidak ada |
| Structured output = kontrak | Validasi JSON sebelum kirim | Sistem multi-agent bergantung JSON valid |

---

## Edge Cases Kritis

**PDF Extraction**:
- Token di batas cell → best-fit overlap, BUKAN any-overlap
- Deskripsi panjang terpotong → incomplete row merging (snap by X)
- Halaman kedua dst → skip row_idx==1 (header berulang)
- Stray header rows → filter: contains "posting" AND "balance"

**Rust Parallel**:
- sync_channel bukan channel (backpressure)
- Pre-create folder sebelum par_iter
- build() bukan build_global()

**Excel Output**:
- Format angka: `#,##0.00` bukan `#.##0,00`
- Formula: `.as_str()` bukan `&String`
- Suffix ` 0,00` di angka → strip sebelum parse

**Dataset**:
- r# raw strings dalam Python string → bug tidak terlihat
- System prompt harus identik di semua sampel
- Cargo check kode sebelum masuk dataset
