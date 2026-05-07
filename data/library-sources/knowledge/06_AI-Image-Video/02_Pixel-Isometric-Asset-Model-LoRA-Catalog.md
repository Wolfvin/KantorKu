---
title: Pixel & Isometric Asset Model & LoRA Catalog
kategori: AI Image & Video Generation
tags: [pixel-art, isometric, LoRA, FLUX, SDXL, game-assets, HuggingFace, Civitai]
---

# Pixel & Isometric Asset Model & LoRA Catalog

## 🎮 Pixel Isometric Assets — Model & LoRA Terbaik

### Tier 1 — Kombinasi Isometric + Pixel Art (paling relevan)

**`strangerzonehf/Flux-Isometric-3D-LoRA`**
👉 https://huggingface.co/strangerzonehf/Flux-Isometric-3D-LoRA
Base: FLUX.1-dev. Khusus isometric 3D. Ini yang paling dekat sama kebutuhanmu.

**`gokaygokay/Flux-Game-Assets-LoRA-v2`**
👉 https://huggingface.co/gokaygokay/Flux-Game-Assets-LoRA-v2
Trigger word `wbgmsst`, support prompt seperti `isometric dwarf character 3D, white background`. Langsung buat game asset isometric.

**`gokaygokay/Flux-2D-Game-Assets-LoRA`**
👉 https://huggingface.co/gokaygokay/Flux-2D-Game-Assets-LoRA
Trigger word `GRPZA`, contoh prompt: `GRPZA, 3D chest, detailed, white background, game asset, pixel art`. Lisensi Apache 2.0 — bebas komersial.

---

### Tier 2 — Pixel Art FLUX LoRA (general, bisa diarahkan isometric)

**`UmeAiRT/FLUX.1-dev-LoRA-Modern_Pixel_art`**
👉 https://huggingface.co/UmeAiRT/FLUX.1-dev-LoRA-Modern_Pixel_art
Modern pixel art style, clean output.

**Pixel game assets by Dever (Civitai)**
👉 https://civitai.com/models/945266/pixel-game-assets-flux-by-dever
Trigger word `dvr-pixel-flux`, dirancang khusus untuk pixel art game assets.

**Pixel Art & Video Game Graphics LoRA 64Bit**
👉 https://civitai.com/models/816360/pixel-art-and-video-game-graphics-lora
Support keyword `isometric view` langsung di prompt, cocok banget untuk isometric RPG.

---

### Tier 3 — SDXL (lebih ringan, VRAM rendah)

**`nerijs/pixel-art-xl`**
👉 https://huggingface.co/nerijs/pixel-art-xl
Base SDXL, trigger word `pixel`. Butuh cuma 8GB VRAM.

**`imagepipeline/Pixel-Art-XL`**
👉 https://huggingface.co/imagepipeline/Pixel-Art-XL
Tidak butuh trigger keyword, langsung works untuk isometric dan non-isometric.

---

## Rekomendasi Combo Terbaik

Kalau VRAM cukup (12GB+):
> **FLUX.1-dev** + **`Flux-Game-Assets-LoRA-v2`** + **`Flux-Isometric-3D-LoRA`** (stack 2 LoRA sekaligus di ComfyUI)

Kalau VRAM pas-pasan (8GB):
> **SDXL** + **`nerijs/pixel-art-xl`** + prompt `isometric view, pixel art, game asset`

GPU kamu berapa VRAM-nya? Biar bisa kasih setup yang pas.