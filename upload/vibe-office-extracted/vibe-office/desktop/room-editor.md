# Desktop — Room Editor (Aplikasi Terpisah, Fase 2+)

> **Konteks untuk session baru:**
> Room editor adalah Tauri v2 app TERPISAH dari vibe-office.
> Fungsi: user bisa drag & drop dekorasi, set tema (halloween, winter, dll),
> resize ruangan, dan atur layout kantor.
> Output: room-config.json yang dibaca oleh vibe-office + life_manager.
> Komunikasi: file-based (file watcher di vibe-office detect perubahan).
> Tidak ada LLM di dalam room editor — murni UI tool.
> File terkait:
>   - `backend/life-manager.md` → yang consume room-config.json
>   - `frontend/needs-system.md` → behavior unlock berdasarkan dekorasi
>   - `frontend/fsm-rooms.md` → multi-lantai dan room sizing

---

## Filosofi

Room editor adalah "creative sandbox" yang terpisah dari "coding office."
Kamu tidak harus buka room editor setiap hari — cukup saat ingin reorganize.
Saat kamu save di room editor → vibe-office otomatis adapt.

```
USER                    ROOM EDITOR                 VIBE-OFFICE
  |                         |                            |
  |── buka room editor ───→ |                            |
  |── drag sofa ke break  → |                            |
  |── set tema halloween  → |                            |
  |── save ─────────────→  |── tulis room-config.json → |
  |                         |                     file watcher detect
  |                         |                     life_manager regenerate rules
  |                         |                     vibe-office reload rooms
  |                         |                     narrator: "office redecorated 🎃"
```

---

## Room Config Schema

```typescript
// Format file: ~/.vibe-office/room-config.json

interface RoomConfig {
  version: string             // "1.0"
  last_edited: string         // ISO timestamp
  theme: ThemeConfig

  floors: FloorConfig[]       // multi-lantai support
}

interface FloorConfig {
  floor_number: number        // 1, 2, 3, ...
  rooms: RoomLayout[]
}

interface RoomLayout {
  id: string                  // "workstation", "break_room", dll
  display_name: string        // bisa di-rename user
  grid_size: GridSize         // { width: 4, height: 4 } — dalam grid units
  grid_position: { x: number; y: number }  // posisi di floor map
  floor: number

  decorations: Decoration[]
  wall_color: string          // hex
  floor_texture: string       // "wood" | "tile" | "carpet" | "concrete"
  lighting: LightingConfig
  ambient_sound: string       // "office_hum" | "rain" | "wind" | "silence"
}

type GridSize =
  | { width: 1; height: 2 }
  | { width: 2; height: 2 }
  | { width: 2; height: 4 }
  | { width: 4; height: 4 }
  | { width: 4; height: 6 }
  | { width: 6; height: 6 }
  | { width: 6; height: 8 }
  | { width: 8; height: 8 }
  | { width: 8; height: 10 }
  | { width: 10; height: 10 }

interface Decoration {
  type: string                // "sofa" | "coffee_machine" | "treadmill" | dll
  position: { x: number; y: number }  // relatif terhadap room grid
  rotation: 0 | 90 | 180 | 270
  variant: string             // "modern" | "retro" | "minimal" — visual only
  label?: string              // nama custom dari user (opsional)
}

interface ThemeConfig {
  name: string                // "default" | "halloween" | "winter" | "cyberpunk" | dll
  primary_color: string       // hex — warna dominan
  accent_color: string        // hex — warna aksen
  overlay_tint: string        // hex + opacity, e.g. "#FF660022"
  tile_set: string            // nama tile set yang dipakai
}

interface LightingConfig {
  brightness: number          // 0.0–1.0
  color_temperature: "warm" | "cool" | "neutral"
  has_shadow: boolean
}
```

---

## Lantai dan Tangga

```typescript
// Lantai 2 otomatis unlock saat workers > 15 ATAU user manually tambah
// Tangga muncul sebagai tile connector antara lantai

interface StaircaseConfig {
  floor_from: number
  floor_to: number
  position_floor1: { x: number; y: number }  // posisi tangga di lantai 1
  position_floor2: { x: number; y: number }  // posisi tangga di lantai 2
}

// Di room-config.json:
{
  "staircases": [
    {
      "floor_from": 1,
      "floor_to": 2,
      "position_floor1": { "x": 58, "y": 20 },
      "position_floor2": { "x": 2, "y": 2 }
    }
  ]
}
```

**Trigger tangga muncul:**
- Otomatis: `active_workers > 15`
- Manual: user klik "Add Floor 2" di room editor
- Animasi: tangga tile fade in + narrator announce "floor 2 unlocked"

**Lantai 2 — default rooms:**
```
viola rooms yang selama ini "entah di mana":
  ROOFTOP   → unlock 50 tasks — outdoor area, wind ambient
  GARDEN    → unlock 1 project complete — plant tiles, calm music
  LOUNGE    → unlock 100 tasks — casual furniture, sosial area
```

---

## UI Room Editor

```
┌─────────────────────────────────────────────────────────┐
│  VIBE ROOM EDITOR                              [Save] [X]│
├──────────┬──────────────────────────────────────────────┤
│ SIDEBAR  │  CANVAS — Floor 1                            │
│          │  ┌──────┐ ┌──────────┐ ┌──────┐             │
│ Rooms    │  │ CEO  │ │workstat. │ │break │             │
│ ────── ↓ │  │office│ │  4×6    │ │room  │             │
│ CEO off. │  │ 2×2  │ │          │ │ 2×4  │             │
│ Workstat.│  └──────┘ └──────────┘ └──────┘             │
│ Break rm │                                              │
│ ...      │  [+ Add Room]   [Floor 1 ▼] [+ Floor 2]     │
│          │                                              │
│ Decor    │                                              │
│ ────── ↓ │  SELECTED: break_room                        │
│ 🛋 Sofa  │  Size: [2×4 ▼]   Floor: wood ▼             │
│ ☕ Coffee │  Lighting: ████░  Warm ▼                    │
│ 🏃 Tread.│  Wall: [#1E2030 ████]                       │
│ 📋 Board │  Theme: [Halloween 🎃 ▼]                    │
│ 📚 Books │                                              │
│ 🪴 Plant │  Decorations in room:                        │
│          │  🛋 sofa (2,3) · ☕ machine (1,1) · 🪴 (3,3)│
│ Themes   │  [+ Add Decoration]                          │
│ ────── ↓ │                                              │
│ Default  │                                              │
│ 🎃 Hall. │                                              │
│ ❄️ Winter │                                              │
│ 🌌 Cyber │                                              │
└──────────┴──────────────────────────────────────────────┘
```

---

## Tauri App Structure

```
room-editor/                    ← repo/folder terpisah dari vibe-office
├── src-tauri/
│   ├── Cargo.toml
│   └── src/
│       ├── main.rs             ← entry point
│       └── commands.rs         ← read/write room-config.json
├── src/
│   ├── main.tsx
│   ├── components/
│   │   ├── RoomCanvas.tsx      ← drag & drop room layout
│   │   ├── DecorationPanel.tsx ← sidebar dekorasi
│   │   ├── RoomProperties.tsx  ← size, color, lighting, theme
│   │   ├── FloorTabs.tsx       ← switch antar lantai
│   │   └── ThemeSelector.tsx   ← preset themes
│   └── lib/
│       ├── room-config.ts      ← schema + validation
│       └── decoration-map.ts   ← dekorasi → behavior mapping (sync dengan vibe-office)
├── package.json
└── tauri.conf.json
```

**Tauri commands:**
```rust
// src-tauri/src/commands.rs

#[tauri::command]
fn load_room_config() -> Result<String, String> {
    let path = dirs::home_dir().unwrap()
        .join(".vibe-office/room-config.json");
    std::fs::read_to_string(path).map_err(|e| e.to_string())
}

#[tauri::command]
fn save_room_config(config: String) -> Result<(), String> {
    let path = dirs::home_dir().unwrap()
        .join(".vibe-office/room-config.json");
    std::fs::write(path, config).map_err(|e| e.to_string())
    // vibe-office file watcher akan detect perubahan ini otomatis
}

#[tauri::command]
fn get_decoration_catalog() -> Vec<DecorationMeta> {
    // Return list semua dekorasi yang tersedia + preview info
    DECORATION_CATALOG.to_vec()
}
```

---

## Tile Set per Tema

```typescript
// Setiap tema punya tile set berbeda — swap tanpa ubah walkability grid

const THEME_TILE_SETS: Record<string, TileSet> = {
  "default": {
    floor: "floor_office.png",
    wall: "wall_office.png",
    overlay_tint: null,
    ambient: "office_hum",
  },
  "halloween": {
    floor: "floor_dark.png",
    wall: "wall_stone.png",
    overlay_tint: "#FF660015",  // subtle orange tint
    ambient: "wind_spooky",
    special_tiles: ["pumpkin", "cobweb", "candle"],
  },
  "winter": {
    floor: "floor_snow.png",
    wall: "wall_cabin.png",
    overlay_tint: "#8BB8FF10",  // subtle blue tint
    ambient: "snow_wind",
    special_tiles: ["snowflake", "fireplace", "christmas_tree"],
  },
  "cyberpunk": {
    floor: "floor_neon.png",
    wall: "wall_metal.png",
    overlay_tint: "#00FFAA08",  // subtle cyan tint
    ambient: "city_night",
    special_tiles: ["neon_sign", "hologram", "server_rack"],
  },
}
```

---

## Komunikasi dengan vibe-office

```
ROOM EDITOR                          VIBE-OFFICE
    |                                     |
    | save room-config.json               |
    |─────────────────────────────────→  |
    |                         file watcher (Tauri watchdog)
    |                                     |
    |                         on_room_config_changed()
    |                                     |
    |                         life_manager regenerate rules
    |                                     |
    |                         ws_broadcast("daily_rules_updated")
    |                                     |
    |                         frontend reload room tiles + decorations
    |                                     |
    |                         narrator: "office updated. life_manager is observing... 🌱"
```

**File watcher setup di vibe-office (Tauri):**
```rust
// src-tauri/src/main.rs

use notify::{Watcher, RecursiveMode, watcher};
use std::sync::mpsc::channel;
use std::time::Duration;

fn watch_room_config(app_handle: tauri::AppHandle) {
    let config_path = dirs::home_dir().unwrap()
        .join(".vibe-office/room-config.json");

    let (tx, rx) = channel();
    let mut watcher = watcher(tx, Duration::from_secs(1)).unwrap();
    watcher.watch(&config_path, RecursiveMode::NonRecursive).unwrap();

    std::thread::spawn(move || {
        loop {
            match rx.recv() {
                Ok(_) => {
                    app_handle.emit_all("room_config_changed", ()).unwrap();
                }
                Err(e) => println!("watch error: {:?}", e),
            }
        }
    });
}
```

---

## Settings — Audio & Room dari Satu Panel

```typescript
// Semua settings terkait room + audio ada di satu panel
// Lihat ux/settings-panel.md untuk panel lengkap

interface RoomSettings {
  // Audio per room (tidak hardcode)
  ambient_volume: number        // 0.0–1.0, default 0.3
  ambient_enabled: boolean

  // Needs visibility
  needs_bar_visible: boolean    // default true, kalau false tetap ada di popup

  // Layout
  show_room_labels: boolean     // tampilkan nama ruangan di tile
  show_worker_names: boolean    // nama di atas kepala worker
}
```

---

## Checklist Fase 2 (Room Editor MVP)

```
[ ] room-editor sebagai Tauri project terpisah berhasil di-build
[ ] load_room_config() dan save_room_config() Tauri commands berjalan
[ ] RoomCanvas: tampilkan rooms dari room-config.json
[ ] RoomProperties: ubah ukuran room (10 size options)
[ ] DecorationPanel: drag decoration ke room (5 dekorasi MVP: sofa, coffee, whiteboard, plant, window)
[ ] ThemeSelector: default + halloween + winter (tile set swap)
[ ] Save → tulis room-config.json ke ~/.vibe-office/
[ ] File watcher di vibe-office detect perubahan dan emit event

Fase 3:
[ ] Semua dekorasi dari DECORATION_CATALOG diimplementasikan
[ ] Multi-lantai: Floor 2 bisa ditambahkan, tangga auto-appear
[ ] Preview animasi karakter dengan dekorasi (mockup, bukan real sprite)

Fase 5:
[ ] Real sprite preview di room editor
[ ] Custom tile set upload
[ ] Share room config (export/import file)
```
