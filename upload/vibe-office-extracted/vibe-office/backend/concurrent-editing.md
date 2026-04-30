# Backend — Concurrent Editing (Fase 3)

> **Konteks untuk session baru:**
> Masalah: dua workers edit file yang sama bersamaan → salah satu overwrite hasil kerja lain.
> Ini sangat mungkin terjadi di post-coding pipeline (scribe + auditor + sentinel paralel).
> Solusi yang dipilih: Git Worktree per worker (dari learn-claude-code s12).
> File locking sebagai fallback kalau worktree terlalu overhead untuk task kecil.

---

## Kapan Terjadi

```
SKENARIO 1 — Post-coding pipeline paralel:
  coder_rust selesai nulis src/http.rs
    ↓ (bridge normalize, trigger paralel)
  scribe      → mau tambah rustdoc ke src/http.rs
  auditor     → mau annotate findings ke src/http.rs
  sentinel    → mau scan src/http.rs untuk secrets
    ↓
  Tiga workers baca file yang sama pada waktu hampir bersamaan
  Scribe tulis dulu → file updated
  Auditor tulis dengan versi LAMA yang dia baca → overwrite rustdoc scribe!

SKENARIO 2 — Dua coder paralel:
  conductor assign dua task sekaligus (via DeerFlow parallel pattern)
  coder_rust  → edit src/lib.rs (tambah module baru)
  coder_python → edit src/lib.rs (tambah Python bindings)
    ↓
  Race condition — siapa yang terakhir tulis, dialah yang "menang"
```

---

## Solusi 1 — Git Worktree per Worker (UTAMA)

Dari learn-claude-code s12 (worktree isolation). Setiap worker yang
butuh **menulis** kode dapat branch dan worktree sendiri.
Setelah selesai, `chronicler` yang merge.

```
project/
├── .git/
│   └── worktrees/
│       ├── coder_rust_task_042/     ← worktree coder_rust untuk task 042
│       ├── coder_python_task_043/   ← worktree coder_python untuk task 043
│       └── scribe_task_042/         ← worktree scribe (setelah coder_rust selesai)
└── src/  (main branch, tidak disentuh workers saat task berjalan)
```

```python
# src/worktree_manager.py

import subprocess
import os
from pathlib import Path

class WorktreeManager:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.worktrees_dir = self.project_path / '.git' / 'worktrees'

    def create_worktree(self, worker_id: str, task_id: str) -> str:
        """
        Buat worktree baru untuk worker + task.
        Return: path ke worktree directory.
        """
        branch_name = f"worker/{worker_id}/task-{task_id}"
        worktree_path = self.project_path.parent / f".vibe-worktrees/{worker_id}-{task_id}"

        # Buat branch dari HEAD
        subprocess.run([
            "git", "-C", str(self.project_path),
            "worktree", "add",
            "-b", branch_name,
            str(worktree_path),
            "HEAD"
        ], check=True)

        # Simpan mapping ke DuckDB Ring 1
        self._register_worktree(worker_id, task_id, worktree_path, branch_name)

        return str(worktree_path)

    def remove_worktree(self, worker_id: str, task_id: str):
        """Hapus worktree setelah task selesai (merge sudah dilakukan)."""
        info = self._get_worktree_info(worker_id, task_id)
        if not info:
            return

        subprocess.run([
            "git", "-C", str(self.project_path),
            "worktree", "remove", "--force",
            info['path']
        ], check=True)

        # Hapus branch
        subprocess.run([
            "git", "-C", str(self.project_path),
            "branch", "-D", info['branch']
        ], check=True)

        self._unregister_worktree(worker_id, task_id)

    def get_worktree_path(self, worker_id: str, task_id: str) -> str | None:
        """Return path worktree aktif untuk worker + task ini."""
        info = self._get_worktree_info(worker_id, task_id)
        return info['path'] if info else None

    def _register_worktree(self, worker_id, task_id, path, branch):
        """Simpan ke DuckDB Ring 1 agar crash-safe."""
        conn = get_ring1_conn()
        conn.execute("""
            INSERT OR REPLACE INTO active_worktrees
            (worker_id, task_id, path, branch, created_at)
            VALUES (?, ?, ?, ?, now())
        """, [worker_id, task_id, str(path), branch])

    def _get_worktree_info(self, worker_id, task_id) -> dict | None:
        conn = get_ring1_conn()
        row = conn.execute("""
            SELECT path, branch FROM active_worktrees
            WHERE worker_id = ? AND task_id = ?
        """, [worker_id, task_id]).fetchone()
        return {'path': row[0], 'branch': row[1]} if row else None

    def _unregister_worktree(self, worker_id, task_id):
        get_ring1_conn().execute("""
            DELETE FROM active_worktrees WHERE worker_id = ? AND task_id = ?
        """, [worker_id, task_id])
```

**DuckDB schema untuk worktree tracking:**
```sql
CREATE TABLE IF NOT EXISTS active_worktrees (
    worker_id  TEXT NOT NULL,
    task_id    TEXT NOT NULL,
    path       TEXT NOT NULL,
    branch     TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    PRIMARY KEY (worker_id, task_id)
);
```

---

## Merge Flow (chronicler's job)

```python
# Di chronicler worker, setelah semua pipeline workers selesai:

async def merge_and_commit(task_id: str, coder_worker_id: str):
    wt = WorktreeManager(project_path)
    worktree_path = wt.get_worktree_path(coder_worker_id, task_id)
    branch = get_branch_name(coder_worker_id, task_id)

    # 1. Checkout main
    subprocess.run(["git", "-C", project_path, "checkout", "main"], check=True)

    # 2. Merge branch worker
    result = subprocess.run([
        "git", "-C", project_path,
        "merge", "--no-ff", branch,
        "-m", f"task({task_id}): merge {coder_worker_id} changes"
    ], capture_output=True)

    if result.returncode != 0:
        # CONFLICT — eskalasi ke conductor (Tier 2 recovery)
        conflict_files = parse_conflict_files(result.stderr)
        await conductor.handle_merge_conflict(task_id, conflict_files)
        return

    # 3. Cleanup worktree
    wt.remove_worktree(coder_worker_id, task_id)

    # 4. Re-index GitNexus (background)
    asyncio.create_task(run_gitnexus_analyze())
```

---

## Solusi 2 — File Locking (FALLBACK untuk task kecil)

Untuk task yang tidak butuh worktree penuh (misal: scribe hanya tambah
rustdoc ke file yang sudah selesai ditulis coder), file locking lebih ringan.

```python
# Di DuckDB Ring 1

async def acquire_file_lock(worker_id: str, filepath: str, timeout: int = 30) -> bool:
    """
    Claim file untuk ditulis. Return True kalau berhasil, False kalau timeout.
    Lock otomatis expire setelah 60 detik (safety net kalau worker crash).
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        conn = get_ring1_conn()
        try:
            conn.execute("""
                INSERT INTO file_locks (filepath, worker_id, expires_at)
                VALUES (?, ?, now() + INTERVAL 60 SECOND)
            """, [filepath, worker_id])
            return True
        except Exception:
            # Lock sudah ada — cek apakah sudah expired
            expired = conn.execute("""
                SELECT 1 FROM file_locks
                WHERE filepath = ? AND expires_at < now()
            """, [filepath]).fetchone()

            if expired:
                # Lock expired — force remove dan coba lagi
                conn.execute("DELETE FROM file_locks WHERE filepath = ?", [filepath])
                continue

            await asyncio.sleep(0.5)  # tunggu sebentar

    return False  # timeout

async def release_file_lock(worker_id: str, filepath: str):
    get_ring1_conn().execute("""
        DELETE FROM file_locks WHERE filepath = ? AND worker_id = ?
    """, [filepath, worker_id])
```

```sql
-- DuckDB schema
CREATE TABLE IF NOT EXISTS file_locks (
    filepath   TEXT PRIMARY KEY,
    worker_id  TEXT NOT NULL,
    acquired_at TIMESTAMP DEFAULT now(),
    expires_at  TIMESTAMP NOT NULL
);
```

**Pakai locking di workers:**
```python
# Di scribe worker:
async def write_rustdoc(task: dict):
    files = task['files_modified']
    locks_acquired = []

    try:
        # Acquire semua lock dulu sebelum mulai
        for f in files:
            ok = await acquire_file_lock('scribe', f, timeout=30)
            if not ok:
                raise TimeoutError(f"Cannot lock {f} — another worker is editing it")
            locks_acquired.append(f)

        # Baru tulis
        for f in files:
            await add_rustdoc_to_file(f)

    finally:
        # Selalu release — bahkan kalau error
        for f in locks_acquired:
            await release_file_lock('scribe', f)
```

---

## Decision Tree: Worktree vs Lock

```
Task butuh TULIS kode baru atau REFACTOR besar?
  → Git Worktree (coder_*, scribe untuk perubahan besar)

Task hanya ANNOTATE atau APPEND ke file yang sudah ada?
  → File Lock (scribe tambah rustdoc, sentinel tambah comment)

Task READ-ONLY? (review, scan, analisis)
  → Tidak perlu lock atau worktree
  → auditor, sentinel dalam mode scan bisa baca tanpa lock
```

---

## Crash Recovery

Kalau worker crash di tengah task:

```python
async def recover_stale_worktrees():
    """
    Jalankan saat startup — cleanup worktrees dari session yang crash.
    """
    conn = get_ring1_conn()
    stale = conn.execute("""
        SELECT worker_id, task_id, path, branch
        FROM active_worktrees
        WHERE created_at < now() - INTERVAL 24 HOUR
    """).fetchall()

    for row in stale:
        worker_id, task_id, path, branch = row
        print(f"[recovery] cleaning stale worktree: {worker_id}/{task_id}")
        try:
            subprocess.run(["git", "-C", project_path, "worktree", "remove", "--force", path])
            subprocess.run(["git", "-C", project_path, "branch", "-D", branch])
        except Exception as e:
            print(f"[recovery] failed: {e}")
        conn.execute("DELETE FROM active_worktrees WHERE worker_id=? AND task_id=?",
                     [worker_id, task_id])

# Juga cleanup stale locks
async def recover_stale_locks():
    get_ring1_conn().execute("""
        DELETE FROM file_locks WHERE expires_at < now()
    """)
```

Panggil keduanya saat conductor startup (sebelum terima task baru).
