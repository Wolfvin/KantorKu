# Credits & Acknowledgments

kantorku tidak akan ada tanpa ekosistem open-source yang luar biasa. Kami berterima kasih kepada semua proyek, komunitas, dan individu yang telah berkontribusi — baik langsung maupun tidak langsung.

---

## Core Framework & Libraries

### Python Backend
| Proyek | Kegunaan | Repo |
|--------|----------|------|
| **FastAPI** | Async web framework untuk server & API | [github.com/fastapi/fastapi](https://github.com/fastapi/fastapi) |
| **Uvicorn** | ASGI server dengan WebSocket support | [github.com/encode/uvicorn](https://github.com/encode/uvicorn) |
| **Pydantic** | Data validation & settings management | [github.com/pydantic/pydantic](https://github.com/pydantic/pydantic) |
| **httpx** | Async HTTP client untuk provider API calls | [github.com/encode/httpx](https://github.com/encode/httpx) |
| **DuckDB** | Ring 1 memory — fast analytical queries | [github.com/duckdb/duckdb](https://github.com/duckdb/duckdb) |
| **aiosqlite** | Ring 2 memory — async SQLite interface | [github.com/omnilib/aiosqlite](https://github.com/omnilib/aiosqlite) |
| **websockets** | WebSocket server untuk real-time events | [github.com/python-websockets/websockets](https://github.com/python-websockets/websockets) |
| **anyio** | Async compatibility layer | [github.com/agronholm/anyio](https://github.com/agronholm/anyio) |

### Next.js Interface
| Proyek | Kegunaan | Repo |
|--------|----------|------|
| **Next.js** | React framework untuk UI | [github.com/vercel/next.js](https://github.com/vercel/next.js) |
| **React** | UI component library | [github.com/facebook/react](https://github.com/facebook/react) |
| **Zustand** | State management | [github.com/pmndrs/zustand](https://github.com/pmndrs/zustand) |
| **shadcn/ui** | UI component library (Radix-based) | [github.com/shadcn-ui/ui](https://github.com/shadcn-ui/ui) |
| **Radix UI** | Accessible UI primitives | [github.com/radix-ui/primitives](https://github.com/radix-ui/primitives) |
| **Tailwind CSS** | Utility-first CSS framework | [github.com/tailwindlabs/tailwindcss](https://github.com/tailwindlabs/tailwindcss) |
| **Recharts** | Chart & visualization library | [github.com/recharts/recharts](https://github.com/recharts/recharts) |
| **react-resizable-panels** | Resizable panel layout | [github.com/bvaughn/react-resizable-panels](https://github.com/bvaughn/react-resizable-panels) |
| **Framer Motion** | Animation library | [github.com/motiondivision/motion](https://github.com/motiondivision/motion) |
| **Lucide** | Icon library | [github.com/lucide-icons/lucide](https://github.com/lucide-icons/lucide) |
| **z-ai-web-dev-sdk** | AI SDK untuk LLM calls | Z.ai SDK |

### CLI Tool
| Proyek | Kegunaan | Repo |
|--------|----------|------|
| **Commander.js** | CLI framework | [github.com/tj/commander.js](https://github.com/tj/commander.js) |
| **Inquirer.js** | Interactive CLI prompts | [github.com/SBoudrias/Inquirer.js](https://github.com/SBoudrias/Inquirer.js) |
| **Chalk** | Terminal colors | [github.com/chalk/chalk](https://github.com/chalk/chalk) |
| **Ora** | Terminal spinners | [github.com/sindresorhus/ora](https://github.com/sindresorhus/ora) |
| **Boxen** | Terminal boxes | [github.com/sindresorhus/boxen](https://github.com/sindresorhus/boxen) |

---

## LLM Providers

kantorku mendukung multiple LLM providers. Terima kasih kepada:

| Provider | Workers yang Menggunakan | Website |
|----------|-------------------------|---------|
| **Anthropic** | Conductor (Claude Opus 4.6), coder_frontend, auditor | [anthropic.com](https://anthropic.com) |
| **Google** | coder_wiring, verifier_designer, scout (Gemini) | [ai.google.dev](https://ai.google.dev) |
| **MiniMax** | coder_backend (M2.7), verifier_engineer (M2.5) | [minimaxi.com](https://minimaxi.com) |
| **DeepSeek** | debugger (V3.2), scribe, summarizer (V4 Flash), Context Pool | [deepseek.com](https://deepseek.com) |
| **OpenAI** | coder_wiring (Codex) | [openai.com](https://openai.com) |
| **xAI** | debugger (Grok 3) | [x.ai](https://x.ai) |
| **Ollama** | intake, narrator, sentinel (Llama3, lokal) | [ollama.com](https://ollama.com) |
| **Z.ai** | Standalone mode SDK | [Z.ai](https://z.ai) |

---

## Inspirasi & Konsep

Konsep kantorku terinspirasi dari beberapa idea dan proyek besar:

| Inspirasi | Deskripsi | Sumber |
|-----------|-----------|--------|
| **CrewAI** | Multi-agent orchestration dengan role-based workers | [github.com/crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) |
| **AutoGen** | Multi-agent conversation framework dari Microsoft | [github.com/microsoft/autogen](https://github.com/microsoft/autogen) |
| **LangGraph** | Graph-based agent orchestration | [github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) |
| **MetaGPT** | Multi-agent dengan SOP & role definition | [github.com/geekan/MetaGPT](https://github.com/geekan/MetaGPT) |
| **ChatDev** | Virtual software company dengan chat-based agents | [github.com/OpenBMB/ChatDev](https://github.com/OpenBMB/ChatDev) |
| **OpenAI Swarm** | Experimental multi-agent framework | [github.com/openai/swarm](https://github.com/openai/swarm) |
| **Agency Swarm** | Agent-based agency framework | [github.com/VRSEN/agency-swarm](https://github.com/VRSEN/agency-swarm) |
| **Cognitive Architectures** | Konsep kantor digital dengan organisasi terstruktur | Research papers on cognitive architectures |

---

## Komunitas & Sumber Belajar

| Sumber | Deskripsi |
|--------|-----------|
| **Hugging Face** | Model hub & benchmark data |
| **OpenRouter** | Multi-provider LLM routing |
| **LMSYS Chatbot Arena** | Model benchmark & Elo ratings |
| **SWE-bench** | Coding benchmark scores |
| **BFCL** | Tool/function calling benchmark |

---

## Kontributor

Proyek ini dikembangkan oleh komunitas. Terima kasih kepada semua yang sudah berkontribusi kode, ide, testing, dan feedback.

Jika Anda ingin berkontribusi, silakan buka issue atau pull request di repository GitHub.

---

## Lisensi

kantorku dirilis di bawah lisensi **MIT**. Semua dependencies tetap menggunakan lisensi masing-masing.

---

> *"Kantor yang sesungguhnya bukan soal gedung — tapi soal orang-orang yang bekerja bersama."*
