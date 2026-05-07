---
title: PDF Table Extraction AI Stack
kategori: Spreadsheet, Excel & Automation
tags: [pdf, table-extraction, fake-table, coordinate-clustering, AI-infrastructure, agent-orchestration, LoRA, Stripe]
---

# PDF Table Extraction & AI Development Stack

---

## 1. Kategori Utama

| No | Kategori | Cakupan |
|----|----------|---------|
| 1 | **PDF Table Extraction** | Fake table detection, coordinate clustering, library comparison |
| 2 | **AI Development Infrastructure** | GPU selection, laptop specs, self-hosting |
| 3 | **Agent Orchestration** | LangGraph, Zencoder, Stripe Minions patterns |
| 4 | **Model Optimization** | LoRA, fine-tuning, parameter efficiency |
| 5 | **Payment & Monetization** | Stripe integration, global vs local payment |

---

## 2. Sub-Topik Mendalam

---

# Kategori 1: PDF Table Extraction

## Sub-topik 1.1: Fake Table Detection

### A. Inti Konsep

**Definisi**: PDF "fake table" adalah dokumen yang secara **visual terlihat seperti tabel** tetapi secara struktural hanya **text dengan positioning** (bukan table object).

**Tujuan**: Mengidentifikasi struktur tabel tersembunyi untuk ekstraksi data yang akurat.

**Masalah yang Diselesaikan**:
- Copy-paste ke Excel menghasilkan 1 cell atau berantakan
- Library table extraction konvensional (`find_tables()`) mengembalikan kosong
- Data bank statement, invoice, report tidak terstruktur otomatis

### B. Mekanisme & Cara Kerja

```
FLOW DETEKSI FAKE TABLE:
1. Load PDF → Extract text items dengan (x,y) coords
2. Analisis Y positions → Cluster menjadi rows
3. Analisis X positions dalam row → Cluster columns
4. Cek keberadaan line/rectangle objects
5. Validasi pola: banyak items + koordinat rapi
6. Keputusan: Fake Table terdeteksi
```

**Indikator Fake Table**:

| Indikator | Fake Table | Real Table |
|-----------|------------|------------|
| `find_tables()` | Kosong | Ada hasil |
| Copy-paste Excel | 1 cell/berantakan | Cell terpisah rapi |
| Text items | Per kata/karakter | Per cell |
| Line objects | Sedikit/tidak ada | Ada grid lengkap |
| Coordinates | Banyak items terpisah | Bbox per cell |

### C. Komponen Penting

| Komponen | Peran | Koneksi |
|----------|-------|---------|
| **Text Items** | Unit terkecil (kata/karakter) | Punya (x, y, width, height) |
| **Y-Clustering** | Group items jadi baris | Tolerance 5-15 pixels |
| **X-Clustering** | Group dalam baris jadi kolom | Tolerance 20-50 pixels |
| **Line Detector** | Cek keberadaan border | OpenCV atau PDF objects |
| **Validation Logic** | Konfirmasi pola fake table | Threshold items > 50 |

### D. Use Case Nyata

**BRI Bank Statement**:
```
Visual: Tabel 7 kolom (Tanggal, Uraian, Teller, User ID, Debet, Kredit, Saldo)
Struktur: 60+ text items per halaman dengan coordinates
Hasil Copy-Paste: Semua masuk 1 cell
Solusi: Coordinate clustering → Export ke Excel rapi
```

**Workflow**:
1. Extract 60+ text items dengan coordinates
2. Group by Y (tolerance 15px) → 30 rows terdeteksi
3. Group by X (tolerance 50px) → 7 columns terdeteksi
4. Mapping: Col1=Tanggal, Col2=Uraian, Col3-4=Teller/UserID, Col5-7=Angka
5. Export CSV/Excel

### E. Tools & Teknologi

| Tool | Bahasa | Fungsi | Gratis |
|------|--------|--------|--------|
| **pdf.js** | JavaScript | Extract text + coords | Ya |
| **Tabula-java** | Java | Auto-detect tables | Ya |
| **lopdf** | Rust | Low-level PDF parsing | Ya |
| **poppler-rust** | Rust | Text + coordinates | Ya |
| **UglyToad.PdfPig** | C# | Letter-level position | Ya |
| **OpenCV** | Multi | Line/border detection | Ya |
| **camelot/tabula-py** | Python | Table extraction | Ya |

### F. Evaluasi Kritis

**Kelebihan**:
- Bisa extract PDF tanpa table object
- Presisi tinggi dengan coordinates
- Otomatis untuk format konsisten

**Kekurangan**:
- Perlu tuning tolerance (X/Y)
- Tidak universal (tiap PDF beda pola)
- Complex untuk nested tables

**Batasan**:
- PDF scan/image-based butuh OCR dulu
- Format sangat irregular butuh ML approach
- Multi-column layout bisa salah detect

### G. Harga & Akses

| Tool | Pricing | Catatan |
|------|---------|---------|
| pdf.js | Gratis | Mozilla open-source |
| Tabula-java | Gratis | Apache 2.0 |
| lopdf | Gratis | MIT license |
| OpenCV | Gratis | BSD license |
| iText7 | Commercial | AGPL atau $$$ |
| UniPDF | Commercial | Trial available |

### H. Perbandingan

| Approach | Keunggulan | Kelemahan | Kapan Dipilih |
|----------|------------|-----------|---------------|
| **Coordinate Clustering** | Fleksibel, cepat | Manual tuning | PDF positioned text |
| **Line Detection (OpenCV)** | Akurat ada border | Butuh convert PDF→Image | PDF ada garis |
| **ML Table Detection** | Paling robust | Kompleks, butuh training | Format sangat beragam |
| **Regex + Position** | Simple untuk format tetap | Tidak fleksibel | Format sangat konsisten |

---

## Sub-topik 1.2: Library Selection Matrix

### A. Inti Konsep

**Definisi**: Framework pemilihan library berdasarkan jenis PDF, bahasa pemrograman, dan kebutuhan performa.

### B. Mekanisme

```
DECISION TREE:
├── PDF punya text layer?
│   ├── Ya → Poppler/lopdf/pdf.js
│   └── Tidak → OCR (tesseract/ocrs) + OpenCV
├── Ada garis border?
│   ├── Ya → OpenCV line detection
│   └── Tidak → Coordinate clustering
├── Butuh kecepatan?
│   ├── Ya → Poppler (5-10x lebih cepat dari OpenCV route)
│   └── Tidak → OpenCV untuk akurasi maksimal
└── Bahasa preference?
    ├── JavaScript → pdf.js
    ├── Java → Tabula-java
    ├── Rust → lopdf/poppler-rust
    └── C# → UglyToad.PdfPig
```

---

# Kategori 2: AI Development Infrastructure

## Sub-topik 2.1: GPU Selection untuk AI

### A. Inti Konsep

**RTX** = NVIDIA GPU dengan **Tensor Cores** untuk akselerasi AI/ML.

### C. Komponen Penting

| Komponen | Fungsi | Relevansi AI |
|----------|--------|--------------|
| **CUDA Cores** | Parallel processing | General compute |
| **Tensor Cores** | Matrix multiplication | LLM training/inference |
| **VRAM** | Model storage | 8GB min, 24GB ideal |
| **TGP** | Power limit | Higher = lebih kencang |

### D. Use Case Nyata

| GPU | VRAM | Use Case | Harga (IDR) |
|-----|------|----------|-------------|
| RTX 3060 | 12GB | Inferensi 7B, LoRA ringan | 5-7jt |
| RTX 3090 | 24GB | Fine-tune 13B, multi-model | 10-15jt (bekas) |
| RTX 4090 | 24GB | Production, fastest | 25-30jt |

---

# Kategori 3: Agent Orchestration

## Sub-topik 3.1: Pattern Comparison (LangGraph vs Zencoder vs Stripe Minions)

### A. Inti Konsep

**Common Pattern**: Graph-based orchestration dengan **hybrid deterministic + agentic nodes**.

### C. Stripe Minions Blueprint Pattern

```
BLUEPRINT STRUCTURE:
[Agent: Pahami task]
     │
     ▼
[Code: Run formatter]  ← Deterministic
     │
     ▼
[Agent: Implementasi]  ← Agentic
     │
     ▼
[Code: Run linters]  ← Loop jika gagal
     │
     ▼
[Code: Push + CI]
     │
     ▼
[Agent: Fix CI failures]  ← Max 2 iterations
     │
     ▼
[Human: Review PR]
```

### D. Prinsip Utama

1. **Devboxes**: Environment terisolasi untuk agent (cattle, not pets)
2. **Hybrid Workflow**: Deterministik untuk yang predictable, agentic untuk yang butuh "pemikiran"
3. **Context Management**: Rule files (CLAUDE.md) + MCP tools
4. **Feedback Loop**: Shift left (linters sebelum CI), max 2 iteration
5. **Scale**: 1.300+ PR/minggu fully AI-generated, human review only

---

# Kategori 4: Model Optimization

## Sub-topik 4.1: LoRA (Low-Rank Adaptation)

### A. Inti Konsep

**Definisi**: Teknik PEFT (Parameter-Efficient Fine-Tuning) yang hanya melatih **<1% parameter** via dekomposisi rank-rendah.

**Formula**: `Output = W·x + (A×B)·x`
- W = weight asli (frozen)
- A×B = adapter yang dilatih (rank kecil)

### D. Use Case

| Scenario | VRAM Needed | Adapter Size |
|----------|-------------|--------------|
| LLaMA-7B LoRA | 12GB | 20-200MB |
| LLaMA-7B QLoRA | 8GB | 20-200MB |
| Full Fine-tune | 28GB | 14GB (seluruh model) |

---

# Kategori 5: Payment & Monetization

## Sub-topik 5.1: Stripe Integration

### C. Pricing

```
Payments: 2.9% + $0.30 per transaksi
Billing: +0.5% untuk recurring
Connect: Fee tambahan untuk platform
Tidak ada: Setup fee, monthly fee, minimum volume
```

### D. Indonesia Consideration

| Aspek | Stripe | Midtrans/Xendit |
|-------|--------|-----------------|
| Merchant ID | Terbatas | Support |
| Payment Methods | Global | Lokal (QRIS, VA) |
| API Experience | Terbaik | Baik |
| Hybrid Approach | Stripe (global) + Midtrans (lokal) | |

---

## 3. Sintesis Pengetahuan

### Prinsip Utama (Core Principles)

1. **Infrastructure First**: Agent AI yang reliable butuh environment terisolasi (Devbox/Docker), bukan hanya prompt engineering.
2. **Hybrid Orchestration**: Kombinasikan deterministic nodes (linters, formatters) dengan agentic nodes (LLM decisions) untuk reliability.
3. **Coordinate-Based Extraction**: Untuk PDF tanpa table object, gunakan positioning (x,y) + clustering, bukan table detection konvensional.
4. **VRAM is King**: Untuk AI lokal, VRAM > GPU clock speed. 24GB VRAM = bisa handle model 13B+.
5. **Parameter Efficiency**: LoRA/QLoRA memungkinkan fine-tuning di consumer GPU dengan <1% parameter trainable.
6. **Feedback Loop Design**: Max 2-3 iteration untuk agent, setelah itu escalate ke human (diminishing returns).
7. **Context Management**: Rule files + standardized tools (MCP) = agent lebih konsisten dan aman.

### Pola Berulang (Patterns)

| Pola | Implementasi |
|------|--------------|
| **Graph Orchestration** | LangGraph StateGraph, Minions Blueprints, Zencoder Zenflow |
| **Isolated Execution** | Devbox (Stripe), Docker container (homelab), Sandbox |
| **Hybrid Workflow** | Deterministic + Agentic nodes |
| **Coordinate Clustering** | Y-axis → rows, X-axis → columns (PDF extraction) |
| **Shift-Left Feedback** | Linters lokal → CI → Human review |
| **Adapter Pattern** | LoRA adapters, Plugin systems, MCP tools |

### Insight Penting (Takeaways)

1. **AMD R5 M330 tidak cocok untuk AI** → Tidak ada CUDA/Tensor Cores, VRAM 2GB.
2. **Poppler 5-10x lebih cepat dari OpenCV** untuk PDF dengan text layer.
3. **Fake table detection = Coordinate analysis** → Bukan table object detection.
4. **Stripe Minions 1.300+ PR/minggu** membuktikan: Agent production-ready butuh infrastructure, bukan hanya LLM.
5. **LoRA adapter 20-200MB** vs Full model 14GB → Multi-task serving jadi feasible.
6. **Hybrid payment (Stripe + Midtrans)** optimal untuk startup global dengan user Indonesia.

---

## 4. Sistem / Framework

### Framework 1: PDF Table Extraction Decision Tree

```
START
  │
  ▼
PDF punya text layer?
  ├── Ya → Poppler/lopdf/pdf.js
  └── Tidak → OCR + OpenCV
       │
       ▼
Ada garis border?
  ├── Ya → OpenCV Line Detect
  └── Tidak → Coordinate Clustering (DBSCAN)
       │
       └────────┬─────────
                ▼
       Export CSV/Excel (calamine)
```

### Framework 2: AI Agent Development Checklist

```
[ ] 1. Environment Setup
    [ ] Docker container / Devbox terisolasi
    [ ] Git repo initialized
    [ ] Dependencies cached

[ ] 2. Orchestration Design
    [ ] Graph structure defined (nodes/edges)
    [ ] Deterministic nodes identified (linters, formatters)
    [ ] Agentic nodes identified (LLM tasks)
    [ ] Max iteration limit set (2-3)

[ ] 3. Context Management
    [ ] Rule files created (.cursorrules / AGENTS.md)
    [ ] Tools defined (MCP or custom)
    [ ] Security boundaries set

[ ] 4. Feedback Loop
    [ ] Pre-commit hooks (linters)
    [ ] CI integration
    [ ] Human review point defined

[ ] 5. Testing & Validation
    [ ] Test cases defined
    [ ] Success metrics set
    [ ] Rollback mechanism ready
```

### Framework 3: GPU Selection Matrix

```
BUDGET          →  <20jt   │  20-35jt   │  >35jt
USE CASE
Coding + Inferensi  → RTX 4060 │ RTX 4070  │ RTX 4080
LoRA Training       → RTX 4070 │ RTX 4080  │ RTX 4090
Production Multi    → RTX 4080 │ RTX 4090  │ 2x 4090
VRAM TARGET         → 8GB      │ 12GB      │ 16-24GB
RAM TARGET          → 32GB     │ 32-64GB   │ 64GB+
```

---

## 5. Output Artefak (.skill)

### Skill: PDF Fake Table Extraction System

**PREREQUISITES**
- [ ] Programming language (JS/Java/Rust/C#/Python)
- [ ] PDF library installed
- [ ] Sample PDF for testing

**WORKFLOW**

Step 1: Detection
```
1. Load PDF
2. Extract text items dengan coordinates
3. Hitung unique Y positions (tolerance 10-15px)
4. Hitung unique X clusters per row (tolerance 20-50px)
5. Cek line objects count
6. Jika: items > 50 + pola koordinat konsisten + lines < 10
   Maka: FAKE TABLE DETECTED
```

Step 2: Extraction
```
1. Group items by Y → rows
2. Dalam setiap row, group by X → columns
3. Concatenate text dalam setiap cell
4. Validate column count consistency
```

Step 3: Export
```
1. Convert to CSV/Excel format
2. Apply number formatting (Debet/Kredit/Saldo)
3. Validate totals (Saldo Awal + Kredit - Debet = Saldo Akhir)
4. Save file
```

**CONFIGURATION TEMPLATE**

```yaml
extraction_config:
  y_tolerance: 15      # pixels untuk row clustering
  x_tolerance: 50      # pixels untuk column clustering
  min_items: 50        # threshold fake table detection
  max_line_objects: 10 # threshold untuk positioned text
  output_format: excel # csv | excel | json
```

**VALIDATION CHECKLIST**
- [ ] Column count consistent across rows
- [ ] Number fields parseable (remove commas)
- [ ] Date fields valid format
- [ ] Balance calculation matches (Saldo Akhir = Saldo Awal + Kredit - Debet)
- [ ] No empty rows in output

**TROUBLESHOOTING**

| Problem | Solution |
|---------|----------|
| Semua jadi 1 kolom | Perbesar x_tolerance (50 → 100) |
| Terlalu banyak baris | Perbesar y_tolerance (10 → 20) |
| Data hilang | Kurangi tolerance, cek text extraction |
| Format angka salah | Post-process: remove commas, parse float |

**LIBRARY RECOMMENDATIONS**

| Language | Primary | Fallback |
|----------|---------|----------|
| JavaScript | pdf.js | tabula-js |
| Java | Tabula-java | PDFBox |
| Rust | lopdf | poppler-rust |
| C# | UglyToad.PdfPig | iText7 |
| Python | camelot | tabula-py |

---

### Skill: Hybrid Agent Blueprint

**CORE PATTERN**

```
[Agent: Understand] → [Code: Validate] → [Agent: Execute] → [Code: Verify] → [Human: Review]
```

**CONFIGURATION**

```yaml
agent_config:
  max_iterations: 2
  feedback_loop: shift_left
  environment: isolated_container
  context_files:
    - .cursorrules
    - AGENTS.md
  tools:
    - linter
    - formatter
    - test_runner
    - git_operations
```

**VALIDATION METRICS**
- [ ] Success rate > 80%
- [ ] Average iterations < 2
- [ ] Human review time < 10 menit/PR
- [ ] Zero production incidents from agent code

---

## Penutup

Sistem pengetahuan ini dirancang untuk:
1. **Reusable** → Copy-paste workflow untuk project baru
2. **Scalable** → Dari homelab ke production
3. **Actionable** → Langsung implement, bukan teori

**Next Steps**:
- Pilih 1 framework untuk implementasi pertama
- Test dengan sample data/PDF Anda
- Iterate berdasarkan hasil

---

*Generated from conversation session: PDF Extraction + AI Infrastructure Stack*
