from __future__ import annotations

import sqlite3
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = APP_ROOT / "data" / "arch_engine.db"
SCHEMA_PATH = APP_ROOT / "schema.sql"
MIGRATIONS_PATH = APP_ROOT / "migrations"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_migration_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )


def migrate_db(db_path: Path | None = None) -> Path:
    path = db_path or DB_PATH
    migration_files = sorted(MIGRATIONS_PATH.glob("*.sql"))

    with get_connection(path) as conn:
        _ensure_migration_table(conn)
        applied = {
            row["name"]
            for row in conn.execute("SELECT name FROM schema_migrations").fetchall()
        }

        for migration_file in migration_files:
            name = migration_file.name
            if name in applied:
                continue

            sql = migration_file.read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_migrations (name) VALUES (?)", (name,))

        conn.commit()

    return path


def init_db(db_path: Path | None = None) -> Path:
    # Keep init_db as public entrypoint, now backed by incremental migration runner.
    return migrate_db(db_path)
