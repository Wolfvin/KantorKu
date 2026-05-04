# Contributing to KantorKu / Panduan Kontribusi

Terima kasih atas minat Anda untuk berkontribusi pada KantorKu! Dokumen ini memberikan panduan untuk berkontribusi pada proyek ini.

Thank you for your interest in contributing to KantorKu! This document provides guidelines for contributing to this project.

---

## Table of Contents / Daftar Isi

- [Code of Conduct](#code-of-conduct)
- [Development Setup / Persiapan Pengembangan](#development-setup--persiapan-pengembangan)
- [Code Style / Gaya Kode](#code-style--gaya-kode)
- [Running Tests / Menjalankan Pengujian](#running-tests--menjalankan-pengujian)
- [Adding Workers / Menambahkan Worker](#adding-workers--menambahkan-worker)
- [Pull Request Process / Proses Pull Request](#pull-request-process--proses-pull-request)
- [Commit Messages / Pesan Commit](#commit-messages--pesan-commit)
- [Bug Reports / Laporan Bug](#bug-reports--laporan-bug)
- [Feature Requests / Permintaan Fitur](#feature-requests--permintaan-fitur)

---

## Code of Conduct

Proyek ini mengikuti [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). Dengan berpartisipasi, Anda diharapkan mematuhi kode ini.

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

---

## Development Setup / Persiapan Pengembangan

### Prerequisites / Prasyarat

| Tool | Version | Purpose |
|------|---------|---------|
| Python | ≥ 3.12 | Backend framework |
| Node.js | ≥ 20 | Frontend & CLI |
| pip | latest | Python package manager |
| npm/pnpm | latest | Node.js package manager |

### Quick Start / Mulai Cepat

```bash
# 1. Fork & clone the repository
git clone https://github.com/Wolfvin/KantorKu.git
cd kantorku

# 2. Set up the Python backend
cd framework
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
pip install -e ".[dev,all]"

# 3. Set up the Next.js frontend
cd ../interface
npm install

# 4. Set up the CLI tool
cd ../cli
npm install

# 5. Copy environment configuration
cp .env.example .env
# Edit .env with your API keys

# 6. Start development servers
# Terminal 1: Backend
cd framework && kantorku serve

# Terminal 2: Frontend
cd interface && npm run dev
```

### Docker Setup / Persiapan Docker

```bash
docker compose up
```

This starts KantorKu backend on `:8000`, Ollama on `:11434`, and the Interface on `:3000`.

Ini akan menjalankan backend KantorKu di `:8000`, Ollama di `:11434`, dan Interface di `:3000`.

---

## Code Style / Gaya Kode

### Python (Backend / framework/)

Kami menggunakan [Ruff](https://docs.astral.sh/ruff/) untuk linting dan formatting.

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
# Lint
cd framework
ruff check .

# Format
ruff format .
```

**Key rules / Aturan utama:**
- Line length: 100 characters
- Use type hints on all public functions
- Docstrings in Google style
- Imports sorted with `isort` (via Ruff)

### TypeScript (Frontend / interface/ & CLI / cli/)

Kami menggunakan ESLint dan Prettier.

We use ESLint and Prettier.

```bash
# Lint
cd interface && npm run lint

# Format
npm run format
```

**Key rules / Aturan utama:**
- Strict TypeScript (no `any` without justification)
- Functional components with hooks (React)
- Tailwind CSS for styling
- Named exports preferred

---

## Running Tests / Menjalankan Pengujian

### Python Tests / Pengujian Python

```bash
cd framework

# Run all tests
pytest

# Run with coverage
pytest --cov=kantorku --cov-report=html

# Run specific test file
pytest tests/test_office.py

# Run with verbose output
pytest -v
```

### TypeScript Tests / Pengujian TypeScript

```bash
cd interface

# Run tests
npm test

# Run in watch mode
npm test -- --watch
```

---

## Adding Workers / Menambahkan Worker

KantorKu menggunakan arsitektur worker-based. Untuk menambahkan worker baru, ikuti panduan lengkap di [docs/ADDING_WORKERS.md](docs/ADDING_WORKERS.md).

KantorKu uses a worker-based architecture. To add a new worker, follow the complete guide in [docs/ADDING_WORKERS.md](docs/ADDING_WORKERS.md).

**Quick overview / Ikhtisar cepat:**

1. **Define the worker** in `framework/workers/` — create a new directory with `worker.toml`
2. **Implement the handler** — Python module with `handle(task)` function
3. **Register in office** — Add the worker to `framework/kantorku.toml`
4. **Test thoroughly** — Add tests in `framework/tests/`
5. **Document** — Update relevant docs

Worker naming convention / Konvensi penamaan worker:
- Use `snake_case` for worker IDs (e.g., `coder_backend`, `verifier_designer`)
- Use descriptive names that reflect the worker's role in the "office"

---

## Pull Request Process / Proses Pull Request

1. **Fork** the repository
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feat/my-new-feature
   ```
3. **Make your changes** and commit with conventional commit messages
4. **Add tests** for new functionality
5. **Update documentation** if needed
6. **Ensure CI passes** — run linting and tests locally first
7. **Open a Pull Request** against the `main` branch

### PR Checklist / Daftar Periksa PR

- [ ] Code follows the project style guidelines
- [ ] Tests added/updated for changes
- [ ] Documentation updated (if applicable)
- [ ] No breaking changes (or clearly documented)
- [ ] Commit messages follow conventional commits
- [ ] Self-reviewed the code

---

## Commit Messages / Pesan Commit

Kami mengikuti [Conventional Commits](https://www.conventionalcommits.org/).

We follow [Conventional Commits](https://www.conventionalcommits.org/).

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types / Tipe

| Type | Description | Contoh |
|------|-------------|--------|
| `feat` | New feature / Fitur baru | `feat(worker): add debugger worker` |
| `fix` | Bug fix / Perbaikan bug | `fix(server): resolve SSE connection leak` |
| `docs` | Documentation / Dokumentasi | `docs(readme): add comparison table` |
| `refactor` | Code refactor / Refaktor kode | `refactor(office): simplify worker dispatch` |
| `test` | Add/update tests / Tambah/perbarui pengujian | `test(conductor): add routing tests` |
| `chore` | Maintenance / Pemeliharaan | `chore(deps): update dependencies` |
| `perf` | Performance / Performa | `perf(memory): optimize context pool` |
| `style` | Code style (formatting) / Gaya kode | `style: fix ruff linting issues` |

### Scopes / Ruang Lingkup

- `worker` — Worker-related changes
- `office` — Office/conductor changes
- `memory` — Memory/context pool changes
- `server` — API server changes
- `interface` — Frontend changes
- `cli` — CLI tool changes
- `docs` — Documentation only

---

## Bug Reports / Laporan Bug

Gunakan template [Bug Report](.github/ISSUE_TEMPLATE/bug_report.yml) saat melaporkan bug.

Use the [Bug Report](.github/ISSUE_TEMPLATE/bug_report.yml) template when reporting bugs.

**Include / Sertakan:**

1. **Description** — Clear description of the bug
2. **Steps to reproduce** — Minimal reproduction steps
3. **Expected behavior** — What should happen
4. **Actual behavior** — What actually happens
5. **Environment** — Python version, OS, KantorKu version
6. **Logs** — Relevant error logs or stack traces
7. **Configuration** — Worker setup (sanitize API keys!)

---

## Feature Requests / Permintaan Fitur

Gunakan template [Feature Request](.github/ISSUE_TEMPLATE/feature_request.yml) atau [Worker Request](.github/ISSUE_TEMPLATE/worker_request.yml).

Use the [Feature Request](.github/ISSUE_TEMPLATE/feature_request.yml) or [Worker Request](.github/ISSUE_TEMPLATE/worker_request.yml) template.

**Include / Sertakan:**

1. **Problem statement** — What problem does this solve?
2. **Proposed solution** — How should it work?
3. **Alternatives considered** — Other approaches you've thought of
4. **Use case** — Real-world scenario where this would help

---

## Questions? / Pertanyaan?

- 💬 [GitHub Discussions](https://github.com/Wolfvin/KantorKu/discussions)
- 🐛 [Issue Tracker](https://github.com/Wolfvin/KantorKu/issues)
- 📖 [Documentation](docs/)

---

Terima kasih telah berkontribusi! 🏢

Thank you for contributing! 🏢
