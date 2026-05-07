---
title: Game Development - Engine Selection & Asset Pipeline
kategori: Game Development
tags: game-development, unity, godot, gdevelop, pixel-art, isometric, asset-pipeline, AI-image-generation
---

# Game Development

## Rent Please! Landlord Sim

### Definisi & Gambaran Umum

Rent Please! Landlord Sim adalah game simulasi manajemen properti mobile yang dikembangkan oleh **Supersonic Studios**. Pemain berperan sebagai pemilik kos-kosan (landlord) yang mengelola penyewa, mengumpulkan uang sewa, menangani kejadian acak, dan mengembangkan properti dari waktu ke waktu.

### Gaya Visual

- Gaya **2D kartun cerah** dengan karakter chibi (kepala besar, tubuh kecil)
- Palet warna pastel yang ramah mata
- Ikon tebal dan jelas untuk UI mobile
- Animasi karakter ekspresif untuk memperkuat narasi ringan

### Mekanisme Gameplay

- **Manajemen penyewa**: rekrut, kelola kepuasan, dan usir penyewa bermasalah
- **Pengumpulan sewa**: kumpulkan uang sewa setiap periode waktu
- **Upgrade kamar**: tingkatkan fasilitas untuk menaikkan nilai sewa
- **Kejadian acak**: kerusakan fasilitas, konflik antar penyewa, kunjungan inspeksi
- **Ekspansi properti**: beli unit baru untuk tingkatkan pendapatan pasif
- **Narasi ringan**: setiap penyewa punya kepribadian dan cerita sendiri

### Platform & Akses

- **Android**: Google Play Store (gratis, in-app purchases)
- **iOS**: App Store (gratis, in-app purchases)

> **Peringatan**: Mengunduh APK dari sumber tidak resmi sangat berbahaya — bisa mengandung malware, spyware, atau ransomware. Selalu gunakan store resmi.

### Kelebihan & Kelemahan

| Aspek | Detail |
|-------|--------|
| Visual | Kartun cerah, ramah semua umur |
| Gameplay | Casual, mudah dipelajari |
| Narasi | Cerita penyewa memberikan konteks emosional |
| Monetisasi | In-app purchase bisa agresif |
| Kedalaman | Kurang kompleks untuk gamer hardcore |

---

## Gaya Visual Isometrik Pixel Art

### Definisi

Isometrik pixel art adalah gaya seni 2D yang menggambar objek dengan **sudut kamera tetap 45 derajat** sehingga menciptakan ilusi kedalaman 3D. Setiap piksel ditempatkan secara manual dengan presisi tinggi.

### Karakteristik Visual

- Sudut pandang kamera: **45 derajat dari atas-samping** (dimetrik atau isometrik sejati)
- Setiap objek memiliki **3 sisi terlihat**: atas, kiri, kanan
- Warna terbatas memberikan estetika **retro** yang khas
- **Outline tebal** untuk kejelasan antar objek
- Pencahayaan konsisten dari satu arah (biasanya atas-kiri)

### Contoh Nyata dari Sesi Ini

Gambar yang diupload menampilkan kamar kos isometrik pixel art dengan elemen:
- Tempat tidur single dengan bantal kuning
- Meja belajar dengan laptop, buku, dan alarm
- Kulkas mini dengan microwave di atasnya
- Wastafel dan kabinet dapur
- Kursi kantor biru
- Karpet bundar kuning
- Tanaman dalam pot (2 jenis)
- Lantai kayu dengan motif garis

Semua elemen menggunakan **perspektif isometrik konsisten** dengan pencahayaan dari atas-kiri.

### Perbandingan Gaya Visual

| Aspek | Isometrik Pixel Art | 2D Flat | 3D Render |
|-------|---------------------|---------|-----------|
| Perspektif | 45 derajat tetap, ilusi 3D | Tampak atas/samping | Perspektif penuh |
| Cara Buat | Piksel manual | Vektor/raster | Software 3D |
| File Size | Sangat kecil | Kecil-sedang | Besar |
| Performa Game | Sangat ringan | Ringan | Berat |
| Tool Utama | Aseprite | Illustrator/Figma | Blender/Maya |
| Kurva Belajar | Sedang | Mudah | Tinggi |
| Estetika | Retro, charming | Modern, bersih | Realistis |

### Tool yang Digunakan

- **Aseprite** (~$20 sekali beli): tool pixel art paling populer, mendukung animasi frame-by-frame, palette management, dan isometric grid
- **Libresprite**: fork gratis dari Aseprite versi lama
- **Photoshop/GIMP**: alternatif untuk yang sudah familiar dengan raster editor

---

## Unity — Engine Terbaik untuk Game Simulasi Mobile

### Definisi & Posisi di Industri

Unity adalah **game engine lintas platform** paling banyak digunakan untuk pengembangan game mobile. Digunakan oleh studio indie hingga AAA, Unity mendukung C# sebagai bahasa pemrograman utama dan menyediakan ekosistem lengkap.

> Rent Please! Landlord Sim kemungkinan besar dibangun menggunakan Unity berdasarkan gaya visual, performa mobile, dan pola monetisasinya.

### Mengapa Unity untuk Game Seperti Rent Please

- **Isometric Tilemap bawaan**: sistem tilemap isometrik built-in tanpa plugin tambahan
- **Asset Store**: ribuan sprite, sound effect, template isometrik siap pakai
- **Build ke Android & iOS**: satu kodebase, dua platform sekaligus
- **Komunitas besar**: dokumentasi lengkap, tutorial berlimpah, forum aktif
- **Unity Ads & IAP**: sistem monetisasi terintegrasi langsung

### Fitur Kunci Unity untuk Game Ini

#### Tilemap System
Buat level isometrik dengan drag-and-drop tile. Mendukung mode isometrik dimetrik dan isometrik sejati dengan sorting layer otomatis berdasarkan posisi Y.

#### ScriptableObjects
Sistem data fleksibel untuk konfigurasi penyewa, kamar, dan harga tanpa mengubah kode — desainer bisa edit langsung dari Inspector.

#### Sprite Atlas
Optimasi memori dengan menggabungkan banyak sprite kecil menjadi satu texture atlas — mengurangi draw call secara signifikan untuk performa mobile.

#### Unity Analytics & Remote Config
Pantau perilaku pemain dan ubah parameter game (harga sewa, difficulty) tanpa update app.

### Struktur Proyek yang Direkomendasikan

```
Assets/
├── Art/
│   ├── Tiles/          # Tile isometrik (lantai, dinding)
│   ├── Characters/     # Sprite penyewa
│   ├── Furniture/      # Aset furnitur kamar
│   └── UI/             # Elemen antarmuka
├── Scripts/
│   ├── GameManager.cs
│   ├── Room.cs
│   ├── Tenant.cs
│   └── Economy.cs
├── ScriptableObjects/
│   ├── TenantData/
│   └── RoomConfig/
└── Scenes/
    ├── MainMenu.unity
    └── Gameplay.unity
```

### Harga & Lisensi

| Tier | Harga | Batas Pendapatan |
|------|-------|-----------------|
| Personal | **Gratis** | Di bawah $200.000/tahun |
| Plus | $40/bulan | Di bawah $200.000/tahun |
| Pro | $150/bulan | Tidak terbatas |
| Industry | $250/bulan | Enterprise |

### Kelebihan & Kelemahan

| Kelebihan | Kelemahan |
|-----------|-----------|
| Ekosistem terlengkap | Runtime fee kontroversial (2023) |
| Build multi-platform | Ukuran install besar (~1GB+) |
| Asset Store kaya | Kurva belajar C# untuk pemula |
| Komunitas sangat besar | Beberapa fitur advanced berbayar |
| Isometric Tilemap built-in | Perubahan kebijakan lisensi tidak terduga |

---

## Godot — Alternatif Open Source

### Definisi

Godot adalah **game engine open source 100% gratis** yang semakin populer sebagai alternatif Unity, terutama setelah kontroversi kebijakan runtime fee Unity pada September 2023. Menggunakan **GDScript** (sintaks mirip Python) atau C# sebagai bahasa pemrograman.

### Kelebihan Godot

- **100% gratis selamanya** — tidak ada biaya lisensi, tidak ada runtime fee
- GDScript mudah dipelajari, terutama bagi yang sudah kenal Python
- Ukuran engine sangat kecil (~40MB vs Unity ~1GB+)
- Node system intuitif untuk organisasi game object
- Export ke Android, iOS, Web, Windows, Mac, Linux
- **Open source**: kamu bisa fork dan modifikasi engine sendiri

### Kelemahan Godot

- Komunitas lebih kecil dari Unity — lebih sedikit tutorial dan asset gratis
- Asset store tidak sekaya Unity Asset Store
- Dukungan mobile masih berkembang
- Plugin ekosistem lebih terbatas
- Isometric support kurang mature dibanding Unity

### Kapan Pilih Godot vs Unity

| Situasi | Pilihan |
|---------|---------|
| Budget nol, proyek kecil | **Godot** |
| Target rilis ke app store profesional | **Unity** |
| Butuh banyak plugin/asset siap pakai | **Unity** |
| Tidak ingin tergantung kebijakan korporat | **Godot** |
| Tim besar, kolaborasi intensif | **Unity** |
| Solo developer, game 2D sederhana | **Godot** |

### Harga

**Sepenuhnya gratis** — MIT License, tidak ada biaya apapun selamanya.

---

## GDevelop — No-Code Game Engine

### Definisi

GDevelop adalah platform pembuatan game berbasis **visual event system** yang tidak memerlukan kemampuan coding sama sekali. Semua logika game dibuat dengan menghubungkan blok kondisi-aksi secara visual.

### Sistem Event Visual

Cara kerja: "**Jika** pemain menyentuh koin → **Maka** tambah skor 10 dan mainkan suara."

Semua logika dibangun tanpa menulis kode — cocok untuk pemula absolut atau desainer game yang tidak memiliki latar belakang programming.

### Keterbatasan untuk Game Simulasi Kompleks

- Sistem isometrik terbatas — tidak ada isometric tilemap bawaan
- Logika kompleks (AI penyewa, sistem ekonomi multi-variabel) sulit diimplementasikan
- Performa kurang optimal untuk banyak objek di layar
- Export ke mobile memerlukan berlangganan berbayar
- Tidak cocok untuk game sekompleks Rent Please

### Kesimpulan Eliminasi

> GDevelop **dieliminasi** dari rekomendasi utama karena keterbatasan teknis untuk game simulasi kompleks. Unity tetap menjadi pilihan utama.

---

## Pipeline Asset Game dengan AI Image Generator

### Gambaran Umum

Workflow modern game indie mengombinasikan **AI image generator** untuk mempercepat pembuatan asset visual, kemudian diproses secara manual sebelum diimplementasikan ke game engine.

### Pipeline Lengkap

```
1. GENERATE
   ChatGPT (DALL-E) / Midjourney / Stable Diffusion
   → Buat gambar kamar, karakter, furnitur dengan prompt

2. EDIT & PIXEL ART
   Aseprite / Photoshop
   → Pixelate, perbaiki detail, tambah outline

3. BACKGROUND REMOVAL
   remove.bg / Photoshop / GIMP
   → Hapus background agar menjadi transparan (PNG)

4. SPRITESHEET
   TexturePacker / Aseprite
   → Susun frame animasi dalam satu gambar atlas

5. IMPORT KE ENGINE
   Unity (Sprite Atlas)
   → Import, atur pivot, buat animasi controller

6. PUBLISH
   Google Play Console / App Store Connect
   → Build APK/IPA, upload, review, release
```

### Contoh Prompt untuk Gaya Rent Please

```
isometric pixel art studio apartment room, cozy warm lighting,
single bed, study desk, laptop, mini fridge, microwave,
wooden floor, yellow round rug, potted plants,
white background, game asset style, 16bitscene,
no cast shadows, clean outlines
```

### Negative Prompt

```
3d render, realistic, photographic, blurry, low quality,
watermark, text, signature, gradient background
```

### Kelebihan & Keterbatasan Pipeline Ini

| Kelebihan | Keterbatasan |
|-----------|-------------|
| Sangat cepat iterasi visual | Konsistensi style antar asset sulit dijaga |
| Biaya rendah untuk solo dev | Hasil perlu editing manual |
| Tidak butuh skill seni profesional | Hak cipta AI-generated masih abu-abu |
| Bisa generate ratusan variasi | Kualitas tergantung prompt skill |
