---
title: Rust + Tauri Desktop App Development
kategori: Rust, Tauri & Desktop Development
tags: [Rust, Tauri, Desktop, IPC, PDF, Async, Type-Safety, Build-System, Frontend]
---

# Sistem Pengetahuan: Rust + Tauri Desktop App Development
*Ekstraksi & Kristalisasi dari Session Pengembangan PDF Extractor*

---

## 1. KATEGORI UTAMA (THEME CLUSTERS)

```
ARSITEKTUR SISTEM
  Rust Backend Logic
  Tauri Bridge (Rust <-> JS)
  Frontend Integration
  Build & Deployment Pipeline

CORE TECHNICAL SKILLS
  PDF Parsing & Extraction
  Excel Generation
  Async/Await Patterns
  Error Handling Strategies
  Type Safety & Serialization

DEVELOPMENT OPERATIONS
  Dependency Management
  Build System Troubleshooting
  Version Compatibility
  Cross-Platform Considerations
  Debugging Workflows

ENGINEERING MINDSET
  First-Principles Problem Solving
  Incremental Development
  Defensive Programming
  Knowledge-Driven Debugging
```

---

## 2. SUB-TOPIK DEEP DIVE

### KATEGORI: ARSITEKTUR SISTEM

#### Sub-topik: Tauri Bridge Pattern (Rust <-> JavaScript)

**A. Inti Konsep**
- **Definisi**: Pola arsitektur di mana Rust berfungsi sebagai backend sistem yang aman dan performan, sementara JavaScript/TypeScript menangani UI/UX, dengan komunikasi dua arah melalui IPC (Inter-Process Communication).
- **Tujuan**: Memisahkan concern -- Rust untuk logika berat (parsing, I/O, kriptografi), JS untuk interaktivitas pengguna.
- **Masalah yang diselesaikan**: Menghindari blokir UI thread, memanfaatkan kekuatan sistem Rust tanpa mengorbankan pengalaman pengguna web-native.

**B. Mekanisme & Cara Kerja**
```
+------------------+     IPC (tauri.invoke)     +------------------+
|   Frontend JS    | <----------------------> |   Rust Backend   |
|   (Svelte/React) |     #[tauri::command]     |   (lib.rs)       |
+------------------+                           +------------------+
         |                                            |
         v                                            v
   - User interaction                          - Process PDF
   - Kirim params via invoke                   - Hash gambar
   - Terima Promise<Result>                    - Generate Excel
                                               - Return JSON
```

**C. Komponen Penting**
| Komponen | Peran | Koneksi |
|----------|-------|---------|
| `#[tauri::command]` | Macro penanda fungsi yang bisa dipanggil dari JS | Rust -> Tauri runtime |
| `tauri::generate_handler!` | Registrasi command ke IPC router | lib.rs -> main.rs |
| `invoke_handler` | Middleware yang menerima request dari frontend | main.rs -> Tauri core |
| `serde::{Serialize, Deserialize}` | Serialisasi data Rust <-> JSON <-> JS | Semua boundary layer |
| `PathBuf` / `String` | Tipe data aman untuk path/file lintas platform | FS operations |

**D. Use Case Nyata: PDF -> Excel Extractor**
```rust
// 1. Frontend: User pilih file & config kolom
await invoke('process_pdfs', {
  pdf_paths: ['/path/a.pdf', '/path/b.pdf'],
  config: { columns: [{id: 'a', field: 'NOMOR_FAKTUR'}] },
  doc_type: 'efaktur_keluaran'
});

// 2. Rust: Proses paralel, ekstraksi, build Excel
#[tauri::command]
async fn process_pdfs(...) -> Result<ProcessResult, String> {
  // - Baca bytes PDF
  // - Ekstrak teks + hash gambar
  // - Mapping ke struct EFakturData
  // - Generate .xlsx dengan rust_xlsxwriter
  // - Return path temp file
}

// 3. Frontend: Terima hasil, tampilkan progress, tawarkan download
```

**E. Tools & Teknologi**
| Tool | Fungsi | Posisi |
|------|--------|--------|
| `tauri` | Framework desktop app | Core runtime |
| `serde` | Serialisasi JSON | Data boundary |
| `tokio` | Async runtime | Concurrency layer |
| `anyhow` / `thiserror` | Error handling | Robustness layer |

**F. Evaluasi Kritis**
| Aspek | Analisis |
|-------|----------|
| Kelebihan | Type-safe boundary, performa native, bundle size kecil (~3MB) |
| Kekurangan | Learning curve Rust, debug IPC lebih kompleks, hot-reload terbatas |
| Batasan | Tidak semua crate Rust kompatibel dengan Tauri (perlu `cfg(not(target_os = "..."))`) |
| Risiko | Version mismatch plugin Rust/NPM bisa bikin build gagal total |

**G. Perbandingan**
| Pendekatan | Kapan Pilih Ini | Kapan Pilih Alternatif |
|------------|----------------|----------------------|
| **Tauri + Rust** | Butuh performa tinggi, keamanan, bundle kecil | Jika tim tidak familiar Rust |
| **Electron + Node** | Prototipe cepat, tim JS-only, butuh npm ecosystem luas | Jika bundle size & RAM usage kritis |
| **Flutter Desktop** | UI sangat kompleks, cross-platform mobile+desktop | Jika butuh akses low-level system |

---

#### Sub-topik: Async/Await & Concurrency Pattern di Rust

**A. Inti Konsep**
- **Definisi**: Pola pemrograman non-blokir menggunakan `async/.await` dengan runtime `tokio`, memungkinkan pemrosesan banyak file PDF secara paralel tanpa memblokir thread utama.
- **Tujuan**: Maksimalkan throughput I/O-bound operations (baca file, parse PDF, write Excel).
- **Masalah yang diselesaikan**: Menghindari "UI freeze" saat proses berat, memanfaatkan multi-core CPU.

**B. Mekanisme & Cara Kerja**
```rust
// Sequential (lambat):
for path in &pdf_paths {
    let data = extract_single_pdf(path)?; // Blokir sampai selesai
    all_data.push(data);
}

// Parallel (cepat):
use futures::stream::{self, StreamExt};

let results: Vec<_> = stream::iter(pdf_paths)
    .map(|path| async move {
        extract_single_pdf(&path) // Async task
    })
    .buffer_unordered(4) // Maks 4 task paralel
    .collect()
    .await;
```

**C. Komponen Penting**
| Komponen | Peran |
|----------|-------|
| `async fn` | Menandai fungsi yang bisa di-await |
| `.await` | Yield kontrol ke runtime saat menunggu I/O |
| `tokio::spawn` | Jalankan task di background thread |
| `futures::stream` | Abstraksi untuk processing stream data |
| `buffer_unordered(n)` | Batasi konkurensi agar tidak overload memory |

**D. Use Case Nyata: Batch PDF Processing**
```rust
// Workflow:
// 1. User pilih 50 file PDF
// 2. Frontend kirim array path ke Rust
// 3. Rust proses 4 file sekaligus (buffer_unordered(4))
// 4. Setiap selesai, kirim progress update via emit()
// 5. Setelah semua selesai, gabungkan hasil -> Excel
```

**E. Tools & Teknologi**
| Tool | Fungsi |
|------|--------|
| `tokio` | Async runtime dengan multi-thread scheduler |
| `futures` | Utility untuk stream, join, select |
| `rayon` *(opsional)* | Parallelism CPU-bound (bukan I/O) |

**F. Evaluasi Kritis**
| Aspek | Analisis |
|-------|----------|
| Kelebihan | Throughput tinggi, responsif, scalable ke 100+ file |
| Kekurangan | Debug async stack trace lebih sulit, risiko deadlock jika salah pakai `block_on` |
| Batasan | Tidak semua crate support async (misal: beberapa PDF parser masih sync) |
| Risiko | Buffer terlalu besar -> OOM; terlalu kecil -> underutilized CPU |

---

### KATEGORI: CORE TECHNICAL SKILLS

#### Sub-topik: PDF Extraction Strategy (Teks vs Gambar vs Metadata)

**A. Inti Konsep**
- **Definisi**: Pendekatan multi-layer untuk mengekstrak informasi dari PDF: (1) teks via `pdf-extract`, (2) gambar via `lopdf` + hashing, (3) metadata via `xmp` atau struktur objek PDF.
- **Tujuan**: Mendapatkan data struktural (nomor faktur, NPWP) + kontekstual (status via watermark/gambar).
- **Masalah yang diselesaikan**: PDF adalah format "visual", bukan database -- butuh heuristik untuk ekstraksi andal.

**B. Mekanisme & Cara Kerja**
```
PDF File
   |
   +-> [Layer 1: Teks] --> pdf_extract::extract_text_from_mem()
   |                      |
   |                      +-> Regex parsing untuk field terstruktur
   |                      +-> Fallback: NLP/heuristik untuk layout kompleks
   |
   +-> [Layer 2: Gambar] --> lopdf::Document::load_mem()
   |                        |
   |                        +-> Iterasi objek, filter Subtype=Image
   |                        +-> Decompress stream -> raw bytes
   |                        +-> SHA-256 hash -> lookup status invoice
   |
   +-> [Layer 3: Metadata] --> XMP / Info dict (opsional)
                              |
                              +-> Creator, Producer, CreationDate
                              +-> Custom properties (jika ada)
```

**C. Komponen Penting**
| Komponen | Peran | Koneksi |
|----------|-------|---------|
| `pdf-extract` | Ekstrak teks mentah dari PDF | Layer 1 |
| `lopdf` | Parse struktur objek PDF, akses stream gambar | Layer 2 |
| `sha2 + hex` | Hash konten gambar untuk fingerprinting | Layer 2 -> Status lookup |
| `regex` | Pattern matching untuk field terstruktur | Layer 1 post-processing |
| `Enum InvoiceStatus` | Type-safe representation status | Business logic layer |

**D. Use Case Nyata: Deteksi Status Invoice via Watermark**
```rust
// Masalah: Status "Approved"/"Cancelled" hanya berupa gambar watermark
// Solusi: Hash gambar pertama -> cocokkan dengan known hashes

const HASH_APPROVED: &str = "2d281785..."; // Pre-computed

fn get_invoice_status(pdf_bytes: &[u8]) -> Option<InvoiceStatus> {
    let hash = hash_first_image(pdf_bytes)?;
    match hash.as_str() {
        HASH_APPROVED => Some(InvoiceStatus::Approved),
        // ...
        _ => Some(InvoiceStatus::Unknown(hash)),
    }
}
```

**E. Tools & Teknologi**
| Tool | Fungsi | Catatan |
|------|--------|---------|
| `pdf-extract` | Teks extraction | Cepat, tapi kehilangan layout |
| `lopdf` | Low-level PDF parsing | Fleksibel, tapi perlu handle decompression manual |
| `image` *(opsional)* | Decode gambar untuk OCR | Jika hash tidak cukup, butuh konten visual |

**F. Evaluasi Kritis**
| Aspek | Analisis |
|-------|----------|
| Kelebihan | Hash-based status detection sangat cepat & deterministik |
| Kekurangan | Jika watermark berubah sedikit (kompresi, rotasi), hash berbeda -> false negative |
| Batasan | Tidak semua PDF menyimpan gambar sebagai stream terpisah (bisa inline) |
| Risiko | PDF malicious bisa crash parser -> selalu wrap dengan `Result` + timeout |

**G. Perbandingan Strategi Ekstraksi**
| Metode | Akurasi | Kecepatan | Kompleksitas | Kapan Dipakai |
|--------|---------|-----------|--------------|---------------|
| **Regex pada teks** | Sedang | Sangat cepat | Rendah | Format PDF konsisten, field terstruktur |
| **Hash gambar** | Tinggi (jika stabil) | Cepat | Sedang | Status/watermark visual, tidak berubah |
| **OCR (tesseract)** | Tinggi | Lambat | Tinggi | PDF scan, teks tidak selectable |
| **ML Layout Analysis** | Sangat tinggi | Sangat lambat | Sangat tinggi | Format sangat bervariasi, skala enterprise |

---

#### Sub-topik: Type-Safe Data Pipeline (Struct -> Serialize -> Excel)

**A. Inti Konsep**
- **Definisi**: Pipeline transformasi data yang mempertahankan type safety dari ekstraksi PDF -> struct Rust -> serialisasi JSON -> frontend -> generate Excel.
- **Tujuan**: Mencegah runtime error, memudahkan testing, memungkinkan refactoring aman.
- **Masalah yang diselesaikan**: "Stringly-typed" code yang rapuh saat format PDF atau requirement Excel berubah.

**B. Mekanisme & Cara Kerja**
```
PDF Bytes
   |
   v
[Extract] -> EFakturData (struct Rust)
   |         - field: String, f64, Vec<EFakturItem>
   |         - derive: Debug, Serialize, Deserialize
   v
[Serialize] -> JSON (via serde_json)
   |          - Aman dikirim ke JS via IPC
   v
[Frontend] -> User review / edit (opsional)
   |
   v
[Build Excel] -> rust_xlsxwriter
   |            - Mapping field -> kolom Excel
   |            - Format: currency, date, merge cells
   v
.xlsx File
```

**C. Komponen Penting**
| Komponen | Peran | Contoh |
|----------|-------|--------|
| `struct EFakturData` | Schema data inti | `nomor_faktur: String, total_harga: f64` |
| `derive(Serialize)` | Auto-JSON conversion | `serde_json::to_string(&data)` |
| `ColumnConfig` | Mapping user-defined columns | `[{id: "a", field: "NOMOR_FAKTUR"}]` |
| `CellValue` enum | Unified representation untuk Excel | `Str(String) | Num(f64)` |
| `rust_xlsxwriter` | Generate .xlsx native | Tanpa dependency Excel installed |

**D. Use Case Nyata: Dynamic Column Mapping**
```rust
// User atur kolom via UI: [a: "NOMOR_FAKTUR", b: "TOTAL_HARGA", c: "QTY"]
// Rust terima config, build Excel sesuai urutan:

for (col_idx, col_cfg) in config.columns.iter().enumerate() {
    let col = col_idx as u16;
    let (val, is_num) = get_value(data, &col_cfg.field); // Type-aware getter
    
    if is_num {
        sheet.write_with_format(row, col, val_num, &fmt_currency)?;
    } else {
        sheet.write_with_format(row, col, val_str, &fmt_text)?;
    }
}
```

**E. Tools & Teknologi**
| Tool | Fungsi |
|------|--------|
| `serde` | Serialisasi/deserialisasi type-safe |
| `rust_xlsxwriter` | Generate Excel tanpa COM/interop |
| `chrono` *(opsional)* | Handling tanggal/timezone |

**F. Evaluasi Kritis**
| Aspek | Analisis |
|-------|----------|
| Kelebihan | Compile-time check, refactoring aman, dokumentasi via type |
| Kekurangan | Boilerplate untuk struct besar, perlu maintain mapping logic |
| Batasan | `rust_xlsxwriter` belum support semua fitur Excel (pivot, macro) |
| Risiko | Schema mismatch antara PDF extractor dan Excel builder -> silent data loss |

---

### KATEGORI: DEVELOPMENT OPERATIONS

#### Sub-topik: Build System Troubleshooting Framework

**A. Inti Konsep**
- **Definisi**: Metodologi sistematis untuk mendiagnosa dan memperbaiki error build di ekosistem Rust + Tauri + NPM.
- **Tujuan**: Minimalkan downtime debugging, ubah error menjadi learning opportunity.
- **Masalah yang diselesaikan**: Error cryptic seperti `E0255`, `os error 3`, version mismatch yang menghambat produktivitas.

**B. Mekanisme & Cara Kerja: Diagnostic Decision Tree**
```
Error Muncul
   |
   +-> [Kategori 1: Macro/Compilation]
   |   |
   |   +-> "name __cmd__xxx defined multiple times"
   |   |   +-> Cek: generate_handler! duplikat?
   |   |   +-> Cek: command didefinisikan di 2 file?
   |   |   +-> Solusi: cargo clean + pastikan single registration
   |   |
   |   +-> "cannot find macro"
   |       +-> Cek: derive macro crate sudah di-dependency?
   |       +-> Solusi: tambahkan serde = { version="...", features=["derive"] }
   |
   +-> [Kategori 2: Filesystem/Path]
   |   |
   |   +-> "os error 3: path not found" di target/
   |   |   +-> Penyebab: Path >260 karakter (Windows MAX_PATH)
   |   |   +-> Solusi: 
   |   |       1. Pindah project ke C:\dev\short-path
   |   |       2. Enable LongPathsEnabled di Registry
   |   |       3. Hapus manual folder target/
   |   |
   |   +-> "permission denied"
   |       +-> Cek: antivirus blocking? run as admin?
   |       +-> Solusi: Add exclusion path ke Defender
   |
   +-> [Kategori 3: Dependency Version]
       |
       +-> "version mismatched Tauri packages"
       |   +-> Penyebab: Rust crate v2.6.0 vs NPM v2.0.0
       |   +-> Solusi: Samakan major.minor di Cargo.toml & package.json
       |   +-> Prevent: Gunakan cargo tauri add plugin-name (auto-match)
       |
       +-> "crate X requires rustc Y"
           +-> Solusi: rustup update stable
```

**C. Komponen Penting**
| Komponen | Peran |
|----------|-------|
| `cargo clean` | Reset build cache, hapus .fingerprint korup |
| `cargo tree` | Visualisasi dependency graph, deteksi conflict |
| `cargo tauri info` | Diagnosa environment Tauri |
| `grep -r "#[tauri::command]" src/` | Cari duplikasi command registration |
| Windows Long Path Policy | Enable path >260 karakter |

**D. Use Case Nyata: Fix E0255 Error**
```bash
# 1. Error: __cmd__process_pdfs defined multiple times
# 2. Diagnosa:
grep -r "process_pdfs" src-tauri/src/  # Cek duplikasi definisi
grep -r "generate_handler" src-tauri/src/  # Cek duplikasi registrasi

# 3. Solusi:
#    - Hapus commands.rs jika fungsi sudah di lib.rs
#    - Pastikan invoke_handler hanya sekali di main.rs
cargo clean
cargo tauri dev  # Build ulang dari nol
```

**E. Tools & Teknologi**
| Tool | Fungsi |
|------|--------|
| `cargo` | Package manager & build system Rust |
| `cargo-tauri` | CLI untuk develop/build Tauri app |
| `rustup` | Manage Rust toolchain versions |
| PowerShell `Remove-Item -Recurse` | Hapus folder target manual (Windows) |
| Registry Editor | Enable LongPathsEnabled |

**F. Evaluasi Kritis**
| Aspek | Analisis |
|-------|----------|
| Kelebihan | Framework ini mengubah debugging dari "trial-error" menjadi proses terstruktur |
| Kekurangan | Tetap butuh pemahaman dasar Rust compiler & Tauri architecture |
| Batasan | Tidak semua error punya pola jelas; beberapa butuh issue tracking ke upstream crate |
| Risiko | `cargo clean` berlebihan -> wasted time recompiling; jangan jadi kebiasaan pertama |

**G. Perbandingan Pendekatan Debugging**
| Pendekatan | Kapan Dipakai |
|------------|---------------|
| **Systematic Framework (ini)** | Error berulang, tim collaboration, dokumentasi knowledge |
| **Stack Overflow Copy-Paste** | Error sangat spesifik, waktu kritis, solusi sudah terverifikasi |
| **Ask Community (Discord/Forum)** | Error obscure, butuh konteks arsitektur, learning opportunity |

---

## 3. SINTESIS PENGETAHUAN (CORE INTELLIGENCE)

### Prinsip Utama (Core Principles)
1.  **Type Safety as Documentation**: Struct Rust bukan hanya container data, tapi kontrak eksplisit antar modul. Jika compile, boundary aman.
2.  **Separation of Concerns via IPC**: Rust = "otak" (logika, I/O, keamanan), JS = "wajah" (interaksi, animasi, state UI). Jangan campur.
3.  **Defensive Extraction**: PDF adalah format "musuh" -- asumsikan malformed, corrupt, atau malicious. Selalu wrap parsing dengan `Result`, timeout, dan fallback.
4.  **Build Reproducibility > Convenience**: Path pendek, versi pinned, clean build sebelum release -- lebih baik build 2 menit ekstra daripada debug 2 jam.
5.  **Knowledge-Driven Debugging**: Setiap error adalah data. Catat pola, buat checklist, ubah menjadi sistem -- jangan hanya "fix dan lupa".

### Pola Berulang (Patterns)
| Pola | Konteks | Implementasi |
|------|---------|--------------|
| **Command Pattern via Macro** | Tauri IPC | `#[tauri::command]` + `generate_handler!` |
| **Enum for State Modeling** | Business logic | `InvoiceStatus::Approved | Unknown(hash)` |
| **Adapter for Heterogeneous Data** | PDF -> Excel | `CellValue::Str/Num` + `get_header_value()` matcher |
| **Buffered Concurrency** | Batch processing | `stream::buffer_unordered(n)` |
| **Hash-Based Fingerprinting** | Visual status detection | SHA-256 gambar -> lookup table |

### Insight Penting (Takeaways)
- **"Compile Error adalah Teman"**: Error Rust yang verbose justru mempercepat debugging -- lebih baik gagal di compile-time daripada runtime di produksi.
- **Tauri v2 Breaking Changes**: Plugin system di-refactor total. Selalu cek [tauri.app/v2/migration](https://tauri.app/v2/migration) sebelum upgrade.
- **Windows Path Hell adalah Nyata**: MAX_PATH 260 karakter bukan mitos. Solusi termahal (pindah path) sering paling efektif.
- **PDF Extraction adalah Heuristik, Bukan Eksak**: Tidak ada "perfect parser". Desain sistem yang graceful degradation: regex -> fallback -> manual review.
- **Async di Rust Bukan Silver Bullet**: `async` hanya berguna untuk I/O-bound. Untuk CPU-bound (image processing), gunakan `rayon` atau thread pool.

---

## 4. SISTEM / FRAMEWORK: Rust+Tauri Dev Workflow

### Workflow Pengembangan (Reusable)

```mermaid
graph LR
    A[Requirement] --> B[Design Data Schema]
    B --> C[Implement Rust Core]
    C --> D[Expose via #[tauri::command]]
    D --> E[Frontend Integration]
    E --> F[Testing: Unit + IPC]
    F --> G[Build: Debug -> Release]
    G --> H[Deploy: Sign + Distribute]
```

### Checklist Praktis per Tahap

#### Tahap 1: Setup Project
```bash
# 1. Inisialisasi dengan versi kompatibel
cargo install cargo-tauri --version "^2.0"
cargo tauri init

# 2. Tambah plugin via CLI (auto-match versi)
cargo tauri add dialog shell

# 3. Konfigurasi path pendek (Windows)
#    Pindah project ke C:\dev\pdf-extractor

# 4. Tambah .cargo/config.toml untuk konsistensi
[build]
target-dir = "target"
```

#### Tahap 2: Develop Core Logic
```rust
// Pattern: Type-safe extraction pipeline
#[derive(Serialize, Deserialize, Debug)]
pub struct ExtractResult { /* ... */ }

#[tauri::command]
pub async fn extract_pdf(path: String) -> Result<ExtractResult, String> {
    // 1. Validasi input
    // 2. Ekstrak dengan fallback
    // 3. Return type yang bisa di-serialize
    // 4. Error message human-readable untuk frontend
}
```

#### Tahap 3: Debugging Protocol
```bash
# Saat error muncul:
# 1. Baca pesan error sampai akhir (sering clue di baris terakhir)
# 2. Kategorikan: Compilation / Filesystem / Dependency
# 3. Jalankan diagnostic command:
cargo check --verbose          # Lihat command rustc sebenarnya
cargo tree -i tauri            # Cek dependency chain
grep -r "command" src/         # Cari duplikasi registration

# 4. Jika stuck: cargo clean + rebuild
# 5. Catat solusi di /docs/troubleshooting.md
```

#### Tahap 4: Pre-Release Validation
```bash
# 1. Build release dengan symbol stripping
cargo tauri build --release

# 2. Test di clean environment (VM / fresh user)
# 3. Verifikasi:
#    - Bundle size < 10MB
#    - Startup time < 3s
#    - Tidak ada panic di log

# 4. Sign executable (Windows: signtool, macOS: codesign)
```

---

## 5. OUTPUT ARTEFAK: `.skill` Template

```markdown
---
skill_id: rust_tauri_pdf_extractor_v1
title: "Bangun Desktop App PDF Extractor dengan Rust + Tauri"
version: 1.0
tags: [rust, tauri, pdf, desktop, async, type-safety]
prerequisites:
  - "Rust basic: struct, enum, Result, async/await"
  - "JavaScript/TypeScript fundamental"
  - "Command line proficiency (PowerShell/bash)"
---

## Objective
Dalam 4 jam, kamu bisa membuat desktop app yang:
- [ ] Memilih multiple PDF via native dialog
- [ ] Mengekstrak teks + mendeteksi status via gambar
- [ ] Menampilkan progress real-time di UI
- [ ] Menggenerate Excel dengan kolom custom
- [ ] Build untuk Windows/macOS/Linux

## Core Components Template

### 1. Data Schema (`src/types.rs`)
```rust
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct ColumnConfig {
    pub id: String,    // "a", "b", ...
    pub field: String, // "NOMOR_FAKTUR", ...
}

#[derive(Serialize, Deserialize, Debug)]
pub struct ExtractResult {
    pub file_name: String,
    pub data: EFacturData,
    pub status: InvoiceStatus,
}
```

### 2. Command Template (`src/commands.rs`)
```rust
#[tauri::command]
pub async fn process_pdfs(
    paths: Vec<String>,
    config: ExtractConfig,
) -> Result<ProcessResult, String> {
    // Pattern: Early validation
    if paths.is_empty() {
        return Err("Pilih minimal 1 file".into());
    }
    
    // Pattern: Parallel processing dengan batas
    use futures::stream::{self, StreamExt};
    let results: Vec<_> = stream::iter(paths)
        .map(|p| async { extract_one(&p) })
        .buffer_unordered(4)
        .collect()
        .await;
    
    // Pattern: Aggregate + error reporting
    let (success, failed): (Vec<_>, Vec<_>) = results
        .into_iter()
        .partition(|r| r.is_ok());
    
    Ok(ProcessResult {
        success_count: success.len() as u32,
        failed_count: failed.len() as u32,
    })
}
```

### 3. Frontend Integration Template (`src/main.js`)
```javascript
// Pattern: Type-safe invoke wrapper
export async function extractPDFs(paths, config) {
  try {
    const result = await invoke('process_pdfs', { 
      pdf_paths: paths, 
      config 
    });
    
    // Pattern: Progress update via event
    listen('extract-progress', (e) => {
      updateProgressBar(e.payload.percent);
    });
    
    return result;
  } catch (err) {
    showToast(`Gagal: ${err}`, 'error');
    throw err;
  }
}
```

## Troubleshooting Quick Reference

| Error | Quick Fix |
|-------|-----------|
| `__cmd__xxx defined multiple times` | `cargo clean` + cek `generate_handler!` duplikat |
| `os error 3: path not found` | Pindah project ke `C:\dev\short` + hapus `target/` manual |
| `version mismatched Tauri packages` | Samakan versi di `Cargo.toml` & `package.json` (major.minor) |
| `cannot find derive macro Serialize` | Tambah `serde = { version="1.0", features=["derive"] }` |
| UI freeze saat proses | Pastikan fungsi command `async` + frontend pakai `await` |

## Success Metrics
- [ ] Build time < 5 menit (incremental)
- [ ] App startup < 3 detik
- [ ] Process 10 PDF < 30 detik (i5, SSD)
- [ ] Bundle size < 15 MB
- [ ] Zero panic di production log (100+ user)

## Resources
- [Tauri v2 Docs](https://tauri.app/v2/)
- [Rust Async Book](https://rust-lang.github.io/async-book/)
- [lopdf Examples](https://github.com/J-F-Liu/lopdf/tree/master/examples)
- [rust_xlsxwriter Docs](https://rustxlsxwriter.github.io/)

---
*Generated: {{date}} | Last Updated: {{last_modified}} | Owner: {{team_name}}*
```

---

## Cara Menggunakan Artefak Ini

1.  **Simpan sebagai file**: `rust_tauri_pdf_extractor.skill.md`
2.  **Import ke knowledge base**: Obsidian, Logseq, atau Notion
3.  **Gunakan sebagai template**: Copy-paste section `.skill` untuk project baru
4.  **Update iteratif**: Tambah pola/error/solusi baru ke checklist troubleshooting
5.  **Share ke tim**: Jadikan onboarding guide untuk developer baru

> **Pro Tip**: Tambahkan script `./scripts/new-feature.sh` yang auto-generate struct + command template dari nama fitur -- konsistensi > kecepatan.
