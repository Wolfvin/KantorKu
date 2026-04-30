# Assets — Sprite Pipeline

Semua tools gratis dan open source.

## Workflow

```
Deskripsi / sketch referensi
  ↓
[1] SD_PixelArt_SpriteSheet_Generator  ← AI generate
  ↓
[2] proper-pixel-art                   ← clean up noise
  ↓
[3] Pixelorama                         ← edit + export
  ↓
webview-ui/public/assets/characters/
```

---

## [1] Generate dengan AI

**Repo:** Onodofthenorth/SD_PixelArt_SpriteSheet_Generator (HuggingFace)
Atau via pixel-sprite-lab: https://github.com/pixel-sprite-lab/pixel-sprite-lab

```python
from diffusers import StableDiffusionPipeline
import torch

pipe = StableDiffusionPipeline.from_pretrained(
    "Onodofthenorth/SD_PixelArt_SpriteSheet_Generator",
    torch_dtype=torch.float16
).to("cuda")  # atau "cpu" (lambat)

def gen(worker_name: str, desc: str):
    image = pipe(
        prompt=f"pixel art sprite sheet, {desc}, top-down view, 4 directions, "
               f"16x16 pixels per frame, 4 frames per direction, white background, "
               f"retro RPG style, clean edges, no anti-aliasing",
        negative_prompt="blurry, high resolution, realistic, 3d, shadow, gradient",
        width=512, height=512, num_inference_steps=30, guidance_scale=7.5,
    ).images[0]
    image.save(f"output/{worker_name}_raw.png")
```

**Prompt per worker:**
```
orchestrator   → "CEO in suit, confident posture, holding tablet"
coder_rust    → "programmer in dark hoodie, round glasses, messy hair"
tester        → "QA engineer with clipboard, checkmark badge on shirt"
auditor       → "code reviewer with magnifying glass, serious expression"
scribe        → "technical writer, pen behind ear, open notebook"
sentinel      → "security engineer, dark clothes, lock icon on badge"
chronicler    → "version control bot, hard hat, merge tool in hand"
scout         → "researcher, many monitors, data cable accessories"
intake → "interpreter, headset, speech bubble icon"
bridge → "router bot, antenna on head, cable connections"
narrator → "presenter, microphone, clean interface"
```

---

## [2] Clean Up — proper-pixel-art

https://github.com/nicholasgasior/proper-pixel-art

```bash
python main.py --input output/coder_rust_raw.png \
               --output output/coder_rust_clean.png \
               --pixel-size 16 --palette-size 16
```

---

## [3] Edit & Export — Pixelorama

https://github.com/Orama-Interactive/Pixelorama (MIT, gratis)

Sprite sheet format yang kompatibel dengan pixel-agents:
```
256×64px per worker
Row 0: walk_down  (4 frames)
Row 1: walk_left  (4 frames)
Row 2: walk_right (4 frames)
Row 3: walk_up    (4 frames)
Row 4: typing     (4 frames) ← tambahan vibe-office
Row 5: reading    (4 frames)
Row 6: sleeping   (2 frames)
```

Export: File → Export Sprite Sheet → PNG + JSON, 4 cols × 7 rows.

**Tips:** Mulai dari orchestrator/CEO dulu — paling distinctive,
jadi reference point untuk karakter lainnya.
