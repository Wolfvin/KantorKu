# Contributing to KantorKu

Thank you for your interest in contributing to KantorKu! This document provides guidelines and instructions for contributing.

---

## Code of Conduct

Be respectful, constructive, and inclusive. We're all here to build something great together.

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- A LLM provider account (or [Ollama](https://ollama.com) for free local usage)

### Setup

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/KantorKu.git
cd KantorKu

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Verify
python -m pytest tests/ -v
```

---

## How to Contribute

### Reporting Bugs

1. Search [existing issues](https://github.com/Wolfvin/KantorKu/issues) to avoid duplicates
2. Open a new issue with:
   - **Clear title** describing the problem
   - **Steps to reproduce** the behavior
   - **Expected behavior** vs actual behavior
   - **Environment details** (Python version, OS, provider)
   - **Relevant logs** or error messages

### Suggesting Features

1. Open an issue with the `enhancement` label
2. Describe the use case and why it would benefit KantorKu
3. If possible, outline how you'd implement it

### Submitting Code

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our style guidelines

3. **Write tests** for new functionality:
   - Unit tests for isolated logic
   - Integration tests for end-to-end flows
   - TUI tests using `App.run_test()` for UI components

4. **Run the test suite**:
   ```bash
   python -m pytest tests/ -v
   ruff check kantorku/
   ```

5. **Commit with clear messages**:
   ```bash
   git commit -m "feat(workers): add security_auditor worker"
   git commit -m "fix(tui): resolve breadcrumb stuck at WORKING state"
   ```

6. **Push and open a Pull Request**:
   ```bash
   git push origin feature/your-feature-name
   ```

---

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

feat(workers): add image generation worker
fix(tui): resolve breadcrumb stuck at WORKING state
docs(readme): update installation instructions
refactor(office): simplify conductor orchestration loop
test(memory): add ring1 integration tests
chore(deps): bump textual to 0.80
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`

**Scopes:** `workers`, `tui`, `office`, `memory`, `providers`, `server`, `core`

---

## Code Style

- **Python 3.11+** — Use modern syntax (type hints, match statements, etc.)
- **Line length:** 100 characters max (enforced by Ruff)
- **Type hints:** Required for all function signatures
- **Docstrings:** Google style for public APIs
- **Async:** All worker and office methods are async
- **Imports:** Use `from kantorku.xxx import Yyy` for internal imports

### Linting

```bash
# Check
ruff check kantorku/

# Auto-fix
ruff check --fix kantorku/
```

---

## Architecture Overview

Before contributing, understand the core architecture:

```
Office (entry point)
├── Conductor (CEO — orchestration + contracts)
├── BriefingRoom (pre-execution discussion)
├── WorkerHub (peer-to-peer DM + broadcast)
├── ContextPool (proactive prefetch)
├── Workers (13 built-in, pluggable)
├── Memory (3-ring: DuckDB / SQLite / GraphRAG)
├── Providers (7 LLM providers)
└── TUI (3-panel terminal UI)
```

Key principles:
- **Workers are autonomous** — each has its own API, model, and personality
- **Context is pre-fetched** — ContextPool works during briefing, not on demand
- **Events drive everything** — 38 event types flow through the EventBus
- **Contracts before execution** — the Conductor negotiates with the client first

---

## Adding a Worker

See [ADDING_WORKERS.md](./ADDING_WORKERS.md) for the complete guide. Quick version:

1. Create `workers/your_worker/plugin.json` with metadata
2. Create `workers/your_worker/SKILL.md` as the system prompt
3. (Optional) Create `workers/your_worker/worker.py` for custom logic
4. Test with `kantorku worker validate workers/your_worker/`

---

## Adding a Provider

1. Create `kantorku/providers/your_provider.py` extending `BaseProvider`
2. Implement `async def complete()` and `async def stream()`
3. Register in `ProviderRouter`
4. Add to `pyproject.toml` optional dependencies
5. Add to `VALID_PROVIDERS` in config
6. Write tests in `tests/`

---

## Testing

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_office.py -v

# With coverage
python -m pytest tests/ --cov=kantorku
```

### Test Categories

- **Unit tests** — Test individual functions and classes in isolation
- **Integration tests** — Test component interactions (worker → provider → memory)
- **TUI tests** — Use Textual's `App.run_test()` harness for UI testing

### Writing TUI Tests

```python
import pytest
from kantorku.tui.app import KantorKuTUI

@pytest.mark.asyncio
async def test_app_starts():
    async with KantorKuTUI.run_test() as pilot:
        assert pilot.app is not None
        # Test interactions...
```

---

## Pull Request Checklist

Before submitting, verify:

- [ ] All tests pass (`python -m pytest tests/ -v`)
- [ ] No lint errors (`ruff check kantorku/`)
- [ ] New code has type hints
- [ ] New code has tests
- [ ] Commit messages follow Conventional Commits
- [ ] Documentation updated if needed
- [ ] No API keys or secrets in the code

---

## Release Process

Maintainers handle releases:

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag v0.x.0`
4. Push tag: `git push origin v0.x.0`
5. GitHub Actions builds and publishes to PyPI

---

## Questions?

- Open a [GitHub Issue](https://github.com/Wolfvin/KantorKu/issues)
- Start a [Discussion](https://github.com/Wolfvin/KantorKu/discussions)

---

Thank you for contributing to KantorKu!
