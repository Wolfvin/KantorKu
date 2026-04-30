# Backend — Sandbox (OpenSandbox + DeerFlow)

> **Konteks untuk session baru:**
> Vibe-office workers coding di lingkungan sandbox terisolasi = kode mereka
> tidak bisa damage host system. Dua opsi dievaluasi:
> - OpenSandbox (github.com/alibaba/OpenSandbox, Apache-2.0, 4.3k stars)
>   → general-purpose, Docker/K8s, unified API, ada contoh claude-code di dalamnya
> - DeerFlow sandbox (github.com/bytedance/deer-flow)
>   → sudah proven untuk AI coding agents, lebih simple
> Decision: untuk Fase 1-3 skip sandbox. Fase 3+ pakai OpenSandbox.
> Dievaluasi session 2026-03-16.

---

## Kenapa Sandbox Diperlukan

Tanpa sandbox:
- rust_worker bisa `rm -rf /home/user/important-project`
- security_worker scan menemukan secret di path sistem
- tester_worker jalankan test yang corrupt database lokal
- Crash satu worker bisa corrupt session state

Dengan sandbox (Docker container per task):
- Setiap task di container fresh, isolated
- Host filesystem tidak tersentuh (kecuali output yang diapprove)
- Crash dalam container → container restart, host aman
- Audit trail: semua yang dilakukan worker tercatat

---

## OpenSandbox — Overview

**Repo:** https://github.com/alibaba/OpenSandbox
Apache-2.0, dari Alibaba. Unified sandbox API untuk AI applications.

**Kenapa OpenSandbox bukan Docker langsung:**
- Unified API untuk Python, TypeScript, Java, Go
- Lifecycle management (create, run, kill, cleanup) sudah handled
- Network policy per-sandbox (ingress + egress control)
- Support Kubernetes untuk scale
- Ada contoh `claude-code` running di OpenSandbox — trust factor tinggi

**Install:**
```bash
pip install opensandbox-server opensandbox-code-interpreter
opensandbox-server init-config ~/.sandbox.toml --example docker
opensandbox-server  # start server
```

---

## Integrasi OpenSandbox dengan Workers

```python
import asyncio
from datetime import timedelta
from code_interpreter import CodeInterpreter, SupportedLanguage
from opensandbox import Sandbox

class SandboxedWorker:
    """
    Worker yang execute di dalam OpenSandbox container.
    File ini ditulis oleh worker, dibaca hasilnya, container di-kill.
    """

    async def execute_rust_task(self, task: dict) -> dict:
        """rust_worker execute code dalam isolated container."""

        sandbox = await Sandbox.create(
            "opensandbox/code-interpreter:v1.0.1",
            entrypoint=["/opt/opensandbox/code-interpreter.sh"],
            env={
                "RUST_TOOLCHAIN": "stable",
                "PROJECT_ROOT": task['context'].get('project_path', '/workspace')
            },
            timeout=timedelta(seconds=task.get('timeout_seconds', 60)),
        )

        async with sandbox:
            # 1. Copy project files ke sandbox
            await sandbox.files.write_files([
                WriteEntry(path=f"/workspace/{f['path']}", data=f['content'])
                for f in task['context'].get('relevant_files', [])
            ])

            # 2. Tulis kode yang dihasilkan worker LLM
            generated_code = await self._llm_generate_code(task)
            await sandbox.files.write_files([
                WriteEntry(path="/workspace/src/generated.rs", data=generated_code)
            ])

            # 3. Compile + test dalam container
            compile_result = await sandbox.commands.run(
                "cd /workspace && cargo build 2>&1"
            )

            test_result = None
            if compile_result.exit_code == 0:
                test_result = await sandbox.commands.run(
                    "cd /workspace && cargo test 2>&1"
                )

            # 4. Read output files
            if compile_result.exit_code == 0:
                output_files = await sandbox.files.list_files("/workspace/src/")
            else:
                output_files = []

        # Container auto-killed saat keluar `async with` block

        return {
            'code': generated_code,
            'compile_success': compile_result.exit_code == 0,
            'compile_output': compile_result.logs.stdout,
            'test_result': test_result,
            'files': output_files,
        }
```

---

## Filesystem Layout dalam Sandbox

Mengikuti pola DeerFlow + OpenSandbox:

```
/workspace/                     ← project files (di-mount dari host)
├── src/                        ← source code
├── Cargo.toml                  ← project config
└── target/                     ← build artifacts

/mnt/skills/                    ← SKILL.md workers (read-only mount)
├── public/
│   └── {worker_id}/SKILL.md
└── custom/

/tmp/                           ← temporary worker scratch space
/output/                        ← hasil yang akan di-copy ke host
```

**Mount strategy:**
```python
sandbox = await Sandbox.create(
    image="vibe-office-worker:latest",
    mounts=[
        Mount(host_path=f"/home/user/.vibe-office/projects/{project_id}",
              container_path="/workspace",
              read_only=False),   # worker bisa write ke project
        Mount(host_path="/home/user/.vibe-office/workers",
              container_path="/mnt/skills",
              read_only=True),    # SKILL.md tidak bisa di-edit dari dalam sandbox
    ]
)
```

---

## Network Policy per Worker

OpenSandbox support egress control — beberapa workers butuh internet, beberapa tidak:

```python
# context_worker butuh akses internet (Lightpanda scrape docs.rs)
context_worker_sandbox = await Sandbox.create(
    image="vibe-office-worker:latest",
    network_policy=NetworkPolicy(
        egress_allowed=["docs.rs", "crates.io", "doc.rust-lang.org"]
    )
)

# rust_worker tidak perlu internet — hanya akses local project
rust_worker_sandbox = await Sandbox.create(
    image="vibe-office-worker:latest",
    network_policy=NetworkPolicy(
        egress_allowed=[]  # no internet access
    )
)
```

---

## Fase Implementasi

```
Fase 1-2: SKIP sandbox — terlalu complex untuk prototyping
           Workers "coding" adalah simulated via WebSocket dummy

Fase 3:   Tambahkan sandbox untuk rust_worker dan tester_worker dulu
           Pakai OpenSandbox local Docker mode (tidak perlu Kubernetes)
           Image: build dari Dockerfile dengan Rust toolchain

Fase 4:   Semua workers di sandbox
           Evaluasi Kubernetes mode kalau vibe-office di-deploy ke server

Fase 5+:  Persistent storage per-project, network isolation per-worker
```

---

## Custom Sandbox Image untuk Vibe-Office

```dockerfile
# vibe-office-worker.Dockerfile
FROM opensandbox/code-interpreter:v1.0.1

# Install Rust toolchain
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install tools yang dipakai workers
RUN cargo install cargo-audit  # security_worker
RUN apt-get install -y git     # git_worker
RUN npm install -g gitnexus    # context_worker (GitNexus CLI)

# Workspace setup
WORKDIR /workspace
```

```bash
# Build image
docker build -f vibe-office-worker.Dockerfile -t vibe-office-worker:latest .

# Register ke OpenSandbox
opensandbox-server register-image vibe-office-worker:latest
```

---

## Visualisasi di Game Kantor

Saat worker masuk sandbox:
- Worker jalan ke workstation
- Speech bubble: "spinning up container..."
- Progress bar mulai dari kiri (compile) ke kanan (test)
- TV update: "[rust_worker] sandboxed execution started"

Saat container selesai/crash:
- Berhasil: worker jalan ke server_room, speech bubble: "done ✓"
- Crash: worker ke dormitory, speech bubble: "container crashed, retrying..."
- TV update dengan compile output (via output_translator)
