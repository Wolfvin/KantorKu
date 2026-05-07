---
title: AKP2I Kalbar - Project Documentation
kategori: Project Docs & Notes
tags: AKP2I, Tauri, Rust, Axum, DuckDB, desktop-app, UI-UX, WebSocket, LAN-server, tax-consultant
---

# Dokumentasi Lengkap Proyek AKP2I Kalbar
### Rekap 10 Sesi Pengembangan — Semua Topik, Semua Keputusan

> **Dokumen ini** merangkum seluruh pembahasan teknis dan desain dari 10 sesi pengembangan aplikasi desktop internal AKP2I Kalimantan Barat. Disusun per kategori, dari konsep dasar hingga implementasi lanjutan.

---

## Daftar Isi

1. [UI/UX Design](#1-uiux-design)
2. [Halaman Aplikasi (Pages)](#2-halaman-aplikasi-pages)
3. [Arsitektur Frontend](#3-arsitektur-frontend)
4. [Arsitektur Backend](#4-arsitektur-backend)
5. [Keamanan](#5-keamanan)
6. [Integrasi Tauri ↔ Backend](#6-integrasi-tauri--backend)
7. [Workflow & Aturan Pengembangan](#7-workflow--aturan-pengembangan)
8. [Roadmap](#8-roadmap)

---

---

# 1. UI/UX Design

## 1.1 Desain Awal & Brand Identity AKP2I

### Latar Belakang

Proyek ini dimulai dari nol pada Sesi 1. Tidak ada template yang dipakai — desain dibangun langsung dari identitas visual organisasi AKP2I (Asosiasi Konsultan Pajak Publik Indonesia) Cabang Kalimantan Barat.

Referensi desain yang digunakan:
- **Logo AKP2I:** Oval hijau dengan teks "AKP2I" di atas pita merah-kuning (warna bendera Indonesia)
- **Poster dan materi organisasi** yang sudah ada
- **Tagline resmi:** *Mitra Terpercaya Direktorat Jenderal Pajak*

### Filosofi Visual

Keputusan desain pertama yang paling krusial: **ini bukan aplikasi startup**. Pengguna akhirnya adalah konsultan pajak profesional yang terbiasa dengan tools enterprise seperti Excel, SAP, dan DJP Online. Oleh karena itu, kesan visual yang dikejar adalah:

- **Warm & Trustworthy** — bukan cold blue tech yang umum di aplikasi modern
- **Indonesia Pride** — identitas nasional tampil lewat aksen merah-putih yang subtle
- **Professional Tax** — established, reliable, formal
- **Native Desktop** — bukan web app yang dikemas ulang

Pendekatan ini berbeda jauh dari tools pajak umum yang biasanya pakai warna biru dingin atau abu-abu korporat. AKP2I memilih palet hangat berbasis **hijau tua, emas, dan krem** — yang terasa seperti dokumen resmi bermaterai, bukan dashboard SaaS generik.

### Kelebihan Pendekatan Ini
- Membangun kepercayaan visual sejak pertama kali dibuka
- Konsisten dengan identitas organisasi yang sudah dikenal anggota
- Membedakan aplikasi dari tools pajak pemerintah (DJP Online) yang terasa kaku

### Kelemahan / Batasan
- Palet warna spesifik ini tidak bisa sembarangan diganti tanpa merusak identitas brand
- Font Google Fonts (Playfair Display, DM Sans) membutuhkan koneksi internet untuk load pertama kali

---

## 1.2 CSS Variables & Design System

### Konsep Dasar

Design system adalah **kontrak visual** — setiap komponen, warna, bayangan, dan spasi mengacu ke satu sumber kebenaran yang sama. Tanpa ini, setiap developer (atau bahkan Claude di sesi yang berbeda) akan menghasilkan tampilan yang inkonsisten.

Implementasinya menggunakan **CSS Custom Properties** (variabel CSS) yang dideklarasikan di `:root` dan bisa digunakan di seluruh file.

### Palet Warna Lengkap

```css
:root {
  /* Hijau — warna dominan */
  --green-deep:   #0d4a2f;   /* sidebar, titlebar — paling gelap */
  --green:        #1a6b40;   /* elemen utama */
  --green-mid:    #2d8a55;   /* hover, aktif */
  --green-light:  #3dab69;   /* dot status, aksen kecil */

  /* Emas — aksen premium */
  --gold:         #c9922a;   /* gold utama */
  --gold-bright:  #f0b53f;   /* highlight, angka penting */
  --gold-pale:    #fde68a;   /* background subtle gold */

  /* Merah — bahaya & urgency */
  --red:          #c0392b;   /* bahaya, konfirmasi hapus */
  --red-light:    #e74c3c;   /* hover merah */

  /* Background */
  --cream:        #faf7f0;   /* background utama halaman */
  --cream2:       #f3ede0;   /* background sedikit lebih gelap */
  --surface:      #ffffff;   /* card putih */
  --surface2:     #faf7f0;
  --surface3:     #f3ede0;

  /* Teks — hierarki 5 level */
  --t1:           #1a1208;   /* judul utama */
  --t2:           #2d2010;   /* subjudul */
  --t3:           #4a3820;   /* teks isi */
  --t4:           #7a6248;   /* label, keterangan */
  --t5:           #a08b6e;   /* placeholder, hint */

  /* Border */
  --border:       rgba(26,18,8,.08);   /* border halus */
  --border2:      rgba(26,18,8,.14);   /* border normal */
  --border3:      rgba(26,18,8,.22);   /* border tegas */

  /* Bayangan */
  --shadow-sm:    0 2px 8px rgba(13,74,47,.08);
  --shadow-md:    0 8px 28px rgba(13,74,47,.13);
  --shadow-lg:    0 20px 60px rgba(13,74,47,.18);

  /* Border radius */
  --r-sm: 8px; --r-md: 12px; --r-lg: 18px; --r-xl: 24px;

  /* Tipografi */
  --font:  'DM Sans', sans-serif;
  --serif: 'Playfair Display', serif;
  --mono:  'DM Mono', monospace;
}
```

### Sistem Tipografi

Tiga font digunakan dengan peran yang berbeda:

| Font | Digunakan Untuk | Contoh |
|------|-----------------|--------|
| **Playfair Display** (serif) | Judul besar, halaman header | "PDF Extractor", "Dashboard" |
| **DM Sans** (sans-serif) | Body text, tombol, label | Semua teks paragraf & UI |
| **DM Mono** (monospace) | Kode, path file, angka, timestamp | `2026-04-01 08:42`, `/path/to/file` |

Import Google Fonts (wajib di setiap file):
```html
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
```

### Animasi Standar

```css
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

Dipakai untuk semua elemen yang muncul saat halaman dimuat — cards, tabel, form. Durasi standar: `0.3s ease`.

### Kelebihan Design System Ini
- Konsistensi terjamin meskipun dikerjakan lintas sesi atau oleh orang berbeda
- Perubahan warna bisa dilakukan di satu tempat, efek ke seluruh app
- Hierarki warna hijau 4 level memungkinkan depth visual yang kaya

### Kelemahan / Batasan
- Tidak ada dark mode — sengaja tidak diimplementasi (konsultan pajak kerja di lingkungan terang)
- CSS Variables tidak didukung IE11, tapi ini tidak relevan karena app berjalan di Tauri (Chromium engine)

---

## 1.3 Standar Komponen UI

### Konsep Dasar

Komponen UI adalah blok bangunan yang dipakai berulang di seluruh halaman. Dengan mendefinisikan standar tiap komponen, tampilan semua halaman menjadi seragam tanpa perlu menyalin kode.

### Titlebar Custom

```
Tinggi: 40px | Background: --green-deep | Draggable: data-tauri-drag-region
```

Titlebar menggunakan macOS-style window dots (tiga lingkaran kecil untuk close/minimize/maximize). Ini berbeda dari Windows-style karena lebih elegan dan tidak terlalu mencolok saat digunakan seharian.

**Mengapa custom titlebar?** Tauri dikonfigurasi dengan `"decorations": false` — artinya OS tidak menambahkan titlebar native. Titlebar HTML ini yang menggantikannya, sehingga desain titlebar sepenuhnya dalam kendali developer.

### Tombol — 4 Jenis

| Jenis | Tampilan | Digunakan Untuk |
|-------|----------|-----------------|
| **Primary** | Gradient hijau, teks putih | Proses/Submit — aksi utama |
| **Gold** | Gradient emas, teks `--green-deep` | Download, CTA penting |
| **Ghost** | Transparan, border `--border2` | Aksi sekunder, cancel |
| **Danger** | Transparan, border merah, teks merah | Hapus, revoke |

### Cards

- Background: `--surface` (putih)
- Border: `1px solid var(--border)`
- Shadow: `var(--shadow-sm)`
- Hover: `translateY(-3px)` + `var(--shadow-md)` + transisi 0.2s
- Top accent: border atas 3px berwarna (tiap card bisa beda warna sesuai konteks)

### Log Box (Terminal Output)

Log box adalah komponen `<pre>` atau `<div>` yang menampilkan output proses seperti terminal. Digunakan di halaman PDF Renamer, Extractor, dll.

```
Header: background --green-deep | teks --gold-bright | font DM Mono
Body: padding 18px | font DM Mono | auto-scroll ke bawah
```

Warna teks per jenis pesan:
- `log-ok` → hijau `#3dab69` — sukses
- `log-error` → merah `#e74c3c` — error
- `log-warn` → emas `#f0b53f` — peringatan
- `log-info` → putih 38% opacity — informasi biasa
- `log-renamed` → biru `#60a5fa` — file berhasil direname

### Upload Zone

```
Border: 2px dashed var(--border2)
Hover: border berubah ke var(--green) + translateY(-2px)
Isi: ikon, teks petunjuk, tombol "Pilih File"
```

### Status Pills

Bukan warna solid — menggunakan tinted background:
- Aktif/Berhasil → hijau tinted (background `rgba(45,138,85,.1)` + teks `--green-mid`)
- Peringatan/Pending → emas tinted
- Error/Ditolak → merah tinted
- Info → biru tinted

---

## 1.4 Pola Desain Split Panel — Standar Extractor

### Latar Belakang Keputusan

Pada Sesi 6, sebelum membuat halaman extractor, tiga opsi desain dipresentasikan:
- **Opsi A:** Form vertikal tradisional — upload di atas, tombol di bawah
- **Opsi B:** Split Panel — upload kiri, stats kanan secara horizontal
- **Opsi C:** Wizard step-by-step — pilih tipe → upload → proses → download

Raymond memilih **Opsi B (Split Panel)** karena:
1. Semua informasi terlihat sekaligus tanpa scroll
2. Konsultan bisa monitor status sambil upload lebih banyak file
3. Terasa seperti professional tool, bukan form web biasa

### Detail Split Panel

**Bank/Mode Selector** (untuk halaman yang punya pilihan tipe):
Kartu 4 kolom dengan warna identitas masing-masing bank:

| Bank | Warna Identitas |
|------|----------------|
| BCA | `#005baa` (biru BCA) |
| BRI | `#003d7c` (biru BRI) |
| BNI | `#f77f00` (oranye BNI) |
| Mandiri | `#003087` (biru Mandiri) |

Active state: border `var(--green)` + background `rgba(13,74,47,.06)`

**Layout Panel:**
- **Panel Kiri:** Upload zone — dashed border, drag & drop, pilih file
- **Panel Kanan:** Stats vertikal — label kecil kiri, angka besar kanan
  - Total PDF dipilih
  - Berhasil diproses
  - Gagal / Error
  - Status (Siap / Memproses / Selesai)
- **Bawah panel:** Tombol "Proses" (gold, full width) + "Download" (green outline, full width)

**Untuk halaman tanpa bank selector:** Panel kanan tetap dipakai untuk stats/status — pola konsisten.

### Kelebihan Split Panel
- Data-dense tanpa terasa sesak
- User tidak perlu scroll bolak-balik
- Cocok untuk workflow berulang (upload → proses → download)

### Kelemahan / Batasan
- Tidak ideal untuk layar kecil (tapi app ini untuk desktop, bukan mobile)
- Membutuhkan minimum lebar ~900px untuk tampil nyaman

---

---

# 2. Halaman Aplikasi (Pages)

> Semua halaman adalah `<section>` di dalam `index.html` — bukan file HTML terpisah. Tauri hanya load satu file entry point.

## 2.1 Page Dashboard

**ID:** `page-dashboard` | **Nav:** 🏠 Dashboard | **Status:** ✅ Selesai

### Fungsi & Konten

Dashboard adalah halaman pertama yang dilihat saat app dibuka. Tujuannya: memberikan gambaran penuh situasi hari ini dalam satu layar.

**Komponen utama:**

**1. Stats Row (atas)** — 4 angka besar:
- Total dokumen diproses hari ini
- Anggota aktif online
- Deadline mendatang (7 hari ke depan)
- Dokumen pending

**2. Donut Chart** — visualisasi distribusi tipe dokumen:
- E-Faktur Keluaran
- E-Faktur Masukan
- BPPU / BP21
- Rekening Koran

**3. Dokumen Terkini** — tabel aktivitas real-time: siapa, tipe dokumen, waktu, jumlah

**4. Deadline Panel** — daftar deadline klien yang mendekat, dengan kode warna urgensi (merah = ≤3 hari, kuning = ≤7 hari, hijau = >7 hari)

**5. Daftar Anggota** — status online/offline semua konsultan di jaringan LAN

### Status Data Saat Ini
Semua angka masih **hardcode** (data dummy). Setelah backend Rust selesai, data akan diambil dari server via REST API dan diperbarui real-time lewat WebSocket.

---

## 2.2 Page Settings & Control Panel

**ID:** `page-settings` | **Nav:** ⚙️ Settings | **Status:** ✅ Selesai

### Struktur

Settings menggunakan navigasi inner sendiri — bukan popup, tapi panel yang swap di kanan. Ada dua lapisan:

**Layer 1 — Control Panel (4 panel aktif):**

| Panel | Fungsi |
|-------|--------|
| File System (`cp-fs`) | Atur folder output default, folder monitoring |
| Notifikasi (`cp-notif`) | Toggle notifikasi OS per jenis event |
| Autostart (`cp-autostart`) | Jalankan app otomatis saat Windows startup |
| Izin Aplikasi (`cp-izin`) | Kelola permission akses file dan folder |

**7 panel placeholder** menunggu implementasi: Tampilan, Keamanan & Akun, Koneksi & Sinkronisasi, Sumber Daya, Log Sistem, Pembaruan, dan lainnya.

**Layer 2 — Setup Aplikasi (Overlay Config):**
Overlay yang muncul di atas panel ketika user klik "Setup" di halaman extractor yang relevan:

| Overlay | Konten |
|---------|--------|
| `settings-efaktur-config` | Path folder, format nama file, aturan ekstraksi E-Faktur |
| `settings-bupot-config` | Konfigurasi E-Bupot Combiner |
| `settings-rekening-config` | Pilihan bank, format tanggal, kolom yang diekstrak |
| `settings-edokumen-config` | Pengaturan folder dokumen umum |
| `settings-scan-config` | DPI default, format output scan |

### Cara Kerja Navigasi Inner Settings

```javascript
document.querySelectorAll('.cp-nav-link').forEach(link => {
  link.addEventListener('click', () => {
    const section = link.dataset.cpSection;
    // Sembunyikan semua cp-section
    document.querySelectorAll('.cp-section').forEach(s => s.style.display = 'none');
    // Tampilkan yang dipilih
    document.getElementById('cp-' + section).style.display = 'flex';
  });
});
```

---

## 2.3 Page Extractor + Subpages

**ID:** `page-extractor` | **Nav:** 📄 PDF Extractor | **Status:** ✅ Selesai

### Halaman Landing (Command Palette Style)

Halaman pertama extractor menampilkan daftar layanan dalam format command palette — setiap item punya accent bar warna berbeda, badge "Tersedia"/"Segera", dan deskripsi singkat.

### Subpage 1: Rekening Koran

Mengekstrak data transaksi dari PDF rekening koran bank. Menggunakan Split Panel dengan bank selector (BCA, BRI, BNI, Mandiri).

**Output yang diekstrak:**
- Tanggal transaksi
- Keterangan/narasi
- Debet / Kredit / Saldo

**Flow:** Pilih bank → Upload PDF → Proses → Preview hasil → Download Excel

### Subpage 2: Dokumen (BPPU & BP21)

Dua tipe dokumen pajak pemotongan dalam satu subpage:

- **BPPU** (Bukti Pemotongan Pajak Unifikasi) — format baru sejak Coretax
- **BP21** (Bukti Pemotongan PPh Pasal 21) — format lama

**Perbedaan penanganan:** Format PDF keduanya berbeda, sehingga parser yang digunakan berbeda. Tapi UI-nya identik — konsultan tidak perlu tahu perbedaan teknis ini.

### Subpage 3: E-Faktur Keluaran

Mengekstrak data dari PDF E-Faktur pajak keluaran:
- Nomor Faktur
- NPWP / Nama Pembeli
- DPP (Dasar Pengenaan Pajak)
- PPN (Pajak Pertambahan Nilai)
- Tanggal Faktur

**Output:** Excel siap upload ke sistem klien atau laporan internal.

### Navigasi Antar Subpage

```javascript
function showExtractorSubpage(type) {
  // Sembunyikan semua subpage
  document.querySelectorAll('.extractor-subpage').forEach(p => p.style.display = 'none');
  // Sembunyikan landing
  document.getElementById('extractor-home-page').style.display = 'none';
  // Tampilkan subpage yang diminta
  document.getElementById(`subpage-${type}`).style.display = 'block';
}
```

---

## 2.4 Page Merge Excel (E-Bupot Combiner)

**ID:** `page-excel` | **Nav:** 📊 Merge Excel | **Status:** ✅ Selesai

### Fungsi

Menggabungkan banyak file Excel E-Bupot (Bukti Pemotongan Unifikasi) dari berbagai klien menjadi satu file Excel terpadu. Pekerjaan ini biasanya dilakukan manual — copy-paste satu per satu — dan sangat rentan error.

### UI Split Panel

- **Kiri:** Upload zone untuk banyak file `.xlsx` sekaligus
- **Kanan:** Stats — jumlah file diupload, total baris data, status proses
- **Bawah:** Tombol "Gabungkan" (gold) + "Download Hasil" (green outline)

### Use Case Nyata

Seorang konsultan menangani 30 klien. Setiap klien punya file E-Bupot bulanan. Daripada buka Excel, copy sheet satu per satu (30× per bulan), cukup drag semua file ke halaman ini, klik Gabungkan, download hasilnya.

---

## 2.5 Page PDF Renamer (4 Subpage)

**ID:** `page-renamer` | **Nav:** 🏷️ PDF Renamer | **Status:** ✅ Selesai (dengan file CSS terpisah `page-renamer.css`)

### Fungsi

Mengubah nama file PDF pajak dari nama generik (biasanya berupa kode acak dari sistem DJP) menjadi nama yang terstruktur dan mudah dicari.

### 4 Tipe Dokumen yang Didukung

| Tipe | Contoh Nama Sebelum | Contoh Nama Sesudah |
|------|---------------------|---------------------|
| **Faktur Keluaran** | `A1234567890.pdf` | `FK_010.000-24.12345678_PT Maju Sejahtera.pdf` |
| **Faktur Masukan** | `FP-202412-001.pdf` | `FM_2024-12_PT Sumber Makmur_3500000.pdf` |
| **BPPU** | `BPPU_20241201.pdf` | `BPPU_2024-12_CV Karya Abadi_PPh23.pdf` |
| **BP21** | `bp_dec2024.pdf` | `BP21_2024-12_Budi Santoso_PPh21.pdf` |

### Cara Kerja

1. User memilih tipe dokumen dari halaman landing (4 kartu besar)
2. Upload banyak PDF sekaligus
3. App membaca isi PDF, ekstrak informasi kunci
4. Preview daftar nama baru sebelum eksekusi
5. Rename semua file sekaligus
6. Log box menampilkan hasil per file

### File CSS Terpisah

Karena `page-renamer` punya banyak class spesifik (`rnm-*`), CSS-nya dipisah ke `page-renamer.css` dan di-link setelah `style.css` di `<head>`. Ini untuk menghindari file `style.css` yang terlalu besar.

---

## 2.6 Page Anggota

**ID:** `page-anggota` | **Nav:** 👥 Anggota | **Status:** ✅ Selesai (dengan `page-anggota.css` + `page-anggota.js`)

### Desain: Bento Grid

Halaman anggota menggunakan desain **bento grid** — 4 kolom kartu dengan ukuran yang bisa bervariasi. Setiap kartu anggota berisi:

- **Avatar** (inisial nama, background warna custom per anggota)
- **Nama lengkap** dan jabatan
- **Badge Brevet** — hijau jika sudah lulus Brevet AB, abu jika belum
- **Kutipan** pendek (opsional, bisa dikosongkan)
- **Status online/offline** — dot hijau/abu

### Warna Custom Per Anggota

Setiap anggota punya warna avatar yang unik — tidak ada dua anggota dengan warna sama. Warna dipilih dari palet yang tetap terlihat baik di atas background hijau tua.

### Data dari JavaScript

Data anggota disimpan di `page-anggota.js` sebagai array of objects, bukan hardcode di HTML. Ini memudahkan penambahan atau perubahan anggota.

```javascript
// Contoh struktur data di page-anggota.js
const ANGGOTA = [
  {
    nama: "Raymond Fo",
    jabatan: "Ketua / Developer",
    warna: "#0d4a2f",
    brevet: true,
    kutipan: "Build things that matter."
  },
  // ...
];
```

---

## 2.7 Page Pengumuman + Agenda (Digabung)

**ID:** `page-pengumuman` + `page-agenda` | **Status:** ✅ Selesai | **Script:** `page-pengumuman-agenda.js`

### Alasan Digabung

Pengumuman dan Agenda adalah dua fitur yang saling terkait — sebuah pengumuman bisa tentang agenda FGD, dan agenda butuh pengumuman untuk disebarkan. Menggabungkan keduanya dalam satu halaman akar (dengan tab switch) mengurangi navigasi yang tidak perlu.

### Halaman Pengumuman

Layout **newspaper-style:**
- Hero post di atas (pengumuman terpinned / terbaru)
- 3 kolom artikel di bawah
- Toolbar: filter kategori (Pajak, Organisasi, FGD, Brevet, Umum) + tombol "Buat Pengumuman"
- Modal popup untuk membuat pengumuman baru

Kategori pengumuman sesuai skema database:
- `pajak` — perubahan peraturan perpajakan
- `organisasi` — kegiatan internal AKP2I
- `fgd` — Forum Group Discussion
- `brevet` — Kelas Brevet AB
- `umum` — lainnya

### Halaman Agenda & FGD

- **Mini calendar** — tampilan bulan berjalan dengan titik pada tanggal yang ada event
- **Filter pills** — FGD, Brevet, Rapat, Deadline
- **Event list** — daftar agenda urut tanggal dengan label kategori berwarna
- Klik tanggal di calendar → filter list ke tanggal itu

---

## 2.8 Page Scan Assistance

**ID:** `page-scan` | **Nav:** 🔍 Scan Assistance | **Status:** ✅ Selesai | **Script:** `scans-guide.js`

### Fungsi

Panduan interaktif penggunaan scanner untuk konsultan yang perlu scan dokumen pajak fisik (SPT, faktur cetak, rekening koran cetak). Bukan hanya panduan teks statis — ada hotkey guide interaktif.

### Konten

- **Panduan pengaturan DPI** — rekomendasi DPI per jenis dokumen:
  - Rekening Koran: 200 DPI cukup
  - Faktur/SPT: 300 DPI
  - Dokumen kuno/buram: 400-600 DPI
- **Format output yang direkomendasikan** — PDF/A untuk arsip jangka panjang
- **Hotkey interaktif** — user bisa klik/hover shortcut scanner untuk lihat fungsinya
- **Tips troubleshooting** — halaman miring, warna pudar, ukuran file terlalu besar

---

## 2.9 Page Expired (Akses Ditolak)

**ID:** `page-expired` | **Status:** ✅ Selesai | **CSS:** `page-expired.css`

### Fungsi & Desain

Halaman ini muncul ketika hardware ID PC tidak terdaftar di whitelist server, atau sudah di-revoke oleh Raymond.

Desain: **Seal card resmi** — tampilan seperti stempel/segel resmi dokumen, dengan:
- Badge merah besar "AKSES DITOLAK"
- Penjelasan singkat alasan (tidak terdaftar / akses dicabut / server tidak bisa dihubungi)
- Tombol **WhatsApp** langsung ke Raymond Fo (085849164168)
- Instruksi cara mendaftarkan PC

### Kapan Halaman Ini Muncul?

1. **PC baru belum terdaftar** — pernah install app tapi belum di-approve Raymond
2. **Akses di-revoke** — karyawan resign, Raymond cabut akses dari Developer Panel
3. **Server tidak bisa dihubungi + cache expired** — sudah lewat 1 hari sejak validasi terakhir

---

## 2.10 Page Owner, Aktivitas, Developer Panel (Dev-Only)

**Status:** ✅ Selesai | **Akses:** Alt+Shift+D + password `akp2idev2026`

### Mengapa Dev-Only?

Ketiga halaman ini berisi informasi sensitif atau tool administrasi yang tidak boleh dilihat konsultan biasa. Mereka disembunyikan di sidebar sampai Dev Mode diaktifkan.

### Page Owner

Stats dan ringkasan sistem dari sudut pandang pemilik:
- Total PC terdaftar
- Total dokumen diproses sejak awal
- Versi app yang beredar di tiap PC
- (Placeholder — data real menunggu backend)

### Page Aktivitas Pengguna

Tabel monitoring real-time semua PC di jaringan:

| Kolom | Isi |
|-------|-----|
| PC Name | Nama device |
| User | Nama konsultan |
| Status | 🟢 Online / 🔴 Offline |
| Versi | Versi app terpasang |
| Dokumen Hari Ini | Jumlah dokumen diproses |
| Last Active | Timestamp terakhir aktif |

### Page Developer Panel

Tool administrasi untuk Raymond:
- **Whitelist management** — lihat, tambah, revoke PC
- **Kill switch** — lock semua app sekaligus (untuk situasi darurat)
- **App info** — versi server, uptime, jumlah koneksi aktif
- **Log viewer** — (planned) lihat log server real-time

---

---

# 3. Arsitektur Frontend

## 3.1 Restrukturisasi File HTML/CSS/JS Terpisah

### Latar Belakang (Sesi 5)

Sebelum Sesi 5, setiap halaman mockup adalah file HTML terpisah dengan `<style>` dan `<script>` inline. Ini tidak bisa dipakai sebagai aplikasi Tauri karena Tauri hanya load satu entry point HTML.

Sesi 5 melakukan **restrukturisasi besar** — semua halaman digabung ke dalam tiga file utama:

```
akp2i-app/
├── index.html                   ← Satu-satunya HTML entry point
├── styles/
│   └── style.css                ← Semua CSS shared
├── page-renamer.css             ← CSS tambahan PDF Renamer
├── page-anggota.css             ← CSS Anggota + Pengumuman + Agenda
├── page-expired.css             ← CSS halaman expired
├── app.js                       ← JS utama: navigasi, sidebar, dev mode
├── page-anggota.js              ← Data + render anggota
├── page-pengumuman-agenda.js    ← Data + render pengumuman & agenda
├── scans-guide.js               ← Hotkey guide scan
└── order_food_page.html         ← Di-embed via iframe di page-food
```

**Aturan mutlak:** Semua page adalah `<section id="page-xxx">` di dalam `index.html`. Tidak ada file HTML lain yang di-load langsung (kecuali iframe order food).

### Kelebihan Arsitektur Ini
- Compatible dengan Tauri — satu entry point
- CSS bisa di-share antar halaman tanpa duplikasi
- JS `app.js` mengelola state global (nav aktif, dev mode, dll)

### Kelemahan / Batasan
- `index.html` bisa jadi sangat panjang seiring halaman bertambah
- Semua halaman di-load sekaligus ke memory (tidak ada lazy loading) — tapi untuk 15-20 halaman ini masih sangat ringan

---

## 3.2 Sistem Navigasi SPA Manual

### Konsep

Tanpa React Router, Vue Router, atau framework apapun. Navigasi dikelola sepenuhnya oleh `app.js` dengan mekanisme show/hide CSS.

### Mekanisme

**CSS yang mengatur visibility:**
```css
.page-section          { display: none; }
.page-section.active   { display: block; }
```

**Fungsi navigasi utama:**
```javascript
function navigateTo(pageId) {
  // 1. Sembunyikan semua page
  document.querySelectorAll('.page-section')
    .forEach(s => s.classList.remove('active'));
  
  // 2. Tampilkan page yang diminta
  document.getElementById('page-' + pageId).classList.add('active');
  
  // 3. Update active state sidebar
  document.querySelectorAll('.nav-item')
    .forEach(n => n.classList.remove('active'));
  document.querySelector(`[data-page="${pageId}"]`)?.classList.add('active');
  
  // 4. Update titlebar & breadcrumb
  document.getElementById('titlebar-page').textContent = PAGE_TITLES[pageId] || pageId;
  document.getElementById('topbar-title').textContent  = PAGE_TITLES[pageId] || pageId;
  document.getElementById('breadcrumb-page').textContent = BREADCRUMBS[pageId] || pageId;
  
  // 5. Simpan state halaman aktif
  currentPage = pageId;
}
```

**Daftar PAGE_TITLES:**
```javascript
const PAGE_TITLES = {
  'dashboard':   '🏠 Dashboard',
  'anggota':     '👥 Anggota',
  'pengumuman':  '📢 Pengumuman',
  'agenda':      '📅 Agenda & FGD',
  'extractor':   '📄 PDF Extractor',
  'excel':       '📊 Merge Excel',
  'scan':        '🔍 Scan Assistance',
  'renamer':     '🏷️ PDF Renamer',
  'downloader':  '⬇️ Smart Downloader',
  'settings':    '⚙️ Settings',
  'food':        '🍱 Order Food',
  'owner':       '👑 Owner Page',
  'aktivitas':   '📊 Aktivitas Pengguna',
  'developer':   '🖥️ Developer Panel',
};
```

### Perbandingan dengan Framework Router

| Aspek | SPA Manual (AKP2I) | React Router / Vue Router |
|-------|-------------------|--------------------------|
| Bundle size | 0KB overhead | +50-200KB |
| Dependency | Tidak ada | npm packages |
| Kompleksitas | Rendah | Sedang-Tinggi |
| Deep linking (URL) | Tidak didukung | Didukung |
| Code splitting | Manual | Otomatis |
| Cocok untuk | App internal ≤20 halaman | App publik banyak halaman |

Untuk kebutuhan AKP2I (aplikasi desktop internal, ~15 halaman, tidak butuh URL sharing), SPA manual adalah pilihan yang tepat dan jauh lebih ringan.

---

## 3.3 Sistem Subnavigasi (Subpage dalam Page)

### Konsep

Beberapa halaman punya "subpage" internal — halaman di dalam halaman. Mekanismenya identik dengan navigasi utama, hanya lingkupnya terbatas pada `<section>` induk.

### Implementasi di PDF Renamer

```javascript
function navigateToPdfRenamerSubpage(type) {
  // Sembunyikan landing
  document.getElementById('pdf-renamer-landing').style.display = 'none';
  // Sembunyikan semua subpage
  ['faktur-keluaran', 'faktur-masukan', 'bppu', 'bp21'].forEach(t => {
    document.getElementById(`pdf-renamer-${t}-subpage`).style.display = 'none';
  });
  // Tampilkan yang dipilih
  document.getElementById(`pdf-renamer-${type}-subpage`).style.display = 'block';
}

function backToPdfRenamerLanding() {
  ['faktur-keluaran', 'faktur-masukan', 'bppu', 'bp21'].forEach(t => {
    document.getElementById(`pdf-renamer-${t}-subpage`).style.display = 'none';
  });
  document.getElementById('pdf-renamer-landing').style.display = 'block';
}
```

### Halaman yang Menggunakan Subnavigasi

| Halaman | Subpage |
|---------|---------|
| `page-extractor` | home-page, subpage-rekening, subpage-dokumen, subpage-bppu, subpage-bp21, subpage-efaktur-keluar |
| `page-renamer` | landing, faktur-keluaran, faktur-masukan, bppu, bp21 |
| `page-settings` | 4 panel aktif + overlay config (efaktur, bupot, rekening, edokumen, scan) |

---

## 3.4 Dev Mode

### Mekanisme

Dev Mode adalah fitur tersembunyi yang hanya diketahui Raymond. Ketika aktif, sidebar menampilkan section tambahan "🛠 Dev Zone" berisi halaman-halaman administrasi.

**Cara aktivasi:** `Alt + Shift + D` → modal password muncul → masukkan `akp2idev2026`

**Implementasi:**
```javascript
const DEV_PASSWORD = 'akp2idev2026';
let devModeActive = false;

document.addEventListener('keydown', e => {
  if (e.altKey && e.shiftKey && e.key === 'D') {
    if (devModeActive) exitDevMode();
    else document.getElementById('dev-modal').style.display = 'flex';
  }
});

function enterDevMode() {
  devModeActive = true;
  // Tampilkan elemen dev di sidebar
  document.querySelectorAll('.nav-dev-separator, .dev-label, .dev-item')
    .forEach(el => { el.style.display = 'flex'; });
  document.getElementById('dev-mode-badge').style.display = 'flex';
}

function exitDevMode() {
  devModeActive = false;
  document.querySelectorAll('.nav-dev-separator, .dev-label, .dev-item')
    .forEach(el => { el.style.display = 'none'; });
  document.getElementById('dev-mode-badge').style.display = 'none';
  // Kalau sedang di dev page, balik ke dashboard
  if (['owner','aktivitas','developer'].includes(currentPage)) {
    navigateTo('dashboard');
  }
}
```

**Visual Dev Zone di Sidebar:**
```
━━━━━━━━━━━━━━━  ← separator emas
🛠 Dev Zone
  👑 Owner Page
  📊 Aktivitas Pengguna
  🖥️ Developer Panel
```

### Pertimbangan Keamanan

Password ini disimpan di `app.js` sebagai plaintext — ini **bukan** keamanan tinggi, tapi cukup untuk tujuannya: menyembunyikan halaman admin dari konsultan yang secara tidak sengaja menekan tombol. Keamanan sebenarnya ada di sistem validasi backend (hardware ID + whitelist).

---

## 3.5 Komponen & Pattern Teknis Tambahan

### Sidebar Collapse

```css
.sidebar.collapsed { width: 64px; }
.sidebar.collapsed .nav-label,
.sidebar.collapsed .logo-text { display: none; }
/* Tooltip otomatis saat hover di mode collapsed */
.sidebar.collapsed .nav-item:hover::after {
  content: attr(data-tooltip);
  position: absolute; left: 70px;
  background: var(--green-deep); color: #fff;
  padding: 4px 10px; border-radius: 6px;
  font-size: .73rem; white-space: nowrap;
}
```

### Titlebar Custom (Tauri)

```html
<div class="titlebar" data-tauri-drag-region>
  <button id="btn-minimize">─</button>
  <button id="btn-maximize">□</button>
  <button id="btn-close">✕</button>
</div>
```

```javascript
import { Window } from '@tauri-apps/api/window';
const appWindow = new Window('main');
document.getElementById('btn-minimize').addEventListener('click', () => appWindow.minimize());
document.getElementById('btn-maximize').addEventListener('click', () => appWindow.toggleMaximize());
document.getElementById('btn-close').addEventListener('click', () => appWindow.close());
```

`data-tauri-drag-region` adalah atribut spesial Tauri — area ini bisa di-drag untuk memindahkan window OS, seperti titlebar native.

### Upload File — Dua Cara

**Cara A: `<input type="file">` HTML native** — sudah berfungsi di Tauri, cukup untuk saat ini.

**Cara B: Tauri `dialog.open()`** — menampilkan file picker native OS, lebih profesional. Diimplementasi setelah integrasi Tauri commands.

```javascript
// Cara B — dipakai nanti
import { open } from '@tauri-apps/plugin-dialog';
const files = await open({
  multiple: true,
  filters: [{ name: 'PDF', extensions: ['pdf'] }]
});
```

### Modal / Popup Dialog

Modal diletakkan di luar `.app-shell` agar muncul di atas semua halaman:

```html
<!-- Di dalam #window, setelah .app-shell -->
<div class="modal-overlay" id="ann-modal">
  <div class="modal-box"> ... </div>
</div>
```

```css
.modal-overlay {
  display: none;
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,.4);
  align-items: center; justify-content: center;
}
```

### Cara Preview Mockup di Browser (Tanpa Tauri)

Buka `index.html` langsung di Chrome/Edge. Yang berfungsi: navigasi sidebar, upload file input, CSS/animasi. Yang **tidak** berfungsi: minimize/maximize/close, drag window, native file picker, OS notification, akses filesystem lokal.

### Build Tauri

```bash
cargo install tauri-cli
cargo tauri dev      # dev mode (hot reload)
cargo tauri build    # build .exe / .dmg / .AppImage
```

Konfigurasi penting di `tauri.conf.json`:
```json
{
  "app": {
    "windows": [{
      "decorations": false    // WAJIB — nonaktifkan titlebar OS native
    }]
  }
}
```

---

---

# 4. Arsitektur Backend

## 4.1 Stack Teknologi: Tauri v2 + Vanilla JS

### Mengapa Tauri v2?

**Tauri vs Electron — Perbandingan:**

| Aspek | Tauri v2 | Electron |
|-------|----------|----------|
| Bundle size | ~5-10 MB | ~150-300 MB |
| Memory usage | ~50-80 MB | ~200-500 MB |
| Engine | WebView OS (Chromium/WebKit) | Bundled Chromium |
| Backend | Rust | Node.js |
| Startup time | Cepat | Lebih lambat |
| Keamanan | Lebih ketat (allowlist) | Lebih longgar |
| Ekosistem | Berkembang | Mature |

Untuk konsultan yang kerja seharian, performa dan memory usage adalah faktor penting. Tauri jauh lebih ringan dari Electron.

### Mengapa Vanilla JS (bukan React/Vue)?

Keputusan ini sadar dan terencana:
1. **Zero build step** — tidak perlu webpack, vite, atau bundler. File HTML langsung jalan.
2. **Mudah di-maintain Raymond** — tidak perlu paham React ecosystem untuk modifikasi kecil
3. **Ukuran lebih kecil** — tidak ada framework overhead
4. **Cukup untuk kebutuhan** — app internal dengan ~15 halaman tidak memerlukan reaktivitas kompleks

### 6 Plugin Tauri v2 yang Digunakan

| Plugin | Fungsi |
|--------|--------|
| `plugin-fs` | Baca/tulis file, watch folder perubahan |
| `plugin-notification` | Notifikasi native OS |
| `plugin-autostart` | Daftar ke registry Windows startup |
| `plugin-dialog` | File/folder picker native OS |
| `plugin-shell` | Buka folder di Windows Explorer |
| `plugin-updater` | Auto-update dari server LAN *(planned)* |

---

## 4.2 Arsitektur Server LAN: Rust + Axum

### Desain Topologi

```
Office WiFi LAN (192.168.x.x)
──────────────────────────────────
  PC Admin / Hub (Raymond)
  ┌─────────────────────────┐
  │   akp2i-server (Rust)   │
  │   ├─ Axum REST API :3000│
  │   ├─ WebSocket Hub :3001│
  │   ├─ Update Server :3002│
  │   ├─ DuckDB (analytics) │
  │   └─ SQLite (state)     │
  └─────────────────────────┘
            │ LAN WiFi
    ┌───────┼───────┬───────┐
   PC1     PC2    PC3  ...PC20+
  Tauri   Tauri  Tauri  Tauri
```

**Prinsip utama:**
- **Satu binary** — server Rust jalan di PC Raymond, tidak ada daemon terpisah
- **LAN only** — tidak ada traffic ke internet, data pajak klien tidak pernah keluar kantor
- **Zero-config client** — PC baru tinggal daftar hardware ID, tidak perlu setup manual

### Mengapa Rust?

| Aspek | Rust | Node.js | Go |
|-------|------|---------|-----|
| Performance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Memory safety | Compile-time guaranteed | Runtime | Runtime |
| Binary size | Kecil | Butuh runtime | Kecil |
| Tauri integration | Native (satu bahasa) | Terpisah | Terpisah |
| Learning curve | Tinggi | Rendah | Sedang |

Karena Tauri sudah pakai Rust, backend server pun pakai Rust — satu bahasa untuk semua backend code, mudah berbagi library dan tipe data.

### Struktur Direktori Server

```
akp2i-server/
├── src/
│   ├── main.rs              ← entry point, setup router, bind port
│   ├── db.rs                ← DuckDB init, schema, query helpers
│   ├── auth.rs              ← hardware_id validation, whitelist check
│   ├── models.rs            ← semua struct: Device, Announcement, WsEvent, dll
│   ├── routes/
│   │   ├── mod.rs
│   │   ├── devices.rs       ← GET/POST/DELETE /api/devices
│   │   ├── announcements.rs ← CRUD /api/announcements
│   │   ├── agenda.rs        ← CRUD /api/agenda
│   │   ├── documents.rs     ← POST /api/documents/processed
│   │   └── presence.rs      ← GET /api/presence
│   └── ws/
│       ├── mod.rs
│       └── hub.rs           ← WebSocket hub + broadcast engine
└── Cargo.toml
```

### REST API Endpoints

| Method | Path | Fungsi |
|--------|------|--------|
| GET | `/api/devices` | List semua PC terdaftar |
| POST | `/api/devices` | Daftarkan PC baru |
| DELETE | `/api/devices/:id` | Revoke akses PC |
| POST | `/api/validate` | Validasi hardware ID saat startup |
| GET | `/api/announcements` | List pengumuman |
| POST | `/api/announcements` | Buat pengumuman baru |
| GET | `/api/agenda` | List agenda |
| POST | `/api/agenda` | Buat agenda baru |
| POST | `/api/documents` | Log dokumen yang diproses |
| GET | `/api/presence` | Status online/offline semua PC |
| GET | `/ws` | WebSocket connection endpoint |

---

## 4.3 Database: DuckDB + Apache Arrow

### Mengapa Bukan PostgreSQL?

Keputusan ini diambil di Sesi 3 setelah membandingkan beberapa opsi:

| Aspek | DuckDB | PostgreSQL | SQLite |
|-------|--------|-----------|--------|
| Setup | Zero (embedded) | Install server | Zero (embedded) |
| Analitik (GROUP BY, SUM, agregasi) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| Concurrent writes | Terbatas (1 writer) | ⭐⭐⭐⭐⭐ | Terbatas |
| Export ke Excel | Native via Arrow | Manual | Manual |
| Arrow columnar | Native | Tidak | Tidak |
| Cocok untuk | Analytics + OLAP | OLTP high-concurrency | Simple CRUD |

Untuk skala AKP2I (20 PC, ribuan faktur per bulan), DuckDB adalah pilihan optimal karena:
- **Embedded** — jalan di dalam Rust binary, zero setup di PC Raymond
- **Columnar storage** — agregasi ribuan faktur dalam milliseconds (`SELECT SUM(dpp) FROM efaktur WHERE bulan = 3`)
- **SQL biasa** — tidak perlu belajar query language baru
- **Arrow native** — export ke Excel via `Arrow → Polars → xlsx` sangat cepat

### Schema Database

```sql
-- Whitelist PC
CREATE TABLE IF NOT EXISTS devices (
    id            VARCHAR PRIMARY KEY,   -- SHA256 dari hardware fingerprint
    name          VARCHAR NOT NULL,      -- "PC1 — Raymond"
    user_name     VARCHAR NOT NULL,
    app_version   VARCHAR DEFAULT '0.0.0',
    is_active     BOOLEAN DEFAULT true,
    registered_at TIMESTAMP DEFAULT now(),
    last_seen     TIMESTAMP
);

-- Pengumuman
CREATE TABLE IF NOT EXISTS announcements (
    id         VARCHAR PRIMARY KEY,
    title      VARCHAR NOT NULL,
    body       TEXT,
    category   VARCHAR DEFAULT 'umum',   -- pajak, organisasi, fgd, brevet, umum
    is_pinned  BOOLEAN DEFAULT false,
    author     VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

-- Agenda & FGD
CREATE TABLE IF NOT EXISTS agenda (
    id          VARCHAR PRIMARY KEY,
    title       VARCHAR NOT NULL,
    category    VARCHAR NOT NULL,         -- fgd, brevet, rapat, deadline
    event_date  DATE NOT NULL,
    event_time  TIME,
    location    VARCHAR,
    description TEXT,
    created_by  VARCHAR NOT NULL,
    created_at  TIMESTAMP DEFAULT now()
);

-- Log Dokumen Diproses
CREATE TABLE IF NOT EXISTS document_logs (
    id           VARCHAR PRIMARY KEY,
    device_id    VARCHAR NOT NULL,
    doc_type     VARCHAR NOT NULL,        -- efaktur, ebupot, rekening, bppu, bp21
    count        INTEGER DEFAULT 1,
    processed_at TIMESTAMP DEFAULT now()
);
```

### Mengapa Ada `document_logs`?

Tabel ini adalah pondasi dari fitur analytics dashboard:
- Berapa dokumen diproses per hari/bulan?
- Siapa konsultan paling produktif?
- Tipe dokumen mana yang paling banyak diproses?
- Tren aktivitas dari waktu ke waktu?

Semua bisa dijawab dengan satu query DuckDB.

---

## 4.4 WebSocket Realtime + Event Types

### Mengapa WebSocket?

Alternatif yang dipertimbangkan:
- **HTTP Polling** — client tanya server tiap N detik → boros bandwidth, data tidak instant
- **Server-Sent Events (SSE)** — satu arah (server ke client) → tidak cukup untuk presence
- **WebSocket** — dua arah, persistent connection → dipilih

### Semua Tipe Event

**Server → Client:**

```json
{ "type": "announcement",  "title": "...", "body": "...", "from": "admin" }
{ "type": "doc_update",    "doc_type": "efaktur", "device": "PC3", "count": 12 }
{ "type": "presence",      "user": "Raymond", "device": "PC1", "status": "online" }
{ "type": "deadline",      "klien": "PT Maju Bersama", "jenis": "PPh 21", "days_left": 3 }
{ "type": "app_update",    "version": "1.2.0", "url": "http://192.168.1.10:3002/app.exe" }
{ "type": "revoke",        "hardware_id": "a3f9..." }
{ "type": "kill" }
```

**Client → Server:**

```json
{ "type": "presence",      "status": "online",  "hardware_id": "a3f9...", "user": "Raymond" }
{ "type": "presence",      "status": "offline", "hardware_id": "a3f9..." }
{ "type": "doc_processed", "doc_type": "efaktur", "count": 12, "hardware_id": "a3f9..." }
{ "type": "file_transfer", "to_hardware_id": "b7c2...", "filename": "faktur_maret.pdf" }
```

### Flow Broadcast

```
Client upload/edit dokumen
        ↓
POST REST ke /api/documents
        ↓
Server update DuckDB (simpan log)
        ↓
Server broadcast WebSocket event ke semua client
        ↓
Semua 20+ client update UI real-time
```

### Implementasi Hub di Rust

Hub adalah struct yang menyimpan daftar semua koneksi WebSocket aktif dan bisa broadcast ke semuanya sekaligus:

```rust
pub struct Hub {
    clients: RwLock<HashMap<ClientId, Tx>>,
}

impl Hub {
    pub async fn broadcast(&self, event: &WsEvent) {
        let msg = serde_json::to_string(event).unwrap_or_default();
        let clients = self.clients.read().await;
        for tx in clients.values() {
            let _ = tx.send(msg.clone()); // kirim ke semua, ignore error
        }
    }
}
```

`RwLock` dipakai bukan `Mutex` biasa — karena broadcast (read) jauh lebih sering terjadi daripada add/remove client (write). `RwLock` memungkinkan banyak reader bersamaan.

---

## 4.5 Strategi Sync: Event-Based (Bukan Polling)

### Keputusan

**Strategi yang dipilih: Event-based** — kirim data ke server **hanya saat ada perubahan**.

Perbandingan:

| Strategi | Cara Kerja | Bandwidth | Latensi | Kompleksitas |
|----------|-----------|-----------|---------|-------------|
| **Polling** | Client tanya tiap N detik | Tinggi | N detik | Rendah |
| **Long Polling** | Server tahan response sampai ada update | Sedang | ~real-time | Sedang |
| **SSE** | Server push satu arah | Rendah | Real-time | Rendah |
| **WebSocket Event-based** | Push dua arah saat ada perubahan | Sangat rendah | Real-time | Sedang |

### Mengapa Event-Based untuk AKP2I?

1. **Data pajak tidak berubah setiap detik** — faktur diproses beberapa kali per jam, bukan per detik
2. **LAN bandwidth bukan masalah**, tapi efisiensi tetap penting untuk 20+ PC
3. **Presence/heartbeat** hanya saat connect/disconnect — tidak ada ping berkala
4. **Server lebih sederhana** — tidak perlu manage polling interval atau cache invalidation

### Conflict Resolution: Last-Write-Wins

Untuk skala AKP2I (20 PC, tapi setiap konsultan punya klien berbeda), konflik data sangat jarang terjadi. Strategi yang dipilih: **last-write-wins** dengan timestamp + user_id di setiap record untuk audit trail.

Ini berbeda dari sistem distributed database besar yang membutuhkan CRDT atau OT (Operational Transformation). Untuk kebutuhan konsultan pajak lokal, last-write-wins lebih dari cukup.

---

## 4.6 Auto-Update via LAN

### Alasan Perlu Auto-Update

Raymond adalah developer sekaligus admin. Setiap ada update (perubahan format PDF, fitur baru), dia harus bisa push update ke semua 20+ PC tanpa harus datang ke tiap meja.

### Mekanisme

```
Server Raymond (:3002)
└── latest.json  →  { "version": "1.2.0", "url": "http://192.168.1.10:3002/app.exe" }
└── app.exe      →  installer/updater binary

Setiap PC saat startup:
→ Tauri plugin-updater cek latest.json
→ Bandingkan versi lokal vs versi server
→ Ada update? → tindakan berdasarkan strategi
```

### Dua Strategi Update

| Strategi | Kapan Dipakai | Behavior |
|----------|---------------|----------|
| **Prompt** | Update fitur baru, perbaikan minor | Notifikasi popup "Versi baru tersedia, update sekarang?" |
| **Force** | Format data pajak berubah (breaking change) | Update wajib — app tidak bisa dipakai sampai update |

**Contoh Force Update:** Jika DJP mengubah format PDF E-Faktur, parser lama tidak bisa baca format baru. Semua PC harus update dulu sebelum bisa proses dokumen.

### Dependency

```toml
# Cargo.toml sisi Tauri
tauri-plugin-updater = "2"
```

---

## 4.7 Kode Rust — Struktur File dan Implementasi

### Dependency Lengkap (Cargo.toml)

```toml
[dependencies]
axum            = { version = "0.7", features = ["ws"] }
tokio           = { version = "1",   features = ["full"] }
tower-http      = { version = "0.5", features = ["cors", "fs"] }
duckdb          = { version = "0.10", features = ["bundled"] }
serde           = { version = "1", features = ["derive"] }
serde_json      = "1"
uuid            = { version = "1", features = ["v4"] }
chrono          = { version = "0.4", features = ["serde"] }
tracing         = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }
sha2            = "0.10"
hex             = "0.4"
anyhow          = "1"
tokio-tungstenite = "0.21"
futures         = "0.3"
```

### Semua Struct Data (models.rs)

```rust
// PC / Device
pub struct Device          { id, name, user_name, app_version, is_active, last_seen }
pub struct RegisterDevice  { hardware_id, name, user_name, app_version }

// Validasi
pub struct ValidateRequest  { hardware_id, app_version }
pub struct ValidateResponse { ok, reason, token }  // reason: "revoked" | "not_registered"

// Konten
pub struct Announcement     { id, title, body, category, is_pinned, author, created_at }
pub struct CreateAnnouncement { title, body, category, is_pinned, author }
pub struct AgendaItem       { id, title, category, event_date, event_time, location, description }
pub struct CreateAgenda     { title, category, event_date, event_time, location, description, created_by }
pub struct LogDocument      { device_id, doc_type, count }

// WebSocket events (tagged enum)
pub enum WsEvent {
    Announcement { title, body, from },
    DocUpdate    { doc_type, device, count },
    Presence     { user, device, status },
    Deadline     { klien, jenis, days_left },
    AppUpdate    { version, url },
    Revoke       { hardware_id },
    Kill,
}
```

### Urutan Implementasi Backend (Rekomendasi)

```
Phase 1 — Fondasi
  [1] Setup Cargo.toml + main.rs skeleton
  [2] DuckDB init + SCHEMA (db.rs)
  [3] Models semua struct (models.rs)
  [4] Route GET /api/devices → return dummy JSON
  [5] Test dengan curl

Phase 2 — Auth & Whitelist
  [6] auth.rs — hash_hardware_id + validate endpoint
  [7] POST /api/devices/register
  [8] DELETE /api/devices/:id (revoke)
  [9] Tauri command get_hardware_id()
  [10] Frontend: panggil validate saat startup

Phase 3 — WebSocket
  [11] ws/hub.rs — Hub struct + broadcast
  [12] WebSocket handler
  [13] Frontend: connect WS, handle event
  [14] Test: 2 browser tab → broadcast dari satu, terima di lain

Phase 4 — Data
  [15] CRUD /api/announcements
  [16] CRUD /api/agenda
  [17] POST /api/documents
  [18] Frontend: ganti hardcode → fetch dari server

Phase 5 — Polish
  [19] Presence tracking
  [20] Kill switch endpoint
  [21] Auto-update server
  [22] Build & packaging
```

### Testing Tanpa Tauri (curl)

```bash
# Jalankan server
cargo run

# Test list devices
curl http://localhost:3000/api/devices

# Test register PC baru
curl -X POST http://localhost:3000/api/devices \
  -H "Content-Type: application/json" \
  -d '{"hardware_id":"test-pc-001","name":"PC Test","user_name":"Budi","app_version":"1.0.0"}'

# Test validasi
curl -X POST http://localhost:3000/api/validate \
  -H "Content-Type: application/json" \
  -d '{"hardware_id":"test-pc-001","app_version":"1.0.0"}'

# Test WebSocket
wscat -c ws://localhost:3000/ws
# ketik: {"type":"presence","user":"Budi","device":"PC1","status":"online"}
```

---

---

# 5. Keamanan

## 5.1 Threat Model — 6 Ancaman Utama

Sebelum membangun sistem keamanan, ancaman-ancaman konkret diidentifikasi terlebih dahulu di Sesi 4:

| No | Ancaman | Mitigasi |
|----|---------|----------|
| 1 | **PC dicuri / hilang** → data klien terbaca | Enkripsi database AES-256 |
| 2 | **Orang dalam kantor** → akses data bukan haknya | Sistem role ADMIN/USER |
| 3 | **PC tamu di WiFi** → connect ke server sync | Hardware ID whitelist |
| 4 | **File PDF ekstraksi tersimpan plaintext** | Enkripsi file output *(planned)* |
| 5 | **License bypass** → app dipakai tanpa approval | Validasi hardware ID saat startup |
| 6 | **Karyawan resign** → akses harus dicabut cepat | Revocation real-time via WebSocket |

---

## 5.2 Hardware ID Fingerprinting

### Konsep

Setiap PC punya identitas unik — bukan berdasarkan username (bisa diganti) atau IP (berubah-ubah di DHCP), tapi berdasarkan kombinasi karakteristik hardware yang sulit dipalsukan.

### Komponen Fingerprint

```rust
let hardware_id = hash(
    mac_address    +  // MAC network interface
    hostname       +  // Nama PC di jaringan Windows
    disk_serial       // Serial number SSD/HDD
);
```

Hasilnya di-hash dengan **SHA-256** sebelum disimpan ke database:
```rust
pub fn hash_hardware_id(raw: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(raw.as_bytes());
    hex::encode(hasher.finalize())
}
```

**Mengapa kombinasi?**
- MAC address saja — bisa diganti via software
- Hostname saja — mudah diubah di Windows settings
- Disk serial saja — bisa di-spoof
- Kombinasi ketiganya — jauh lebih sulit dipalsukan

**Catatan:** Kalau PC ganti NIC atau SSD, hardware ID berubah dan perlu daftar ulang ke Raymond. Ini trade-off yang diterima.

---

## 5.3 Validasi Startup + Cache Lokal

### Flow Lengkap

```
App startup
    ↓
Cek cache lokal (Tauri secure store)
— sudah validated hari ini?
    ├─ YA → App langsung jalan
    └─ TIDAK → Hubungi server LAN
                    ↓
               Server bisa dihubungi?
                    ├─ YA → Cek hardware_id di whitelist
                    │           ├─ Ada & aktif → simpan cache → app jalan
                    │           └─ Tidak ada / tidak aktif → Expired page
                    └─ TIDAK → Apakah cache masih valid (< 1 hari)?
                                    ├─ YA → App tetap jalan (grace period)
                                    └─ TIDAK → Expired page
```

### Cache Format

```json
{
  "validated_at": "2026-04-02",
  "hardware_id":  "a3f9...",
  "token":        "eyJ..."
}
```

Disimpan di **Tauri Stronghold** (OS keychain) — tidak bisa dibaca atau diedit manual dari luar app, tidak seperti file JSON biasa.

### Token Harian

Token dihasilkan server dengan formula:
```rust
fn generate_token(hardware_id: &str) -> String {
    let today = chrono::Utc::now().format("%Y-%m-%d").to_string();
    hash_hardware_id(&format!("{hardware_id}:{today}:akp2i-secret"))
}
```

Token otomatis "expired" besok — app harus validasi ulang ke server. Ini memastikan kalau Raymond revoke akses, efeknya paling lama 1 hari (sampai token expired).

---

## 5.4 Revocation Real-Time

### Skenario

Karyawan A resign hari ini. Raymond perlu memastikan A tidak bisa akses app lagi, bahkan kalau cache hari ini masih valid.

### Mekanisme

1. Raymond buka Developer Panel → klik "Revoke" di samping nama karyawan A
2. Server update database: `UPDATE devices SET is_active = false WHERE id = ?`
3. Server broadcast WebSocket event:
   ```json
   { "type": "revoke", "hardware_id": "a3f9..." }
   ```
4. **Semua PC** menerima event ini dan memeriksa: "Apakah ini hardware_id saya?"
5. PC karyawan A: YA → hapus cache → tampilkan Expired page **seketika**
6. PC lain: TIDAK → abaikan event

### Kelebihan

- Efek langsung, tidak perlu tunggu sampai token expired
- Tidak perlu restart app di PC karyawan
- Aman meski karyawan sedang aktif menggunakan app

---

## 5.5 Enkripsi Data Lokal

### DuckDB + AES-256

File database DuckDB yang disimpan di disk dienkripsi menggunakan AES-256. Jika PC dicuri, database tidak bisa dibuka tanpa key.

**Penyimpanan key:**
- Key TIDAK disimpan di file config (mudah dibaca)
- Key disimpan di **Tauri Stronghold** / OS keychain
- Key hanya bisa dibaca oleh app yang sama, di PC yang sama

```rust
// Key encryption database — disimpan di OS keychain
let key = app.stronghold().get("db_encryption_key")?;
let conn = Connection::open_with_flags(
    "akp2i.db",
    duckdb::Config::default().with_encryption_key(&key)
)?;
```

### Yang Tidak Dipakai (Sengaja)

| Mekanisme | Alasan Tidak Dipakai |
|-----------|---------------------|
| HTTPS/TLS | LAN-only, overhead tidak sebanding manfaat |
| 2FA | Terlalu ribet untuk konsultan pajak sehari-hari |
| Database cluster (PostgreSQL) | Overkill untuk 20 PC dan DuckDB sudah cukup |
| Audit log detail per query | Planned untuk Phase 5 |

---

## 5.6 Sistem Role: ADMIN vs USER

### Hanya 2 Role — Sengaja Sederhana

| Aspek | ADMIN (Raymond) | USER (Konsultan) |
|-------|-----------------|------------------|
| Kelola whitelist PC | ✅ | ❌ |
| Kirim pengumuman | ✅ | ❌ (hanya baca) |
| Lihat semua data | ✅ | ❌ (hanya milik sendiri) |
| Approve PC baru | ✅ | ❌ |
| Push update | ✅ | ❌ |
| Dashboard monitoring | ✅ | ❌ |
| Proses dokumen PDF | ✅ | ✅ |
| Lihat agenda | ✅ | ✅ |
| Terima notifikasi | ✅ | ✅ |

Mengapa tidak lebih dari 2 role? Untuk skala AKP2I Kalbar, hierarki yang lebih kompleks (misalnya "manajer" yang bisa lihat data konsultan bawahannya tapi tidak bisa manage PC) akan menambah kompleksitas tanpa manfaat nyata.

---

---

# 6. Integrasi Tauri ↔ Backend

## 6.1 Cara Client Tauri Connect ke Server

### Konfigurasi Koneksi

```javascript
// config.js — dikonfigurasi saat pertama install
const SERVER_URL = 'http://192.168.1.10:3000'; // IP PC Raymond
const WS_URL     = 'ws://192.168.1.10:3000/ws';
```

IP ini di-set satu kali saat Raymond install app pertama kali. Semua PC lain dikonfigurasi dengan IP yang sama.

### Validasi Hardware ID Saat Startup

```javascript
async function validateWithServer(hardwareId) {
  try {
    const res = await fetch(`${SERVER_URL}/api/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        hardware_id: hardwareId,
        app_version: APP_VERSION
      })
    });
    const data = await res.json();

    if (data.ok) {
      await invoke('store_token', { token: data.token });
      return true;
    } else {
      showExpiredPage(data.reason); // "revoked" atau "not_registered"
      return false;
    }
  } catch (e) {
    // Server tidak bisa dihubungi — cek cache
    const cached = await invoke('get_cached_validation');
    if (cached && cached.valid_today) return true;
    showExpiredPage('server_unreachable');
    return false;
  }
}
```

### WebSocket Connection + Event Handler

```javascript
function connectWebSocket() {
  const ws = new WebSocket(WS_URL);

  ws.onmessage = (e) => {
    const event = JSON.parse(e.data);
    switch (event.type) {
      case 'announcement': showToast(event.title); refreshAnnouncements(); break;
      case 'doc_update':   refreshDashboardStats(); break;
      case 'presence':     updatePresenceUI(event); break;
      case 'deadline':     showDeadlineAlert(event); break;
      case 'revoke':
        if (event.hardware_id === myHardwareId) showExpiredPage('revoked');
        break;
      case 'kill':
        showExpiredPage('killed'); break;
      case 'app_update':
        promptUpdate(event.version, event.url); break;
    }
  };

  ws.onclose = () => {
    setTimeout(connectWebSocket, 5000); // auto-reconnect setiap 5 detik
  };
}
```

Auto-reconnect penting: jika Raymond restart server (misalnya setelah update), semua PC akan otomatis reconnect tanpa perlu restart app.

---

## 6.2 Tauri Commands: Operasi Native OS

Tauri Commands adalah bridge antara frontend JavaScript dan backend Rust — memungkinkan JS memanggil fungsi Rust yang punya akses ke OS.

### get_hardware_id()

```rust
#[tauri::command]
fn get_hardware_id() -> String {
    let mac      = get_mac_address().unwrap_or_default();
    let hostname = hostname::get()
        .unwrap_or_default()
        .to_string_lossy()
        .to_string();
    let raw = format!("{mac}:{hostname}");
    let mut hasher = sha2::Sha256::new();
    hasher.update(raw.as_bytes());
    hex::encode(hasher.finalize())
}
```

Di-panggil dari JS: `const hwId = await invoke('get_hardware_id');`

### store_token()

```rust
#[tauri::command]
async fn store_token(token: String, app: tauri::AppHandle) -> Result<(), String> {
    use tauri_plugin_stronghold::StrongholdExt;
    app.stronghold()
        .set("validation_token", token.as_bytes())
        .map_err(|e| e.to_string())
}
```

Menyimpan token validasi ke OS keychain — tidak bisa dibaca/diedit dari luar app.

### get_cached_validation()

```rust
#[tauri::command]
async fn get_cached_validation(app: tauri::AppHandle) -> Option<CachedValidation> {
    // Ambil dari OS keychain
    // Cek apakah validated_at == hari ini
    // Return Some jika masih valid, None jika sudah expired atau belum pernah
    todo!() // Diimplementasi di Phase 2 backend
}
```

---

---

# 7. Workflow & Aturan Pengembangan

## 7.1 Aturan Proaktif Desain + Aturan Keras Integrasi

### Aturan Proaktif Desain (Berlaku Permanen)

Ditambahkan ke skill di Sesi 6 dan berlaku untuk semua sesi setelahnya:

> **Setiap kali ada halaman baru yang ditempel, Claude WAJIB memberikan rekomendasi desain alternatif TANPA perlu diminta.**

**Format wajib:**
1. Sebutkan elemen unik halaman yang membuka peluang pola berbeda
2. Tunjukkan 2–3 pilihan visual via widget sebelum mulai kode
3. Tunggu persetujuan Raymond — baru mulai kode

**Konteks pengguna akhir yang selalu diingat:**
Konsultan pajak profesional butuh UI yang terasa enterprise, informasi langsung kelihatan tanpa banyak scroll, efisien (klik sesedikit mungkin), dan familiar dengan Excel/SAP/DJP Online.

### Aturan Keras Integrasi (Jangan Sentuh Elemen Fungsional)

Saat mengintegrasikan halaman baru ke `index.html`:

1. **Tidak boleh mengurangi elemen** — semua `id`, class fungsional, `data-*`, `onclick`, logika JS dipertahankan 100%
2. **Tidak boleh mengganti nama elemen** — jika ada `id="rek-upload-zone"`, tetap `id="rek-upload-zone"`
3. **Boleh menambah elemen** — badge, icon wrapper, wrapper div untuk visual — selama tidak merusak fungsi
4. **Tidak boleh kontradiksi** dengan `index.html`, `style.css`, `app.js` yang sudah ada

**Mengapa aturan ini ada?** Di Sesi 5-6, sempat terjadi kasus di mana `onclick` handler di-rename saat re-design, menyebabkan tombol tidak berfungsi. Aturan ini dibuat untuk mencegah terulangnya masalah itu.

### Output Wajib Per Sesi Integrasi

Setiap kali halaman baru diintegrasikan, output yang harus dihasilkan adalah:

1. **CSS baru** → tambahkan ke `style.css` dengan separator komentar: `/* ══ PAGE: [NAMA] ══ */`
2. **HTML** → konversi jadi `<section class="page-section" id="page-[nama]">` tanpa `<html>/<head>/<body>`
3. **JS** → init function baru, daftarkan di `DOMContentLoaded`
4. **Nav item** → tambahkan ke sidebar dengan `data-page` dan `data-tooltip`
5. **Update SKILL.md** — catat halaman baru di tabel Status Proyek

---

## 7.2 Aturan Update Skill Sebelum Kode Besar

### Prinsip

Setiap keputusan arsitektur penting **harus didokumentasikan ke SKILL.md terlebih dahulu**, sebelum diimplementasi dalam kode.

### Alasan

Claude tidak punya memori antar sesi. SKILL.md adalah "memori eksternal" yang memastikan:
1. Konsistensi keputusan dari sesi ke sesi
2. Tidak ada keputusan yang dibuat ulang atau berkontradiksi
3. Raymond tidak perlu menjelaskan ulang konteks setiap sesi baru

### Apa yang Wajib Dicatat ke SKILL.md?

- Keputusan teknologi baru (database, library, framework)
- Keputusan desain yang sudah disetujui
- Halaman/komponen baru yang selesai dikerjakan
- Aturan baru yang berlaku permanen
- Catatan "sesi ini membahas apa"

---

---

# 8. Roadmap

## 8.1 Roadmap Phase 1–3

### Phase 1 — Core (Status: 90% Selesai)

| Item | Status |
|------|--------|
| Re-design UI semua halaman | ✅ Selesai |
| Control Panel Tauri native | ✅ Selesai |
| Semua halaman utama diimplementasi | ✅ Selesai |
| Arsitektur server Rust final | 🔧 Sedang dikerjakan |
| Dashboard data real (tidak hardcode) | ⏳ Menunggu backend |
| Pengumuman & broadcast real | ⏳ Menunggu backend |

### Phase 2 — Sync (Planned)

| Item | Deskripsi |
|------|-----------|
| Auto-update via LAN | Plugin updater Tauri, server :3002 |
| Sync dokumen antar PC | Upload → server log → broadcast ke semua |
| Notifikasi deadline dari server | Server kirim event `deadline` H-7 dan H-3 |
| Log aktivitas & presence real | WebSocket presence event |

### Phase 3 — Power Features (Future)

| Item | Deskripsi |
|------|-----------|
| DuckDB analytics chart | Visualisasi tren DPP/PPN per bulan per klien |
| File transfer antar PC via LAN | Kirim PDF langsung ke PC konsultan lain |
| Export laporan otomatis | Generate laporan bulanan tanpa manual |
| Kelas Brevet AB module | Materi, jadwal, progress tracking |
| Manajemen deadline klien | Input deadline, reminder otomatis |

---

## 8.2 Admin Monitoring Dashboard

### Gambaran Final

Ketika backend selesai, dashboard admin akan menampilkan:

```
┌──────────────────────────────────────────────┐
│  PC1 — Raymond         🟢 Online             │
│  Dokumen hari ini: 48  │  v1.2.0             │
│  Last active: 2 menit lalu                   │
├──────────────────────────────────────────────┤
│  PC2 — Sari            🟢 Online             │
│  Dokumen hari ini: 31  │  v1.2.0             │
│  Last active: 5 menit lalu                   │
├──────────────────────────────────────────────┤
│  PC3 — Budi            🔴 Offline            │
│  Last seen: kemarin 16:42                    │
└──────────────────────────────────────────────┘
Total dokumen hari ini: 248  ← agregasi real dari DuckDB
```

Angka 248 bukan hardcode — diambil dari:
```sql
SELECT SUM(count) FROM document_logs
WHERE processed_at::DATE = today();
```

---

## 8.3 Halaman Placeholder + Kill-Switch HP

### Smart Downloader (`page-downloader`)

Halaman untuk download dokumen pajak dari sumber online secara batch. Belum ada spec detail — direncanakan setelah backend selesai.

### Order Food (`page-food`)

Halaman unik — bukan fitur pajak, tapi fitur kenyamanan kantor. Di-embed via `<iframe>` ke file terpisah `order_food_page.html`:

```html
<section class="page-section" id="page-food">
  <iframe src="order_food_page.html" style="width:100%;height:100%;border:none;"></iframe>
</section>
```

Ini memungkinkan halaman food dikembangkan secara terpisah tanpa menyentuh `index.html`.

### Kill-Switch dari HP

**Rencana:** Endpoint khusus di port :3003 dengan web UI sederhana yang bisa diakses Raymond dari HP lewat WiFi kantor.

```
Raymond buka browser di HP:
http://192.168.1.10:3003

→ Input password
→ Klik "Kill All"
→ Server broadcast: { "type": "kill" }
→ Semua app di 20+ PC: hapus cache → tampilkan Expired page
```

**Kapan dipakai?** Situasi darurat — kantor dibobol, data sensitif terancam, atau perlu maintenance mendadak yang butuh semua konsultan stop bekerja dulu.

**Status:** Diimplementasi setelah server Rust Phase 3 selesai.

---

---

## Ringkasan Status Proyek (Per Sesi 10)

| Komponen | Status |
|----------|--------|
| **Frontend (semua halaman)** | ✅ **SELESAI** — dinyatakan oleh Raymond di Sesi 9 |
| **Design System** | ✅ Selesai & terdokumentasi |
| **Arsitektur Backend** | ✅ Blueprint lengkap di SKILL.md |
| **Kode Rust (struktur + auth + ws)** | 🔧 Blueprint siap, implementasi dimulai |
| **Integrasi Frontend ↔ Backend** | ⏳ Menunggu backend berfungsi |
| **Smart Downloader** | 📋 Placeholder |
| **Order Food** | 📋 Iframe embed belum dikerjakan |
| **Kill-switch HP** | 📋 Direncanakan Phase 3 backend |

---

*Dokumen ini dihasilkan dari rekap 10 sesi pengembangan AKP2I Kalbar.*
*Developer: Raymond Fo · 085849164168 · Pontianak, Kalimantan Barat*
*Last updated: April 2026*
