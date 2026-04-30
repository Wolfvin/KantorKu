# Design — FectTral Design System Integration

> **Konteks untuk session baru:**
> Wolfvin sudah punya design system lengkap bernama FectTral — cyberpunk/sci-fi UI
> dengan dark void background, electric blue neon, animasi starfield, perspective grid.
> File asli ada di FectTral.rar yang sudah diekstrak dan dianalisis session 2026-03-17.
> Keputusan: Design Library Pipeline diintegrasikan PENUH ke vibe-office sebagai
> satu sistem terpadu, bukan terpisah.
> FectTral bukan hanya "design studio" — ini adalah visual identity SELURUH vibe-office
> untuk semua overlay, CEO office, brain visualization, dan monitor design studio.

---

## FectTral = Visual Identity Vibe-Office

Dua layer visual yang berbeda tapi terhubung:

```
LAYER 1 — PIXEL ART KANTOR (game world)
  Karakter workers berjalan di kantor 16px top-down
  Tile-based rooms, sprite animations
  Ini adalah "dunia" vibe-office

LAYER 2 — FECTRAL UI (overlays + studio)
  Semua overlay dan panel yang tampil DI ATAS pixel art
  CEO office papers → FectTral card style
  Status popup → FectTral card style  
  TV screen content → FectTral terminal/dashboard
  Brain visualization → FectTral DNA Report style
  Design Studio Room → full FectTral takeover

  Transisi: pixel art → klik monitor di design studio
  → seamless zoom in → full FectTral UI mengisi layar
```

Ini bukan dua sistem terpisah. FectTral adalah "skin" untuk semua UI yang
bukan pixel art. Kalau ada overlay, panel, atau monitor dalam game → FectTral.

---

## FectTral Design Tokens (Wajib Konsisten di Semua UI)

```css
:root {
  /* Backgrounds */
  --bg-void:       #020408;   /* halaman, deepest space */
  --bg-deep:       #050912;   /* secondary depth */
  --bg-panel:      #0a1428;   /* sidebar, panel surfaces */
  --bg-card:       #0d1a32;   /* card, widget backgrounds */

  /* Blue accent */
  --blue-core:     #00aaff;   /* primary neon */
  --blue-bright:   #00d4ff;   /* highlight, active */
  --blue-electric: #0066ff;   /* deep electric */
  --blue-dim:      #003a8c;   /* muted, inactive */

  /* Glow */
  --glow-sm:   0 0 8px rgba(0,170,255,0.4);
  --glow-md:   0 0 16px rgba(0,170,255,0.5), 0 0 32px rgba(0,102,255,0.2);
  --glow-text: 0 0 10px rgba(0,212,255,0.8), 0 0 20px rgba(0,170,255,0.4);

  /* Borders */
  --border-dim:    rgba(0,140,255,0.10);
  --border-mid:    rgba(0,170,255,0.22);

  /* Text */
  --text-primary:  #e8f4ff;
  --text-secondary:#8ab8d8;
  --text-muted:    #3a5a78;

  /* Typography */
  --font-display: 'Orbitron', monospace;    /* headings, logo, worker names */
  --font-body:    'Exo 2', sans-serif;      /* body text, descriptions */
  --font-mono:    'JetBrains Mono', monospace; /* terminal, code, task IDs */

  /* Layout */
  --sidebar-w: 220px;
  --topbar-h:  48px;
}
```

Google Fonts import (wajib di semua FectTral pages):
```html
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;900&family=Exo+2:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

---

## FectTral Page Templates yang Tersedia

File lengkap ada di `boilerplate.md` dan `SKILL-v3.md` dari FectTral.rar.
Yang paling relevan untuk vibe-office:

**Template 5B — Split Panel Tool** → Design Studio input/output panel
**Template 5C — Review Queue / Focus Card** → stylist review queue (approve/reject elemen)
**Template 5D — Data / Analytics / Report** → Brain visualization, DNA Report

Background layers yang selalu ada:
```html
<div class="bg-root">
  <div class="bg-space"></div>      <!-- radial gradient deep space -->
  <div class="bg-grid"></div>       <!-- animated dot grid -->
  <div class="bg-floor"></div>      <!-- perspective grid floor -->
  <div class="orb orb-1"></div>     <!-- blue glow orb top-left -->
  <div class="orb orb-2"></div>     <!-- blue glow orb bottom-right -->
  <canvas id="starCanvas"></canvas> <!-- 220 animated stars -->
  <div class="data-stream"></div>   <!-- falling data streams -->
  <div class="scan-beam"></div>     <!-- horizontal scan line -->
  <div class="scanlines"></div>     <!-- CRT scanlines overlay -->
  <div class="vignette"></div>      <!-- edge darkening -->
</div>
```

---

## Transisi Pixel Art → FectTral UI

Ketika player masuk design studio dan klik monitor:

```typescript
// Canvas game layer
function enterDesignStudio() {
  const monitor = getMonitorTilePosition()
  
  // 1. Zoom in ke monitor (CSS transform pada canvas)
  canvas.style.transition = 'transform 400ms cubic-bezier(0.4,0,0.2,1)'
  canvas.style.transform = `scale(8) translate(-${monitor.x}px, -${monitor.y}px)`
  
  // 2. Setelah zoom selesai (400ms), fade in FectTral overlay
  setTimeout(() => {
    const overlay = document.getElementById('fectral-overlay')
    overlay.style.opacity = '0'
    overlay.style.display = 'flex'
    overlay.style.transition = 'opacity 200ms ease'
    requestAnimationFrame(() => overlay.style.opacity = '1')
  }, 380)
}

function exitDesignStudio() {
  const overlay = document.getElementById('fectral-overlay')
  overlay.style.opacity = '0'
  setTimeout(() => {
    overlay.style.display = 'none'
    canvas.style.transition = 'transform 300ms ease-out'
    canvas.style.transform = 'scale(1) translate(0,0)'
  }, 200)
}
```

Di pixel art: monitor di design studio punya animasi "glowing screen" (tile
berkedip biru lemah) saat idle. Saat player mendekati → glow lebih terang.

---

## File Referensi FectTral (dari FectTral.rar)

Semua file ini perlu disimpan di project vibe-office:
```
frontend/fectral/
├── SKILL-v3.md          ← skill AI untuk generate FectTral UI (Claude pakai ini)
├── boilerplate.md       ← full HTML shell yang langsung bisa dipakai
├── components.md        ← semua komponen: buttons, badges, forms, cards
└── design-tools/        ← MCP server TypeScript
    ├── index.ts         ← entry point, tool registrations
    ├── database.ts      ← SQLite schema + helpers
    ├── claude-generator.ts ← generate design dari Claude knowledge
    └── web-extractor.ts ← fetch URL → ekstrak CSS/animasi
```
