---
title: Continual Learning & Self-Hosted AI Infrastructure
kategori: AI Model & Arsitektur
tags: [Continual-Learning, EWC, LoRA, Self-Hosted, GPU, Jetson, VRAM, Infrastructure]
---
# 🧠 SISTEM PENGETAHUAN: CONTINUAL LEARNING & INFRASTRUKTUR AI SELF-HOSTED

---

## 1. KATEGORI (TEMA BESAR)

| Kategori | Cakupan |
|----------|---------|
| **A. Continual Learning Theory** | Metode anti-forgetting, arsitektur, regularisasi |
| **B. Hardware Infrastructure** | Edge vs Desktop, GPU selection, spesifikasi |
| **C. System Expansion** | VRAM, RAM, Storage optimization strategies |
| **D. Implementation Framework** | Tools, repositori, workflow deployment |

---

## 2. SUB-TOPIK (TEMA SPESIFIK)

---

### A1. ELASTIC WEIGHT CONSOLIDATION (EWC)

#### A. Inti Konsep
| Aspek | Deskripsi |
|-------|-----------|
| **Definisi** | Teknik regularisasi yang melindungi bobot penting dari tugas sebelumnya saat belajar tugas baru |
| **Tujuan** | Mencegah Catastrophic Forgetting dalam Continual Learning |
| **Masalah yang Diselesaikan** | Neural network yang lupa pengetahuan lama saat belajar hal baru |

#### B. Mekanisme & Cara Kerja
```
Alur EWC:
1. Train Task A → Simpan bobot optimal (θ*A)
2. Hitung Fisher Information Matrix (F) → Ukur kepentingan tiap bobot
3. Train Task B → Modifikasi loss function:
   L(θ) = L_new(θ) + Σ(λ/2) × F_i × (θ_i - θ*A_i)²
4. Bobot penting (F besar) → Penalty besar → Tidak berubah
5. Bobot tidak penting (F kecil) → Penalty kecil → Bebas berubah
```

#### C. Komponen Penting
| Komponen | Peran | Hubungan |
|----------|-------|----------|
| **Fisher Information Matrix** | Mengukur kepentingan bobot | Input untuk penalty calculation |
| **λ (Lambda)** | Hyperparameter kekuatan proteksi | Mengontrol trade-off stabilitas-plastisitas |
| **θ*A (Old Weights)** | Bobot optimal tugas lama | Reference point untuk penalty |
| **L_new** | Loss tugas baru | Objective utama training |

#### D. Use Case Nyata
```
Workflow EWC:
1. Selesaikan training Task A (misal: klasifikasi kucing)
2. Export bobot + hitung Fisher Matrix
3. Simpan θ*A dan F sebagai "memori"
4. Mulai training Task B (misal: klasifikasi anjing)
5. Gunakan modified loss dengan EWC penalty
6. Evaluasi pada Task A + Task B → Pastikan tidak lupa
```

#### E. Tools & Teknologi
| Tool | Fungsi | Posisi |
|------|--------|--------|
| **Avalanche** | Framework CL lengkap | Orchestrator training |
| **PyTorch** | Deep learning backend | Core computation |
| **TensorBoard** | Monitoring | Visualization |

#### F. Evaluasi Kritis
| Aspek | Detail |
|-------|--------|
| **Kelebihan** | Tidak perlu simpan data lama, efisien memori, terinspirasi biologis |
| **Kekurangan** | Komputasi Fisher mahal, asumsi bobot independen, performa menengah |
| **Batasan** | Tidak optimal untuk tugas sangat banyak (100+) |
| **Risiko** | λ terlalu besar → model kaku; λ terlalu kecil → tetap lupa |

#### G. Harga & Akses
| Item | Harga | Akses |
|------|-------|-------|
| **EWC Algorithm** | Gratis | Open source |
| **Avalanche Framework** | Gratis | GitHub: ContinualAI/avalanche |

#### H. Perbandingan
| Metode | Kapan Lebih Unggul |
|--------|-------------------|
| **EWC vs Replay** | EWC: privasi tinggi (no data storage); Replay: akurasi lebih baik |
| **EWC vs SI** | EWC: lebih stabil; SI: lebih cepat (online computation) |
| **EWC vs LoRA** | EWC: single model; LoRA: multiple adapters (lebih scalable) |

---

### A2. ADVANCED CONTINUAL LEARNING METHODS

#### A. Inti Konsep
| Metode | Definisi | Tujuan |
|--------|----------|--------|
| **SI (Synaptic Intelligence)** | Regularisasi online berbasis kontribusi gradient | Lebih cepat dari EWC |
| **MAS (Memory Aware Synapses)** | Importance berdasarkan sensitivitas fungsi | Alternatif Fisher-free |
| **Replay (iCaRL, DER, GEM)** | Simpan data/logits lama untuk diulang | Akurasi tertinggi |
| **Architecture-based (PNN, PackNet)** | Tambah/prune arsitektur per tugas | Zero forgetting |
| **PEFT/LoRA** | Adapter kecil pada frozen backbone | Efisien untuk LLM/Transformer |
| **Prompt Learning (L2P)** | Belajar prompt vector, bukan bobot | Edge-native untuk ViT/LLM |

#### B. Mekanisme & Cara Kerja
```
Hierarki Metode CL:

┌─────────────────────────────────────────┐
│         REGULARIZATION-BASED            │
│  EWC → SI → MAS (proteksi bobot)        │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│           REPLAY-BASED                  │
│  iCaRL (data) → DER (logits) → GEM      │
│  (gradient projection)                  │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│        ARCHITECTURE-BASED               │
│  PNN (add columns) → PackNet (prune)    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         PARAMETER-EFFICIENT             │
│  LoRA → Prompt Learning → O-LoRA        │
└─────────────────────────────────────────┘
```

#### C. Komponen Penting
| Komponen | Metode Terkait | Peran |
|----------|---------------|-------|
| **Exemplar Buffer** | iCaRL, GEM | Simpan data lama |
| **Logits Memory** | DER | Simpan output model lama (privacy-safe) |
| **Adapter Modules** | LoRA, O-LoRA | Parameter kecil per tugas |
| **Prompt Vectors** | L2P | Input conditioning per tugas |
| **Task Router** | Dynamic Architecture | Deteksi & aktifkan adapter yang sesuai |
| **Generative Replay** | Advanced Replay | Generate data sintetis (no raw data storage) |

#### D. Use Case Nyata
```
Stack Rekomendasi per Skenario:

🎯 General Research:
   Avalanche + EWC/Replay → Prototyping cepat

🎯 Vision Transformer:
   L2P (google-research/l2p) + Mammoth (DER) → SOTA accuracy

🎯 LLM Fine-tuning:
   HuggingFace PEFT (LoRA) + O-LoRA → Efficient CL

🎯 Production Edge:
   Frozen Backbone + Dynamic LoRA + Generative Replay → Nexus-CL
```

#### E. Tools & Teknologi
| Tool | Repository | Fungsi |
|------|------------|--------|
| **Avalanche** | ContinualAI/avalanche | Framework CL lengkap |
| **L2P** | google-research/l2p | Prompt learning untuk ViT |
| **PEFT** | huggingface/peft | LoRA adapter untuk LLM |
| **Mammoth** | aimagelab/mammoth | DER implementation |
| **O-LoRA** | huangzheng12/O-LoRA | Orthogonal adapter |
| **LLM-CL** | ZhengyiMa/LLM-Continual-Learning | CL khusus LLM |

#### F. Evaluasi Kritis
| Metode | Kelebihan | Kekurangan |
|--------|-----------|------------|
| **Regularization** | No data storage, simple | Akurasi menengah |
| **Replay** | Akurasi tertinggi | Butuh memori, privacy concern |
| **Architecture** | Zero forgetting | Model membesar tak terbatas |
| **PEFT/Prompt** | Efisien, scalable | Butuh backbone pre-trained bagus |

#### G. Harga & Akses
Semua tools **open source & gratis**. Biaya hanya untuk komputasi (GPU cloud atau hardware lokal).

#### H. Perbandingan
| Skenario | Metode Terbaik | Alasan |
|----------|---------------|--------|
| Privacy-critical | LwF / MAS | No data storage |
| Accuracy-critical | DER / GEM | Replay memberikan hasil terbaik |
| Resource-limited | LoRA / L2P | Minimal parameter training |
| Production-scale | Nexus-CL (hybrid) | Balance semua faktor |

---

### B1. HARDWARE SELECTION: EDGE VS DESKTOP

#### A. Inti Konsep
| Aspek | Edge (Jetson) | Desktop (RTX) |
|-------|---------------|---------------|
| **Filosofi** | AI di ujung jaringan, low-power | Powerhouse workstation |
| **Target** | Robotika, IoT, 24/7 server | Gaming, training, heavy inference |
| **Trade-off** | Efisiensi vs Performa | Performa vs Konsumsi daya |

#### B. Mekanisme & Cara Kerja
```
Decision Framework:

                    ┌─────────────────┐
                    │   Use Case?     │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   Mobile/Portable     Server 24/7         Training/Heavy
   (Drone, Robot)      (Nextcloud)         (LLM, Gaming)
        │                    │                    │
        ▼                    ▼                    ▼
   Jetson Orin Nano     Jetson Orin Nano    Desktop RTX 5060+
   Super (7-25W)        Super (7-25W)       (145W+)
```

#### C. Komponen Penting
| Komponen | Jetson Orin Nano Super | RTX 5060 |
|----------|----------------------|----------|
| **GPU Architecture** | Ampere (1024 CUDA) | Blackwell 2.0 (3840 CUDA) |
| **AI Performance** | 67 TOPS (INT8) | ~614 TOPS (INT8) |
| **Memory** | 8GB LPDDR5 (102 GB/s) | 8GB GDDR7 (448 GB/s) |
| **Power** | 7-25W | 145W |
| **I/O** | MIPI CSI, GPIO, UART | HDMI, DP, PCIe |
| **CPU** | 6-core Arm A78AE | Tidak ada (butuh host) |
| **Harga** | $249 (kit lengkap) | $299 (GPU only) |

#### D. Use Case Nyata
```
🤖 Edge Deployment (Jetson):
   - Robot otonom dengan object detection
   - Kamera surveillance dengan AI inferensi
   - Nextcloud server + AI edge (24/7, low-power)

🖥️ Desktop Deployment (RTX):
   - Training model CV/NLP lokal
   - Gaming 1440p dengan ray tracing
   - LLM inference 7B-13B parameter
   - Content creation (rendering, video editing)
```

#### E. Tools & Teknologi
| Platform | SDK/Software |
|----------|--------------|
| **Jetson** | JetPack 6.0, TensorRT, CUDA, cuDNN |
| **Desktop** | NVIDIA Driver, CUDA Toolkit, PyTorch, TensorFlow |

#### F. Evaluasi Kritis
| Aspek | Jetson Orin Nano | RTX 5060 |
|-------|-----------------|----------|
| **Performa** | 6-10x lebih lambat | Baseline |
| **Efisiensi** | 2.68 TOPS/W | 4.23 TOPS/W |
| **Fleksibilitas** | Embedded I/O lengkap | Butuh PC lengkap |
| **Biaya Total** | $249 (all-in) | $299 + PC build ($800+) |
| **24/7 Viability** | ✅ Excellent ($5-10/tahun listrik) | ⚠️ Bisa ($50-80/tahun) |

#### G. Harga & Akses
| Produk | Harga | Link |
|--------|-------|------|
| **Jetson Orin Nano Super** | $249 | seeedstudio.com / nvidia.com |
| **RTX 5060** | $299 | Retail partners |
| **RTX 4090** | $1.599 | Retail partners |
| **RTX 3090 (bekas)** | $800-900 | Marketplace |

#### H. Perbandingan
| GPU | VRAM | AI TOPS | Harga | Best For |
|-----|------|---------|-------|----------|
| **RTX 5060** | 8GB | ~614 | $299 | Entry AI + Gaming |
| **RTX 5070** | 12GB | ~988 | $549 | Balance |
| **RTX 4090** | 24GB | ~1328 | $1.599 | LLM Training |
| **RTX 5090** | 32GB | ~3352 | $1.999 | Flagship AI |
| **RTX 3090 (bekas)** | 24GB | ~664 | $850 | Value AI |
| **RTX 4060 Ti 16GB** | 16GB | ~400 | $450 | Budget AI Server |

---

### B2. GPU HIERARCHY & SELECTION

#### A. Inti Konsep
**Prinsip**: VRAM adalah bottleneck utama untuk AI, bukan raw compute.

#### B. Mekanisme & Cara Kerja
```
VRAM Requirements untuk LLM:

Model Size    FP16    INT8    INT4
─────────────────────────────────────
7B            14GB    7GB     4GB
13B           26GB    13GB    7GB
32B           64GB    32GB    16GB
70B           140GB   70GB    35GB

Rule of Thumb: VRAM_needed = Model_params × Precision_bytes + Context_overhead
```

#### C. Komponen Penting
| Faktor | Impact pada AI |
|--------|---------------|
| **VRAM Capacity** | Menentukan model size maksimal |
| **Memory Bandwidth** | Menentukan inference speed (token/detik) |
| **Tensor Cores** | Accelerasi matrix operation (AI-specific) |
| **CUDA Cores** | General parallel compute |

#### D. Use Case Nyata
```
Rekomendasi per Budget:

💰 < $500:
   RTX 4060 Ti 16GB → LLM 7B-13B quantized

💰 $500-1000:
   RTX 3090 bekas → LLM 20B+ quantized (best value)

💰 $1000-2000:
   RTX 4090 → LLM 32B+ full precision

💰 > $2000:
   RTX 5090 → Future-proof, model terbesar
```

#### E. Tools & Teknologi
| Tool | Fungsi |
|------|--------|
| **vLLM** | Multi-GPU tensor parallelism |
| **llama.cpp** | CPU offloading untuk model besar |
| **TensorRT** | Model optimization & quantization |
| **bitsandbytes** | 4-bit/8-bit quantization |

#### F. Evaluasi Kritis
| Strategi | Kelebihan | Kekurangan |
|----------|-----------|------------|
| **Single High-VRAM GPU** | Simple, fast | Mahal |
| **Multi-GPU** | VRAM additive | Kompleks, butuh motherboard support |
| **CPU Offloading** | Murah (pakai RAM) | Lambat (2-5 token/detik) |
| **Quantization** | Hemat VRAM 50-75% | Akurasi turun sedikit |

#### G. Harga & Akses
Lihat tabel di B1.G

#### H. Perbandingan
| Kebutuhan | Solusi Terbaik |
|-----------|---------------|
| LLM 7B inference | RTX 4060 Ti 16GB |
| LLM 13B-20B | RTX 3090 bekas / 4070 Ti Super |
| LLM 32B+ | RTX 4090 / 5090 |
| Multi-tasking + Gaming | RTX 5070 Ti |
| Server 24/7 | RTX 4060 Ti 16GB (efisiensi) |

---

### C1. VRAM EXPANSION STRATEGIES

#### A. Inti Konsep
**VRAM tidak bisa di-upgrade fisik** (chip disolder). Solusi: workaround software + arsitektur.

#### B. Mekanisme & Cara Kerja
```
Strategi Ekspansi VRAM:

┌─────────────────────────────────────────────────┐
│  1. GANTI GPU (Solusi Fisik)                    │
│     Beli GPU dengan VRAM lebih besar            │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  2. MULTI-GPU (Tensor Parallelism)              │
│     vLLM: VRAM_effektif = VRAM_GPU1 + VRAM_GPU2 │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  3. CPU OFFLOADING                              │
│     llama.cpp: Layer GPU + Layer RAM sistem     │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┘
│  4. QUANTIZATION                                │
│     FP16 → INT8 → INT4 (hemat 50-75% VRAM)      │
└─────────────────────────────────────────────────┘
```

#### C. Komponen Penting
| Komponen | Fungsi |
|----------|--------|
| **vLLM** | Multi-GPU tensor parallelism |
| **llama.cpp** | CPU+GPU hybrid inference |
| **GGUF Format** | Quantized model format untuk llama.cpp |
| **AWQ/GPTQ** | Quantization algorithms |

#### D. Use Case Nyata
```bash
# Multi-GPU dengan vLLM
python -m vllm.entrypoints.api_server \
    --model meta-llama/Llama-2-7b-hf \
    --tensor-parallel-size 2 \
    --gpu-memory-utilization 0.9

# CPU Offloading dengan llama.cpp
./main -m models/llama-3-8b.Q4_K_M.gguf \
       -ngl 32 \
       --n-gpu-layers 32
```

#### E. Tools & Teknologi
| Tool | Fungsi |
|------|--------|
| **vLLM** | Multi-GPU inference |
| **llama.cpp** | CPU offloading |
| **AutoAWQ** | Automatic weight quantization |
| **ExLlamaV2** | Optimized inference engine |

#### F. Evaluasi Kritis
| Metode | Speed | VRAM Save | Complexity |
|--------|-------|-----------|------------|
| **Multi-GPU** | 100% | 2x VRAM | Medium |
| **CPU Offload** | 10-20% | Unlimited | Low |
| **Quantization** | 90-100% | 50-75% | Low |

#### G. Harga & Akses
Semua tools **gratis & open source**.

#### H. Perbandingan
| Skenario | Metode Terbaik |
|----------|---------------|
| Budget cukup | Ganti GPU |
| Budget terbatas | Quantization + CPU Offload |
| Production scale | Multi-GPU |

---

### C2. RAM & STORAGE EXPANSION

#### A. Inti Konsep
**RAM dan Storage bisa di-upgrade** — ini adalah ekspansi paling cost-effective untuk AI workstation.

#### B. Mekanisme & Cara Kerja
```
RAM Upgrade Path:
16GB → 32GB → 64GB → 128GB

Storage Hierarchy:
├── NVMe PCIe 4.0/5.0 → OS + Model AI (3.5-14 GB/s)
├── SATA SSD → Dataset sekunder (500 MB/s)
└── HDD → Arsip/Cold storage (150-250 MB/s)
```

#### C. Komponen Penting
| Komponen | Rekomendasi |
|----------|-------------|
| **RAM Minimum AI** | 32GB DDR5 |
| **RAM Optimal AI** | 64-128GB DDR5 |
| **OS Drive** | NVMe 500GB |
| **Model Storage** | NVMe 1-2TB |
| **Data Storage** | SATA SSD 4TB + HDD 8TB |

#### D. Use Case Nyata
```bash
# Setup Swap untuk Emergency Offloading
sudo fallocate -l 32G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Kernel Optimization untuk AI
echo 'vm.swappiness=1' | sudo tee -a /etc/sysctl.conf
echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.conf
echo 'vm.nr_hugepages=2048' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

#### E. Tools & Teknologi
| Tool | Fungsi |
|------|--------|
| **zram-config** | RAM compression |
| **nvme-cli** | NVMe management |
| **hdparm/fio** | Storage benchmarking |

#### F. Evaluasi Kritis
| Upgrade | Cost | Benefit |
|---------|------|---------|
| **RAM 32→64GB** | $80-120 | CPU offloading lebih smooth |
| **NVMe 1→2TB** | $60-100 | Lebih banyak model lokal |
| **HDD 8TB** | $150-200 | Arsip jangka panjang |

#### G. Harga & Akses
| Item | Harga (2026) |
|------|-------------|
| DDR5 32GB | $80-120 |
| DDR5 64GB | $150-250 |
| NVMe 1TB | $60-100 |
| HDD 8TB | $150-200 |

#### H. Perbandingan
| Platform | Storage Option |
|----------|---------------|
| **Desktop** | NVMe + SATA + HDD (flexible) |
| **Jetson** | NVMe M.2 + USB external (limited) |

---

### C3. JETSON-SPECIFIC EXPANSION

#### A. Inti Konsep
**Jetson Orin Nano: RAM & VRAM fixed (8GB unified)**. Hanya storage yang bisa di-upgrade.

#### B. Mekanisme & Cara Kerja
```
Jetson Optimization Stack:

┌─────────────────────────────────────────┐
│  1. NVMe Installation                   │
│     M.2 2280 → Primary storage          │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  2. TensorRT Quantization               │
│     FP16 → INT8 (hemat 50% memori)      │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  3. zram + Swap di NVMe                 │
│     Bukan di microSD!                   │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  4. Service Optimization                │
│     Disable unused services             │
└─────────────────────────────────────────┘
```

#### C. Komponen Penting
| Komponen | Fungsi |
|----------|--------|
| **NVMe M.2 2280** | Primary storage (2-3 GB/s) |
| **TensorRT** | Model optimization untuk Jetson |
| **zram** | RAM compression |
| **JetPack 6.0** | SDK lengkap (CUDA, cuDNN, TensorRT) |

#### D. Use Case Nyata
```bash
# Install NVMe di Jetson Orin Nano
sudo nvme list
sudo mkfs.ext4 /dev/nvme0n1
sudo mkdir /mnt/nvme
sudo mount /dev/nvme0n1 /mnt/nvme

# Setup Swap di NVMe (bukan microSD!)
sudo fallocate -l 8G /mnt/nvme/swapfile
sudo chmod 600 /mnt/nvme/swapfile
sudo mkswap /mnt/nvme/swapfile
sudo swapon /mnt/nvme/swapfile

# TensorRT Conversion
trtexec --onnx=model.onnx \
        --saveEngine=model_int8.engine \
        --int8
```

#### E. Tools & Teknologi
| Tool | Fungsi |
|------|--------|
| **JetPack SDK** | Driver + libraries |
| **TensorRT** | Inference optimization |
| **jtop** | System monitoring |
| **jetson_clocks** | Performance tuning |

#### F. Evaluasi Kritis
| Aspek | Detail |
|-------|--------|
| **Kelebihan** | Low-power, embedded I/O, TensorRT optimized |
| **Kekurangan** | RAM/VRAM fixed, tidak bisa upgrade |
| **Batasan** | Model maksimal ~7B quantized |
| **Risiko** | microSD untuk swap → cepat rusak |

#### G. Harga & Akses
| Item | Harga |
|------|-------|
| **Jetson Orin Nano Super Kit** | $249 |
| **NVMe 1TB** | $60-100 |
| **JetPack SDK** | Gratis |

#### H. Perbandingan
| Platform | RAM | VRAM | Storage |
|----------|-----|------|---------|
| **Jetson Orin Nano** | 8GB (fixed) | 8GB (unified) | NVMe expandable |
| **Desktop RTX** | Expandable | GPU-dependent | Unlimited |

---

### D1. HYBRID ARCHITECTURE FRAMEWORK

#### A. Inti Konsep
**Gabungkan Edge + Desktop** untuk optimalisasi: Edge handle 24/7 low-power tasks, Desktop handle heavy computation.

#### B. Mekanisme & Cara Kerja
```
🏠 Hybrid Setup Architecture:

┌─────────────────────────────────────────────────┐
│              JETSON ORIN NANO (Edge)            │
│  • Nextcloud server (24/7, 7-25W)               │
│  • Real-time AI: kamera, sensor, pre-processing │
│  • Storage: NVMe 1TB + HDD 4TB                  │
│  • Sync ke desktop via rsync/Syncthing          │
└─────────────────────────────────────────────────┘
                        │
                        │ Network Sync
                        ▼
┌─────────────────────────────────────────────────┐
│              DESKTOP PC (Workstation)           │
│  • Training / fine-tuning model AI              │
│  • Heavy inference (batch, LLM besar)           │
│  • Backup / mirror dari Jetson                  │
│  • Storage: NVMe 2TB + HDD 8TB                  │
└─────────────────────────────────────────────────┘
```

#### C. Komponen Penting
| Komponen | Lokasi | Fungsi |
|----------|--------|--------|
| **Nextcloud** | Jetson | File sync & sharing |
| **YOLO/Whisper** | Jetson | Real-time inference |
| **LLM Training** | Desktop | Heavy computation |
| **rsync/Syncthing** | Both | Data synchronization |
| **Docker** | Both | Container management |

#### D. Use Case Nyata
```
Workflow Hybrid:

1. Jetson capture data dari kamera/sensor
2. Pre-processing & inferensi ringan di Jetson
3. Data penting sync ke Desktop
4. Desktop train/fine-tune model dengan data baru
5. Model updated deploy kembali ke Jetson
6. Repeat
```

#### E. Tools & Teknologi
| Tool | Fungsi |
|------|--------|
| **Nextcloud** | Self-hosted cloud |
| **Docker** | Containerization |
| **rsync/Syncthing** | File synchronization |
| **Ollama** | LLM inference |
| **Portainer** | Container management UI |

#### F. Evaluasi Kritis
| Aspek | Detail |
|-------|--------|
| **Kelebihan** | Best of both worlds, scalable, privacy-first |
| **Kekurangan** | Kompleksitas setup, butuh 2 device |
| **Batasan** | Network dependency untuk sync |
| **Risiko** | Data inconsistency jika sync gagal |

#### G. Harga & Akses
| Komponen | Harga |
|----------|-------|
| **Jetson Orin Nano** | $249 |
| **Desktop RTX 5060** | $299 + PC build |
| **Total** | ~$1.300-1.500 |

#### H. Perbandingan
| Setup | Cost | Complexity | Capability |
|-------|------|------------|------------|
| **Jetson Only** | $249 | Low | Edge inference only |
| **Desktop Only** | $1.000+ | Medium | Heavy compute only |
| **Hybrid** | $1.500+ | High | Full spectrum |

---

### D2. IMPLEMENTATION ROADMAP

#### A. Inti Konsep
**Step-by-step deployment** untuk self-hosted AI infrastructure.

#### B. Mekanisme & Cara Kerja
```
Phase 1: Foundation (Week 1-2)
├── Setup hardware (Jetson/Desktop)
├── Install OS (Ubuntu 22.04 + JetPack)
├── Configure storage (NVMe + swap)
└── Basic Docker setup

Phase 2: Core Services (Week 3-4)
├── Nextcloud installation
├── Database (PostgreSQL/MySQL)
├── Redis caching
└── Backup system

Phase 3: AI Integration (Week 5-6)
├── Ollama/llama.cpp installation
├── Model download & quantization
├── API endpoint setup
└── Integration dengan Nextcloud

Phase 4: Optimization (Week 7-8)
├── TensorRT optimization
├── Monitoring setup (jtop, nvitop)
├── Automation (cron, systemd)
└── Documentation
```

#### C. Komponen Penting
| Phase | Deliverables |
|-------|-------------|
| **1** | Working hardware + OS |
| **2** | Nextcloud accessible + backup working |
| **3** | LLM inference via API |
| **4** | Optimized, monitored, documented system |

#### D. Use Case Nyata
```yaml
# docker-compose.yml untuk Nextcloud + AI
version: '3.8'
services:
  nextcloud:
    image: nextcloud:latest
    ports:
      - "8080:80"
    volumes:
      - ./nextcloud:/var/www/html
    environment:
      - MYSQL_PASSWORD=xxx
  
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ./models:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

#### E. Tools & Teknologi
| Tool | Phase |
|------|-------|
| **Ubuntu 22.04** | 1 |
| **Docker** | 1-4 |
| **Nextcloud** | 2 |
| **Ollama** | 3 |
| **TensorRT** | 4 |
| **Portainer** | 2-4 |

#### F. Evaluasi Kritis
| Aspek | Detail |
|-------|--------|
| **Kelebihan** | Structured, repeatable, documented |
| **Kekurangan** | 8 weeks timeline (bisa dipercepat) |
| **Batasan** | Butuh basic Linux knowledge |
| **Risiko** | Configuration errors, data loss |

#### G. Harga & Akses
Semua software **gratis & open source**.

#### H. Perbandingan
| Approach | Time | Reliability |
|----------|------|-------------|
| **Ad-hoc** | 1-2 weeks | Low |
| **Structured (ini)** | 8 weeks | High |
| **Managed Service** | 1 day | Medium (vendor lock-in) |

---

## 3. SINTESIS PENGETAHUAN

### 🎯 Prinsip Utama (Core Principles)

| Prinsip | Penjelasan |
|---------|------------|
| **1. VRAM > Compute** | Untuk AI, kapasitas memori lebih kritis daripada raw FLOPS |
| **2. Edge + Cloud Hybrid** | Tidak ada satu device yang sempurna — gabungkan strengths |
| **3. Quantization First** | Selalu coba quantize sebelum upgrade hardware |
| **4. Privacy by Design** | Proses data sensitif di edge, sync hanya yang diperlukan |
| **5. Modular Architecture** | Pisahkan services (Nextcloud, LLM, DB) untuk scalability |
| **6. No Free Lunch** | Setiap optimasi ada trade-off (speed vs accuracy vs memory) |

### 🔁 Pola Berulang (Patterns)

| Pola | Konteks | Solusi |
|------|---------|--------|
| **Memory Bottleneck** | Model terlalu besar untuk VRAM | Quantization + CPU Offloading |
| **Privacy Concern** | Data tidak boleh keluar | Edge processing + encrypted sync |
| **Cost Limitation** | Budget terbatas | Bekas GPU + open source software |
| **Power Constraint** | 24/7 operation | Jetson/low-power GPU + hibernation |
| **Scale Requirement** | Multiple tasks/users | Multi-GPU + container orchestration |

### 💡 Insight Penting (Takeaways)

1. **EWC adalah foundation**, tapi **LoRA/Prompt Learning adalah SOTA** untuk Transformer-based models
2. **RTX 3090 bekas adalah value king** untuk AI — VRAM 24GB dengan harga setengah dari 4090
3. **Jetson Orin Nano Super** cocok untuk edge, tapi **8GB unified memory adalah hard limit**
4. **Hybrid architecture** memberikan best of both worlds dengan kompleksitas manageable
5. **Software optimization** (quantization, TensorRT) sering lebih cost-effective daripada hardware upgrade
6. **Continual Learning** masih research-heavy — production systems masih pakai fine-tuning + replay

---

## 4. SISTEM / FRAMEWORK

### 📋 DECISION FRAMEWORK: Pilih Hardware & Metode CL

```
┌─────────────────────────────────────────────────────────────┐
│                    START: Kebutuhan AI Anda?                │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
    Edge/Portable        Server 24/7         Training/Heavy
    (Robot, Drone)       (Nextcloud)         (LLM, Gaming)
         │                    │                    │
         ▼                    ▼                    ▼
   Jetson Orin Nano     Jetson Orin Nano    Desktop RTX 5060+
   Super                Super               (5070/4090/5090)
   7-25W                7-25W               145W+
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
         ┌─────────────────────────────────────────┐
         │     Continual Learning Method?          │
         └─────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
    Privacy-Critical    Accuracy-Critical    Resource-Limited
    (No data storage)   (Best performance)   (Limited VRAM)
         │                    │                    │
         ▼                    ▼                    ▼
    LwF / MAS           DER / GEM           LoRA / L2P
    Regularization      Replay-based        PEFT-based
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
         ┌─────────────────────────────────────────┐
         │     VRAM Expansion Needed?              │
         └─────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
    Budget Cukup         Budget Terbatas     Production Scale
    (Ganti GPU)          (Software workarounds) (Multi-GPU)
         │                    │                    │
         ▼                    ▼                    ▼
    Buy Higher VRAM     Quantize + Offload   vLLM Tensor Parallel
    GPU                 llama.cpp
```

### 📋 IMPLEMENTATION CHECKLIST

```
□ HARDWARE
  □ GPU selected (VRAM ≥ kebutuhan model)
  □ RAM ≥ 32GB (64GB recommended)
  □ NVMe SSD untuk OS + models
  □ PSU adequate (GPU TDP + 20% headroom)

□ SOFTWARE
  □ Ubuntu 22.04 LTS installed
  □ NVIDIA drivers + CUDA toolkit
  □ Docker + Docker Compose
  □ Nextcloud deployed
  □ Ollama/llama.cpp installed

□ AI STACK
  □ Models downloaded & quantized
  □ TensorRT optimization (Jetson)
  □ API endpoints configured
  □ Integration dengan Nextcloud

□ OPTIMIZATION
  □ Swap configured (NVMe, bukan microSD)
  □ zram enabled
  □ Monitoring setup (jtop, nvitop)
  □ Backup system tested

□ DOCUMENTATION
  □ Configuration documented
  □ Recovery procedures written
  □ Monitoring alerts configured
```

---

## 5. OUTPUT ARTEFAK (.skill)

```yaml
# =============================================================================
# SKILL: AI_SELF_HOSTED_INFRASTRUCTURE
# Version: 1.0
# Created: 2026
# =============================================================================

name: AI Self-Hosted Infrastructure Mastery
description: >
  Sistem pengetahuan komprehensif untuk membangun, mengoptimalkan, dan 
  maintaining infrastruktur AI self-hosted dengan Continual Learning capabilities.

domains:
  - Continual Learning Theory
  - Hardware Selection (Edge vs Desktop)
  - System Expansion (VRAM/RAM/Storage)
  - Implementation Framework

competencies:
  - name: "Continual Learning Method Selection"
    levels:
      beginner: "Memahami EWC dan catastrophic forgetting"
      intermediate: "Bisa implement SI, MAS, Replay methods"
      advanced: "Design hybrid CL architecture (Nexus-CL)"
    
  - name: "Hardware Architecture Design"
    levels:
      beginner: "Bisa pilih GPU berdasarkan VRAM needs"
      intermediate: "Design hybrid Edge+Desktop setup"
      advanced: "Multi-GPU tensor parallelism optimization"
    
  - name: "System Optimization"
    levels:
      beginner: "Install drivers, Docker, basic services"
      intermediate: "TensorRT quantization, swap optimization"
      advanced: "Full stack monitoring, automation, scaling"

tools_required:
  - Avalanche (Continual Learning)
  - HuggingFace PEFT (LoRA)
  - vLLM / llama.cpp (Inference)
  - Docker / Portainer (Orchestration)
  - Nextcloud (Self-hosted cloud)
  - TensorRT (Optimization)
  - jtop / nvitop (Monitoring)

decision_trees:
  hardware_selection: |
    IF mobile/portable → Jetson Orin Nano Super
    ELSE IF 24/7 server → Jetson Orin Nano Super OR RTX 4060 Ti 16GB
    ELSE IF training/heavy → RTX 5070+ / 4090 / 5090
    
  cl_method_selection: |
    IF privacy_critical → LwF / MAS
    ELSE IF accuracy_critical → DER / GEM
    ELSE IF resource_limited → LoRA / L2P
    
  vram_expansion: |
    IF budget_cukup → Ganti GPU
    ELSE IF budget_terbatas → Quantization + CPU Offload
    ELSE IF production_scale → Multi-GPU

workflows:
  - name: "New Deployment"
    steps:
      - "Select hardware based on decision tree"
      - "Install OS + drivers"
      - "Configure storage (NVMe + swap)"
      - "Deploy Docker services (Nextcloud, Ollama)"
      - "Download & quantize models"
      - "Setup monitoring & backup"
      - "Test & document"
    
  - name: "VRAM Optimization"
    steps:
      - "Measure current VRAM usage (nvitop)"
      - "Apply quantization (INT8/INT4)"
      - "If still insufficient: CPU offloading (llama.cpp)"
      - "If still insufficient: Multi-GPU (vLLM)"
      - "If still insufficient: Upgrade GPU"
    
  - name: "Continual Learning Pipeline"
    steps:
      - "Train Task A, save weights + Fisher Matrix"
      - "Collect Task B data"
      - "Train Task B with EWC/Replay penalty"
      - "Evaluate on Task A + Task B"
      - "If forgetting detected: adjust λ or add replay"
      - "Deploy updated model"

metrics:
  - "Inference speed (token/detik)"
  - "VRAM utilization (%)"
  - "Power consumption (Watt)"
  - "Model accuracy (before/after CL)"
  - "Forgetting measure (Task A accuracy drop)"

resources:
  repositories:
    - "https://github.com/ContinualAI/avalanche"
    - "https://github.com/huggingface/peft"
    - "https://github.com/google-research/l2p"
    - "https://github.com/ggerganov/llama.cpp"
    - "https://github.com/vllm-project/vllm"
  
  documentation:
    - "NVIDIA Jetson Documentation"
    - "HuggingFace PEFT Guide"
    - "llama.cpp Documentation"
    - "vLLM Documentation"

warnings:
  - "VRAM tidak bisa di-upgrade fisik pada GPU"
  - "Jetson RAM/VRAM fixed (8GB unified)"
  - "Swap di microSD → cepat rusak, gunakan NVMe"
  - "Multi-GPU butuh motherboard dengan PCIe bifurcation support"
  - "Quantization mengurangi akurasi (trade-off)"

version_history:
  - version: "1.0"
    date: "2026"
    changes: "Initial release based on comprehensive session analysis"
```

---

## 🏁 PENUTUP

Sistem pengetahuan ini mengkompres seluruh sesi menjadi **framework yang dapat ditindaklanjuti**. Gunakan decision trees untuk pemilihan, workflows untuk implementasi, dan .skill artifact untuk referensi berkelanjutan.

**Next Action**: Pilih satu workflow (misal: "New Deployment") dan eksekusi step-by-step dengan checklist yang disediakan.