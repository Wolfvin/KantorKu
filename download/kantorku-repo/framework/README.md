# kantorku

Kantor digital yang sesungguhnya — AI worker orchestration framework.

## Install

```bash
pip install kantorku
```

## Quick Start

```python
import asyncio
from kantorku import Office

async def main():
    office = Office.from_config("kantorku.toml")
    await office.initialize()
    result = await office.run("Buat rate limiter di Rust")

asyncio.run(main())
```

## Architecture

- **Conductor**: CEO — orchestrates workers, manages contracts
- **BriefingRoom**: Workers discuss before executing
- **WorkerHub**: Peer-to-peer DM between workers
- **ContextPool**: Proactive prefetch with DeepSeek
- **3-Ring Memory**: DuckDB (hot) → SQLite (warm) → Cognee (cold)

## Workers

| Worker | Model | Role |
|--------|-------|------|
| coder_frontend | Claude Sonnet 4.6 | React/CSS/UI |
| coder_backend | MiniMax M2.7 | Python/Rust/Systems |
| coder_wiring | Gemini 3.1 Pro | API/WS/MCP/Glue |
| verifier_designer | Gemini 3.1 Pro | Visual/UX judge |
| verifier_engineer | MiniMax M2.5 | Logic/test/security |

## License

MIT
