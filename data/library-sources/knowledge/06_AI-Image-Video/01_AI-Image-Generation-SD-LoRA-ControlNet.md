---
title: AI Image Generation - Stable Diffusion, LoRA, ControlNet
kategori: AI Image & Video Generation
tags: [stable-diffusion, LoRA, ControlNet, FLUX, ComfyUI, AUTOMATIC1111, pixel-art, isometric]
---

# AI Image Generation

## Stable Diffusion

### Definisi & Sejarah

Stable Diffusion adalah **model generasi gambar open source** berbasis diffusion yang dikembangkan oleh Stability AI. Dirilis pada Agustus 2022, model ini menjadi standar de facto open source karena dapat berjalan di GPU konsumen dengan VRAM minimal 4-8GB — berbeda dari model proprietari seperti DALL-E yang hanya bisa diakses via API.

### Cara Kerja Diffusion Model

Model dimulai dengan **noise acak murni** (gambar buram penuh gangguan), kemudian secara iteratif "membersihkan" noise tersebut selama N langkah hingga terbentuk gambar koheren sesuai prompt teks.

```
Noise acak → [Denoise step 1] → [Denoise step 2] → ... → [Denoise step N] → Gambar final
```

Proses ini terjadi di **latent space** (representasi terkompresi 8x lebih kecil dari pixel space) untuk efisiensi komputasi. Ini yang membuat SD bisa berjalan di GPU konsumen.

### Varian Model Stable Diffusion

| Model | Resolusi Native | Kualitas | VRAM Minimum | Keterangan |
|-------|----------------|----------|--------------|------------|
| SD 1.5 | 512×512 | ⭐⭐⭐ | 4GB | Ringan, LoRA paling banyak tersedia |
| SD 2.0/2.1 | 768×768 | ⭐⭐⭐ | 6GB | Kurang populer, komunitas kecil |
| SDXL 1.0 | 1024×1024 | ⭐⭐⭐⭐ | 8GB | Lompatan kualitas signifikan |
| SDXL Turbo | 512×512 | ⭐⭐⭐ | 6GB | 1-4 langkah, sangat cepat |
| SD 3.5 Large | 1024×1024 | ⭐⭐⭐⭐⭐ | 12GB | Teks dalam gambar lebih baik |

### LoRA (Low-Rank Adaptation)

LoRA adalah teknik **fine-tuning efisien** yang menambahkan "adapter" kecil ke model base tanpa memodifikasi bobot utama. Hasilnya: model khusus untuk style atau subjek tertentu dengan ukuran file yang jauh lebih kecil (2-200MB vs 2-7GB untuk full model).

**Cara penggunaan LoRA pixel art di AUTOMATIC1111:**
```
Prompt: <lora:pixel-art-xl:1.2> pixel, isometric room, cozy bedroom
Negative: 3d render, realistic, blurry
```

**LoRA populer untuk pixel art:**
- `pixel-art-xl` — trigger word: `pixel`
- `isopixel` — trigger word: `isopixel style`
- `16bit-scene` — trigger word: `16bitscene`

### ControlNet — Kontrol Postur & Komposisi

ControlNet memungkinkan generasi gambar dengan **panduan visual tambahan** — bukan hanya teks. Sangat berguna untuk menjaga konsistensi karakter atau layout isometrik:

- **Canny**: ikuti outline dari gambar referensi
- **Depth**: pertahankan kedalaman/perspektif dari referensi
- **OpenPose**: ikuti pose karakter dari skeleton

### Kelebihan & Kelemahan

| ✅ Kelebihan | ⚠️ Kelemahan |
|-------------|-------------|
| Gratis, jalankan lokal | Butuh GPU kuat (4-12GB VRAM) |
| 90.000+ model di HuggingFace | Kurva belajar untuk prompting |
| LoRA, ControlNet, inpainting | Setup teknis cukup rumit |
| Tidak ada batasan konten (lokal) | Teks dalam gambar masih lemah |
| Komunitas sangat aktif | Konsistensi karakter sulit dijaga |

---

## FLUX.2 - Generasi Terbaru (2025) — Generasi Terbaru (2025)

### Definisi

FLUX.2 adalah model image generation terbaru dari **Black Forest Labs** (November 2025), menawarkan kualitas produksi-grade yang melampaui Stable Diffusion dalam hal detail, konsistensi prompt, dan rendering teks.

### Varian FLUX.2

| Varian | Akses | Keterangan |
|--------|-------|------------|
| FLUX.2 [pro] | API berbayar | Kualitas terbaik, production-grade |
| FLUX.2 [flex] | API + lokal | Kontrol parameter detail untuk developer |
| FLUX.2 [dev] | Open-weight (32B) | Jalankan lokal, GPU sangat powerful |

### Keunggulan vs Stable Diffusion

- Prompt fidelity lebih tinggi — mengikuti instruksi teks lebih akurat
- Detail visual lebih konsisten
- Teks dalam gambar jauh lebih baik
- Arsitektur baru (bukan diffusion konvensional)

### Catatan Lisensi

Untuk penggunaan komersial FLUX.2 [dev], diperlukan lisensi terpisah dari Black Forest Labs. FLUX.2 [schnell] tersedia dengan lisensi Apache 2.0 (bebas komersial).

---

## isopixel-diffusion-v1 - Model Spesifik Isometrik — Model Spesifik Isometrik

### Definisi

`isopixel-diffusion-v1` adalah model fine-tuned di **HuggingFace** yang dirancang khusus untuk menghasilkan gambar isometrik pixel art. Ini adalah model paling relevan untuk membuat asset game seperti Rent Please.

**URL**: `huggingface.co/nerijs/isopixel-diffusion-v1`

### Parameter Optimal

```
Prompt  : isometric pixel art cozy bedroom, wooden floor,
          bed desk plant, isopixel style
Steps   : 50
Sampler : Euler a
CFG     : 7.5
Size    : 768×768
```

### Pasca-Proses yang Diperlukan

Model ini belum menghasilkan pixel art yang benar-benar "pixel perfect" — perlu pasca-proses:

1. **Pixelation tool**: pinetools.com/pixelate-effect-image atau Aseprite
2. **Palette reduction**: kurangi jumlah warna ke 16/32/64 warna
3. **Manual touch-up**: perbaiki piksel yang tidak konsisten di Aseprite

### Model Pixel Art Lain di HuggingFace

| Model | Trigger Word | Keterangan |
|-------|-------------|------------|
| `nerijs/pixel-art-xl` | `pixel` | Berbasis SDXL, kualitas lebih tinggi |
| `PublicPrompts/All-In-One-Pixel-Model` | `pixelsprite` / `16bitscene` | Sprite + scene pixel art |
| `isopixel-diffusion-v1` | `isopixel style` | Khusus isometrik |

---

## ComfyUI & AUTOMATIC1111 - UI untuk Stable Diffusion — UI untuk Stable Diffusion

### Mengapa Perlu UI Terpisah?

Stable Diffusion sendiri hanya berupa model dan kode Python. UI memberikan antarmuka visual yang memudahkan penggunaan tanpa menulis kode setiap saat.

### AUTOMATIC1111 (A1111 / Stable Diffusion WebUI)

**Deskripsi**: WebUI berbasis form, standar de facto untuk pengguna baru dan menengah.

**Instalasi**:
```bash
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui
cd stable-diffusion-webui
./webui.sh  # Linux/Mac
webui-user.bat  # Windows
```

**Fitur utama**:
- Interface form yang familier
- Txt2img, img2img, inpainting, outpainting
- Extra Networks: LoRA, embedding, hypernetwork
- 500+ ekstensi komunitas
- Batch processing
- PNG info (metadata tersimpan di gambar)

### ComfyUI

**Deskripsi**: Sistem berbasis **node visual** — kamu membangun workflow dengan menghubungkan node pemrosesan.

**Instalasi**:
```bash
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI
pip install -r requirements.txt
python main.py
```

**Keunggulan untuk pipeline game asset**:
- Workflow bisa disimpan dan dibagi sebagai JSON
- Batch processing ribuan gambar otomatis
- Integrasi ControlNet lebih fleksibel
- API untuk otomasi programatik

### Perbandingan Langsung

| Aspek | AUTOMATIC1111 | ComfyUI |
|-------|--------------|---------|
| Kemudahan awal | ⭐⭐⭐⭐⭐ Sangat mudah | ⭐⭐⭐ Butuh belajar |
| Fleksibilitas | ⭐⭐⭐ Terbatas UI | ⭐⭐⭐⭐⭐ Hampir unlimited |
| Batch otomatis | ⭐⭐⭐ Terbatas | ⭐⭐⭐⭐⭐ Sangat powerful |
| Komunitas | Sangat besar | Berkembang pesat |
| Cocok untuk | Eksperimen cepat | Pipeline produksi |
| Harga | Gratis | Gratis |

### Rekomendasi

- **Pemula**: mulai dengan AUTOMATIC1111
- **Pipeline produksi game**: migrasi ke ComfyUI setelah mahir
- **Keduanya** bisa diinstal bersamaan di satu mesin
