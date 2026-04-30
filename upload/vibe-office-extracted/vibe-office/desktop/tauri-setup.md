# Desktop — Tauri v2 Setup

> **Konteks untuk session baru:**
> Tauri hanya sebagai window host. Semua logic game di webview (Canvas 2D).
> AI communication via WebSocket langsung di webview layer.
> File ini adalah step-by-step dari clone sampai `cargo tauri dev` jalan.

---

## Prerequisites

```bash
# Rust toolchain
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup update stable

# Node.js + pnpm
curl -fsSL https://get.pnpm.io/install.sh | sh
# atau: npm install -g pnpm

# Tauri CLI
cargo install tauri-cli --version "^2.0"

# Verify
cargo tauri --version   # harus 2.x
```

---

## Fase 1 Setup (dari pixel-agents ke vibe-office)

```bash
# 1. Clone pixel-agents sebagai base
git clone https://github.com/pablodelucca/pixel-agents vibe-office
cd vibe-office

# 2. Hapus VS Code extension layer (tidak dibutuhkan)
rm -rf src/                    # VS Code extension source
rm -f .vscodeignore esbuild.js # VS Code build artifacts
# webview-ui/ tetap — ini yang kita pakai

# 3. Install webview dependencies
cd webview-ui && pnpm install && cd ..

# 4. Init Tauri v2 di root project
cargo tauri init
# Jawab prompts:
#   App name: vibe-office
#   Window title: vibe-office
#   Web assets path: ../webview-ui/dist
#   Dev server URL: http://localhost:5173
#   Frontend dev command: pnpm --filter webview-ui dev
#   Frontend build command: pnpm --filter webview-ui build
```

---

## tauri.conf.json

```json
{
  "productName": "vibe-office",
  "version": "0.1.0",
  "identifier": "dev.vibeoffice.app",
  "build": {
    "frontendDist": "../webview-ui/dist",
    "devUrl": "http://localhost:5173",
    "beforeDevCommand": "pnpm --filter webview-ui dev",
    "beforeBuildCommand": "pnpm --filter webview-ui build"
  },
  "app": {
    "windows": [
      {
        "title": "vibe-office",
        "width": 1280,
        "height": 800,
        "minWidth": 1024,
        "minHeight": 600,
        "resizable": true,
        "center": true
      }
    ],
    "security": {
      "csp": "default-src 'self'; connect-src 'self' ws://localhost:8765; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com"
    }
  },
  "plugins": {
    "fs": {
      "all": true,
      "scope": [
        "$HOME/.vibe-office/**",
        "$APPDATA/vibe-office/**"
      ]
    }
  }
}
```

**CSP notes:**
- `ws://localhost:8765` — WebSocket ke Python backend
- `fonts.googleapis.com` + `fonts.gstatic.com` — FectTral Google Fonts
- Kalau pakai SpacetimeDB nanti, tambahkan `ws://localhost:3000`

---

## Ganti vscode API di webview-ui

Pixel-agents pakai `vscode.*` API. Semua harus diganti:

```typescript
// LAMA → BARU (lengkap)

// State persistence
vscode.getState()          →  localStorage.getItem('vibe-office-state')
vscode.setState(data)      →  localStorage.setItem('vibe-office-state', JSON.stringify(data))

// Messaging
vscode.postMessage(msg)    →  ws.send(JSON.stringify(msg))
window.addEventListener('message', h) → ws.onmessage = (e) => h(JSON.parse(e.data))

// Layout save
vscode.postMessage({type:'saveLayout', data})  →  saveLayoutToFile(data)  // via Tauri fs plugin

// Tauri fs untuk save layout ke disk
import { writeTextFile, BaseDirectory } from '@tauri-apps/plugin-fs'

async function saveLayoutToFile(layout: object) {
  await writeTextFile(
    '.vibe-office/layout.json',
    JSON.stringify(layout, null, 2),
    { baseDir: BaseDirectory.Home }
  )
}
```

---

## Pixel-Perfect CSS (wajib Fase 1)

```css
/* webview-ui/src/styles/global.css */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; overflow: hidden; background: #020408; }

canvas {
  image-rendering: pixelated;      /* Chrome, Edge, Opera */
  image-rendering: crisp-edges;   /* Firefox */
  display: block;
}
```

---

## Dev Workflow Harian

```bash
# Terminal 1: Python simulated backend (Fase 1-2)
python3 backend/simulate.py
# → "Simulated backend running on ws://localhost:8765"

# Terminal 2: Tauri dev (hot reload webview)
cargo tauri dev
# → app window buka otomatis
# → edit webview-ui/src/*.ts → auto reload
# → edit src-tauri/src/*.rs → recompile

# Build production (Fase 5+)
cargo tauri build
# → target/release/bundle/ berisi installer
```

---

## Struktur Direktori Final

```
vibe-office/
├── src-tauri/
│   ├── src/
│   │   └── main.rs          ← Tauri entry point (minimal)
│   ├── Cargo.toml
│   └── tauri.conf.json      ← config di atas
├── webview-ui/
│   ├── src/
│   │   ├── main.ts          ← init game
│   │   ├── workerWatcher.ts ← WebSocket (ganti agentWatcher)
│   │   ├── workerManager.ts ← state machine
│   │   ├── tileMap.ts       ← dari pixel-agents
│   │   ├── renderer.ts      ← dari pixel-agents + extend
│   │   ├── gameLoop.ts      ← dari pixel-agents
│   │   ├── overlays/        ← TV, popup, progress bar
│   │   ├── types.ts         ← WebSocket event types
│   │   └── styles/
│   │       └── global.css
│   ├── public/
│   │   └── assets/
│   │       ├── workers/     ← sprite sheets per worker
│   │       └── tiles/       ← tile graphics
│   └── package.json
├── backend/
│   └── simulate.py          ← dummy backend Fase 1-2
└── README.md
```

---

## Troubleshooting

**`cargo tauri dev` gagal dengan "Error: Could not determine the frontend dev server":**
Pastikan `beforeDevCommand` di tauri.conf.json sudah benar dan webview-ui bisa dijalankan mandiri dengan `pnpm dev`.

**WebSocket connect refused:**
Backend Python belum jalan. Jalankan `python3 backend/simulate.py` dulu.

**Fonts FectTral tidak load (CSP error di console):**
Tambahkan `https://fonts.googleapis.com` dan `https://fonts.gstatic.com` ke CSP di tauri.conf.json seperti contoh di atas.

**Canvas blur:**
Pastikan CSS `image-rendering: pixelated` sudah aktif. Cek dengan DevTools → element canvas → computed styles.
