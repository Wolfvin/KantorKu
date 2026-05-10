# Database Migrations

Folder ini berisi skrip dan panduan untuk inisialisasi database KantorKu dari scratch.

## Cara Init DB dari Scratch

### Ring 1 (DuckDB) — `data/ring1.duckdb`
```bash
cd packages/core
python -c "from kantorku.memory.ring1 import Ring1; Ring1().initialize()"
```

### Ring 2 (SQLite) — `data/ring2.db`
```bash
cd packages/core
python -c "from kantorku.memory.ring2 import Ring2; Ring2().initialize()"
```

### Custom DB (SQLite) — `db/custom.db`
```bash
cd packages/gui
npx prisma migrate dev --name init
```

## Catatan
- File `.db` dan `.duckdb` TIDAK di-commit ke git (ada di `.gitignore`)
- Setiap developer harus menjalankan inisialisasi sendiri setelah clone
- Jika ada perubahan schema, buat migration script baru di folder ini
