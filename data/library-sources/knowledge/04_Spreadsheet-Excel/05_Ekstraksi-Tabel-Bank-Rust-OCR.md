---
title: Ekstraksi Tabel Bank Berbasis Rust & OCR
kategori: Spreadsheet, Excel & Automation
tags: [rust, OCR, tesseract, table-extraction, bank-statement, parallel-processing]
---

# Sistem Pengetahuan: Ekstraksi Tabel Struktur Bank Berbasis Rust

## 1. Kategori: Arsitektur Sistem & Stack Teknologi

### Sub-topik: Ekosistem Rust untuk Computer Vision & OCR

**A. Inti Konsep**
Pemanfaatan bahasa pemrograman Rust untuk membangun pipeline ekstraksi data tabel dari dokumen scanned (PDF/Image) dengan fokus pada performa tinggi, keamanan memori, dan paralelisasi.

**B. Mekanisme & Cara Kerja**
Sistem bekerja sebagai pipeline sequential yang dioptimasi secara paralel pada bagian berat (OCR). Image dimuat, diproses untuk deteksi struktur, dipotong menjadi sel-sel kecil, lalu didistribusikan ke worker threads untuk OCR, dan hasilnya digabungkan kembali.

**C. Komponen / Fitur Penting**
1.  **Memory Safety:** Mencegah crash saat memproses gambar besar.
2.  **Zero-cost Abstractions:** Performa setara C++ tanpa overhead runtime.
3.  **Concurrency Model:** Ownership model Rust memudahkan paralelisasi tanpa race condition.

**D. Use Case Nyata**
Ekstraksi ratusan halaman statement bank (BNI) secara batch dalam waktu singkat dibandingkan menggunakan Python single-threaded.

**E. Tools & Teknologi**
1.  **`image` crate:** Manipulasi pixel dasar (load, crop, get_pixel).
2.  **`leptess`:** Binding Rust untuk Tesseract OCR & Leptonica.
3.  **`rayon`:** Data parallelism untuk memproses sel tabel secara simultan.
4.  **`serde`/`serde_json`:** Serialisasi hasil ekstraksi.

**F. Evaluasi Kritis**
*   **Kelebihan:** Performa ekstrem, binary tunggal (static linking possible), type safety.
*   **Kekurangan:** Kurva belajar curam (borrow checker), ekosistem CV belum selengkap Python (OpenCV).
*   **Batasan:** Binding library C++ (Tesseract) masih memerlukan dependensi sistem eksternal.
*   **Risiko:** Kompleksitas manajemen memori jika tidak paham ownership saat berbagi data antar thread.

**G. Harga & Akses**
Semua crate bersifat Open Source (MIT/Apache). Tesseract engine gratis.

**H. Perbandingan**
*   **vs Python (OpenCV + PyTesseract):** Rust lebih cepat 10-50x pada proses image processing loop, namun Python lebih cepat dalam prototyping awal.
*   **vs Go:** Rust lebih aman secara memori untuk operasi pixel raw, Go lebih sederhana untuk concurrency tapi kurang optimal untuk komputasi numerik berat tanpa CGO.

---

## 2. Kategori: Deteksi Struktur Tabel (Grid Detection)

### Sub-topik: Strategi Segmentasi Garis & ROI

**A. Inti Konsep**
Mengidentifikasi batas tabel dan sel secara geometris berdasarkan kontras warna pixel, tanpa mengubah struktur gambar asli secara destruktif.

**B. Mekanisme & Cara Kerja**
1.  **ROI Detection:** Menemukan koordinat `Box Kunci` (x_start, y_start, x_end, y_end) yang membatasi area tabel utama.
2.  **Projection Profile:** Menghitung densitas pixel putih pada sumbu X (untuk garis vertikal) dan sumbu Y (untuk garis horizontal) within ROI.
3.  **Thresholding:** Menentukan garis valid berdasarkan kontinuitas pixel (bukan sekadar titik putih noise).

**C. Komponen / Fitur Penting**
1.  **Table ROI:** Area scanning utama untuk efisiensi.
2.  **Column Dividers (X-cut):** Koordinat vertikal pemisah kolom.
3.  **Row Dividers (Y-cut):** Koordinat horizontal pemisah baris.
4.  **White Line Detector:** Algoritma scanning pixel bernilai tinggi (putih) pada background gelap/berwarna.

**D. Use Case Nyata**
Dokumen BNI memiliki garis tabel putih tebal di atas background biru. Sistem mendeteksi putih murni (RGB > 240) sebagai garis pemisah.

**E. Tools & Teknologi**
1.  **`image::DynamicImage`:** Akses pixel raw.
2.  **Custom Logic:** Algoritma scanning manual (lebih ringan daripada Hough Transform untuk kasus garis lurus tegas).

**F. Evaluasi Kritis**
*   **Kelebihan:** Sangat cepat, kontrol penuh, tidak butuh dependensi berat (OpenCV).
*   **Kekurangan:** Rentan jika garis putus-putus parah atau warna garis berubah.
*   **Batasan:** Asumsi garis harus lurus horizontal/vertikal.
*   **Risiko:** Noise putih (noda scan) bisa terdeteksi sebagai garis palsu.

**G. Harga & Akses**
N/A (Logika custom).

**H. Perbandingan**
*   **vs OpenCV Hough Lines:** OpenCV lebih robust untuk garis miring/putus, tapi overkill dan lambat untuk tabel bank yang kaku.
*   **vs Warna Manipulasi (White->Red):** Tidak mengubah warna lebih disarankan untuk menjaga integritas gambar asli untuk OCR, cukup deteksi putih di memori sementara.

---

## 3. Kategori: Logika Ekstraksi & Agregasi Data

### Sub-topik: Mapping OCR ke Grid & State Machine Baris

**A. Inti Konsep**
Mengubah hasil OCR yang berupa daftar teks bebas (bounding boxes) menjadi struktur tabel terrelasi berdasarkan posisi geometris dan logika bisnis spesifik.

**B. Mekanisme & Cara Kerja**
1.  **Cell Assignment:** Setiap BBOX OCR dicek apakah ≥90% luasannya berada dalam koordinat sel grid.
2.  **Row State Machine:**
    *   **New Row:** Jika Kolom 0 ada isi → Buat record baru.
    *   **Continuation:** Jika Kolom 0 kosong → Append ke record sebelumnya (menangani text wrapping).
3.  **Aggregation:** Menggabungkan teks per sel menjadi satu string per kolom.

**C. Komponen / Fitur Penting**
1.  **Containment Check:** Validasi 90% area BBOX dalam sel.
2.  **Column 0 Trigger:** Penentu utama awal transaksi baru.
3.  **Merge Logic:** Penggabungan string dengan spasi atau newline.
4.  **Confidence Filter:** Mengabaikan teks dengan skor OCR rendah.

**D. Use Case Nyata**
Keterangan transaksi BNI yang panjang sering terpotong ke baris visual berikutnya. Kolom pertama (Tanggal/No) kosong di baris lanjutan. Logika ini menggabungkannya kembali menjadi satu transaksi utuh.

**E. Tools & Teknologi**
1.  **`leptess`:** Mengambil BBOX (x, y, w, h) dan teks.
2.  **Struct Data:** `TableRow`, `TableCell` untuk penyimpanan interim.

**F. Evaluasi Kritis**
*   **Kelebihan:** Menyelesaikan masalah utama OCR tabel (multi-line text).
*   **Kekurangan:** Bergantung pada konsistensi format dokumen (Kolom 0 harus selalu jadi penanda).
*   **Batasan:** Tidak menangani merged cells yang kompleks (misal: header tabel).
*   **Risiko:** False negative pada Kolom 0 (teks tipis tidak terbaca) bisa menyebabkan penggabungan baris yang salah.

**G. Harga & Akses**
N/A (Logika Bisnis).

**H. Perbandingan**
*   **vs Sequential Reading:** Membaca kiri-kanan atas-bawah tanpa grid akan hancur pada tabel multi-kolom.
*   **vs Deep Learning Table Detection:** Model AI (seperti TableNet) lebih fleksibel tapi butuh training data dan GPU. Logika rule-based lebih cepat dan deterministik untuk format bank yang tetap.

---

## 4. Kategori: Optimasi & Reliabilitas Sistem

### Sub-topik: Parallel Processing & Error Handling

**A. Inti Konsep**
Memastikan sistem tetap cepat saat skala data besar dan tetap stabil saat menghadapi dokumen rusak atau anomali.

**B. Mekanisme & Cara Kerja**
1.  **Rayon Parallel Map:** Membagi tugas OCR per sel atau per baris ke banyak core CPU.
2.  **Thread-safe Aggregation:** Menggunakan channel atau struktur data terkunci untuk menggabungkan hasil.
3.  **Graceful Degradation:** Jika deteksi garis gagal, fallback ke mode scanning teks bebas.
4.  **Config Driven:** Parameter threshold tidak di-hardcode.

**C. Komponen / Fitur Penting**
1.  **`rayon::par_iter`:** Eksekusi paralel.
2.  **Channel (`mpsc`/`crossbeam`):** Komunikasi antar thread.
3.  **Config Struct:** Menyimpan threshold (90%, 80%, dll).
4.  **Visual Debugger:** Output gambar dengan overlay garis dan BBOX untuk validasi.

**D. Use Case Nyata**
Memproses 100 halaman statement dalam waktu < 1 menit. Jika satu halaman gagal, sistem tidak crash tapi mencatat error dan lanjut ke halaman berikutnya.

**E. Tools & Teknologi**
1.  **`rayon`:** Parallelism.
2.  **`anyhow`/`thiserror`:** Manajemen error Rust.
3.  **`serde`:** Load config dari TOML/JSON.

**F. Evaluasi Kritis**
*   **Kelebihan:** Skalabilitas linear dengan jumlah core CPU.
*   **Kekurangan:** Overhead thread management untuk tugas sangat kecil.
*   **Batasan:** IO Bound (baca gambar) bisa jadi bottleneck jika tidak diasync.
*   **Risiko:** Race condition jika shared state tidak diamankan dengan benar.

**G. Harga & Akses**
N/A (Library Open Source).

**H. Perbandingan**
*   **vs Single Thread:** Jauh lebih lambat pada mesin multi-core.
*   **vs Async (Tokio):** Async lebih baik untuk IO bound (network), Rayon lebih baik untuk CPU bound (image processing/OCR).

---

## 3. Sintesis Pengetahuan

### Prinsip Utama (Core Principles)
1.  **Kontras adalah Kunci:** Deteksi struktur paling akurat ketika memanfaatkan kontras warna asli dokumen (Garis Putih vs Background Biru) tanpa manipulasi destruktif.
2.  **Struktur Mendahului Konten:** Pahami grid tabel (X/Y cuts) sebelum mencoba membaca teks. Struktur adalah peta, teks adalah isinya.
3.  **Logika Bisnis > OCR Murni:** OCR hanya memberikan teks kasar. Logika aplikasi (Kolom 0 = New Row) yang memberikan makna dan struktur data yang benar.
4.  **Paralelisasi CPU Bound:** Tugas berat (OCR per sel) harus disebar ke semua core CPU untuk efisiensi maksimal.

### Pola Berulang (Patterns)
1.  **ROI -> Grid -> Cell -> OCR:** Pipeline standar ekstraksi tabel terstruktur.
2.  **Thresholding Configuration:** Semua angka magic (90%, 240 RGB) harus bisa dikonfigurasi.
3.  **Fallback Mechanism:** Selalu siapkan jalan alternatif jika deteksi utama (garis) gagal.

### Insight Penting (Takeaways)
*   Jangan ubah warna gambar (White->Red) jika tidak perlu; itu menambah komputasi dan risiko noise. Deteksi saja warnanya.
*   Gunakan `image` crate (Pure Rust) untuk kasus garis lurus tegas karena lebih ringan daripada OpenCV.
*   Masalah terbesar OCR tabel bukan pada membaca teks, tapi pada **menghubungkan teks multi-baris** menjadi satu record transaksi.
*   Validasi 90% containment lebih baik daripada centroid saja untuk menghindari teks yang "mengambang" di perbatasan sel.

---

## 4. Sistem / Framework

### Workflow Implementasi Ekstraksi Tabel Bank (Rust)

**Fase 1: Persiapan & Konfigurasi**
1.  [ ] Setup project Rust (`cargo init`).
2.  [ ] Install dependencies: `image`, `leptess`, `rayon`, `serde`.
3.  [ ] Install Tesseract Engine & Language Data (`eng.traineddata`) di sistem.
4.  [ ] Buat struct `Config` untuk threshold (warna, luas, kontinuitas).

**Fase 2: Deteksi Struktur (Single Thread)**
1.  [ ] Load image dokumen.
2.  [ ] **Deteksi ROI:** Cari area terbesar yang mengandung garis grid.
3.  [ ] **Deteksi Garis:**
    *   Scan sumbu X dalam ROI -> Simpan koordinat vertikal valid (`Vec<x>`).
    *   Scan sumbu Y dalam ROI -> Simpan koordinat horizontal valid (`Vec<y>`).
4.  [ ] **Validasi Grid:** Pastikan garis memiliki kontinuitas minimal (misal 80%).
5.  [ ] **Generasi Sel:** Buat matriks sel dari perpotongan koordinat X dan Y.

**Fase 3: Ekstraksi Teks (Parallel Thread)**
1.  [ ] Inisialisasi instance Tesseract (`leptess`).
2.  [ ] Gunakan `rayon` untuk iterasi setiap Sel.
3.  [ ] **Preprocess Sel:** Crop sel -> Grayscale -> Threshold (Hitam/Putih).
4.  [ ] **OCR:** Eksekusi Tesseract pada sel -> Dapatkan Text + BBOX + Confidence.
5.  [ ] **Filter:** Buang hasil dengan confidence rendah.

**Fase 4: Agregasi & Logika Bisnis (Single Thread)**
1.  [ ] Kumpulkan hasil OCR dari semua thread.
2.  [ ] **Mapping:** Assign setiap BBOX ke Sel berdasarkan validasi 90% luas.
3.  [ ] **State Machine:**
    *   Iterasi baris visual.
    *   Cek Kolom 0.
    *   Jika Ada Isi → Push `New Row`.
    *   Jika Kosong → Append ke `Previous Row`.
4.  [ ] **Export:** Simpan ke CSV/JSON/Database.

**Fase 5: Validasi & Debugging**
1.  [ ] Generate **Debug Image**: Gambar asli + Overlay Garis Detected + Overlay BBOX Teks.
2.  [ ] Cek manual apakah garis merah (deteksi) sesuai dengan garis putih asli.
3.  [ ] Cek apakah teks multi-baris sudah tergabung dengan benar.

---

## 5. Output Artefak (.skill)

```markdown
# .skill: Rust Table Extraction System

## Role
Anda adalah Senior Rust Engineer specializing in Computer Vision & OCR Pipeline.

## Task
Build a high-performance table extraction system for structured bank documents (e.g., BNI Statements).

## Constraints
- Language: Rust (Stable)
- Performance: Must utilize parallel processing (Rayon)
- Accuracy: Must handle multi-line text wrapping within table rows
- Dependencies: Minimal external C++ bindings (Prefer pure Rust for image processing)

## Knowledge Base
1. **Structure Detection**: Use Projection Profile on high-contrast lines (White lines on Blue bg). Do NOT modify image colors destructively.
2. **Grid Mapping**: Assign OCR BBOX to cells only if >=90% area containment.
3. **Row Logic**: 
   - IF Cell[0] has text -> New Transaction Row.
   - IF Cell[0] is empty -> Continuation of Previous Row (Merge text).
4. **OCR Engine**: Tesseract via `leptess`. Preprocess cells (binarize) before OCR.
5. **Config**: All thresholds (color, area, confidence) must be configurable.

## Workflow
1. Define `Config` struct.
2. Implement `detect_roi()` & `detect_grid_lines()`.
3. Implement `parallel_ocr_cells()` using Rayon.
4. Implement `aggregate_rows()` with State Machine logic.
5. Output JSON/CSV + Debug Image overlay.

## Critical Checks
- [ ] Line continuity validation (ignore noise).
- [ ] Thread-safe result aggregation.
- [ ] Fallback mechanism if grid detection fails.
- [ ] Visual debugging output for verification.

## Output Format
- Modular Rust code structure.
- Clear error handling (`thiserror`).
- Documentation for tuning parameters.
```