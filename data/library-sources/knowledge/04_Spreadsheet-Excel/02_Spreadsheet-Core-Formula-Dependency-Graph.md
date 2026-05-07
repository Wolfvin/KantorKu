---
title: Spreadsheet Core Formula Dependency Graph
kategori: Spreadsheet, Excel & Automation
tags: [spreadsheet, formula-engine, dependency-graph, AI-backend, rust, reactive-system]
---

# Spreadsheet Core Formula Dependency Graph

> Knowledge compression + system reconstruction: Membangun Excel + AI dari nol (engine, formula, AI backend, arsitektur)

---

## 1. Kategori (Tema Besar)

| ID | Kategori |
|----|----------|
| A | Spreadsheet Core System |
| B | Formula Engine System |
| C | Dependency Graph & Calculation Engine |
| D | AI Backend System |
| E | Frontend Spreadsheet System |
| F | Rust Implementation System |
| G | Future Spreadsheet Evolution |

---

## A. Spreadsheet Core System

### Sub-topik 1: Struktur Spreadsheet (Workbook → Cell)

#### A. Inti Konsep

Spreadsheet adalah:

> Sistem data berbasis grid (2D) yang menyimpan relasi antar sel

Tujuan:
- Menyimpan data
- Memodelkan relasi
- Menghitung otomatis

Masalah yang diselesaikan:
- Perhitungan manual
- Tracking data kompleks

#### B. Mekanisme & Cara Kerja

```
Workbook
 ├ Sheet
 │  ├ Row
 │  ├ Column
 │  └ Cell
```

Setiap cell:

```
Cell {
  value
  formula
  metadata
}
```

#### C. Komponen Penting
- Cell → unit data
- Range → kumpulan cell
- Sheet → layer
- Workbook → container

#### D. Use Case Nyata
- Finance model
- Dashboard
- Database ringan

#### E. Tools & Teknologi
- Grid renderer
- Storage engine
- Memory model

#### F. Evaluasi Kritis

Kelebihan:
- Fleksibel
- Mudah dipakai

Kekurangan:
- Tidak scalable
- Tidak terstruktur (flat)

#### H. Perbandingan

| Spreadsheet    | Database   |
| -------------- | ---------- |
| Flexible       | Structured |
| Mudah          | Kompleks   |
| Tidak scalable | Scalable   |

---

## B. Formula Engine System

### Sub-topik 2: Formula Engine

#### A. Inti Konsep

Formula engine =

> Sistem yang membaca dan menghitung formula

#### B. Mekanisme

Flow:

```
User input → Parse → AST → Evaluate → Result
```

#### C. Komponen
- Parser
- AST (Abstract Syntax Tree)
- Evaluator

#### D. Use Case

```
=SUM(A1:A10)
=IF(A1>10,"Yes","No")
```

#### F. Evaluasi

Kelebihan:
- Powerful
- Declarative

Kekurangan:
- Parsing kompleks
- Error sulit debug

---

## C. Dependency Graph & Calculation Engine

### Sub-topik 3: Dependency Graph (INTI DARI EXCEL)

#### A. Inti Konsep

> Spreadsheet = Dependency Graph

Setiap formula menciptakan relasi:

```
A3 = A1 + A2
```

Graph:

```
A1 ─┐
    ├── A3
A2 ─┘
```

#### B. Mekanisme

1. Parse formula
2. Ambil reference
3. Bangun graph
4. Topological sort
5. Hitung ulang

#### C. Komponen
- Node → cell
- Edge → dependency
- Graph → seluruh sistem

#### D. Use Case

Jika A1 berubah:

```
A1 → A3 → A4 → A5
```

Hanya chain ini dihitung ulang (bukan seluruh sheet)

#### E. Tools
- Graph system (networkx / custom)
- DAG engine

#### F. Evaluasi

Kelebihan:
- Efisien
- Scalable

Kekurangan:
- Kompleks
- Circular reference problem

### Insight Penting

> Spreadsheet bukan grid, tapi **graph engine dengan UI grid**

---

## D. AI Backend System

### Sub-topik 4: AI Spreadsheet Engine

#### A. Inti Konsep

AI layer =

> Sistem yang memahami data spreadsheet dan memberi insight

#### B. Mekanisme

Flow:

```
User → AI Request
     → Extract Data
     → Build Context
     → Send to LLM
     → Return result
```

#### C. Komponen
- Prompt builder
- Context extractor
- Model API
- Result injector

#### D. Use Case

```
=AI("summarize column A")

=AI_ANALYZE(A1:D100)
```

#### E. Tools
- LLM API
- Vector DB (optional)
- Context builder

#### F. Evaluasi

Kelebihan:
- Automation tinggi
- User friendly

Kekurangan:
- Mahal (API)
- Latency

#### H. Perbandingan

| Traditional Excel | AI Excel         |
| ----------------- | ---------------- |
| Manual formula    | Natural language |
| Static            | Dynamic          |

---

## E. Frontend Spreadsheet System

### Sub-topik 5: Grid UI

#### A. Inti Konsep

Frontend =

> Visual layer untuk spreadsheet engine

#### B. Mekanisme

```
User input → UI → backend → result → render
```

#### C. Komponen
- Grid renderer
- Cell editor
- Selection system
- Formula bar

#### F. Evaluasi

Kelebihan:
- User friendly

Kekurangan:
- Bukan inti sistem

> Banyak orang salah mulai dari sini

---

## F. Rust Implementation System

### Sub-topik 6: Engine Implementation

#### A. Inti Konsep

Gunakan Rust untuk:
- Performance
- Safety

#### B. Mekanisme

Core:

```
Cell struct
Dependency graph
Formula parser
Evaluator
```

#### C. Komponen
- HashMap
- Graph
- Parser

#### D. Use Case

```rust
struct Cell {
  value: Option<f64>,
  formula: Option<String>
}
```

#### F. Evaluasi

Kelebihan:
- Cepat
- Aman

Kekurangan:
- Sulit

---

## G. Future Spreadsheet Evolution

### Sub-topik 7: Spreadsheet = OS Data

#### A. Inti Konsep

Spreadsheet masa depan:

```
Spreadsheet = Database + Programming + AI
```

#### D. Use Case

```
=SQL("SELECT * FROM table")

=PYTHON(A1:A100)

=AI("explain data")
```

### Insight

Spreadsheet akan jadi:

> **Data operating system**

---

## 3. Sintesis Pengetahuan (Inti)

### Core Principles

1. Spreadsheet = Dependency Graph
2. Cell = Node
3. Formula = Relationship
4. Recalculation = Graph traversal
5. AI = Context-based reasoning layer

### Patterns
- Input → Transform → Output
- Dependency chain
- Lazy recalculation
- Declarative programming

### Insight Paling Penting

> Excel bukan software UI, tapi **calculation engine + graph system**

---

## 4. System Framework (Langkah Praktis)

### Build Excel from Zero

#### Step 1 — Data Model

```
Cell
Sheet
Workbook
```

#### Step 2 — Formula Engine

```
Parser → AST → Evaluator
```

#### Step 3 — Dependency Graph

```
Build graph
Topological sort
```

#### Step 4 — Calculation Engine

```
Recalculate only affected cells
```

#### Step 5 — Core Functions

```
SUM
IF
XLOOKUP
FILTER
UNIQUE
SORT
```

#### Step 6 — AI Backend

```
Context → LLM → Result
```

#### Step 7 — Frontend

```
Grid UI
```

---

## 5. Output Artefak (.skill)

### .skill ExcelAI_System

**INPUT:**
- Spreadsheet data
- User commands
- AI requests

**PROCESS:**

1. Build Data Model (Cell, Sheet, Workbook)
2. Build Formula Engine (Parse formula, Create AST, Evaluate)
3. Build Dependency Graph (Extract references, Create DAG, Detect cycles)
4. Calculation Engine (Track dependencies, Recalculate affected nodes only)
5. Implement Core Functions (SUM, IF, XLOOKUP, FILTER, UNIQUE, SORT)
6. AI Backend (Extract spreadsheet context, Build prompt, Call AI model, Inject result)
7. Frontend Layer (Render grid, Handle user input)

**OUTPUT:**
- Computed spreadsheet
- AI insights
- Interactive UI

**GOAL:** Transform spreadsheet into:
- Calculation engine
- Data system
- AI interface

---

## Penutup

Kalau kamu benar-benar paham ini:

> Kamu bukan lagi bikin Excel clone, kamu sedang bikin **data operating system**

---

### Referensi

- [CWAN - What are dependency graphs and why are they important?](https://cwan.com/resources/blog/what-are-dependency-graphs-and-why-are-they-important/)
- [GRID - We built a spreadsheet engine from scratch. Here's what we learned.](https://grid.is/blog/we-built-a-spreadsheet-engine-from-scratch-heres-what-we-learned)
