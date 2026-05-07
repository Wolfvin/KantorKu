---
title: AI Pajak - Self-Learning Stack
kategori: Infrastruktur & Self-Hosting AI
tags: AI-pajak, self-learning, Ollama, OpenClaw, Qwen, PMK-6-2026, ChromaDB, Telegram-bot
---

# AI Pajak Self-Learning Stack

> **Dokumen ini mengkristalkan seluruh sesi diskusi menjadi sistem pengetahuan terstruktur yang dapat digunakan kembali untuk membangun sistem AI Pajak lokal dengan kemampuan self-learning.**

---

## 1. KATEGORI UTAMA

| No | Kategori | Deskripsi |
|----|----------|-----------|
| 1 | **Arsitektur Sistem AI Lokal** | Stack teknologi untuk menjalankan AI secara self-hosted |
| 2 | **Model AI & Seleksi** | Pemahaman model Qwen, parameter, dan kriteria pemilihan |
| 3 | **Regulasi Pajak & Ekstraksi** | PMK 6/2026 dan mekanisme ekstraksi rule dari dokumen hukum |
| 4 | **Self-Learning & Versioning** | Sistem AI yang belajar dari feedback dengan manajemen versi rule |
| 5 | **Integrasi & Otomasi** | OpenClaw, Telegram, Dashboard, Excel automation |
| 6 | **Infrastruktur & Hardware** | RAM, storage, optimasi performa, deployment |

---

## 2. SUB-TOPIK DETAIL

---

### 2.1 Arsitektur Sistem AI Lokal

#### A. Inti Konsep
**Definisi**: Sistem AI yang berjalan sepenuhnya di infrastruktur lokal (laptop/PC/server pribadi) tanpa ketergantungan pada cloud API.

**Tujuan**: 
- Privasi data 100% (data pajak klien tidak keluar perangkat)
- Biaya operasional Rp 0 setelah investasi hardware
- Kontrol penuh atas model, update, dan integrasi

**Masalah yang Diselesaikan**: 
- Ketergantungan pada API berbayar (OpenAI, Anthropic)
- Risiko kebocoran data sensitif
- Latency network dan rate limit

#### B. Mekanisme & Cara Kerja
```
┌─────────────────────────────────────────────────────────────┐
│                    📱 FRONTEND (User Interface)             │
│         Streamlit Dashboard / Telegram Bot / VS Code        │
└───────────────────────┬─────────────────────────────────────┘
                        │ (HTTP Request / API Call)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                 🦞 AGENT FRAMEWORK (OpenClaw)               │
│         • Orchestrate workflow                              │
│         • Manage skills & tools                             │
│         • Handle human-in-the-loop decisions                │
└───────────────────────┬─────────────────────────────────────┘
                        │ (Localhost API: 11434)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  🧠 MODEL RUNNER (Ollama)                   │
│         • Load model GGUF ke RAM/VRAM                       │
│         • Handle inference & quantization                   │
│         • Manage multiple models                            │
└───────────────────────┬─────────────────────────────────────┘
                        │ (Model Weights)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   🤖 AI MODEL (Qwen/DeepSeek)               │
│         • Qwen2.5-Coder-7B (logic & coding)                 │
│         • Qwen2.5-VL-7B (vision & PDF extraction)           │
│         • nomic-embed-text (RAG & search)                   │
└─────────────────────────────────────────────────────────────┘
```

#### C. Komponen Penting
| Komponen | Peran | Koneksi |
|----------|-------|---------|
| **Ollama** | Model runner & API server | Port 11434 (localhost) |
| **OpenClaw** | Agent orchestration | Call Ollama API + execute skills |
| **Streamlit** | Dashboard UI | Python app, call OpenClaw/Ollama |
| **ChromaDB** | Vector database untuk RAG | Store regulasi & Q&A history |
| **Telegram Bot** | Mobile interface & notifications | Webhook → OpenClaw |
| **pandas/openpyxl** | Excel automation | Generate report & calculations |

#### D. Use Case Nyata
**Proyek Pajak AI PMK 6/2026**:
1. User upload PDF PMK via dashboard
2. Qwen2.5-VL extract rule (tarif 5%, periode Okt 2025-Des 2026)
3. Rule disimpan ke ChromaDB + training_data.jsonl
4. User input data peserta magang via Telegram
5. AI hitung PPh 21 DTP otomatis
6. Generate Excel report + kirim ke user

#### E. Tools & Teknologi
| Tool | Fungsi | Status |
|------|--------|--------|
| Ollama | Model runner | ✅ Open Source, Gratis |
| OpenClaw | Agent framework | ✅ Open Source, Gratis |
| Qwen2.5-Coder | Logic & coding model | ✅ Apache 2.0, Gratis |
| Qwen2.5-VL | Vision & PDF extraction | ✅ Apache 2.0, Gratis |
| Streamlit | Dashboard UI | ✅ Open Source, Gratis |
| ChromaDB | Vector database | ✅ Open Source, Gratis |

#### F. Evaluasi Kritis
| Aspek | Penilaian |
|-------|-----------|
| **Kelebihan** | Privasi 100%, biaya 0 setelah hardware, kontrol penuh, offline-capable |
| **Kekurangan** | Butuh setup teknis, performa tergantung hardware, maintenance manual |
| **Batasan** | Model size terbatas oleh RAM, kecepatan inference lebih lambat dari cloud |
| **Risiko** | Data loss jika tidak backup, model bisa outdated tanpa update rutin |

#### G. Harga & Akses
- **Semua komponen**: Gratis (open source)
- **Investasi hardware**: RAM 16GB (~Rp 400-600rb), SSD recommended
- **Biaya operasional**: Listrik & internet (minimal, karena lokal)

#### H. Perbandingan
| Aspek | Lokal (Ollama) | Cloud (OpenAI/Anthropic) |
|-------|---------------|-------------------------|
| Privasi | ✅ 100% lokal | ❌ Data ke server provider |
| Biaya | ✅ Gratis setelah hardware | ❌ Bayar per token |
| Kecepatan | ⚠️ Tergantung hardware | ✅ Sangat cepat (GPU enterprise) |
| Kontrol | ✅ Penuh | ❌ Terbatas |
| Setup | ⚠️ Ribet awal | ✅ Instant |

---

### 2.2 Model AI & Seleksi

#### A. Inti Konsep
**Definisi**: Parameter (3B, 7B, 14B, dll) adalah jumlah "neuron" dalam model AI yang menentukan kapasitas pembelajaran dan reasoning.

**Tujuan**: Memilih model yang seimbang antara kecerdasan, kecepatan, dan resource usage.

**Masalah yang Diselesaikan**: Over-engineering (pakai model terlalu besar) atau under-performance (model terlalu kecil untuk tugas kompleks).

#### B. Mekanisme & Cara Kerja
```
Parameter Count → Memory Requirement → Inference Speed → Intelligence Level

3B  = ~2.5 GB RAM  = 20-40 tok/s = Basic logic
7B  = ~5.5 GB RAM  = 10-20 tok/s = Sweet spot
14B = ~10 GB RAM   = 5-10 tok/s  = Complex reasoning
72B = ~45 GB RAM   = 1-3 tok/s   = Enterprise grade
```

#### C. Komponen Penting
| Model | Parameter | RAM (Q4_K_M) | Use Case Optimal |
|-------|-----------|--------------|------------------|
| Qwen2.5-Coder-3B | 3B | ~2.5 GB | Testing, basic logic, 8GB RAM |
| Qwen2.5-Coder-7B | 7B | ~5.5 GB | ✅ Production, coding, tax logic |
| Qwen2.5-VL-7B | 7B | ~5.5 GB | PDF extraction, image analysis |
| DeepSeek-R1-7B | 7B | ~5.5 GB | Complex reasoning, chain-of-thought |
| Llama3.2-7B | 7B | ~5.5 GB | Fallback, general chat |

#### D. Use Case Nyata
**Untuk Proyek Pajak AI**:
- **Model utama**: Qwen2.5-Coder-7B (hitung PPh 21, generate Excel code)
- **Model vision**: Qwen2.5-VL-7B (extract tabel dari Lampiran A PMK)
- **Model embedding**: nomic-embed-text (RAG untuk search regulasi)

#### E. Tools & Teknologi
| Tool | Fungsi |
|------|--------|
| Ollama | Pull & run models (`ollama pull qwen2.5-coder:7b`) |
| Hugging Face | Download manual GGUF files |
| llama.cpp | Alternative runner (more control) |

#### F. Evaluasi Kritis
| Aspek | Penilaian |
|-------|-----------|
| **Kelebihan** | 7B = sweet spot untuk kebanyakan use case, quantization efisien |
| **Kekurangan** | Model besar butuh RAM signifikan, speed trade-off |
| **Batasan** | 8GB RAM hanya cukup untuk 3B model dengan nyaman |
| **Risiko** | Model bisa di-discontinue atau license berubah |

#### G. Harga & Akses
- **Semua model open source**: Gratis (Apache 2.0, MIT, dll)
- **Quantization**: Ollama default Q4_K_M (optimal size/quality)

#### H. Perbandingan
| Model | Intelligence | Speed | RAM | Recommendation |
|-------|-------------|-------|-----|----------------|
| 3B | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 8GB | Testing, low-end hardware |
| 7B | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 16GB | ✅ Production sweet spot |
| 14B+ | ⭐⭐⭐⭐⭐ | ⭐⭐ | 24GB+ | Enterprise, complex tasks |

---

### 2.3 Regulasi Pajak & Ekstraksi (PMK 6/2026)

#### A. Inti Konsep
**Definisi**: PMK Nomor 6 Tahun 2026 adalah regulasi yang memberikan insentif PPh Pasal 21 ditanggung pemerintah untuk peserta pemagangan lulusan perguruan tinggi.

**Tujuan**: Memberikan stimulus ekonomi bagi peserta magang melalui fasilitas fiskal.

**Masalah yang Diselesaikan**: Beban pajak bagi peserta magang, meningkatkan partisipasi program pemagangan.

#### B. Mekanisme & Cara Kerja
```
┌─────────────────────────────────────────────────────────────┐
│  PDF PMK 6/2026 Upload                                      │
│  ↓                                                          │
│  Qwen2.5-VL Extract:                                        │
│  • Tarif: 5% (Pasal 17 UU PPh)                             │
│  • Periode: Okt 2025 - Des 2026 (Pasal 3)                  │
│  • Syarat: NPWP/NIK, tidak dapat insentif lain (Pasal 5)   │
│  ↓                                                          │
│  Rule disimpan ke training_data.jsonl + ChromaDB           │
│  ↓                                                          │
│  AI hitung otomatis untuk data peserta baru                │
└─────────────────────────────────────────────────────────────┘
```

#### C. Komponen Penting (Dari PMK 6/2026)
| Pasal | Isi | Implementasi AI |
|-------|-----|-----------------|
| **Pasal 2** | Penghasilan meliputi uang saku, iuran JKK/JKM, penghasilan lain | AI ekstrak semua komponen bruto |
| **Pasal 3** | Insentif PPh 21 DTP untuk Masa Pajak Okt 2025 - Des 2026 | AI validasi periode sebelum hitung |
| **Pasal 5** | Syarat: NPWP/NIK terintegrasi, tidak dapat insentif lain | AI checklist eligibility |
| **Pasal 6** | PPh 21 DTP dibayar tunai, tidak diperhitungkan sebagai penghasilan | AI hitung peserta terima utuh |
| **Pasal 7** | Laporan realisasi paling lambat tanggal 20 bulan berikutnya | AI reminder deadline |
| **Lampiran A** | Contoh perhitungan: 5% × Penghasilan Bruto | AI template perhitungan |

#### D. Use Case Nyata
**Contoh Perhitungan (dari Lampiran A)**:
```
Peserta A:
• Uang Saku: Rp 5.396.761
• Iuran JKK/JKM: Rp 16.800
• Penghasilan Bruto: Rp 5.413.561
• PPh 21 (5%): Rp 270.678
• PPh 21 DTP: Rp 270.678 (ditanggung pemerintah)
• Diterima Peserta: Rp 5.413.561 (utuh)
```

#### E. Tools & Teknologi
| Tool | Fungsi |
|------|--------|
| Qwen2.5-VL | Extract text & tables dari PDF scan |
| pandas | Calculate & structure data |
| openpyxl | Generate Excel report (Lampiran B format) |
| ChromaDB | Store regulasi untuk RAG |

#### F. Evaluasi Kritis
| Aspek | Penilaian |
|-------|-----------|
| **Kelebihan** | Rule jelas, contoh perhitungan eksplisit, periode definitif |
| **Kekurangan** | Edge cases tidak cover (misal: magang + kerja part-time) |
| **Batasan** | Hanya untuk Anggaran 2026, perlu update regulasi tahunan |
| **Risiko** | AI hallucination jika prompt tidak spesifik, perlu validasi manusia |

#### G. Harga & Akses
- **PMK 6/2026**: Publik, gratis dari jdih.kemenkeu.go.id
- **Implementasi AI**: Gratis (open source stack)

#### H. Perbandingan
| Aspek | Manual | AI-Assisted |
|-------|--------|-------------|
| Kecepatan | 15-30 menit per peserta | <1 menit per peserta |
| Akurasi | ✅ Tinggi (jika ahli) | ⚠️ Perlu validasi |
| Skalabilitas | ❌ Linear dengan jumlah peserta | ✅ Otomatis |
| Audit Trail | ⚠️ Manual | ✅ Otomatis tersimpan |

---

### 2.4 Self-Learning & Versioning

#### A. Inti Konsep
**Definisi**: Sistem AI yang meningkatkan akurasi seiring waktu melalui feedback manusia (human-in-the-loop) dengan manajemen versi rule.

**Tujuan**: AI menjadi lebih pintar tanpa retrain dari nol, dengan audit trail perubahan rule.

**Masalah yang Diselesaikan**: AI stagnan, tidak belajar dari kesalahan, tidak ada version control untuk rule.

#### B. Mekanisme & Cara Kerja
```
┌─────────────────────────────────────────────────────────────┐
│  AI proses data client                                      │
│  ↓                                                          │
│  Confidence Score < 80%?                                    │
│  ↓ YES                          ↓ NO                        │
│  Tanya user via Telegram        Proses otomatis             │
│  ↓                                                          │
│  User jawab & koreksi                                       │
│  ↓                                                          │
│  Simpan sebagai training data baru                          │
│  ↓                                                          │
│  Setelah N pertanyaan baru → Auto-retrain LoRA              │
│  ↓                                                          │
│  Next time kondisi sama → Proses otomatis (tidak tanya)    │
└─────────────────────────────────────────────────────────────┘
```

#### C. Komponen Penting
| Komponen | Fungsi |
|----------|--------|
| **Confidence Scoring** | Hitung similarity dengan training data existing |
| **Telegram Integration** | Tanya user kalau confidence rendah |
| **training_data.jsonl** | Store semua Q&A pairs dengan metadata |
| **Versioning System** | Rule lama ditandai `deprecated`, bukan dihapus |
| **LoRA Adapter** | Fine-tune model dengan data baru (efisien) |

#### D. Use Case Nyata
**Skenario Regulasi Berubah**:
```
1. PMK 25/2026 terbit (revisi tarif kredit pajak LN dari 20% → 15%)
2. User infokan via Telegram: /update_regulasi PMK-25/2026
3. AI tandai rule lama sebagai deprecated (valid_until: 2025-12-31)
4. AI buat rule baru (effective_from: 2026-01-01)
5. Next time:
   - Kasus periode ≤2025 → pakai rule v1 (deprecated)
   - Kasus periode ≥2026 → pakai rule v2 (active)
```

#### E. Tools & Teknologi
| Tool | Fungsi |
|------|--------|
| ChromaDB | Vector search untuk similarity scoring |
| Sentence Transformers | Embedding untuk compare conditions |
| Unsloth + TRL | Efficient LoRA fine-tuning |
| OpenClaw | Orchestrate HITL workflow |

#### F. Evaluasi Kritis
| Aspek | Penilaian |
|-------|-----------|
| **Kelebihan** | AI improve over time, audit trail lengkap, rollback possible |
| **Kekurangan** | Butuh disiplin user untuk jawab pertanyaan, retrain butuh resource |
| **Batasan** | Confidence threshold perlu tuning, false positive/negative possible |
| **Risiko** | Data training corruption jika tidak backup, versioning conflict |

#### G. Harga & Akses
- **Semua komponen**: Gratis (open source)
- **Retrain cost**: Listrik & waktu (QLoRA ~1-2 jam untuk 10-20 Q&A baru)

#### H. Perbandingan
| Aspek | Static AI | Self-Learning AI |
|-------|-----------|-----------------|
| Akurasi | ⚠️ Tetap | ✅ Improve over time |
| Maintenance | ❌ Manual update | ✅ Otomatis + human feedback |
| Audit Trail | ❌ Tidak ada | ✅ Lengkap dengan versioning |
| Complexity | ✅ Simpel | ⚠️ Lebih kompleks |

---

### 2.5 Integrasi & Otomasi

#### A. Inti Konsep
**Definisi**: Menghubungkan berbagai komponen (AI, database, Excel, Telegram) menjadi workflow otomatis yang end-to-end.

**Tujuan**: Mengurangi intervensi manual, meningkatkan kecepatan & konsistensi output.

**Masalah yang Diselesaikan**: Siloed tools, copy-paste error, proses manual yang repetitif.

#### B. Mekanisme & Cara Kerja
```
┌─────────────────────────────────────────────────────────────┐
│  📱 Telegram: User kirim data peserta                       │
│  ↓                                                          │
│  🦞 OpenClaw: Parse message, validate input                 │
│  ↓                                                          │
│  🧠 Ollama + Qwen: Hitung PPh 21 sesuai rule                │
│  ↓                                                          │
│  📊 Python (pandas): Generate Excel report                  │
│  ↓                                                          │
│  📱 Telegram: Kirim hasil + file Excel ke user              │
└─────────────────────────────────────────────────────────────┘
```

#### C. Komponen Penting
| Skill OpenClaw | Fungsi |
|---------------|--------|
| `pajak-pmk6-2026` | Hitung PPh 21 DTP sesuai regulasi |
| `cek-syarat-pmk6` | Validasi eligibility peserta |
| `generate-laporan-bulanan` | Buat format Lampiran B |
| `voice-generator` | Convert teks hasil ke audio (clonev) |
| `frontend-design` | Generate dashboard UI code |

#### D. Use Case Nyata
**Workflow Lengkap**:
1. User upload PDF PMK → AI extract rule
2. User kirim data 25 peserta via Telegram → AI hitung semua
3. AI generate Excel dengan format Lampiran B
4. AI kirim notifikasi: "✅ 25 peserta diproses, total PPh DTP: Rp 12.345.000"
5. User review → approve → file tersimpan ke folder terstruktur

#### E. Tools & Teknologi
| Tool | Fungsi |
|------|--------|
| OpenClaw | Agent orchestration & skills |
| python-telegram-bot | Telegram integration |
| pandas + openpyxl | Excel manipulation |
| Streamlit | Dashboard UI |
| clonev | Voice generation (Coqui XTTS v2) |

#### F. Evaluasi Kritis
| Aspek | Penilaian |
|-------|-----------|
| **Kelebihan** | End-to-end otomatis, konsisten, scalable |
| **Kekurangan** | Setup awal kompleks, debugging lebih sulit |
| **Batasan** | Error di satu komponen bisa break seluruh workflow |
| **Risiko** | Over-automation tanpa validasi → error masif |

#### G. Harga & Akses
- **Semua tools**: Gratis (open source)
- **Telegram Bot**: Gratis (hingga limit tertentu)

#### H. Perbandingan
| Aspek | Manual | Semi-Auto | Full Auto |
|-------|--------|-----------|-----------|
| Kecepatan | 🐌 | 🚶 | 🚀 |
| Akurasi | ✅ (jika teliti) | ✅ | ⚠️ (perlu validasi) |
| Effort | ❌ Tinggi per kasus | ⚠️ Sedang | ✅ Tinggi di awal, rendah setelahnya |
| Risk | ✅ Terkontrol | ✅ | ⚠️ Perlu monitoring |

---

### 2.6 Infrastruktur & Hardware

#### A. Inti Konsep
**Definisi**: Spesifikasi hardware yang dibutuhkan untuk menjalankan stack AI lokal dengan performa optimal.

**Tujuan**: Memastikan sistem berjalan lancar tanpa bottleneck atau crash.

**Masalah yang Diselesaikan**: RAM不足导致 swap 到 disk (非常慢), GPU 不支持导致无法加速。

#### B. Mekanisme & Cara Kerja
```
Model Size → RAM Requirement → Performance

3B  (Q4_K_M) = ~2.5 GB  → 8 GB RAM sufficient
7B  (Q4_K_M) = ~5.5 GB  → 16 GB RAM recommended
14B (Q4_K_M) = ~10 GB   → 24-32 GB RAM recommended
```

#### C. Komponen Penting
| Komponen | Minimum | Recommended | Impact |
|----------|---------|-------------|--------|
| **RAM** | 8 GB | 16 GB DDR4/DDR5 | Model size & speed |
| **Storage** | 50 GB SSD | 256 GB NVMe SSD | Load time (5x faster than HDD) |
| **CPU** | Intel i5 / Ryzen 5 | Intel i7 / Ryzen 7 | Inference speed |
| **GPU** | Optional | NVIDIA RTX 3060+ (8GB VRAM) | 3-5x speedup for inference |

#### D. Use Case Nyata
**Setup untuk Proyek Pajak AI**:
```
• RAM: 16 GB DDR4 3200MHz (dual channel) → ~Rp 600rb
• Storage: 256 GB NVMe SSD → ~Rp 400rb
• GPU: Optional (RTX 3060 12GB → ~Rp 4-5jt)
• Total: ~Rp 1-1,5jt upgrade dari 8GB baseline
```

#### E. Tools & Teknologi
| Tool | Fungsi |
|------|--------|
| CPU-Z | Check RAM type, speed, slots |
| Task Manager / Activity Monitor | Monitor RAM usage real-time |
| Ollama | Auto-detect GPU & offload layers |

#### F. Evaluasi Kritis
| Aspek | Penilaian |
|-------|-----------|
| **Kelebihan** | One-time investment, no recurring cost, full control |
| **Kekurangan** | Upfront cost, hardware depreciation, maintenance |
| **Batasan** | Laptop RAM sering disolder (tidak bisa upgrade) |
| **Risiko** | Hardware failure → backup critical |

#### G. Harga & Akses
| Komponen | Harga (IDR) |
|----------|-------------|
| RAM 8GB DDR4 | Rp 300-450rb |
| RAM 16GB DDR4 | Rp 550-800rb |
| SSD 256GB NVMe | Rp 300-500rb |
| GPU RTX 3060 12GB | Rp 4-5jt |

#### H. Perbandingan
| Setup | Cost | Performance | Recommendation |
|-------|------|-------------|----------------|
| 8GB RAM, CPU-only | Rp 0 (existing) | ⚠️ 3B model only | Testing only |
| 16GB RAM, CPU-only | ~Rp 600rb | ✅ 7B model comfortable | ✅ Best value |
| 16GB RAM + GPU | ~Rp 5-6jt | 🚀 7B model fast | Production use |
| 32GB RAM + GPU | ~Rp 8-10jt | 🚀🚀 14B model possible | Enterprise |

---

## 3. SINTESIS PENGETAHUAN

### Prinsip Utama (Core Principles)

| No | Prinsip | Penjelasan |
|----|---------|-----------|
| 1 | **Privasi First** | Data pajak sensitif → selalu lokal, enkripsi, tidak ke cloud publik |
| 2 | **Human-in-the-Loop** | AI tidak 100% autonomous untuk domain kritis → validasi manusia wajib |
| 3 | **Versioning Everything** | Rule, model, training data → semua punya versi & audit trail |
| 4 | **Start Small, Scale Smart** | Mulai 3B model → test → upgrade ke 7B → production |
| 5 | **Backup Religiously** | training_data.jsonl > model weights (model bisa download ulang, data tidak) |

### Pola Berulang (Patterns)

| Pattern | Deskripsi | Contoh |
|---------|-----------|--------|
| **Extract → Validate → Store → Execute** | Workflow standar untuk regulasi baru | PMK 6/2026 extraction |
| **Confidence Threshold → HITL → Learn** | Self-improvement loop | Telegram tanya user jika confidence <80% |
| **Active Rule + Deprecated Rule** | Versioning tanpa delete | PMK lama tetap akses untuk kasus historis |
| **Local API Abstraction** | Ganti model tanpa ubah kode | `AI_MODEL = "qwen2.5-coder:7b"` di config |

### Insight Penting (Takeaways)

1. **7B adalah Sweet Spot**: Untuk 90% use case (termasuk pajak), 7B model dengan 16GB RAM = optimal balance.
2. **Quantization adalah Teman**: Q4_K_M reduce size 50-75% dengan quality loss minimal.
3. **Jangan Delete, Deprecate**: Rule lama tetap berharga untuk audit & kasus historis.
4. **AI adalah Co-pilot, bukan Pilot**: Untuk domain pajak, human validation tetap mandatory.
5. **Ollama = Game Changer**: 1 command install, 1 command pull → democratize local AI.

---

## 4. SISTEM / FRAMEWORK

### Workflow Implementasi Pajak AI (Step-by-Step)

```
PHASE 1: SETUP (Hari 1-2)
├─ 1. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh
├─ 2. Pull models:
│   ├─ ollama pull qwen2.5-coder:7b
│   ├─ ollama pull qwen2.5-vl:7b
│   └─ ollama pull nomic-embed-text
├─ 3. Install OpenClaw: npm install -g openclaw
├─ 4. Setup ChromaDB untuk RAG
└─ 5. Test: ollama run qwen2.5-coder:7b "Halo!"

PHASE 2: REGULASI INGESTION (Hari 3-4)
├─ 1. Upload PMK 6/2026 PDF ke dashboard
├─ 2. Qwen2.5-VL extract rule (tarif, periode, syarat)
├─ 3. Simpan ke training_data.jsonl + ChromaDB
├─ 4. Test dengan contoh dari Lampiran A
└─ 5. Validate hasil vs contoh di PDF

PHASE 3: INTEGRATION (Hari 5-7)
├─ 1. Setup Telegram bot (via BotFather)
├─ 2. Connect OpenClaw ke Telegram
├─ 3. Create skill `pajak-pmk6-2026`
├─ 4. Setup Excel template (Lampiran B format)
└─ 5. Test end-to-end: Telegram → AI → Excel → Telegram

PHASE 4: SELF-LEARNING (Ongoing)
├─ 1. Set confidence threshold: 80%
├─ 2. Enable HITL: AI tanya via Telegram jika <80%
├─ 3. Simpan semua Q&A ke training_data.jsonl
├─ 4. Auto-retrain setelah 10 pertanyaan baru
└─ 5. Monitor & backup weekly

PHASE 5: PRODUCTION (Ongoing)
├─ 1. Deploy dashboard Streamlit (local or VPS)
├─ 2. Setup backup automation (training data + models)
├─ 3. Document all rules & versions
├─ 4. Train team on validation workflow
└─ 5. Review & update regulasi quarterly
```

### Checklist Deployment

```
[ ] Ollama installed & models pulled
[ ] OpenClaw configured dengan Ollama API
[ ] training_data.jsonl backup routine setup
[ ] Telegram bot tested end-to-end
[ ] Excel template match Lampiran B format
[ ] Confidence threshold set (80% recommended)
[ ] Human validation workflow documented
[ ] Backup strategy: 2 locations minimum
[ ] Monitoring: RAM usage, error logs, response time
[ ] Documentation: All rules, versions, contacts
```

---

## 5. OUTPUT ARTEFAK (.skill)

### Template: `pajak-pmk6-2026.skill`

```json
{
  "name": "pajak-pmk6-2026",
  "version": "1.0.0",
  "description": "Menghitung PPh 21 DTP untuk Peserta Pemagangan sesuai PMK Nomor 6 Tahun 2026",
  "author": "Your Name",
  "license": "Apache 2.0",
  
  "config": {
    "model": "qwen2.5-coder:7b",
    "ollama_url": "http://localhost:11434",
    "confidence_threshold": 0.80,
    "regulasi_version": "PMK-6/2026"
  },
  
  "rules": {
    "tarif_pph21": 0.05,
    "periode_mulai": "2025-10-01",
    "periode_selesai": "2026-12-31",
    "syarat": [
      "memiliki_npwp_nik",
      "tidak_dapat_insentif_lain",
      "lulusan_perguruan_tinggi"
    ]
  },
  
  "inputs": {
    "nama_peserta": "string (required)",
    "uang_saku": "number (required)",
    "iuran_jkk_jkm": "number (required)",
    "bulan_magang": "date (required)",
    "npwp_nik": "string (required)"
  },
  
  "outputs": {
    "penghasilan_bruto": "number",
    "pph21": "number",
    "pph_dtp": "number",
    "diterima_bersih": "number",
    "status_eligibility": "string",
    "dasar_hukum": "array"
  },
  
  "workflow": [
    {
      "step": 1,
      "action": "validate_periode",
      "check": "bulan_magang >= 2025-10-01 AND bulan_magang <= 2026-12-31"
    },
    {
      "step": 2,
      "action": "validate_syarat",
      "check": "npwp_nik exists AND tidak_dapat_insentif_lain == true"
    },
    {
      "step": 3,
      "action": "calculate_bruto",
      "formula": "uang_saku + iuran_jkk_jkm"
    },
    {
      "step": 4,
      "action": "calculate_pph21",
      "formula": "penghasilan_bruto * 0.05"
    },
    {
      "step": 5,
      "action": "generate_output",
      "template": "excel_lampiran_b"
    }
  ],
  
  "hitl": {
    "enabled": true,
    "confidence_threshold": 0.80,
    "telegram_channel": "@your_bot",
    "fallback_action": "ask_user"
  },
  
  "versioning": {
    "current_version": "1.0.0",
    "replaces": null,
    "replaced_by": null,
    "valid_from": "2026-02-21",
    "valid_until": null,
    "changelog": [
      "2026-02-21: Initial release based on PMK-6/2026"
    ]
  },
  
  "backup": {
    "training_data_path": "~/.openclaw/memory/pajak_learning/training_data.jsonl",
    "backup_frequency": "weekly",
    "backup_locations": ["external_drive", "encrypted_cloud"]
  }
}
```

### Template: `prompt-ekstraksi-pmk.prompt`

```
Anda adalah asisten pakar perpajakan Indonesia.

Tugas: Ekstrak rule perhitungan pajak dari dokumen regulasi berikut.

Output HARUS dalam JSON format:
{
  "regulasi_id": "PMK-X/YYYY",
  "topik": "string",
  "periode_berlaku": {
    "mulai": "YYYY-MM-DD",
    "selesai": "YYYY-MM-DD"
  },
  "tarif": {
    "jenis": "string",
    "nilai": number,
    "satuan": "persen"
  },
  "syarat": ["list string"],
  "contoh_perhitungan": [
    {
      "input": {...},
      "output": {...},
      "langkah": ["step-by-step"]
    }
  ],
  "pasal_referensi": ["list pasal"],
  "confidence": 0-1
}

Dokumen:
{{document_text}}

Mulai ekstraksi:
```

### Template: `backup-script.sh`

```bash
#!/bin/bash
# backup-pajak-ai.sh - Backup training data & models

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/pajak-ai/$DATE"
mkdir -p $BACKUP_DIR

# Backup training data
cp -r ~/.openclaw/memory/pajak_learning $BACKUP_DIR/

# Backup Ollama models (optional, besar)
# cp -r ~/.ollama/models $BACKUP_DIR/

# Create checksum
find $BACKUP_DIR -type f -exec md5sum {} \; > $BACKUP_DIR/checksums.md5

# Compress
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR

# Copy to external drive (if mounted)
if [ -d "/media/external-drive" ]; then
    cp $BACKUP_DIR.tar.gz /media/external-drive/
fi

echo "✅ Backup selesai: $BACKUP_DIR.tar.gz"
```

---

## Metadata Dokumen

| Field | Value |
|-------|-------|
| **Dokumen** | SISTEM PENGETAHUAN - AI PAJAK SELF-LEARNING STACK |
| **Versi** | 1.0.0 |
| **Tanggal** | 2026-02-21 |
| **Berdasarkan** | Sesi diskusi + PMK 6/2026 |
| **Lisensi** | CC BY-SA 4.0 (bebas digunakan & dimodifikasi) |
| **Penyusun** | AI Assistant + User Collaboration |
| **Status** | Production Ready |

---

> 🎯 **Dokumen ini siap disimpan sebagai `.md` atau `.txt` file untuk referensi masa depan.**