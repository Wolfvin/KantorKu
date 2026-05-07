---
title: Async Runtime & Tauri Bridge Architecture
kategori: Rust, Tauri & Desktop Development
tags: [Rust, Tauri, Async, Tokio, Architecture, CLI, Runtime, IPC]
---

# Sistem Pengetahuan: Arsitektur Async Rust & Tauri yang Robust

## 1. Kategori: Manajemen Runtime & Konkurensi (Async Rust)

### Sub-topik: Nested Runtime Panic & Solusinya

**A. Inti Konsep**
- **Definisi:** Kondisi panic pada Rust (`tokio`) ketika mencoba membuat runtime baru (`block_on`) di dalam thread yang sudah menjalankan runtime async aktif.
- **Tujuan:** Memahami batas eksekusi thread agar tidak terjadi konflik kepemilikan thread antara scheduler runtime luar dan dalam.
- **Masalah:** Aplikasi crash total dengan pesan `Cannot start a runtime from within a runtime`, menghentikan semua worker thread.

**B. Mekanisme & Cara Kerja**
- **Alur Panic:**
  1.  Tauri Command dijalankan di dalam Tokio Runtime (thread sudah menjadi "driver" async).
  2.  Kode memanggil `block_on(...)`, yang mencoba mengambil alih thread untuk menjalankan future secara sinkron.
  3.  Tokio mendeteksi konflik kepemilikan thread -> Panic.
- **Solusi Alur:** Mengubah seluruh rantai pemanggilan menjadi `async` murni (`.await`) tanpa interupsi `block_on` di tengah jalur.

**C. Komponen / Fitur Penting**
- **`tokio::runtime`:** Engine eksekusi async.
- **`block_on`:** Fungsi pemaksa eksekusi sync (hanya aman di entry point `main`).
- **`await`:** Operator penyerahan kontrol (aman di dalam runtime).
- **`async fn`:** Penanda fungsi yang mengembalikan future.

**D. Use Case Nyata**
- **Skenario:** Fungsi `process_pdfs` (Tauri Command) memanggil helper `process_rekening_via_core`.
- **Implementasi Salah:** Helper menggunakan `block_on` untuk memanggil logic OCR.
- **Implementasi Benar:** Helper diubah jadi `async fn`, caller memanggil dengan `.await`.

**E. Tools & Teknologi**
- **Tokio:** Runtime async default.
- **Tauri:** Framework GUI yang menginisiasikan runtime async untuk command.
- **rust-analyzer:** IDE tool untuk mendeteksi kebutuhan `.await`.

**F. Evaluasi Kritis**
- **Kelebihan Solusi Await:** Non-blocking, efisien, thread-safe dalam konteks runtime.
- **Kekurangan:** Memerlukan propagasi signature (`async` menular ke atas).
- **Risiko:** Jika ada satu caller lupa `.await`, kode tidak akan compile (safety guarantee).

**G. Harga & Akses**
- **Open Source:** Tokio dan Tauri gratis (MIT/Apache 2.0).

**H. Perbandingan**
- **`block_on` di CLI:** Aman karena CLI adalah *owner* runtime.
- **`block_on` di Tauri:** Berbahaya karena Tauri adalah *guest* di runtime yang sudah ada.

---

## 2. Kategori: Arsitektur Aplikasi Hybrid (GUI + CLI)

### Sub-topik: Pemisahan Core Logic dan Entry Point

**A. Inti Konsep**
- **Definisi:** Memisahkan logika bisnis murni (Core) dari konteks eksekusi (GUI/CLI).
- **Tujuan:** Agar logika bisnis tidak terkontaminasi oleh keputusan runtime (sync vs async).
- **Masalah:** Kode sulit di-reuse karena terikat erat dengan Tauri `AppHandle` atau `block_on`.

**B. Mekanisme & Cara Kerja**
- **Struktur Workspace:**
  1.  **Core Library:** Fungsi murni `async`, tanpa `block_on`, tanpa dependency UI.
  2.  **Tauri Bin:** Entry point async, memanggil Core dengan `.await`.
  3.  **CLI Bin:** Entry point sync (`fn main`), membuat Runtime sendiri, memanggil Core dengan `block_on`.
- **Alur Data:** Input -> Core (Process) -> Output (Kembali ke Caller).

**C. Komponen / Fitur Penting**
- **Cargo Workspace:** Mengelola multiple crates dalam satu repo.
- **Feature Flags (Opsional):** `#[cfg(feature = "cli")]` untuk kompilasi kondisional.
- **Dependency Injection:** Passing `AppHandle` hanya di layer GUI, tidak di Core.

**D. Use Case Nyata**
- **Skenario:** Fitur ekstraksi PDF digunakan di Desktop (Tauri) dan Server (CLI).
- **Implementasi:** Logic OCR ada di crate `core`. Tauri dan CLI hanya menjadi "pintu masuk".

**E. Tools & Teknologi**
- **Cargo:** Package manager & build system.
- **Clap:** Library untuk parsing argumen CLI.
- **Serde:** Serialisasi data antara Core dan UI/CLI.

**F. Evaluasi Kritis**
- **Kelebihan:** Reusability tinggi, testing lebih mudah, arsitektur bersih.
- **Kekurangan:** Initial setup lebih kompleks (multiple crates).
- **Batasan:** Memerlukan disiplin agar tidak menaruh logic UI di Core.

**G. Harga & Akses**
- **Gratis:** Seluruh toolchain Rust standar.

**H. Perbandingan**
- **Monolit vs Modular:** Monolit lebih cepat awal tapi sulit di-maintain. Modular (Workspace) lebih stabil jangka panjang.

---

## 3. Kategori: Manajemen Sumber Daya & Keandalan (Resource & Reliability)

### Sub-topik: Cleanup File Temp & Error Handling

**A. Inti Konsep**
- **Definisi:** Memastikan sumber daya (file temp, memori) dibebaskan terlepas dari keberhasilan operasi.
- **Tujuan:** Mencegah kebocoran disk (file sampah menumpuk) dan inkonsistensi state.
- **Masalah:** File temp tidak terhapus jika terjadi panic atau error di tengah proses `await`.

**B. Mekanisme & Cara Kerja**
- **Pola "Compute Then Cleanup":**
  1.  Buat temp dir.
  2.  Eksekusi logic dalam block `async` yang menangkap `Result`.
  3.  Eksekusi cleanup (`remove_dir_all`) setelah block selesai (di luar logic utama).
  4.  Return hasil logic.
- **Error Propagation:** Menggunakan `thiserror` untuk mapping error yang jelas.

**C. Komponen / Fitur Penting**
- **RAII (Resource Acquisition Is Initialization):** Konsep dasar Rust (meski di async butuh perhatian ekstra).
- **`std::fs::remove_dir_all`:** Fungsi cleanup eksplisit.
- **`Result<T, E>`:** Tipe return wajib untuk menangani failure case.

**D. Use Case Nyata**
- **Skenario:** Proses OCR membutuhkan file PDF fisik di disk.
- **Implementasi:** File dibuat -> OCR -> **Hapus File** -> Return JSON. Meskipun OCR gagal, file tetap dihapus.

**E. Tools & Teknologi**
- **`thiserror`:** Macro untuk definisi error type yang bersih.
- **`uuid`:** Membuat nama folder temp unik untuk menghindari konflik.

**F. Evaluasi Kritis**
- **Kelebihan:** Disk tetap bersih, aman terhadap crash sebagian.
- **Kekurangan:** Overhead I/O untuk hapus file.
- **Risiko:** Jika cleanup gagal (permission denied), error bisa tertutupi oleh error utama.

**G. Harga & Akses**
- **Gratis:** Library standar ekosistem Rust.

**H. Perbandingan**
- **Manual Cleanup vs RAII Guard:** Manual lebih sederhana untuk awal (seperti diskusi), RAII Guard lebih aman untuk kompleksitas tinggi.

---

## 4. Kategori: Strategi Pengujian & Validasi (Testing & Validation)

### Sub-topik: Hierarki Testing untuk Async App

**A. Inti Konsep**
- **Definisi:** Layered approach untuk menguji komponen berdasarkan ketergantungan eksternalnya.
- **Tujuan:** Mendeteksi regresi secepat mungkin tanpa overhead environment GUI.
- **Masalah:** Testing logic bisnis lewat UI (Tauri) itu lambat dan flaky.

**B. Mekanisme & Cara Kerja**
- **Layer 1: Unit Test (Pure Function):** Test fungsi mapping JSON -> Struct. Tidak butuh async runtime berat.
- **Layer 2: Integration Test (Async Helper):** Test fungsi `process_rekening_via_core` dengan `#[tokio::test]`.
- **Layer 3: Manual/E2E Test:** Test jalur penuh lewat UI untuk validasi interaksi manusia.

**C. Komponen / Fitur Penting**
- **`#[tokio::test]`:** Attribute untuk menjalankan test di dalam runtime.
- **Mock Data:** File PDF sampel untuk input test.
- **Assertion:** Memastikan tidak panic dan output sesuai tipe.

**D. Use Case Nyata**
- **Skenario:** Memastikan fix panic `block_on` tidak kembali lagi.
- **Implementasi:** Tambah test yang memanggil fungsi async helper. Jika panic, test gagal di CI.

**E. Tools & Teknologi**
- **Cargo Test:** Runner test bawaan.
- **Fixtures:** Folder berisi sample data statis.

**F. Evaluasi Kritis**
- **Kelebihan:** Feedback loop cepat, isolasi error jelas.
- **Kekurangan:** Butuh maintenance mock data.
- **Batasan:** Tidak bisa test interaksi UI (klik tombol) dengan unit test.

**G. Harga & Akses**
- **Gratis:** Built-in dalam Rust toolchain.

**H. Perbandingan**
- **Unit vs E2E:** Unit lebih cepat untuk logika, E2E lebih yakin untuk user experience. Kombinasi keduanya wajib.

---

## 3. Sintesis Pengetahuan

### Prinsip Utama (Core Principles)
1.  **Runtime Agnostic Core:** Logika bisnis tidak boleh tahu siapa yang memanggilnya (CLI atau GUI). Ia hanya harus `async`.
2.  **Single Runtime Ownership:** Hanya ada satu pemilik runtime per thread. Jangan pernah nested (`block_on` di dalam `await`).
3.  **Cleanup Guarantee:** Pembersihan sumber daya harus terjadi di luar blok logika utama agar tetap jalan saat error.
4.  **Compiler as Guide:** Biarkan error kompilasi Rust memandu refactoring async (jika butuh `.await`, compiler akan bilang).

### Pola Berulang (Patterns)
1.  **Async Propagation:** Jika fungsi bawah `async`, fungsi atas wajib `async`.
2.  **Entry Point Separation:** `main()` sync untuk CLI, `#[tauri::command]` async untuk GUI.
3.  **Result Wrapping:** Selalu bungkus operasi I/O dalam `Result` untuk memudahkan cleanup terpusat.

### Insight Penting (Takeaways)
-   Panic `nested runtime` adalah kesalahan arsitektur, bukan sekadar bug kode.
-   Memisahkan CLI bukan hanya untuk fitur CLI, tapi untuk **memaksa** arsitektur yang bersih.
-   Testing fungsi murni (mapping) jauh lebih efektif untuk catching logic error daripada testing full flow di awal.

---

## 4. Sistem / Framework

### Framework: Refactoring Async Safety Protocol

**Fase 1: Isolasi & Analisis**
1.  [ ] Identifikasi semua penggunaan `block_on` di dalam kodebase.
2.  [ ] Tandai mana yang ada di dalam `async fn` (Bahaya) vs `fn main` (Aman).
3.  [ ] Pisahkan logika bisnis ke modul/library terpisah (Core).

**Fase 2: Transformasi Kode**
1.  [ ] Ubah signature helper bisnis menjadi `async fn`.
2.  [ ] Hapus `block_on` di dalam helper, ganti dengan `.await`.
3.  [ ] Propagasi `.await` ke caller (Tauri Command).
4.  [ ] Perbaiki error borrowing (`AppHandle` clone jika perlu).

**Fase 3: Manajemen Sumber Daya**
1.  [ ] Pastikan semua pembuatan file temp diikuti `remove_dir_all` di akhir fungsi.
2.  [ ] Gunakan `uuid` untuk nama folder temp unik.
3.  [ ] Wrap logic utama dalam block untuk memastikan cleanup berjalan di `finally`-like pattern.

**Fase 4: Validasi & Pengujian**
1.  [ ] Jalankan `cargo check` (Pastikan tidak ada error tipe).
2.  [ ] Buat Unit Test untuk fungsi mapping murni.
3.  [ ] Buat Integration Test untuk fungsi async helper (cek tidak panic).
4.  [ ] Manual Test: Jalankan 1 file via UI, pastikan tidak crash.

**Fase 5: Ekspansi (Opsional)**
1.  [ ] Buat binary CLI terpisah yang memanggil Core Library.
2.  [ ] Setup CI/CD untuk menjalankan test core secara otomatis.

---

## 5. Output Artefak (.skill)

```markdown
---
skill_id: rust_async_architecture_safety
version: 1.0.0
name: Rust Async & Tauri Architecture Safety
description: Kompetensi merancang sistem Rust/Tauri yang bebas dari nested runtime panic dan manajemen sumber daya yang aman.
tags: [Rust, Tauri, Async, Tokio, Architecture, CLI]
---

# [SKILL] Rust Async & Tauri Architecture Safety

## 1. Diagnostic Checklist
- [ ] Apakah ada `block_on` di dalam `#[tauri::command]`?
- [ ] Apakah logika bisnis tergantung pada `AppHandle` secara langsung?
- [ ] Apakah file temp dihapus bahkan saat terjadi error?
- [ ] Apakah signature fungsi konsisten (semua async atau semua sync)?

## 2. Implementation Template

### Core Logic (library/src/lib.rs)
```rust
pub async fn process_core_logic(input: Data) -> Result<Output, Error> {
    // Logic murni, tanpa block_on, tanpa UI dependency
    let temp = create_temp()?;
    let res = do_work(&temp).await;
    cleanup(&temp)?; // Guarantee cleanup
    res
}
```

### Tauri Command (src-tauri/src/main.rs)
```rust
#[tauri::command]
async fn my_command(data: Data) -> Result<Output, String> {
    // Caller async, pakai .await
    process_core_logic(data).await.map_err(|e| e.to_string())
}
```

### CLI Entry (src-cli/src/main.rs)
```rust
fn main() {
    // Owner runtime, boleh block_on
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        process_core_logic(data).await
    });
}
```

## 3. Safety Rules
1.  **NO NESTING:** Jangan pernah memanggil `block_on` di dalam fungsi yang sudah `async`.
2.  **CLEANUP LAST:** Kode cleanup harus berada setelah `await` selesai, tidak peduli hasilnya.
3.  **PURE CORE:** Logika bisnis tidak boleh mengimpor modul Tauri UI.

## 4. Verification Command
```bash
# Check compilation
cargo check --workspace

# Run core tests
cargo test -p core_lib

# Run CLI
cargo run -p cli_bin -- --input test.pdf
```

## 5. Troubleshooting Guide
- **Panic: "Cannot start runtime"** -> Cari `block_on` di dalam `async fn`, hapus/ganti `await`.
- **Error: "future cannot be sent"** -> Cek borrow `AppHandle` lintas `await`, lakukan clone.
- **File not found** -> Pastikan cleanup tidak terjadi sebelum operasi baca selesai.

---
Status: Active
Last Updated: 2023-10-27
```
