---
title: Table Detection & Structure Recognition
kategori: Spreadsheet, Excel & Automation
tags: [table-detection, SLANet, OCR, PaddleOCR, deep-learning, structure-recognition]
---

# Table Detection & Structure Recognition

---

## 1. KATEGORI (TEMA BESAR)

| No | Kategori | Deskripsi |
|----|----------|-----------|
| 1 | **Table Detection & Structure Recognition** | Sistem ekstraksi tabel dari gambar dengan/tanpa border |
| 2 | **Deep Learning Architecture** | Arsitektur model SLANet dan cara kerjanya |
| 3 | **Performance & Optimization** | Waktu proses, hardware, dan optimasi |
| 4 | **AI Model Selection Strategy** | Pemilihan model Claude untuk coding & design |

---

## 2. SUB-TOPIK

### **KATEGORI 1: TABLE DETECTION & STRUCTURE RECOGNITION**

#### **1.1 Layout Analysis → Table Detection Pipeline**

**A. Inti Konsep**
- **Definisi**: Pipeline 2-layer untuk mendeteksi region table lalu ekstrak struktur internal
- **Tujuan**: Mengubah gambar tabel (dengan/tanpa border) menjadi data terstruktur (Excel/JSON/HTML)
- **Masalah yang Diselesaikan**: Tabel di dokumen scan/PDF sering berantakan saat dikonversi ke Excel; pipeline ini menjaga struktur row/column tetap rapi

**B. Mekanisme & Cara Kerja**
```
┌─────────────────────────────────────────────────────────────┐
│  PIPELINE: Image → Layout → Table Structure → OCR → Excel  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  STEP 1: Layout Analysis                                    │
│  Input: Full document image                                 │
│  Process: Deteksi region (table, text, image, title)        │
│  Output: Bbox table region [x1, y1, x2, y2]                 │
│                                                              │
│  STEP 2: Table Structure Recognition (SLANet)               │
│  Input: Cropped table image                                 │
│  Process: Prediksi struktur HTML + cell coordinates         │
│  Output: HTML structure + bbox per cell                     │
│                                                              │
│  STEP 3: Cell OCR (DB + CRNN)                               │
│  Input: Each cell bbox                                      │
│  Process: Text recognition per cell                         │
│  Output: Text content per cell                              │
│                                                              │
│  STEP 4: Merge & Export                                     │
│  Input: HTML structure + Cell text                          │
│  Output: Excel / HTML / JSON                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**C. Komponen / Fitur Penting**

| Komponen | Peran | Output Format |
|----------|-------|---------------|
| Layout Detection | Identifikasi area table | Bbox [x1,y1,x2,y2] |
| SLANet | Ekstrak struktur row/column | HTML + cell bbox |
| DB (Detection) | Deteksi text area dalam cell | Text bbox |
| CRNN (Recognition) | OCR text per cell | Text string |
| Export Module | Konversi ke format akhir | Excel/HTML/JSON |

**Output Structure:**
```json
{
  "bbox": [10, 10, 100, 50],
  "row": 0,
  "col": 0,
  "rowspan": 1,
  "colspan": 2,
  "text": "Nama Lengkap",
  "confidence": 0.95
}
```

**D. Use Case Nyata**

| Scenario | Workflow |
|----------|----------|
| **Invoice Processing** | Scan invoice → Detect table → Extract line items → Export to Excel |
| **Financial Report** | PDF report → Detect multiple tables → Structure each → Merge to spreadsheet |
| **Borderless Table** | Screenshot without borders → SLANet detect pattern → Extract structure |

**E. Tools & Teknologi**

| Tool | Fungsi | Posisi dalam Sistem |
|------|--------|---------------------|
| **PaddleOCR PP-Structure** | Main engine | Core pipeline |
| **SLANet** | Table structure recognition | Layer 2 |
| **SLANet_plus** | Improved borderless detection | Layer 2 (enhanced) |
| **DB (Differentiable Binarization)** | Text detection | Layer 3 |
| **CRNN** | Text recognition | Layer 3 |
| **pandas/openpyxl** | Excel export | Layer 4 |

**F. Evaluasi Kritis**

| Aspek | Kelebihan | Kekurangan | Batasan | Risiko |
|-------|-----------|------------|---------|--------|
| **Accuracy** | 90-95% (dengan border), 85-92% (tanpa border) | Borderless lebih challenging | Complex merged cells masih error | False positive pada non-table |
| **Speed** | 1-3 detik/image (CPU), 350ms (GPU) | GPU butuh setup tambahan | Large image (>4000px) lambat | Memory overflow untuk batch besar |
| **Flexibility** | Handle border & borderless | Need fine-tune untuk domain spesifik | Bahasa non-Latin kurang optimal | OCR error pada text berkualitas rendah |

**G. Harga & Akses**

| Versi | Harga | Akses |
|-------|-------|-------|
| **PaddleOCR (Open Source)** | Gratis | GitHub, pip install |
| **PaddlePaddle GPU** | Gratis (butuh GPU hardware) | CUDA support |
| **Cloud API Alternative** | Azure Form Recognizer: $1-5/1000 pages | Paid API |

**H. Perbandingan**

| Tool | Accuracy | Speed | Cost | Best For |
|------|----------|-------|------|----------|
| **PaddleOCR SLANet** | 90-95% | Fast (1-3s) | Free | Production open-source |
| **Tesseract + Custom** | 70-80% | Slow (5-10s) | Free | Simple tables only |
| **EasyOCR** | 85-90% | Medium (3-5s) | Free | General OCR |
| **Azure Form Recognizer** | 95-98% | Medium (2-5s) | Paid | Enterprise, no setup |

**Kapan Pilih Masing-Masing:**
- **PaddleOCR**: Production, cost-sensitive, need control
- **Azure**: Enterprise, budget available, no maintenance
- **Tesseract**: Legacy system, simple requirements

---

#### **1.2 Border vs Borderless Table Detection**

**A. Inti Konsep**
- **Definisi**: Kemampuan model mendeteksi tabel dengan garis border eksplisit vs hanya pola whitespace
- **Tujuan**: Handle berbagai format tabel dari berbagai sumber dokumen
- **Masalah yang Diselesaikan**: Tabel tanpa border sering gagal di traditional approach (OpenCV line detection)

**B. Mekanisme & Cara Kerja**

```
┌─────────────────────────────────────────────────────────────┐
│  DETECTION CUES                                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  DENGAN BORDER:                                             │
│  - Edge detection (garis horizontal/vertical)               │
│  - Contour finding (kotak-kotak jelas)                      │
│  - Cell boundary pasti                                      │
│  - Intersection points (grid structure)                     │
│                                                              │
│  TANPA BORDER:                                              │
│  - Whitespace pattern (jarak konsisten antar kolom)         │
│  - Text alignment (vertical alignment rapi)                 │
│  - Row consistency (tinggi row serupa)                      │
│  - Header pattern (row pertama berbeda)                     │
│  - Content type pattern (mix text/number dalam grid)        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**C. Komponen / Fitur Penting**

| Fitur | Dengan Border | Tanpa Border |
|-------|---------------|--------------|
| **Visual Cue** | Garis eksplisit | Whitespace pattern |
| **Confidence Score** | 95-98% | 85-92% |
| **Model Requirement** | SLANet | SLANet_plus (recommended) |
| **Cell Separation** | Presise | Andalkan alignment |

**D. Use Case Nyata**

| Scenario | Border Status | Solution |
|----------|---------------|----------|
| **Bank Statement** | Dengan border | SLANet standard |
| **Email Export** | Tanpa border | SLANet_plus |
| **Web Screenshot** | Mix | SLANet_plus (robust) |
| **PDF Export** | Biasanya ada border | SLANet standard |

**E. Tools & Teknologi**

| Tool | Border Support | Recommendation |
|------|----------------|----------------|
| **SLANet** | Both (better with border) | Simple tables |
| **SLANet_plus** | Both (optimized for borderless) | Production use |
| **OpenCV Traditional** | Border only | Legacy/deprecated |

**F. Evaluasi Kritis**

| Aspek | Dengan Border | Tanpa Border |
|-------|---------------|--------------|
| **Accuracy** | 95-98% | 85-92% |
| **Merged Cells** | Lebih akurat | Agak challenging |
| **Preprocessing Need** | Minimal | May need enhancement |
| **Risk** | Low | Medium (false negatives) |

**G. Harga & Akses**
- Tidak ada perbedaan harga (same model family)
- SLANet_plus slightly lebih berat komputasi

**H. Perbandingan**

| Approach | Border | Borderless | Recommendation |
|----------|--------|------------|----------------|
| **Traditional (OpenCV)** | ✅ Works | ❌ Fails | Deprecated |
| **SLANet** | ✅ Excellent | ⚠️ Good | Simple use case |
| **SLANet_plus** | ✅ Excellent | ✅ Very Good | **Production** |

---

### **KATEGORI 2: DEEP LEARNING ARCHITECTURE**

#### **2.1 SLANet Architecture (Structure Location Alignment Network)**

**A. Inti Konsep**
- **Definisi**: Neural network khusus untuk table structure recognition
- **Tujuan**: Mapping image pattern → HTML structure + cell coordinates
- **Masalah yang Diselesaikan**: Traditional OCR tidak paham struktur tabel, hanya text per line

**B. Mekanisme & Cara Kerja**

```
┌─────────────────────────────────────────────────────────────┐
│  SLANet Architecture                                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  INPUT IMAGE                                                │
│       ↓                                                      │
│  ┌─────────────────┐                                        │
│  │  PP-LCNet       │  ← Backbone (feature extractor)        │
│  │  (Lightweight)  │     Ekstrak fitur visual dari image    │
│  └─────────────────┘                                        │
│       ↓                                                      │
│  ┌─────────────────┐                                        │
│  │  CSP-PAN        │  ← Feature Pyramid Network             │
│  │                 │     Gabungkan fitur multi-scale        │
│  └─────────────────┘                                        │
│       ↓                                                      │
│  ┌─────────────────┐                                        │
│  │  Attention      │  ← Fokus ke area penting               │
│  │  Mechanism      │     Highlight region table             │
│  └─────────────────┘                                        │
│       ↓                                                      │
│  ┌─────────────────────────────────────────────┐            │
│  │              OUTPUT HEADS                    │            │
│  ├─────────────────────────────────────────────┤            │
│  │  1. structure_pobs  → HTML code structure   │            │
│  │  2. loc_preds       → Cell bbox coordinates │            │
│  └─────────────────────────────────────────────┘            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**C. Komponen / Fitur Penting**

| Komponen | Fungsi | Output |
|----------|--------|--------|
| **PP-LCNet** | Lightweight backbone | Feature maps |
| **CSP-PAN** | Multi-scale feature fusion | Enhanced features |
| **Attention Mechanism** | Focus on table regions | Weighted features |
| **structure_pobs** | HTML structure prediction | `<table><tr><td>...` |
| **loc_preds** | Cell location prediction | [x1,y1,x2,y2] per cell |

**D. Use Case Nyata**
- Training dari ribuan contoh table image dengan label HTML structure
- Model belajar mapping: Image Pattern → HTML Structure

**E. Tools & Teknologi**
- **PaddlePaddle**: Deep learning framework
- **SLANet**: Model architecture
- **SLANet_plus**: Improved version for borderless

**F. Evaluasi Kritis**

| Aspek | Kelebihan | Kekurangan |
|-------|-----------|------------|
| **Architecture** | Lightweight, fast inference | Need GPU for training |
| **Accuracy** | High for standard tables | Complex merged cells still challenging |
| **Flexibility** | Handle border & borderless | Domain-specific fine-tune may needed |

**G. Harga & Akses**
- Open source (PaddlePaddle)
- Pre-trained models available free

**H. Perbandingan**

| Model | Speed | Accuracy | Borderless Support |
|-------|-------|----------|-------------------|
| **SLANet** | Faster | Good | Good |
| **SLANet_plus** | Slightly slower | Better | **Excellent** |
| **TableBank Models** | Varies | Good | Limited |

---

### **KATEGORI 3: PERFORMANCE & OPTIMIZATION**

#### **3.1 Processing Time & Hardware Requirements**

**A. Inti Konsep**
- **Definisi**: Benchmark waktu inference dan requirement hardware
- **Tujuan**: Plan capacity dan choose deployment strategy
- **Masalah yang Diselesaikan**: Uncertainty tentang scalability dan cost

**B. Mekanisme & Cara Kerja**

| Hardware | Waktu per Image | Use Case |
|----------|-----------------|----------|
| **CPU (Intel)** | 1-3 detik | Small scale, testing |
| **GPU (T4)** | 350ms | Production medium |
| **GPU (A100)** | 100-200ms | High-scale production |
| **SLANet_plus inference only** | 23-63ms | Model only (no pre/post) |

**C. Komponen / Fitur Penting**

| Faktor | Impact | Optimization |
|--------|--------|--------------|
| **Image Resolution** | Tinggi = Lebih lama | Resize max 2000px |
| **Table Complexity** | Banyak cell = Lebih lama | Use SLANet for speed |
| **Hardware** | GPU 3-5x CPU | Batch processing |
| **Model Version** | SLANet vs SLANet_plus | Choose based on need |

**D. Use Case Nyata**

| Volume | Recommended Setup | Estimated Time |
|--------|-------------------|----------------|
| **100 images/hari** | CPU only | 3-5 menit total |
| **1000 images/hari** | Single GPU | 5-10 menit total |
| **10000 images/hari** | Multi-GPU batch | Parallel processing |

**E. Tools & Teknologi**
- **CUDA**: GPU acceleration
- **Batch Processing**: Parallel inference
- **Image Preprocessing**: cv2.resize, contrast enhancement

**F. Evaluasi Kritis**

| Aspek | Kelebihan | Kekurangan |
|-------|-----------|------------|
| **CPU** | No extra cost, easy setup | 3-5x slower |
| **GPU** | Fast, scalable | Hardware cost, setup complexity |
| **Cloud** | No maintenance | Ongoing cost, latency |

**G. Harga & Akses**
- CPU: Free (existing hardware)
- GPU: $0.50-3/jam (cloud), or hardware purchase
- Cloud API: Alternative to self-host

**H. Perbandingan**

| Setup | Cost | Speed | Recommendation |
|-------|------|-------|----------------|
| **CPU Only** | Low | Slow | Testing, small scale |
| **Single GPU** | Medium | Fast | Production standard |
| **Multi-GPU** | High | Very Fast | Enterprise scale |
| **Cloud API** | Variable | Fast | No maintenance |

---

### **KATEGORI 4: AI MODEL SELECTION STRATEGY**

#### **4.1 Claude Model Comparison (Opus, Sonnet, Haiku)**

**A. Inti Konsep**
- **Definisi**: 3 tier model dari Anthropic dengan trade-off capability, speed, cost
- **Tujuan**: Choose right model for specific use case
- **Masalah yang Diselesaikan**: Overpaying for capability not needed, or underperforming with cheap model

**B. Mekanisme & Cara Kerja**

```
┌─────────────────────────────────────────────────────────────┐
│  MODEL TIER STRUCTURE                                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  OPUS 4.6:    Premium (Strongest)                           │
│  - Complex reasoning, critical tasks                         │
│  - 5x cost of Haiku                                          │
│                                                              │
│  SONNET 4.6:  Balanced (Sweet Spot)                          │
│  - 90% use cases                                             │
│  - Best value proposition                                    │
│                                                              │
│  HAIKU 4.5:   Fast & Cheap                                   │
│  - High-volume, simple tasks                                 │
│  - 1/5 cost of Opus                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**C. Komponen / Fitur Penting**

| Model | Context Window | Speed | Cost (Input/Output) |
|-------|----------------|-------|---------------------|
| **Opus 4.6** | 200K tokens | Slowest | $5 / $25 per 1M tokens |
| **Sonnet 4.6** | 200K tokens | Fast | $3 / $15 per 1M tokens |
| **Haiku 4.5** | 200K tokens | Fastest | $1 / $5 per 1M tokens |

**D. Use Case Nyata**

| Task Type | Recommended Model | Reason |
|-----------|-------------------|--------|
| **Coding - Daily** | Sonnet 4.6 | 90% tasks, cost efficient |
| **Coding - Complex** | Opus 4.6 | Architecture, security, complex bugs |
| **Coding - Quick** | Haiku 4.5 | Autocomplete, simple fixes |
| **Design - Daily** | Sonnet 4.6 | UI/UX, design-to-code |
| **Design - Premium** | Opus 4.6 | Design system, Figma Make |
| **Design - Quick** | Haiku 4.5 | Color, typography ideas |
| **Table Detection Project** | Sonnet 4.6 | Balance cost & quality |

**E. Tools & Teknologi**
- **Anthropic API**: Direct access
- **Claude.ai**: Web interface
- **Third-party wrappers**: Various integrations

**F. Evaluasi Kritis**

| Model | Kelebihan | Kekurangan | Batasan |
|-------|-----------|------------|---------|
| **Opus** | Highest accuracy, complex reasoning | Most expensive, slower | Overkill for simple tasks |
| **Sonnet** | Best balance, 90% use cases | Not strongest for complex | May miss edge cases |
| **Haiku** | Fastest, cheapest | Lower accuracy for complex | Not for critical tasks |

**G. Harga & Akses**

| Volume/Month | Opus | Sonnet | Haiku |
|--------------|------|--------|-------|
| **10M tokens** | ~$300 | ~$180 | ~$60 |
| **100M tokens** | ~$3000 | ~$1800 | ~$600 |
| **Annual (10M/day)** | ~$900K | ~$180K | ~$60K |

**H. Perbandingan**

| Criteria | Opus | Sonnet | Haiku |
|----------|------|--------|-------|
| **Coding Quality** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Design Quality** | ⭐⭐⭐⭐⭐ (76%) | ⭐⭐⭐ (18.5%) | ⭐⭐ |
| **Speed** | 🐌 | ⚡ | 🚀 |
| **Cost Efficiency** | Low | **High** | **Highest** |
| **Recommendation** | 10% tasks | **90% tasks** | High-volume |

---

## 3. SINTESIS PENGETAHUAN

### **Prinsip Utama (Core Principles)**

```
┌─────────────────────────────────────────────────────────────┐
│  PRINSIP 1: MODEL BELAJAR POLA, BUKAN GARIS                 │
├─────────────────────────────────────────────────────────────┤
│  Table detection modern tidak mencari garis border, tapi    │
│  memahami pola visual: whitespace, alignment, consistency   │
│  → Bisa handle table dengan/tanpa border                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  PRINSIP 2: PIPELINE 2-LAYER (Layout → Structure)           │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Deteksi region table (bbox)                       │
│  Layer 2: Ekstrak struktur internal (HTML + cell coords)    │
│  → Separation of concerns, modular, maintainable            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  PRINSIP 3: SWEET SPOT > PREMIUM                            │
├─────────────────────────────────────────────────────────────┤
│  Sonnet 4.6 handle 90% use case dengan 80% cost savings     │
│  vs Opus. Tidak selalu perlu model terkuat.                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  PRINSIP 4: HYBRID WORKFLOW                                 │
├─────────────────────────────────────────────────────────────┤
│  Combine multiple models based on task complexity:          │
│  - Sonnet: Daily work (90%)                                 │
│  - Opus: Complex/critical (10%)                             │
│  - Haiku: Quick tasks (high-volume)                         │
└─────────────────────────────────────────────────────────────┘
```

### **Pola Berulang (Patterns)**

| Pattern | Deskripsi | Contoh |
|---------|-----------|--------|
| **Trade-off Triangle** | Speed ↔ Accuracy ↔ Cost | Opus (accurate, slow, expensive) vs Haiku (fast, cheap, less accurate) |
| **Progressive Enhancement** | Start simple, upgrade if needed | SLANet → SLANet_plus for borderless |
| **Hybrid Routing** | Route tasks by complexity | Sonnet 90%, Opus 10%, Haiku for quick |
| **Preprocessing Matters** | Image quality affects accuracy | Resize, contrast, sharpen before inference |

### **Insight Penting (Takeaways)**

1. **Border bukan requirement**: Model modern detect pattern, bukan garis
2. **SLANet_plus untuk production**: Lebih robust untuk edge cases
3. **Sonnet adalah sweet spot**: 90% use case, cost efficient
4. **1-3 detik per image**: Sudah acceptable untuk production
5. **GPU 3-5x faster**: Worth it untuk batch processing
6. **HTML output universal**: Easy convert ke Excel/JSON
7. **Hybrid model strategy**: Maximize value, minimize cost

---

## 4. SISTEM / FRAMEWORK

### **WORKFLOW: Table Detection Implementation**

```
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: SETUP                                             │
├─────────────────────────────────────────────────────────────┤
│  1. Install PaddleOCR                                       │
│     pip install paddlepaddle paddleocr                      │
│                                                             │
│  2. Download Model                                          │
│     - SLANet_plus (recommended for production)              │
│     - SLANet (if speed priority)                            │
│                                                             │
│  3. Test Environment                                        │
│     - CPU: Verify basic functionality                       │
│     - GPU: Setup CUDA if available                          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 2: PREPROCESSING                                     │
├─────────────────────────────────────────────────────────────┤
│  1. Load Image                                              │
│     img = cv2.imread('table.png')                           │
│                                                             │
│  2. Resize if Needed                                        │
│     if img.shape[0] > 2000: resize to max 2000px            │
│                                                             │
│  3. Enhance (Optional)                                      │
│     - Contrast adjustment                                   │
│     - Sharpening for border detection                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 3: INFERENCE                                         │
├─────────────────────────────────────────────────────────────┤
│  1. Initialize Engine                                       │
│     table_engine = TableSystem(model_name='SLANet_plus')    │
│                                                             │
│  2. Run Detection                                           │
│     result = table_engine(image_path)                       │
│                                                             │
│  3. Extract Data                                            │
│     cells = result[0]['cells']  # bbox, row, col, text      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 4: POST-PROCESSING                                   │
├─────────────────────────────────────────────────────────────┤
│  1. Validate Output                                         │
│     - Check confidence scores                               │
│     - Flag low-confidence cells for review                  │
│                                                             │
│  2. Export Format                                           │
│     - Excel: pandas.DataFrame.to_excel()                    │
│     - JSON: Structured output                               │
│     - HTML: Direct from model output                        │
│                                                             │
│  3. Quality Check                                           │
│     - Sample verification                                   │
│     - Edge case handling                                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 5: OPTIMIZATION                                      │
├─────────────────────────────────────────────────────────────┤
│  1. Benchmark Performance                                   │
│     - Time per image                                        │
│     - Accuracy metrics                                      │
│                                                             │
│  2. Scale Strategy                                          │
│     - CPU: <100 images/day                                  │
│     - Single GPU: 100-1000 images/day                       │
│     - Multi-GPU: >1000 images/day                           │
│                                                             │
│  3. Model Routing (if using Claude for code)                │
│     - Sonnet: Daily development                             │
│     - Opus: Complex debugging                               │
│     - Haiku: Quick fixes                                    │
└─────────────────────────────────────────────────────────────┘
```

### **DECISION MATRIX: Model Selection**

```
┌─────────────────────────────────────────────────────────────┐
│  TABLE DETECTION MODEL                                      │
├─────────────────────────────────────────────────────────────┤
│  Border visible?                                            │
│  ├── YES → SLANet (faster)                                  │
│  └── NO → SLANet_plus (more robust)                         │
│                                                             │
│  Volume/day?                                                │
│  ├── <100 → CPU                                             │
│  ├── 100-1000 → Single GPU                                  │
│  └── >1000 → Multi-GPU / Cloud                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  CLAUDE MODEL FOR CODING/DESIGN                             │
├─────────────────────────────────────────────────────────────┤
│  Task Complexity?                                           │
│  ├── Critical/Complex → Opus 4.6                            │
│  ├── Standard/Daily → Sonnet 4.6 (DEFAULT)                  │
│  └── Simple/Quick → Haiku 4.5                               │
│                                                             │
│  Budget Constraint?                                         │
│  ├── High → Opus for all                                    │
│  ├── Medium → Sonnet default, Opus for critical             │
│  └── Low → Haiku default, Sonnet for important              │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. OUTPUT ARTEFAK (.skill)

```
┌─────────────────────────────────────────────────────────────┐
│  FILE: table_detection_system.skill                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  NAME: Table Detection & AI Model Selection System          │
│  VERSION: 1.0                                               │
│  AUTHOR: Knowledge Extraction System                        │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  MODULE 1: TABLE DETECTION PIPELINE                         │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  INPUT:                                                     │
│    - image_path: string                                     │
│    - model_type: 'SLANet' | 'SLANet_plus'                   │
│    - hardware: 'CPU' | 'GPU'                                │
│                                                             │
│  PROCESS:                                                   │
│    1. Preprocess image (resize, enhance)                    │
│    2. Run layout analysis                                   │
│    3. Run table structure recognition                       │
│    4. Run cell OCR                                          │
│    5. Merge and export                                      │
│                                                             │
│  OUTPUT:                                                    │
│    - cells: [{bbox, row, col, text, confidence}]            │
│    - html: string                                           │
│    - excel_path: string                                     │
│    - processing_time: float                                 │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  MODULE 2: MODEL SELECTION ROUTER                           │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  INPUT:                                                     │
│    - task_type: 'coding' | 'design' | 'analysis'            │
│    - complexity: 'simple' | 'standard' | 'complex'          │
│    - budget: 'low' | 'medium' | 'high'                      │
│                                                             │
│  PROCESS:                                                   │
│    IF complexity == 'complex' OR budget == 'high':          │
│      RETURN 'opus-4.6'                                      │
│    ELIF complexity == 'standard':                           │
│      RETURN 'sonnet-4.6'  # DEFAULT                         │
│    ELSE:                                                    │
│      RETURN 'haiku-4.5'                                     │
│                                                             │
│  OUTPUT:                                                    │
│    - model: string                                          │
│    - estimated_cost: float                                  │
│    - estimated_time: float                                  │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  MODULE 3: PERFORMANCE BENCHMARK                            │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  METRICS:                                                   │
│    - images_per_hour: int                                   │
│    - avg_processing_time: float                             │
│    - accuracy_rate: float                                   │
│    - cost_per_image: float                                  │
│                                                             │
│  THRESHOLDS:                                                │
│    - CPU: <100 images/day acceptable                        │
│    - GPU: 100-1000 images/day recommended                   │
│    - Multi-GPU: >1000 images/day                            │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  MODULE 4: QUALITY VALIDATION                               │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  CHECKS:                                                    │
│    1. Confidence score >= 0.7 for all cells                 │
│    2. Row/column consistency                                │
│    3. Merged cells properly handled                         │
│    4. Text OCR accuracy >= 90%                              │
│                                                             │
│  FLAGS:                                                     │
│    - low_confidence_cells: list                             │
│    - manual_review_required: boolean                        │
│    - quality_score: float (0-1)                             │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  USAGE EXAMPLE:                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  from table_detection_system import TableDetector           │
│                                                             │
│  detector = TableDetector(                                  │
│      model_type='SLANet_plus',                              │
│      hardware='GPU'                                         │
│  )                                                          │
│                                                             │
│  result = detector.process('invoice.png')                   │
│  print(f"Found {len(result['cells'])} cells")               │
│  print(f"Processing time: {result['processing_time']}s")    │
│                                                             │
│  # Export to Excel                                          │
│  detector.export_to_excel(result, 'output.xlsx')            │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  MAINTENANCE:                                               │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  - Update models quarterly                                  │
│  - Monitor accuracy metrics weekly                          │
│  - Fine-tune for domain-specific tables                     │
│  - Review cost vs performance monthly                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. QUICK REFERENCE CARD

```
┌─────────────────────────────────────────────────────────────┐
│  📋 QUICK REFERENCE: TABLE DETECTION                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  INSTALL:                                                   │
│  pip install paddlepaddle paddleocr                         │
│                                                              │
│  MODEL SELECTION:                                           │
│  - Border visible → SLANet                                  │
│  - Borderless → SLANet_plus                                 │
│  - Production → SLANet_plus (default)                       │
│                                                              │
│  PERFORMANCE:                                               │
│  - CPU: 1-3 detik/image                                     │
│  - GPU: 350ms/image                                         │
│  - Max image size: 2000px                                   │
│                                                              │
│  OUTPUT FORMAT:                                             │
│  - HTML (default)                                           │
│  - JSON (cells with bbox, row, col, text)                   │
│  - Excel (direct export supported)                          │
│                                                              │
│  CLAUDE MODEL FOR CODING:                                   │
│  - Daily work → Sonnet 4.6 (90%)                            │
│  - Complex → Opus 4.6 (10%)                                 │
│  - Quick → Haiku 4.5                                        │
│                                                              │
│  COST OPTIMIZATION:                                         │
│  - Sonnet = 80% savings vs Opus                             │
│  - GPU = 3-5x faster than CPU                               │
│  - Batch processing for high volume                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

**STATUS**: ✅ Complete Knowledge System
**READY FOR**: Markdown export, team documentation, implementation guide