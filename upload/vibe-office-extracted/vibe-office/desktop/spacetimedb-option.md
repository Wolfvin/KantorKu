# Desktop — SpacetimeDB (Alternatif Arsitektur)

> **Konteks untuk session baru:**
> File ini mendokumentasikan SpacetimeDB (github.com/clockworklabs/SpacetimeDB,
> BSL 1.1, 22.6k stars) sebagai OPSI ALTERNATIF untuk arsitektur game layer.
> Ini BUKAN rencana implementasi saat ini — arsitektur default tetap:
> Python backend → WebSocket → Canvas game.
> SpacetimeDB adalah pivot besar yang perlu pertimbangan matang sebelum Fase 3.
> Dievaluasi session 2026-03-16.

---

## Apa itu SpacetimeDB

Database yang sekaligus server. Application logic di-upload langsung ke dalam
database sebagai "module" (Rust/C#/TypeScript). Client connect langsung ke
database, tidak ada server di antaranya.

```
ARSITEKTUR BIASA:
Client → Web Server → Database
            ↑ kamu harus maintain ini

ARSITEKTUR SpacetimeDB:
Client → SpacetimeDB (database = server)
           kamu hanya tulis module
```

Seluruh backend MMORPG BitCraft Online — chat, items, terrain, posisi player
ribuan user — dijalankan sebagai satu SpacetimeDB module.

**Quick Start:**
```bash
# Install
curl -sSf https://install.spacetimedb.com | sh

# Login
spacetime login

# Dev (auto-publish ke cloud saat save)
spacetime dev --template chat-react-ts

# Atau self-host via Docker
docker run --rm -p 3000:3000 clockworklabs/spacetimedb start
```

---

## Kenapa Menarik untuk Vibe-Office

Masalah arsitektur saat ini:
```
Python backend emit WebSocket event → Canvas game terima → update state
```

Setiap state change butuh: Python emit → WebSocket → JS parse → game update.
Schema harus dijaga konsisten di kedua sisi (backend Python + frontend TS).
Kalau ada bug sinkronisasi, susah debug.

Dengan SpacetimeDB:
```
Python AI backend call reducer → SpacetimeDB update table → Canvas game auto-sync
```

State workers (posisi, FSM, task progress) di-define sebagai SpacetimeDB tables.
Game UI subscribe ke tables dan otomatis dapat update tanpa manual WebSocket handling.

---

## Contoh Konkret: Worker State Sync

**Module (Rust, di-upload ke SpacetimeDB):**
```rust
use spacetimedb::{spacetimedb, Identity, ReducerContext};

// Table: state semua workers
#[spacetimedb::table(accessor = worker_states, public)]
pub struct WorkerState {
    #[primary_key]
    worker_id: String,
    fsm_state: String,       // idle|working|meeting|reviewing|resting|blocked|done
    current_task: String,
    room: String,
    progress: f32,
    last_updated: u64,
}

// Reducer: Python backend panggil ini saat worker pindah state
#[spacetimedb::reducer]
pub fn update_worker_state(
    ctx: &ReducerContext,
    worker_id: String,
    new_state: String,
    room: String,
    progress: f32,
) {
    ctx.db.worker_states().worker_id().update(WorkerState {
        worker_id,
        fsm_state: new_state,
        room,
        progress,
        ..
    });
}
```

**Python AI backend:**
```python
from spacetimedb_sdk import SpacetimeDBClient

client = SpacetimeDBClient("ws://localhost:3000", "vibe-office-db")
await client.connect()

# Panggil reducer saat worker state berubah
await client.call_reducer("update_worker_state", {
    "worker_id": "coder_rust",
    "new_state": "working",
    "room": "workstation",
    "progress": 0.3
})
```

**Game UI (TypeScript):**
```typescript
import { useTable } from '@clockworklabs/spacetimedb-sdk'

// Subscribe ke table — auto-update tanpa WebSocket manual
const [workerStates] = useTable(tables.worker_state)

// workerStates otomatis terupdate saat backend panggil reducer
// Tidak perlu: ws.onmessage, JSON.parse, state management manual
```

---

## Perbandingan vs Arsitektur Default

| Aspek | WebSocket Default | SpacetimeDB |
|-------|-------------------|-------------|
| Kompleksitas setup | Sedang (Python + WS schema) | Lebih tinggi (Rust module) |
| State sync | Manual (schema di 2 tempat) | Otomatis (single source of truth) |
| Debugging | Susah (WS event trace) | Mudah (query tables langsung) |
| Latency | Low | Very low (in-memory DB) |
| Untuk game multiplayer | Bisa | Didesain untuk ini |
| License | Bebas | BSL 1.1 (bukan full open source) |
| Learning curve | Rendah (sudah tahu WS) | Tinggi (Rust module, SpacetimeDB concepts) |
| Fase implementasi | Fase 1 (langsung) | Butuh spike/PoC dulu |

---

## Warning: License BSL 1.1

SpacetimeDB pakai **Business Source License 1.1** — bukan MIT/Apache.

Artinya:
- Gratis untuk personal/non-commercial use
- Bisnis tidak boleh pakai untuk competing service
- Otomatis jadi AGPL setelah beberapa tahun (dengan linking exception)

Untuk vibe-office (personal project) → tidak masalah.
Kalau suatu saat vibe-office di-commercialize → perlu review ulang lisensi.

---

## Recommendation

**Jangan ganti arsitektur sekarang.** Arsitektur WebSocket yang ada sudah cukup
untuk Fase 1-3. SpacetimeDB adalah pivot besar yang perlu PoC.

**Kalau mau experiment:** Buat mini PoC di Fase 2 — satu room saja (break room)
pakai SpacetimeDB untuk sync worker positions. Kalau smooth, pertimbangkan migrate
untuk Fase 3. Kalau tidak, lanjut WebSocket default.

**Referensi untuk PoC:**
```bash
git clone https://github.com/clockworklabs/SpacetimeDB
# Lihat: modules/ folder untuk contoh game modules
# Lihat: sdks/typescript/ untuk client SDK
# Demo: demo/Blackholio/ — multiplayer game demo
```
