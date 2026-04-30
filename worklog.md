---
Task ID: 2
Agent: Main Agent
Task: Upgrade worker system with per-worker API support and detailed documentation

Work Log:
- Created WorkerAPI dataclass with provider, model, api_key, base_url, extra fields
- Added ${ENV_VAR} resolution to WorkerAPI (resolve_env_vars method)
- Upgraded WorkerIdentity to use WorkerAPI instead of plain "model" string
- Added backwards compat: WorkerIdentity(id="x", model="provider/model") still works
- Added self.api property to BaseWorker (access WorkerAPI config)
- Added self.api_call(method, url) to BaseWorker for direct HTTP API calls
- Added self._ensure_own_provider() for lazy provider creation per-worker
- self.llm_call() now tries worker's own API first, falls back to global router
- Updated all 13 builtin worker plugin.json with proper "api" sections
- Each worker now has a DIFFERENT API: Anthropic, Google, OpenAI, xAI, DeepSeek, MiniMax, Ollama
- Created ADDING_WORKERS.md with complete documentation (Bahasa Indonesia)
- Updated __init__.py with WorkerAPI export
- Fixed validation to not check env vars at discovery time (only at runtime)
- All 40 tests passing

Stage Summary:
- Workers now have truly independent API configurations
- coder_wiring uses OpenAI Codex 5.3, debugger uses xAI Grok 3, verifier_designer uses Google Gemini 2.5 Pro
- self.api_call() enables direct HTTP calls with auto-injected Bearer token
- Detailed ADDING_WORKERS.md guide created
- Full backwards compatibility maintained
