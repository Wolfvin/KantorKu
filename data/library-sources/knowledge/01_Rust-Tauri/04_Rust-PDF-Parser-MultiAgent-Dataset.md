---
title: Rust PDF Parser Multi-Agent AI Dataset Engineering
kategori: Rust, Tauri & Desktop Development
tags: [Rust, PDF, Multi-Agent, AI, Dataset, ChatML, Parallel, Excel, dLLM, Fine-Tuning]
---

# 🗂️ SISTEM PENGETAHUAN TERPADU
## Rust PDF Extraction · Multi-Agent AI · Dataset Engineering

> Kristalisasi penuh dari seluruh session — dari kode hingga arsitektur AI.

---

# BAGIAN 1 — PETA KATEGORI

| # | Kategori | Isi Utama |
|---|----------|-----------|
| 1 | **Image-Based PDF Extraction** | Render PNG, flood fill, token assignment |
| 2 | **Rust Parallel Architecture** | Rayon, pipeline channel, thread pool |
| 3 | **Excel Output Engineering** | rust_xlsxwriter, format Rupiah, border, autofit |
| 4 | **Multi-Agent AI System** | Orchestrator, dLLM, Worker Registry |
| 5 | **Dataset Engineering** | ChatML, kategori Rust, fine-tuning pipeline |
| 6 | **Skill System** | Format .skill, universal AI compatibility |

---

# 🗂️ KATEGORI 1 — IMAGE-BASED PDF EXTRACTION

## 📌 1.1 Filosofi: Mengapa Render ke Gambar Dulu

### A. Inti Konsep
PDF tidak selalu menyimpan tabel sebagai struktur data — ia menyimpan *visual*.
Terutama laporan bank: tabel ada sebagai cell berwarna di atas background putih.
`pdftotext` langsung gagal karena tidak tahu batas kolom visual.

**Solusi**: Render PDF → PNG → analisis pixel → deteksi cell → assign teks.

### B. Mekanisme Kerja
```
PDF
 └─ pdftoppm (DPI=220) ──→ PNG per halaman
      └─ replace_white → [0,255,0] (isolasi background)
           └─ flood_fill BFS ──→ Vec<CellBox> (bounding box per cell)
                └─ group by Y ──→ Vec<Row> (baris tabel)
                     └─ filter separator ──→ baris data bersih
                          └─ pdftotext -bbox-layout ──→ WordBoxPt
                               └─ scale pt→px ──→ WordBoxPx
                                    └─ best_fit_assign ──→ Vec<Vec<String>>
                                         └─ write_to_xlsx ──→ file Excel
```

### C. Komponen Kritis

**Rendering (pdftoppm)**
- DPI 220: balance akurasi vs kecepatan. < 150 = batas cell kabur. > 300 = lambat tanpa gain.
- Output: file PNG per halaman, path prefix-nya bisa dikontrol.

**Flood Fill — Deteksi Cell**
- BFS dari setiap pixel non-hijau yang belum dikunjungi.
- Setiap connected component = satu potential cell.
- Filter: komponen < 2000 px² dibuang (noise, titik, garis tipis).
- Output: `CellBox { x, y, right, bottom }` — bounding box pixel.

```rust
const COLOR_REGION_MIN_AREA_PX: usize = 2_000;

fn detect_color_regions(img: &RgbImage) -> Vec<CellBox> {
    let mut labels = vec![0u32; (w * h) as usize];
    let mut queue = VecDeque::new();
    // BFS: kunjungi semua pixel yang terhubung dengan warna yang sama
    // Kumpulkan min/max x,y per label → CellBox
    // Filter: area < threshold → buang
}
```

**Row Grouping**
- Cluster CellBox berdasarkan Y-center dengan toleransi dinamis.
- Toleransi = `min(median_height * 0.12, median_gap / 2).clamp(2, 6)` pixel.
- Kenapa dinamis? Halaman beda bisa punya row height beda.

**Separator Filter — Dua Jenis**
```rust
const SEP_THIN_PX: u32 = 4;      // garis horizontal tipis
const SEP_INFO_H_PX: u32 = 60;   // separator info lebar
const SEP_INFO_W_PCT: u32 = 70;  // % lebar halaman

// Separator tipe 1: satu cell, tinggi ≤ 4px → garis horizontal
// Separator tipe 2: satu cell, lebar ≥ 70% halaman, tinggi ≤ 60px → divider info
```

**Token Assignment — Best-Fit Overlap**
- Masalah: token di batas dua cell → masuk ke kolom mana?
- Solusi: hitung area overlap (pixel²) dengan semua cell di row, assign ke yang terbesar.
- Bukan any-overlap — any-overlap menyebabkan double assignment.

```rust
fn overlap_area(cell: CellBox, w: &WordBoxPx) -> u32 {
    let ix = cell.right.min(w.right).saturating_sub(cell.x.max(w.left));
    let iy = cell.bottom.min(w.bottom).saturating_sub(cell.y.max(w.top));
    ix * iy
}
// Assign token ke cell dengan overlap_area terbesar — bukan pertama yang overlap
```

### D. Incomplete Row Merging

**Masalah**: Deskripsi panjang di PDF terkadang dipotong ke baris berikutnya,
menghasilkan row "pendek" (jumlah cell < normal).

**Deteksi**: Hitung mode dari jumlah cell per row → itu adalah `normal_col_count`.
Row dengan cell < normal → incomplete row.

**Solusi**: Snap token ke kolom terdekat berdasarkan X-boundary median, append ke row sebelumnya.

```rust
// Hitung normal_col_count dari mode
let normal_col_count = cell_counts.into_iter()
    .max_by_key(|(_, v)| *v)
    .map(|(k, _)| k)?;

// Snap: untuk setiap token di incomplete row,
// temukan batas kolom yang X-nya paling dekat
let snap_col = |x: u32| -> usize {
    col_boundaries.iter().enumerate()
        .min_by_key(|(_, bx)| x.abs_diff(**bx))
        .map(|(i, _)| i)
        .unwrap_or(0)
};
```

### E. Ekstraksi Khusus: Banner & EOM

**Banner** (info header di atas tabel):
- Anchor-based split: cari token "Account" atau "Period" di setiap baris.
- Col 1 = token sebelum anchor = nama perusahaan/cabang
- Col 2 = anchor tokens sampai ":" = label
- Col 3 = 2 token setelah ":" (Account) atau 1 token (Period) = nilai utama
- Col 4 = sisa = keterangan tambahan

**EOM (End of Month)** — baris total di akhir:
- Anchor: token mengandung "ending" atau "total" (case-insensitive)
- Token tanpa digit → label (col A)
- Token dengan digit, sorted by X:
  - Token terakhir = amount (col C)
  - Token kedua dari akhir = count (col B)

### F. Evaluasi Kritis

| Aspek | Detail |
|-------|--------|
| ✅ Kelebihan | Bekerja untuk PDF berformat visual apapun |
| ✅ Kelebihan | Tidak bergantung pada struktur internal PDF |
| ⚠️ Kekurangan | Lambat untuk PDF banyak halaman (rendering) |
| ⚠️ Kekurangan | Sensitif terhadap DPI — terlalu rendah = error |
| ❌ Batasan | Tidak bekerja untuk PDF yang di-scan (gambar bukan teks) |
| ❌ Batasan | Perlu pdftoppm dan pdftotext terinstall di sistem |

### G. Tools & Teknologi

| Tool | Fungsi | Notes |
|------|--------|-------|
| `pdftoppm` | Render PDF → PNG | DPI=220, bagian dari poppler-utils |
| `pdftotext -bbox-layout` | Ekstrak token + bounding box | Output XML dengan koordinat pt |
| `image` crate | Proses PNG di Rust | `RgbImage`, pixel manipulation |
| `rayon` | Paralel per-pixel processing | `par_chunks_mut(3)` untuk replace pixel |
| `rust_xlsxwriter` | Output Excel | Format, border, formula |

---

## 📌 1.2 Struktur Data Utama

```rust
// Bounding box hasil flood fill (unit: pixel)
struct CellBox { x: u32, y: u32, right: u32, bottom: u32 }

// Token dari pdftotext (unit: pixel setelah konversi)
struct WordBoxPx {
    text: String,
    left: u32, top: u32, right: u32, bottom: u32,
}

// Token dari pdftotext (unit: point — koordinat asli PDF)
struct WordBoxPt {
    text: String,
    left: f32, top: f32, right: f32, bottom: f32,
}

// Metadata dimensi halaman untuk konversi skala
struct PageWordBoxesPt {
    width_pt: f32, height_pt: f32,
    boxes: Vec<WordBoxPt>,
}

// Hasil render satu halaman
struct RenderedPage {
    page_num: u32,
    width_px: u32, height_px: u32,
    image_path: PathBuf,
}

// Hasil pemrosesan satu halaman (dikirim via channel)
struct PageResult {
    page_num: u32,
    rows: Vec<Vec<(String, u32)>>,  // (teks cell, X position)
    words: Vec<WordBoxPx>,           // semua token untuk banner/EOM
}
```

### H. Konstanta Teruji untuk BNI Statement

```rust
const RENDER_DPI: u32 = 220;
const COLOR_REGION_MIN_AREA_PX: usize = 2_000;
const SEP_THIN_PX: u32 = 4;
const SEP_INFO_H_PX: u32 = 60;
const SEP_INFO_W_PCT: u32 = 70;
const ROW_TOL_MAX: u32 = 6;
```

> **Catatan**: Untuk PDF bank lain, DPI dan threshold mungkin perlu disesuaikan.
> Mulai dari konstanta ini sebagai baseline.

---

# 🗂️ KATEGORI 2 — RUST PARALLEL ARCHITECTURE

## 📌 2.1 Tiga Pola Paralel — Pilih Berdasarkan Karakteristik Task

### A. Pola 1: Flat Work-Stealing (Satu Jenis Task Homogen)

**Kapan**: Semua task setara, tidak ada fase berbeda.

```rust
let results: Vec<Output> = items.par_iter()
    .map(|item| process(item))
    .collect();
```

**Mengapa flatten lebih baik dari nested par_iter**:
- Nested `par_iter` dalam `par_iter` = oversubscription = terlalu banyak thread aktif
- Flatten semua task ke satu level → Rayon work-stealing otomatis distribusi optimal

```rust
// BURUK: nested paralel
pdfs.par_iter().for_each(|pdf| {
    pdf.pages.par_iter().for_each(|page| process(page));
    // jika 8 core: 8 PDF × 8 pages = 64 thread aktif → contention
});

// BAGUS: flatten ke satu level
let all_pages: Vec<_> = pdfs.iter()
    .flat_map(|pdf| pdf.pages.iter().map(move |p| (pdf, p)))
    .collect();
all_pages.par_iter().for_each(|(pdf, page)| process(pdf, page));
```

### B. Pola 2: Split Thread Pool (Dua Fase Berbeda)

**Kapan**: I/O-bound phase + CPU-bound phase, tidak perlu overlap.

```rust
let n = std::thread::available_parallelism()
    .map(|n| n.get())
    .unwrap_or(4);

let render_pool = rayon::ThreadPoolBuilder::new()
    .num_threads(n / 2).build()?;     // I/O bound
let process_pool = rayon::ThreadPoolBuilder::new()
    .num_threads(n - n/2).build()?;   // CPU bound
```

**Aturan `* 2`**: JANGAN kalikan thread count untuk subprocess (pdftoppm, ffmpeg).
Subprocess berat punya CPU-nya sendiri → mengalikan hanya menambah contention.

**`build_global()` vs `build()`**:
- `build_global()` = mencemari global pool, tidak bisa di-undo, conflict jika dipanggil dua kali
- `build()` = pool lokal, scoped, bisa multiple instance → SELALU pilih ini

### C. Pola 3: Pipeline Channel (Dua Fase Overlap)

**Kapan**: Fase render dan proses bisa berjalan bersamaan (overlap waktu).

```
render_thread (OS thread)         process_pool
      │                                │
      │── render PDF 1 ──→ channel ───→│── process halaman 1
      │── render PDF 2 ──→ channel ───→│── process halaman 2
      │── render PDF 3 ──→ channel ───→│── process halaman 3
      │ (tx di-drop)                   │
      │                          rx.into_iter() selesai
```

**Implementasi Benar** (menghindari deadlock):

```rust
// KUNCI: tx harus MOVE ke OS thread, bukan dibungkus Arc<Mutex<>>
// Arc<Mutex<Sender>> → Arc masih hidup setelah thread selesai → rx tidak pernah selesai → DEADLOCK

let (tx, rx) = std::sync::mpsc::sync_channel::<PageMsg>(64);

let render_thread = std::thread::spawn(move || {
    // tx di-MOVE ke sini — di-drop otomatis saat thread selesai
    render_pool.install(|| {
        pdfs.par_iter().for_each(|pdf| {
            for page in render(pdf) {
                let _ = tx.send(page); // blocks jika buffer penuh (backpressure)
            }
        });
    });
    // tx di-drop DI SINI → rx.into_iter() akan berhenti
});

let messages: Vec<PageMsg> = rx.into_iter().collect(); // blocks sampai tx di-drop
render_thread.join().ok();

let results: Vec<Output> = process_pool.install(|| {
    messages.par_iter().map(|m| process(m)).collect()
});
```

**`sync_channel(N)` vs `channel()`**:
- `channel()` = unbounded → produsen jauh lebih cepat = memory meledak
- `sync_channel(64)` = bounded → blok produsen jika buffer penuh = backpressure natural

### D. Deadlock Diagnosis Guide

| Gejala | Penyebab | Fix |
|--------|----------|-----|
| Program hang tidak bergerak | `tx` tidak di-drop (Arc masih hidup) | Move `tx` ke OS thread tanpa Arc |
| Memory naik terus | `channel()` unbounded, produsen lebih cepat | Ganti ke `sync_channel(N)` |
| CPU idle padahal ada data | Thread pool tidak di-install dengan benar | Pastikan `pool.install(|| ...)` |
| "already initialized" warning | `build_global()` dipanggil dua kali | Ganti ke `build()` pool lokal |

### E. Race Condition: Pre-create Subfolder

```rust
// Jika tiap thread butuh folder sendiri, buat SEMUA sebelum paralel dimulai
// Jangan buat folder di dalam par_iter — mkdir race condition!

for idx in 0..pdf_paths.len() {
    std::fs::create_dir_all(temp_dir.join(format!("pdf_{idx}")))?;
}
// Baru paralel
pdf_paths.par_iter().enumerate().for_each(|(idx, pdf)| {
    let dir = temp_dir.join(format!("pdf_{idx}"));
    // dir sudah pasti ada
});
```

### F. Kapan Tidak Perlu Paralel

```
Task < 1ms → overhead paralel > keuntungan → gunakan sequential
Contoh: extract_banner(~20 token), extract_eom(~10 token)

// TIDAK PERLU rayon::join untuk ini:
let banner = extract_banner(words);  // sequential, cukup
let eom    = extract_eom(words);
```

---

# 🗂️ KATEGORI 3 — EXCEL OUTPUT ENGINEERING

## 📌 3.1 Format Numerik Indonesia

**Masalah**: Format angka berbeda antara PDF (bisa English: 514,227.00) dan
kebutuhan output (Indonesia: 514.227,00 atau Excel universal: #,##0.00).

### Konversi: String PDF → f64 → Excel

```rust
fn parse_id_number(s: &str) -> Option<f64> {
    // Input dari PDF bisa: "514,227.00" atau "514227,00" atau "514.227,00 0,00"
    
    // Step 1: hapus titik ribuan (jika English format) atau koma ribuan
    let no_thousands = s.replace(',', "").replace('.', ",");
    
    // Step 2: hapus suffix " 0,00" yang muncul dari double-parse PDF
    let trimmed = no_thousands.trim_end();
    let clean = if trimmed.ends_with(" 0,00") {
        trimmed[..trimmed.len() - 5].trim_end()
    } else {
        trimmed
    };
    
    // Step 3: konversi ke f64 (ganti koma desimal → titik)
    clean.replace(',', ".").parse::<f64>().ok()
}

// Di Excel, tulis sebagai numeric bukan string
ws.write_number_with_format(row, col, value, &rp_format)?;
```

**Format Excel Universal**: `#,##0.00`
- JANGAN pakai `#.##0,00` — bergantung locale Windows, bisa salah di beberapa sistem
- `#,##0.00` adalah format Excel standar internasional yang diterjemahkan otomatis

### Semua Format yang Digunakan

```rust
// Format angka Rupiah
let rp_format = Format::new()
    .set_num_format("#,##0.00")
    .set_border(FormatBorder::Thin);

// Header tabel: biru bold putih
let header_fmt = Format::new()
    .set_bold()
    .set_background_color(Color::RGB(0x4472C4))  // Microsoft blue
    .set_font_color(Color::White)
    .set_border(FormatBorder::Thin)
    .set_align(FormatAlign::Center);

// Cell data biasa dengan border
let cell_fmt = Format::new()
    .set_border(FormatBorder::Thin);

// Cell deskripsi dengan text wrap
let wrap_fmt = Format::new()
    .set_border(FormatBorder::Thin)
    .set_text_wrap();
```

## 📌 3.2 Formula, Text Wrap, dan Autofit

### Formula dengan Escape yang Benar

```rust
// PENTING: escape quote dalam format string Rust
let formula = format!("=IF(G{}=\"D\",F{},0)", row_1based, row_1based);

// PENTING: pakai .as_str() bukan &String — API tidak accept &String
ws.write_formula_with_format(row, col, formula.as_str(), &rp_format)?;
```

### Pipe → Newline (Alt+Enter dalam Cell)

```rust
fn pipe_wrap(s: &str) -> String {
    s.replace(" | ", " |\n")  // \n dalam cell = Alt+Enter dengan text wrap
}

ws.write_string_with_format(row, col, &pipe_wrap(description), &wrap_fmt)?;
```

### Autofit dan Row Height

```rust
ws.autofit();                          // autofit semua kolom
ws.set_column_width(4, 60.0)?;        // cap kolom deskripsi (E) di 60 char

// Row height berdasarkan jumlah newline
let pipe_count = desc.matches(" | ").count() as f64;
let height = ((pipe_count + 1.0) * 15.0).min(150.0);
if pipe_count > 0.0 {
    ws.set_row_height(data_row, height)?;
}
ws.set_row_height(header_row, 20.0)?;  // header sedikit lebih tinggi
```

## 📌 3.3 Struktur Output Excel (Urutan Penulisan)

```
[Banner rows]          ← info rekening di atas tabel
[blank row]
[Header row]           ← Posting Date | Eff Date | Branch | ... | Balance
[Data rows]            ← satu row per transaksi
[blank row]
[EOM rows]             ← Ending Balance, Total Debet, Total Kredit
```

**10 Kolom Final untuk BNI Statement**:

| Col | Header | Tipe | Formula/Format |
|-----|--------|------|----------------|
| A | Posting Date | String | — |
| B | Effective Date | String | — |
| C | Branch | String | — |
| D | Journal | String | — |
| E | Transaction Description | String | pipe→newline, wrap |
| F | Amount | Numeric | #,##0.00 |
| G | DB/CR | String | "D" atau "K" |
| H | Debit | Formula | =IF(G{n}="D",F{n},0) |
| I | Credit | Formula | =IF(G{n}="K",F{n},0) |
| J | Balance | Numeric | #,##0.00 |

---

# 🗂️ KATEGORI 4 — MULTI-AGENT AI SYSTEM

## 📌 4.1 Arsitektur Sistem

### A. Visi dan Filosofi

Sistem autonomous coding yang terdiri dari AI khusus dengan peran berbeda:

```
USER
  │ goal/visi
  ▼
AR ORCHESTRATOR  ← otak, reasoning, planning, deciding
  │ output plan (JSON)
  ▼
dLLM CLARIFICATION LAYER  ← sekretaris, deteksi noise, tanya sebelum kirim
  │ plan terverifikasi
  ▼
WORKER REGISTRY  ← katalog kemampuan, extensible
  │
  ├── Rust Worker    ← spesialis kode Rust
  ├── Tester Worker  ← unit test, integration test
  ├── Context Worker ← baca file, check deps, project state
  └── [Worker Baru]  ← tambah kapan saja tanpa retrain
```

**Lima Prinsip Inti**:
1. AR = otak (reasoning kuat, kadang ceroboh)
2. dLLM = sekretaris (deteksi noise, TANYA sebelum kirim — bukan perbaiki sendiri)
3. Workers = spesialis (hanya kerjakan domain-nya)
4. Registry = extensible (tambah worker tanpa retrain Orchestrator)
5. Memory = persisten (Orchestrator tidak amnesia antar session)

### B. AR Orchestrator — Tiga Mode Operasi

**MODE 1 — PLANNING** (menerima goal baru dari user):
- Tanya clarifying questions
- Buat project plan (JSON)
- Decompose ke tasks
- Assign ke workers via registry

**MODE 2 — EXECUTION** (task sedang berjalan):
- Kirim task ke worker
- Evaluasi hasil worker
- Putuskan langkah berikutnya
- Handle worker gagal (recovery)

**MODE 3 — CONSULTATION** (dipanggil dLLM):
- Terima pertanyaan dari dLLM
- Jawab dengan tepat
- dLLM finalize berdasarkan jawaban

**Model Rekomendasi**:
- Produksi: Qwen2.5 32B atau Llama 3.1 70B
- Development: Qwen2.5 14B
- Minimum/PoC: Qwen2.5 7B

## 📌 4.2 dLLM Clarification Layer

### A. Inti Konsep

dLLM (Diffusion Language Model) bukan autonomous corrector — ia adalah **detektor noise**.

```
dLLM TIDAK:                      dLLM MELAKUKAN:
─────────────────────────────────────────────────────
✗ Perbaiki error sendiri         ✓ Deteksi token/bagian noisy
✗ Buat keputusan baru            ✓ Tanya Orchestrator: "ini maksudnya?"
✗ Override keputusan AR          ✓ Finalize output sesuai jawaban AR
✗ Autonomous reasoning           ✓ Structural/syntactic validation
```

### B. Jenis Noise yang Dideteksi

**1. JSON Structural Noise**
- Malformed JSON, bracket tidak tutup, koma berlebih
- Field yang hilang / tidak sesuai schema
- Type mismatch

**2. Semantic Noise**
- Worker assignment ambigu
- Task dependencies circular
- Logical ordering salah (deploy sebelum build)

**3. Registry Noise**
- Worker ID tidak ada di registry
- Capability mismatch
- Worker status inactive tapi di-assign

**4. Context Noise**
- Referensi ke file yang belum dibuat
- Dependency ke task yang belum selesai
- Konflik dengan keputusan di memory

### C. Confidence Gate

```python
def confidence_gate(ar_output, registry, memory):
    checks = {
        "json_valid":         validate_json(ar_output),
        "schema_valid":       validate_schema(ar_output),
        "workers_exist":      check_worker_registry(ar_output, registry),
        "no_circular_deps":   check_dependencies(ar_output),
        "logical_order":      check_task_order(ar_output),
        "context_consistent": check_memory_consistency(ar_output, memory),
    }
    confidence = sum(checks.values()) / len(checks)

    if confidence == 1.0:  return "PASS"       # langsung ke worker
    if confidence >= 0.7:  return "CLARIFY"    # kirim ke dLLM
    return "REGENERATE"                         # terlalu banyak error, AR ulang
```

### D. Alur Clarification

```
AR generate plan → dLLM terima sebagai "noisy sequence"
  │
  ├─ Semua token confident? → YES → finalize (skip query)
  │
  └─ Ada noise?
       └─ Flag posisi bermasalah
       └─ Formulasi pertanyaan ke AR:
          "task_3 worker assignment ambigu — rust_worker atau tester_worker?"
               ↓
          AR jawab dengan reasoning
               ↓
          dLLM finalize berdasarkan jawaban
```

### E. Riset Pendukung (2025-2026)

| Paper | Speedup | Metode |
|-------|---------|--------|
| FailFast (Des 2025) | 4.9× | dLLM drafter + AR verifier |
| DEER (Des 2025) | 5.54× | dLLM draft → AR verify |
| TiDAR/NVIDIA (Nov 2025) | 5.91× | Hybrid AR+diffusion backbone |
| ReFusion (Des 2025) | 18× | AR+diffusion, 34% perf gain |
| Spiffy (Sep 2025) | 2.8–3.1× | lossless dLLM acceleration |

**Model dLLM yang Direkomendasikan** (2026):
- Terbaik: Open-dCoder (pengzhangzhi/Open-dLLM)
- Alternatif: LLaDA-8B, Dream-7B
- Update model setiap 3 bulan (teknologi berkembang cepat)

## 📌 4.3 Worker Registry — Sistem Extensible

### A. Format Registry JSON

```json
{
  "registry_version": "1.0",
  "last_updated": "2026-03-10",
  "workers": {
    "rust_worker": {
      "id": "rust_worker",
      "version": "1.0",
      "description": "Spesialis Rust coding — write, debug, refactor",
      "capabilities": ["write_code", "debug", "refactor"],
      "supported_task_types": ["write_code", "debug", "refactor"],
      "input_schema": {
        "type": "object",
        "required": ["task_id", "type", "instruction", "context"]
      },
      "output_schema": {
        "type": "object",
        "required": ["task_id", "status", "result"]
      },
      "model": "qwen2.5-coder-7b-finetuned",
      "timeout_seconds": 60,
      "status": "active"
    }
  }
}
```

### B. Cara Tambah Worker Tanpa Retrain

```python
# Hanya tambah entry di JSON — Orchestrator baca saat startup
new_worker = {
    "id": "docs_worker",
    "description": "Spesialis dokumentasi Rust — write_docs, generate_readme",
    "capabilities": ["write_docs", "generate_readme"],
    "status": "active"
}
registry["workers"]["docs_worker"] = new_worker
save_registry(registry)
# Selesai! Worker langsung tersedia
```

### C. Communication Protocol (Universal JSON)

**Orchestrator → Worker**:
```json
{
  "message_id": "msg_001",
  "from": "orchestrator",
  "to": "rust_worker",
  "task": {
    "id": "task_001",
    "type": "write_code",
    "priority": "high",
    "instruction": "Buat async HTTP GET function",
    "context": {
      "project_state": "...",
      "relevant_files": ["src/main.rs"],
      "dependencies": ["reqwest", "tokio"]
    },
    "timeout_seconds": 60
  }
}
```

**Worker → Orchestrator**:
```json
{
  "from": "rust_worker",
  "task_id": "task_001",
  "status": "success",
  "result": {
    "code": "async fn fetch(url: &str) -> Result<String, reqwest::Error> { ... }",
    "explanation": "Fungsi async dengan error handling",
    "files_modified": ["src/http.rs"],
    "warnings": ["Tambahkan #[tokio::main] di main"]
  }
}
```

## 📌 4.4 Error Recovery Strategy (5 Level)

```
Level 1 — RETRY       : Timeout/network error → kirim ulang, maks 3×
Level 2 — REPHRASE    : Worker butuh klarifikasi → ubah instruksi lebih spesifik
Level 3 — DECOMPOSE   : Gagal 3× → pecah task jadi sub-tasks lebih kecil
Level 4 — ESCALATE    : Semua gagal → tanya user: "aku stuck di X, butuh inputmu"
Level 5 — SKIP & LOG  : User minta lanjut → skip, catat di memory, kembali nanti
```

**Undo Strategy**:
- Sebelum setiap action: snapshot state
- Simpan di undo stack
- Yang bisa di-undo: file writes, code changes, config updates
- Yang tidak bisa: external API calls, production deployments

## 📌 4.5 Memory System (3 Layer)

| Layer | Storage | Isi | Persisten? |
|-------|---------|-----|------------|
| Short-term | Context Window | Percakapan aktif | Tidak (per session) |
| Long-term | Supabase/PostgreSQL | Project decisions, error history | Ya |
| Project | File System | Kode, tests, Cargo.toml, git | Ya |

---

# 🗂️ KATEGORI 5 — DATASET ENGINEERING

## 📌 5.1 Dataset untuk Rust Worker

### A. Target dan Distribusi

```
Target: 3000–5000 sampel
Format: ChatML JSONL

Distribusi:
├── 40% — Write code dari spesifikasi (1500–2000 sampel)
├── 35% — Debug & fix compiler error (1050–1750 sampel)
└── 25% — Refactor ke idiomatic Rust (750–1250 sampel)

Sumber:
├── 60% — Synthetic generation (AI-assisted)
├── 30% — GitHub scraping (tokio, serde, axum, clap, rayon)
└── 10% — Manual / curated
```

### B. Kategori Wajib (Checklist)

**A. Konsep Dasar Rust** (sangat penting untuk model kecil)
- Ownership & borrowing — wajib 200+ sampel
- Lifetimes
- Traits & generics
- Result & Option (error handling)
- Pattern matching

**B. Kode Praktis**
- Async/await dengan Tokio
- HTTP (reqwest, axum)
- Serialization (serde, serde_json)
- CLI (clap)
- File I/O, JSONL reader/writer

**C. Compiler Errors (debug category)**
- Borrow checker errors (paling umum, prioritaskan)
- Lifetime errors
- Type mismatch
- Missing trait implementations
- Move/copy semantics errors

**D. Idiomatic Rust (refactor category)**
- Manual loop → iterator chains
- Nested match → Option methods
- unwrap() → proper Result
- if-else chain → match + range patterns
- Constructor banyak parameter → Builder pattern
- Vec<Box<dyn Trait>> → enum untuk closed types

**E. Worker-Specific JSON I/O** (kritis untuk sistem multi-agent)
- Terima JSON task → parse → execute → return JSON
- Error response JSON yang konsisten
- Validasi output sebelum dikirim
- compile-check kode yang digenerate

### C. Format ChatML (Standar)

```json
{
  "messages": [
    {
      "role": "system",
      "content": "Kamu adalah Rust AI Worker dalam sistem multi-agent. Tugasmu: terima task JSON dari Orchestrator, kerjakan, dan selalu kembalikan response JSON yang valid. Jangan tambahkan teks di luar JSON."
    },
    {
      "role": "user",
      "content": "{\"task_id\":\"001\",\"type\":\"write_code\",\"instruction\":\"Buat async HTTP GET\",\"context\":{\"dependencies\":[\"reqwest\",\"tokio\"]}}"
    },
    {
      "role": "assistant",
      "content": "{\"task_id\":\"001\",\"status\":\"success\",\"result\":{\"code\":\"...\",\"explanation\":\"...\",\"files_modified\":[],\"warnings\":[]}}"
    }
  ]
}
```

**Prinsip system prompt**: Jelas bahwa output HARUS JSON valid. "Jangan tambahkan teks di luar JSON" adalah instruksi kritis untuk structured output.

### D. JSON Schema Output Worker (Standar)

```json
// Success response
{
  "task_id": "string",
  "status": "success",
  "result": {
    "code": "string",
    "explanation": "string",
    "files_modified": ["string"],
    "warnings": ["string"]
  }
}

// Error response
{
  "task_id": "string",
  "status": "error",
  "error": {
    "error_type": "string",
    "message": "string",
    "recovery_suggestion": "string"
  }
}

// Debug response
{
  "task_id": "string",
  "status": "success",
  "result": {
    "error_type": "string",
    "original_code": "string",
    "fixed_code": "string",
    "explanation": "string",
    "warnings": ["string"]
  }
}

// Refactor response
{
  "task_id": "string",
  "status": "success",
  "result": {
    "original_code": "string",
    "refactored_code": "string",
    "changes": ["string"],
    "explanation": "string"
  }
}
```

## 📌 5.2 Training Pipeline

### A. Stack Training

| Komponen | Tools | Notes |
|----------|-------|-------|
| Fine-tuning AR | Unsloth + TRL SFTTrainer | QLoRA/DoRA |
| Model base | Qwen2.5-Coder-7B-Instruct-bnb-4bit | 6GB VRAM dengan 4-bit |
| Training dLLM | Open-dLLM | MDM objective, bukan QLoRA biasa |
| Serving produksi | vLLM | Throughput tinggi |
| Testing lokal | Ollama (GGUF Q4_K_M) | Deployment ringan |

### B. Konfigurasi Unsloth (Rust Worker)

```python
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit",
    max_seq_length=4096,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    lora_alpha=16,
    lora_dropout=0,
    target_modules=["q_proj", "k_proj", "v_proj", "up_proj", "down_proj"],
    use_dora=False,  # True untuk DoRA (lebih baik, +2GB VRAM)
)

# Training args
args = TrainingArguments(
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    num_train_epochs=3,
    learning_rate=2e-4,
    fp16=True,
    output_dir="rust-worker-output",
    logging_steps=10,
    save_steps=100,
)
```

### C. Strategi Dataset Orchestrator

**JANGAN fine-tune dari synthetic data pertama!**

```
Fase 1 (bulan 1-2): Rule-based Orchestrator
  → Log SEMUA interaksi (input, keputusan, output, hasil)
  → Target: 500-1000 successful trajectories

Fase 2 (bulan 3): Format trajectories ke ChatML
  → Filter: ambil hanya yang sukses
  → Augmentasi dengan synthetic variations

Fase 3 (bulan 3-4): Fine-tune dari real trajectories
  → Base: Qwen2.5 32B
  → Evaluasi: SWE-bench style benchmark

Fase 4 (bulan 5+, opsional): GRPO/RLHF
  → Reward: task sukses? kode compile? assignment benar?
```

**Referensi nyata — Cosine AI (2025)**:
- Fine-tune dari successful trajectories → 31% peningkatan SWE-bench
- 3× latency improvement, 60% reduction GPU footprint

### D. Format Trajectory Orchestrator

```json
{
  "messages": [
    {"role": "system", "content": "Kamu adalah Orchestrator..."},
    {"role": "user", "content": "Buat todo app REST API"},
    {"role": "assistant", "content": "{\"clarifying_questions\": [...]}"},
    {"role": "user", "content": "Ya butuh auth JWT, pakai PostgreSQL"},
    {"role": "assistant", "content": "{\"project_plan\": {\"tasks\": [...]}}"},
    {"role": "tool", "content": "{\"task_id\":\"1\",\"status\":\"success\",...}"},
    {"role": "assistant", "content": "{\"next_action\": \"assign_task_2\",...}"}
  ]
}
```

## 📌 5.3 Checklist Kualitas Dataset

```
Sebelum Training:
□ Format ChatML JSONL (bukan Alpaca, bukan ShareGPT)?
□ Minimal 500 sampel (target 3000+)?
□ Kode Rust sudah divalidasi bisa compile?
□ JSON output format konsisten?
□ System prompt jelas tentang structured output?
□ Train/val split 90/10?
□ No r# raw strings atau karakter escape aneh di Python generator?

Saat Training:
□ Monitor: train loss turun?
□ Monitor: val loss tidak naik (overfit)?
□ Save checkpoint setiap 100 steps?

Setelah Training:
□ Test: output SELALU valid JSON?
□ Test: kode Rust bisa dikompilasi?
□ Test: instruksi dari Orchestrator diikuti?
□ Export ke GGUF (Q4_K_M) untuk Ollama?
□ A/B test vs base model?
```

---

# 🗂️ KATEGORI 6 — SKILL SYSTEM

## 📌 6.1 Format .skill — Standar Universal

### A. Struktur File

```
nama-skill/
├── SKILL.md              ← Wajib: instruksi utama
├── scripts/              ← Opsional: script deterministic
├── references/           ← Opsional: docs panjang
└── assets/               ← Opsional: template, data
```

File `.skill` = ZIP dari folder tersebut. Buat dengan:
```bash
python scripts/package-skill.py ./nama-skill
```

### B. Frontmatter Standar

```yaml
---
name: nama-skill          # lowercase, hyphens, max 64 char
description: |
  [APA yang dilakukan — spesifik]
  [KAPAN trigger — 8-10 kata kunci yang user akan tulis]
  [Max 1024 karakter total]
license: Apache-2.0
metadata:
  author: nama-author
  version: "1.0"
---
```

### C. Description yang Bagus vs Buruk

```
❌ Buruk:  "Membantu dengan Rust"
✅ Bagus:  "Spesialis Rust coding untuk sistem multi-agent. Terima task JSON dari
           Orchestrator, generate kode Rust, debug compiler error, refactor ke
           idiomatic. Trigger: rust worker, write code, fix error, refactor rust,
           borrow checker, async tokio, serde json, clippy."
```

### D. Kompatibilitas Open-Source

Paste body SKILL.md sebagai system prompt — selesai.

```python
def load_skill_body(skill_path: str) -> str:
    with open(f"{skill_path}/SKILL.md") as f:
        content = f.read()
    if content.startswith("---"):
        parts = content.split("---", 2)
        return parts[2].strip() if len(parts) >= 3 else content
    return content

# Pakai dengan Ollama (OpenAI-compatible API)
import openai
client = openai.OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
response = client.chat.completions.create(
    model="qwen2.5-coder:7b",
    messages=[
        {"role": "system", "content": load_skill_body("./rust-worker")},
        {"role": "user", "content": task_json}
    ]
)
```

**Kompatibilitas Model**:

| Model | Ukuran | Ikuti Skill | Rekomendasi |
|-------|--------|-------------|-------------|
| Qwen2.5 7B | 7B | ✅ Sangat bagus | Terbaik untuk skill following |
| Llama 3.1 8B | 8B | ✅ Bagus | Reliable |
| Mistral 7B | 7B | ✅ Bagus | Strong instruction |
| Phi-3.5 Mini | 3.8B | ⚠️ OK | Skill harus simpel |
| Gemma 2 2B | 2B | ⚠️ Terbatas | 1-2 langkah saja |

---

# 🗂️ SINTESIS PENGETAHUAN

## Prinsip Utama (Core Principles)

### P1: Visual-First untuk PDF Berformat Visual
Jangan asumsi PDF punya struktur data. Render dulu, analisis pixel, ekstrak struktur.
Ini berlaku untuk semua dokumen yang tampilannya adalah konten (bukan kontennya adalah tampilan).

### P2: Paralel Hanya Satu Level
Nested paralel = kontradiksi diri. Flatten semua task ke satu level dan biarkan
work-stealing yang urus distribusi. Jika dua fase berbeda, beri pool terpisah.

### P3: Channel Ownership adalah Kunci
Di Rust, channel selesai ketika Sender di-drop. Jika Sender dibungkus Arc,
ia tidak pernah di-drop → rx tidak pernah selesai → deadlock.
**Aturan**: Sender selalu move ke OS thread, tidak pernah ke Arc.

### P4: Numerik sebagai Numerik
Data keuangan di Excel harus `f64`, bukan string. `write_number_with_format` bukan
`write_string`. String tidak bisa dihitung, tidak bisa diformat, tidak bisa difilter.

### P5: Separation of Concerns di Multi-Agent
Setiap agent punya satu tanggung jawab. dLLM bukan corrector — ia detektor.
Worker bukan planner — ia executor. Orchestrator bukan coder — ia coordinator.
Mencampur peran = kompleksitas quadratik.

### P6: Data Nyata Lebih Baik dari Synthetic
Untuk Orchestrator: log dari rule-based system adalah gold standard.
Synthetic data bisa melatih pola yang tidak ada di production.
Collect data nyata dulu, fine-tune kemudian.

### P7: Structured Output adalah Kontrak
Sistem multi-agent bergantung pada JSON yang valid. System prompt harus eksplisit.
Validasi output sebelum kirim. Fallback ke error JSON jika serialization gagal.
Tidak ada "partial JSON" — either valid atau error.

## Pola Berulang (Patterns)

**Pola A — Confidence Gate**:
Sebelum setiap tahap yang mahal, ada gate yang mengecek kualitas input.
Jika tidak lolos → feedback ke upstream, bukan terusan ke downstream.
Berlaku: dLLM gate, compile-check sebelum return, validasi JSON sebelum kirim.

**Pola B — Anchor-Based Extraction**:
Untuk teks tidak terstruktur, cari token "anchor" yang stabil (kata kunci, separator).
Split berdasarkan anchor. Token sebelum = konteks, setelah = nilai.
Berlaku: banner extraction (Account/Period), EOM extraction (ending/total).

**Pola C — Mode-Based Normalization**:
Untuk menentukan "normal" dalam data yang variatif, gunakan mode (nilai paling sering muncul).
Berlaku: normal_col_count dari mode cell count per row.

**Pola D — Defensive Output**:
Selalu sediakan fallback jika operasi utama gagal.
Berlaku: `unwrap_or_else(|| fallback_json)` pada serialization,
`compile_check` sebelum return kode, `validate_output` sebelum kirim ke Orchestrator.

**Pola E — Registry-Driven Extensibility**:
Tambah kemampuan baru via data (registry JSON), bukan via kode.
Berlaku: Worker Registry, SKILL.md yang dibaca runtime, tool catalog di agent.

## Insight Penting (Takeaways)

1. **DPI 220 adalah sweet spot** untuk PDF bank — terlalu rendah = border kabur,
   terlalu tinggi = lambat tanpa benefit nyata.

2. **Best-fit overlap area** lebih robust dari any-overlap untuk token assignment.
   Any-overlap dengan distribusi seragam bisa 2× salah di batas cell.

3. **sync_channel(64) bukan channel()** — backpressure alami mencegah memory meledak.

4. **dLLM training berbeda** — bukan QLoRA biasa, gunakan MDM (Masked Diffusion Model)
   objective via Open-dLLM framework.

5. **Qwen2.5-Coder** terbaik untuk fine-tuning Rust worker di hardware terbatas.
   Outperform CodeLlama di instruction following dan structured output.

6. **`#,##0.00` adalah format angka universal Excel** — tidak bergantung locale.
   `#.##0,00` adalah locale-specific dan bisa salah.

7. **Skills bisa di-compose** — satu agent bisa load multiple skills,
   dan skill bisa reference skill lain via path.

---

# 🗂️ FRAMEWORK PRAKTIS

## Framework 1: PDF Table Extraction Pipeline

```
STEP 1: Assess PDF
  → Buka PDF manual, lihat: apakah tabel punya cell berwarna?
  → YES: gunakan image-based pipeline
  → NO: coba pdftotext langsung dengan layout flag

STEP 2: Configure Constants
  → Mulai dari: DPI=220, MIN_AREA=2000, SEP_THIN=4, SEP_INFO_H=60, ROW_TOL=6
  → Test pada 1-2 halaman sample
  → Adjust jika: cell tidak terdeteksi (kurangi MIN_AREA), row tergabung (kurangi ROW_TOL)

STEP 3: Build & Test Pipeline
  render → replace_bg → flood_fill → group_rows → filter_sep
  → Test: print jumlah cell per row, bandingkan dengan visual PDF

STEP 4: Add Text Assignment  
  pdftotext -bbox-layout → parse XML → scale pt→px → best_fit_assign
  → Test: print text per cell, bandingkan dengan visual PDF

STEP 5: Handle Edge Cases
  → Incomplete rows (append ke row sebelumnya)
  → Stray header rows (filter: contains "posting" + "balance")
  → Multi-page (skip row_idx==0 semua halaman, skip row_idx==1 untuk halaman > 0)

STEP 6: Output Excel
  → Tulis numerik sebagai f64, bukan string
  → Tambah formula Debit/Credit
  → Autofit + row height berdasarkan newline count
```

## Framework 2: Rust Parallel Pipeline

```
STEP 1: Identifikasi Fase
  → Satu jenis task? → Pola 1 (flat par_iter)
  → Dua fase berbeda tapi tidak overlap? → Pola 2 (split pool)
  → Dua fase bisa overlap? → Pola 3 (pipeline channel)

STEP 2: Hitung Thread
  → n = available_parallelism().unwrap_or(4)
  → Jangan * 2 jika ada subprocess
  → Pola 2/3: render_threads = n/2, process_threads = n - n/2

STEP 3: Build Pools (bukan build_global)
  → render_pool = ThreadPoolBuilder::new().num_threads(render_threads).build()?
  → process_pool = ThreadPoolBuilder::new().num_threads(process_threads).build()?

STEP 4: Pipeline Channel Setup (hanya Pola 3)
  → (tx, rx) = mpsc::sync_channel(64)  // bounded!
  → spawn OS thread, MOVE tx ke dalamnya
  → render_pool.install di dalam OS thread
  → rx.into_iter().collect() setelah spawn

STEP 5: Pre-create Folders
  → Buat semua folder output SEBELUM paralel dimulai
  → mkdir di dalam par_iter = race condition

STEP 6: Error Collection
  → Arc<Mutex<Vec<Error>>> untuk collect errors dari threads
  → Propagate setelah join
```

## Framework 3: Multi-Agent AI System Build

```
FASE 1 — Fondasi (Minggu 1-2)
  □ Finalize JSON communication protocol
  □ Buat Worker Registry (JSON file)
  □ Buat rule-based Orchestrator (Python, no AI)
  □ Implementasi Memory system (Supabase)
  □ Buat Confidence Gate (rule-based)
  □ LOG SEMUA INTERAKSI ← penting untuk Fase 4

FASE 2 — Workers (Minggu 3-6)
  □ Kumpulkan dataset Rust Worker (500 sampel seed)
  □ Expand ke 3000+ sampel (synthetic + scraping)
  □ Fine-tune Rust Worker dengan QLoRA (Unsloth)
  □ Evaluasi: compile rate > 85%, JSON valid > 99%
  □ Buat Context Worker (rule-based, baca file system)
  □ Buat Tester Worker (fine-tune atau rule-based)

FASE 3 — dLLM Layer (Minggu 7-9)
  □ Setup Open-dLLM
  □ Buat noise detection pipeline
  □ Implementasi clarification protocol
  □ Test: persentase false positive/negative dLLM

FASE 4 — Orchestrator AI (Minggu 10-14)
  □ Kumpulkan 500+ successful trajectories dari log
  □ Format ke ChatML trajectory format
  □ Fine-tune Orchestrator dengan QLoRA
  □ A/B test: rule-based vs AI orchestrator

FASE 5 — Production
  □ Monitoring: Netdata (GPU/CPU/memory)
  □ Training metrics: W&B
  □ Database: Supabase + Prisma
  □ Retrain pipeline: mingguan/bulanan
```

## Framework 4: Dataset Generation untuk Rust Worker

```
STEP 1: Seed Dataset
  → Buat 50-100 sampel manual berkualitas tinggi
  → Cover semua 5 kategori wajib
  → Pastikan: compile-valid, JSON-valid, instructive

STEP 2: Expand via Templating
  → Setiap sampel seed = template
  → Variasi: ganti tipe data, nama variabel, konteks task
  → Target: 10× expansion dari seed

STEP 3: Quality Filter
  □ JSON parse valid?
  □ Kode Rust valid secara sintaks (cargo check)?
  □ System prompt konsisten di semua sampel?
  □ Output selalu JSON (tidak ada prose di luar JSON)?

STEP 4: Balance Check
  → 40% write_code, 35% debug, 25% refactor
  → Dalam write_code: 30% basic, 30% async, 20% error handling, 20% workers

STEP 5: Split & Export
  → 90% train.jsonl, 10% val.jsonl
  → Validate dengan: python -c "import json; [json.loads(l) for l in open('train.jsonl')]"

STEP 6: Training
  → Unsloth + Qwen2.5-Coder-7B + QLoRA
  → r=16, lora_alpha=16, 3 epochs, lr=2e-4
  → Monitor: train_loss dan val_loss per epoch
```

---

# 🗂️ OUTPUT ARTEFAK

## Artefak A: System Prompt — Rust AI Worker

```
Kamu adalah Rust AI Worker dalam sistem multi-agent coding otomatis.

PERAN: Spesialis eksekusi kode Rust. Terima task dari Orchestrator, kerjakan, return hasil.

ATURAN MUTLAK:
1. Output SELALU JSON valid — tidak ada teks di luar JSON
2. Format output sesuai schema yang ditentukan
3. Jika tidak bisa kerjakan task, return error JSON (bukan prose)
4. Kode Rust harus idiomatic dan compile-valid

SCHEMA OUTPUT SUCCESS:
{"task_id":"...", "status":"success", "result":{"code":"...", "explanation":"...", "files_modified":[], "warnings":[]}}

SCHEMA OUTPUT ERROR:
{"task_id":"...", "status":"error", "error":{"error_type":"...", "message":"...", "recovery_suggestion":"..."}}

TIPE TASK:
- write_code: Generate kode Rust sesuai instruksi dan dependencies
- debug: Fix compiler error — identifikasi root cause, berikan fixed_code
- refactor: Ubah non-idiomatic Rust menjadi idiomatic

KUALITAS KODE:
- Gunakan ? operator, bukan unwrap() di production code
- Prefer iterator chains daripada manual loops
- Gunakan thiserror atau anyhow untuk error types
- Annotasi lifetime hanya jika diperlukan compiler
- Derive traits yang relevan (Debug, Clone, Serialize, Deserialize)
```

## Artefak B: Confidence Gate Python

```python
import json
from typing import Dict, Any

def confidence_gate(
    ar_output: str,
    registry: Dict,
    memory: Dict,
    schema: Dict
) -> tuple[str, list[str]]:
    """
    Gate antara AR Orchestrator output dan worker execution.
    Returns: ("PASS"|"CLARIFY"|"REGENERATE", list_of_issues)
    """
    issues = []
    
    # Check 1: JSON valid
    try:
        plan = json.loads(ar_output)
    except json.JSONDecodeError as e:
        return "REGENERATE", [f"Invalid JSON: {e}"]
    
    # Check 2: Schema valid
    required_fields = schema.get("required", [])
    for field in required_fields:
        if field not in plan:
            issues.append(f"Missing field: {field}")
    
    # Check 3: Workers exist in registry
    for task in plan.get("tasks", []):
        worker_id = task.get("worker")
        if worker_id and worker_id not in registry.get("workers", {}):
            issues.append(f"Unknown worker: {worker_id}")
        
        # Check 4: Capability match
        if worker_id in registry.get("workers", {}):
            worker = registry["workers"][worker_id]
            task_type = task.get("type")
            caps = worker.get("supported_task_types", [])
            if task_type and task_type not in caps:
                issues.append(f"Worker {worker_id} doesn't support {task_type}")
    
    # Check 5: No circular dependencies
    tasks = {t["id"]: t.get("depends_on", []) for t in plan.get("tasks", [])}
    if _has_cycle(tasks):
        issues.append("Circular task dependencies detected")
    
    # Check 6: Logical order (basic: deploy after build)
    if _violates_order(plan.get("tasks", [])):
        issues.append("Task ordering violates logical constraints")
    
    # Decision
    confidence = 1.0 - (len(issues) / max(6, len(issues) + 1))
    
    if not issues:         return "PASS", []
    if confidence >= 0.7:  return "CLARIFY", issues
    return "REGENERATE", issues


def _has_cycle(deps: Dict[str, list]) -> bool:
    visited, in_stack = set(), set()
    def dfs(node):
        visited.add(node); in_stack.add(node)
        for dep in deps.get(node, []):
            if dep not in visited and dfs(dep): return True
            if dep in in_stack: return True
        in_stack.discard(node)
        return False
    return any(dfs(n) for n in deps if n not in visited)


def _violates_order(tasks: list) -> bool:
    seen_types = []
    for task in tasks:
        t = task.get("type", "")
        if t == "deploy" and "build" not in seen_types:
            return True
        seen_types.append(t)
    return False
```

## Artefak C: Rust Worker Output Validator

```rust
use serde_json::Value;

pub enum ValidationResult {
    Valid,
    Invalid(Vec<String>),
}

pub fn validate_worker_output(json_str: &str) -> ValidationResult {
    let mut errors = vec![];
    
    let v: Value = match serde_json::from_str(json_str) {
        Ok(v) => v,
        Err(e) => return ValidationResult::Invalid(vec![format!("Invalid JSON: {}", e)]),
    };
    
    // Required fields
    for field in &["task_id", "status"] {
        if v.get(field).is_none() {
            errors.push(format!("Missing required field: '{}'", field));
        }
    }
    
    // Status must be valid
    let status = v["status"].as_str().unwrap_or("");
    if status != "success" && status != "error" {
        errors.push(format!("Invalid status '{}': must be 'success' or 'error'", status));
    }
    
    // success: result.code must exist
    if status == "success" && v["result"]["code"].is_null() {
        errors.push(String::from("result.code required when status=success"));
    }
    
    // error: error.message must exist
    if status == "error" && v["error"]["message"].is_null() {
        errors.push(String::from("error.message required when status=error"));
    }
    
    if errors.is_empty() { ValidationResult::Valid }
    else { ValidationResult::Invalid(errors) }
}

/// Wrapper: generate → validate → fallback ke error JSON jika invalid
pub fn safe_output(task_id: &str, gen: impl Fn() -> String) -> String {
    let output = gen();
    match validate_worker_output(&output) {
        ValidationResult::Valid => output,
        ValidationResult::Invalid(errs) => serde_json::json!({
            "task_id": task_id,
            "status": "error",
            "error": {
                "error_type": "output_validation_failed",
                "message": errs.join("; "),
                "recovery_suggestion": "Periksa format output worker"
            }
        }).to_string(),
    }
}
```
