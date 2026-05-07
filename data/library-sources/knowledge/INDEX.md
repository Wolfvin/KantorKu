# KNOWLEDGE LIBRARY — New Information

> Rekonstruksi total: nama bersih, format seragam (.md), konten dirapikan, duplikasi dihapus, dikelompokkan per tema.

---

## Tentang Library Ini

Library ini berisi kristalisasi pengetahuan dari sesi-sesi diskusi dan riset yang diorganisir menjadi 12 kategori tematik. Setiap file telah direkonstruksi dengan:

- **Nama deskriptif** — tidak ada lagi nama terpotong atau karakter aneh
- **Format seragam** — semua file dalam format Markdown (.md)
- **Header YAML** — setiap file punya metadata (title, kategori, tags)
- **Heading hierarchy** — struktur `#` → `##` → `###` yang konsisten
- **Tanpa duplikasi** — konten overlap telah di-merge

---

## Statistik

| Metrik | Nilai |
|--------|-------|
| Total File | 49 |
| Format | 100% Markdown (.md) |
| Kategori | 12 |
| File Terbesar | `12_Project-Docs/01_AKP2I-Kalbar-Project-Documentation.md` (65 KB) |
| Kategori Terbesar | `03_Cybersecurity-EDR` (9 file) |

---

## Katalog

### 01 — Rust, Tauri & Desktop Development
> Arsitektur async Rust, Tauri desktop app, PDF extraction pipeline, parallel processing, multi-agent AI system, dataset engineering

| # | File | Topik |
|---|------|-------|
| 1 | `01_Async-Runtime-Tauri-Bridge.md` | Nested runtime panic, core/CLI separation, async patterns |
| 2 | `02_Rust-Computer-Vision-Image-Processing.md` | Rust CV ecosystem, pixel manipulation, Hough/LSD detection |
| 3 | `03_Rust-Tauri-Desktop-Development.md` | Tauri Bridge IPC, PDF strategy, build troubleshooting |
| 4 | `04_Rust-PDF-Parser-MultiAgent-Dataset.md` | PDF extraction, Rayon parallel, Excel output, multi-agent AI, ChatML dataset |
| 5 | `05_Rust-AI-Worker-System-Skill.md` | .skill artifact untuk Rust AI Worker system |

---

### 02 — AI Model & Arsitektur
> Arsitektur model AI, continual learning, GPU hardware research, framework eksplorasi

| # | File | Topik |
|---|------|-------|
| 1 | `01_DeepSeek-Engram-Conditional-Memory.md` | Engram n-gram embeddings, conditional memory, multi-head hashing |
| 2 | `02_Open-dLLM-Diffusion-Language-Model.md` | Diffusion LM untuk code generation, vs autoregressive |
| 3 | `03_Continual-Learning-Self-Hosted-Infra.md` | EWC, SI, MAS, Replay, PEFT/LoRA, hardware planning |
| 4 | `04_Modular-Semantic-AI-Framework.md` | Semantic Encoder, Thinker, Knowledge Graph, Decoder, Memory |
| 5 | `05_GPU-DL-Framework-Research.md` | AMD/NVIDIA/Intel GPU, ROCm vs CUDA, 9 kategori riset |

---

### 03 — Cybersecurity & EDR
> Keamanan siber, kriptografi, EDR/Sysmon, tools hacking, autentikasi, monitoring

| # | File | Topik |
|---|------|-------|
| 1 | `01_Keamanan-Siber-Pengawasan-NSA-MITM-TEMPEST.md` | NSA UPSTREAM, MITM, Faraday Cage, Van Eck Phreaking |
| 2 | `02_Kriptografi-AES-RSA-ECC-Hashing.md` | AES-256, RSA, ECC P-256, bcrypt, Argon2id, side-channel |
| 3 | `03_Autentikasi-Web-Keamanan-Server.md` | Magic Link, Base64, Windows Server hardening, 5-layer defense |
| 4 | `04_OS-Level-Monitoring-EDR-Kernel.md` | Kernel monitoring, EDR workflow, Sysmon+Osquery+ETW, Python script |
| 5 | `05_Security-Monitoring-Sysmon-Hash.md` | SHA256 hash, AI log analysis, privacy-first, virtual env setup |
| 6 | `06_Panduan-Install-Sysmon.md` | Step-by-step Sysmon install (PowerShell, SwiftOnSecurity config) |
| 7 | `07_Panduan-Uninstall-Sysmon.md` | Sysmon uninstall guide (force uninstall, file cleanup) |
| 8 | `08_Tools-Cybersecurity-Dasar.md` | Nmap, Wireshark, Burp Suite, Yara, Ghidra + Python integration |
| 9 | `09_Hacking-Toolkits-Cyber-Defense-2026.md` | 10 toolkits pemula 2026, gamification, sandboxing |

---

### 04 — Spreadsheet, Excel & Automation
> Spreadsheet engine, formula system, PDF/OCR table extraction, automation workflow

| # | File | Topik |
|---|------|-------|
| 1 | `01_Excel-V4-Next-Generation-Spreadsheet.md` | Spreadsheet beyond Excel, 14 kategori design, AI integration |
| 2 | `02_Spreadsheet-Core-Formula-Dependency-Graph.md` | Core system, formula engine, dependency graph, reactive model |
| 3 | `03_PDF-Table-Extraction-AI-Stack.md` | Fake table detection, coordinate clustering, GPU selection, LoRA |
| 4 | `04_Table-Detection-Structure-Recognition.md` | PaddleOCR PP-Structure, SLANet, border/borderless, benchmarks |
| 5 | `05_Ekstraksi-Tabel-Bank-Rust-OCR.md` | Rust+Tesseract+Rayon pipeline, BNI statement, grid detection |
| 6 | `06_Automation-Parsing-Workflow-Data.md` | n8n/Zapier, regex, PDF parsing, no-code, POS workflow |

---

### 05 — AI Agent & Orchestration
> Multi-agent system, context management, tool calling, local AI agent

| # | File | Topik |
|---|------|-------|
| 1 | `01_AI-Coding-Agent-Orchestration.md` | Agent landscape, LangGraph, semantic indexing, sandbox, recovery |
| 2 | `02_Strategic-Context-Compaction.md` | Strategic vs auto-compaction, PreToolUse hooks, token optimization |
| 3 | `03_AI-Tools-Landscape-Anthropic-Qwen-OmniCoder.md` | Anthropic tool calling, Qwen 3.5, OmniCoder-9B, JSON Render, KARL |
| 4 | `04_AI-Agent-Notebook-Lokal-OpenSource.md` | Ollama, llama.cpp, GGUF, FAISS/ChromaDB, LangGraph, CrewAI |

---

### 06 — AI Image & Video Generation
> Stable Diffusion, LoRA, game asset, video generation, Google Stitch, Alpha Evolve

| # | File | Topik |
|---|------|-------|
| 1 | `01_AI-Image-Generation-SD-LoRA-ControlNet.md` | SD 1.5/2.0/SDXL/3.5, ControlNet, FLUX.2, A1111 vs ComfyUI |
| 2 | `02_Pixel-Isometric-Asset-Model-LoRA-Catalog.md` | Verified LoRA list (HF/Civitai), tier by VRAM, combo recommendation |
| 3 | `03_AI-Video-Generation-Transition-Automation.md` | Image→Video, Runway/Pika/Kaiber, hybrid workflow |
| 4 | `04_Google-Stitch-Vibe-Design-MiniMax.md` | Stitch infinite canvas, design.md, MiniMax M2.7, JEPRA |
| 5 | `05_AI-Tools-Deep-Dive-AlphaEvolve-Bitnet-RLM.md` | Alpha Evolve, Bitnet, RLM, GLM OCR, OpenClaw, free API platforms |

---

### 07 — Game Development
> Game engine, simulation game, asset pipeline

| # | File | Topik |
|---|------|-------|
| 1 | `01_Game-Development-Engine-Asset-Pipeline.md` | Unity vs Godot, isometric pixel art, AI asset pipeline |

---

### 08 — Jaringan Komputer & Kriptografi
> HTTPS, TLS, infrastruktur internet

| # | File | Topik |
|---|------|-------|
| 1 | `01_HTTPS-TLS-Infrastruktur-Internet.md` | TLS 1.3 handshake, PFS, HTTP/3 QUIC, URL anatomy |

---

### 09 — AI Career, Strategy & Trends
> Karir AI, tren model frontier, visi CEO, coding platform

| # | File | Topik |
|---|------|-------|
| 1 | `01_AI-Infrastructure-GPT6-Claude-Mythos-KimK2.md` | GPT-6 Native World Logic, Claude Mythos, TCO H100 vs API |
| 2 | `02_AI-Career-Skills-Trends-2027.md` | 5 skills $500K/year, AEO, AI Agent, Tesla TeraFab, Gaussian Splatting |
| 3 | `03_AI-CEO-Vision-Superintelligence-XZ-Backdoor.md` | 5 CEO convergence, XZ Utils backdoor, vibe coding decline |
| 4 | `04_AI-Coding-Platform-KiloAI-vs-BlackboxAI.md` | Assisted vs autonomous coding, multi-model infrastructure |

---

### 10 — Self-Hosting AI
> AI lokal, self-hosting, AI pajak, browser analysis

| # | File | Topik |
|---|------|-------|
| 1 | `01_Self-Hosting-AI-OpenSource-Model-Lisensi.md` | Model selection, lisensi (Apache/MIT vs Llama), Ollama, vLLM, S.A.F.E framework |
| 2 | `02_AI-Pajak-Self-Learning-Stack.md` | Qwen+Ollama+OpenClaw, PMK 6/2026, self-learning versioning, Telegram/Excel |
| 3 | `03_Browser-Screen-Analysis-AI-Code-Understanding.md` | getDisplayMedia, Canvas pixel, glassmorphism, AI co-pilot vs autopilot |

---

### 11 — Multi-Domain Knowledge
> Pengetahuan lintas domain: dev tools, keuangan, mindset

| # | File | Topik |
|---|------|-------|
| 1 | `01_Git-VSCode-AI-Agent-Excel-Sandbox.md` | Git workflow, VS Code optimization, AI agent, Excel automation |
| 2 | `02_Manajemen-Risiko-Margin-Safety-Decision.md` | Margin of safety, survivability, luck dynamics, AntiFragile framework |
| 3 | `03_Infrastruktur-Keuangan-Crypto-Wealth.md` | Cloud, server, crypto, ETF, portfolio strategy, Wealth System Builder |

---

### 12 — Project Docs & Notes
> Dokumentasi proyek, spesifikasi fitur, catatan

| # | File | Topik |
|---|------|-------|
| 1 | `01_AKP2I-Kalbar-Project-Documentation.md` | 10 sesi dev: UI/UX, 10 halaman, Tauri+Rust+Axum, DuckDB, security |
| 2 | `02_Agenda-TodoList-Feature-Spec.md` | Fitur agenda, todo 3 kolom (deadline/progress/done), UI spec |
| 3 | `03_Semantic-Core-Vocabulary.md` | Kata kunci semantik dasar: CORE, EXTENDED, CRITICAL |

---

## Perubahan dari Versi Sebelumnya

| Aspek | Sebelum (v1) | Sesudah (v2) |
|-------|-------------|-------------|
| Nama file | Terpotong, emoji, karakter aneh | `NN_Descriptive-Name.md` bersih |
| Format | Campuran (.txt, .md, .skill) | 100% Markdown (.md) |
| Header | Tidak ada | YAML header (title, kategori, tags) |
| Heading | Tidak konsisten | Hierarchy `# → ## → ###` seragam |
| Duplikasi | NI-1 = NI-5, pixel = Oke bro | Deduplicated, konten di-merge |
| .skill file | ZIP binary, tidak bisa dibaca | Diekstrak ke .md readable |
| Emoji di heading | Banyak emoji dekoratif | Dihapus untuk kejelasan |

---

*Dibangun oleh Super Z — Knowledge Library Reconstructor*
