# Backend — life_manager Worker (Fase 3)

> **Konteks untuk session baru:**
> life_manager adalah worker baru yang generate "ruleset harian" untuk semua workers.
> Dipanggil SEKALI per session start, atau saat room config berubah.
> Output: `daily_rules.json` — dibaca oleh needs engine di frontend.
> Model: small LLM (Qwen2.5-1.5B via Ollama) — cukup untuk task ini, tidak butuh besar.
> Inspirasi arsitektur: airi (moeru-ai) — "Thinking" dipisah dari "Doing."
> Tidak pakai kode airi — hanya polanya.
> File terkait:
>   - `frontend/needs-system.md` → needs engine yang baca daily_rules.json
>   - `desktop/room-editor.md` → room-config.json yang jadi input life_manager

---

## Posisi di Workers Registry

```
life_manager
  Room:   library_room (unlocked setelah 10 tasks)
  Model:  Qwen2.5-1.5B (Ollama) — BUKAN Qwen2.5-32B
  Badge:  🌱
  Trigger: session_start + room_config_changed
  Output: ~/.vibe-office/daily_rules.json
```

Ini worker yang paling "tenang" — tidak ada di pipeline coding, tidak
di-trigger oleh user task. Berjalan di background, sekali per session.

---

## Input yang Dibaca life_manager

```python
# backend/workers/life_manager.py

def build_life_manager_context(project_path: str) -> dict:
    """
    Kumpulkan semua info yang dibutuhkan untuk generate daily rules.
    """
    return {
        # Dari room editor
        "room_config": load_json("~/.vibe-office/room-config.json"),

        # Dari workers registry
        "workers": [
            {
                "id": w.id,
                "display_name": w.display_name,
                "role": w.role,
                "personality": {
                    "tone": w.personality.tone,
                    "catchphrase": w.personality.catchphrase,
                    "system_prompt_addon": w.personality.system_prompt_addon,
                },
                "stats": {
                    "tasks_done": w.stats.tasks_done,
                    "errors": w.stats.errors,
                    "uptime_hours": w.stats.uptime_hours,
                },
                "home_room": w.home_room,
            }
            for w in load_all_workers()
            if w.status == 'active'
        ],

        # Konteks waktu (opsional — bisa bikin rules musiman)
        "session_time": {
            "hour": datetime.now().hour,
            "day_of_week": datetime.now().strftime("%A"),
            "month": datetime.now().month,
        },

        # Project context ringkas
        "project": {
            "name": get_project_name(project_path),
            "tasks_today": count_tasks_today(),
            "last_error": get_last_error_summary(),
        }
    }
```

---

## Prompt ke LLM

```python
LIFE_MANAGER_SYSTEM = """
You are life_manager. You observe the office — its rooms, furniture, decorations,
and the personalities of every worker. Each morning, you generate behavioral rules
that will guide how workers spend their non-coding time throughout the day.

Rules must be grounded in what actually exists in the office.
If there is no treadmill, do not include 'use_treadmill'.
If the theme is Halloween, workers should prefer darker behaviors.
If a worker has 'formal' tone, they do not 'play_ping_pong' — they 'pace_room'.

Output ONLY valid JSON. No explanations, no preamble.
"""

LIFE_MANAGER_PROMPT = """
Given this office state:

{context_json}

Generate daily behavioral rules for each active worker.
Available decoration behaviors (only include if decoration exists in room_config):
{available_behaviors}

Output format:
{{
  "generated_at": "ISO timestamp",
  "theme_notes": "one sentence describing today's office vibe",
  "workers": {{
    "<worker_id>": {{
      "energy_drain_rate": <0.3–1.0, higher = tires faster>,
      "social_tendency": <0.0–1.0, higher = needs more social>,
      "break_behaviors": ["<behavior1>", "<behavior2>"],
      "food_behaviors": ["<behavior1>"],
      "exercise_behaviors": ["<behavior1>"],
      "idle_animations": ["<anim1>", "<anim2>"],
      "stress_threshold": <0.2–0.7>,
      "sleep_hour": <0–23>,
      "wake_hour": <0–23>,
      "personality_note": "one sentence about how this worker acts today"
    }}
  }}
}}
"""

def generate_daily_rules(project_path: str) -> dict:
    context = build_life_manager_context(project_path)
    available = get_available_behaviors(context['room_config'])

    prompt = LIFE_MANAGER_PROMPT.format(
        context_json=json.dumps(context, indent=2),
        available_behaviors=json.dumps(available, indent=2),
    )

    # Pakai Ollama local — Qwen2.5-1.5B cukup untuk JSON generation
    response = ollama_client.chat(
        model="qwen2.5:1.5b",
        messages=[
            {"role": "system", "content": LIFE_MANAGER_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        options={"temperature": 0.7},  # sedikit random agar rules bervariasi tiap hari
    )

    raw = response['message']['content']

    # Strip markdown fences kalau ada
    clean = raw.strip().removeprefix("```json").removesuffix("```").strip()

    rules = json.loads(clean)

    # Save ke file — dibaca oleh frontend needs engine
    output_path = Path("~/.vibe-office/daily_rules.json").expanduser()
    output_path.write_text(json.dumps(rules, indent=2))

    return rules
```

---

## Behavior Catalog — Apa yang Bisa Di-generate

```python
# Mapping: decoration di room-config.json → behavior yang tersedia

DECORATION_BEHAVIOR_MAP = {
    # Furniture umum (hampir selalu ada)
    "desk":           ["stare_monitor", "type_fast", "lean_back"],
    "chair":          ["sit_idle", "spin_chair"],
    "window":         ["look_out_window", "lean_on_window"],

    # Break room items
    "sofa":           ["sit_at_sofa", "lounge", "nap_sofa"],
    "coffee_machine": ["make_coffee", "drink_coffee", "wait_for_coffee"],
    "dining_table":   ["eat_at_table", "chat_at_table"],
    "vending_machine":["buy_snack", "stare_at_vending"],

    # Aktivitas
    "treadmill":      ["use_treadmill", "stretch_after_run"],
    "ping_pong_table":["play_ping_pong", "watch_ping_pong"],
    "whiteboard":     ["write_whiteboard", "stare_at_whiteboard", "erase_whiteboard"],
    "bookshelf":      ["read_book", "browse_books", "put_back_book"],
    "plant":          ["water_plant", "talk_to_plant"],  # quirky behavior

    # Design studio
    "drawing_tablet": ["sketch_on_tablet", "zoom_in_design"],
    "mood_board":     ["study_mood_board", "pin_to_moodboard"],

    # Theme-based (dari tema ruangan)
    "halloween_deco": ["spooky_idle", "pretend_scared", "carve_pumpkin"],
    "winter_deco":    ["warm_hands", "look_at_snow", "sip_hot_cocoa"],
    "xmas_deco":      ["decorate_tree", "wrap_gift"],
}

def get_available_behaviors(room_config: dict) -> dict:
    """
    Dari room-config.json, extract behaviors yang tersedia.
    Life_manager hanya bisa generate behaviors yang ada di sini.
    """
    available = {"base": ["stretch", "pace_room", "stare_at_nothing", "deep_sigh"]}

    for room in room_config.get("rooms", []):
        for decoration in room.get("decorations", []):
            deco_type = decoration.get("type")
            if deco_type in DECORATION_BEHAVIOR_MAP:
                category = room.get("id", "general")
                if category not in available:
                    available[category] = []
                available[category].extend(DECORATION_BEHAVIOR_MAP[deco_type])

    # Dedup
    for k in available:
        available[k] = list(set(available[k]))

    return available
```

---

## Trigger Lifecycle

```python
# Di backend/main.py

async def on_session_start(project_path: str):
    """Dipanggil saat vibe-office pertama kali dibuka."""
    print("[life_manager] session started — generating daily rules")

    # Notify game UI
    await ws_broadcast({
        "type": "speech_bubble",
        "worker_id": "life_manager",
        "text": "observing office... 🌱",
        "color": "#C3E88D",
        "duration_ms": 3000,
    })

    rules = generate_daily_rules(project_path)

    await ws_broadcast({
        "type": "daily_rules_ready",
        "theme_notes": rules.get("theme_notes", ""),
        "worker_count": len(rules.get("workers", {})),
    })

    await ws_broadcast({
        "type": "speech_bubble",
        "worker_id": "life_manager",
        "text": f"\"{rules.get('theme_notes', 'ready.')}\"",
        "color": "#C3E88D",
        "duration_ms": 4000,
    })


async def on_room_config_changed():
    """
    Dipanggil kalau room-config.json berubah.
    File watcher di desktop/room-editor.md yang trigger ini.
    """
    print("[life_manager] room config changed — regenerating rules")
    generate_daily_rules(get_current_project_path())
    await ws_broadcast({"type": "daily_rules_updated"})
```

---

## Contoh Output daily_rules.json

```json
{
  "generated_at": "2026-03-17T09:00:00",
  "theme_notes": "Spooky Halloween office — workers are restless and energetic tonight.",
  "workers": {
    "coder_rust": {
      "energy_drain_rate": 0.8,
      "social_tendency": 0.2,
      "break_behaviors": ["stare_at_nothing", "pace_room", "look_out_window"],
      "food_behaviors": ["drink_coffee", "buy_snack"],
      "exercise_behaviors": [],
      "idle_animations": ["stretch", "stare_monitor"],
      "stress_threshold": 0.5,
      "sleep_hour": 23,
      "wake_hour": 7,
      "personality_note": "Rusty is in deep focus mode today — minimal social, maximum code."
    },
    "conductor": {
      "energy_drain_rate": 0.4,
      "social_tendency": 0.7,
      "break_behaviors": ["pace_room", "write_whiteboard", "chat_at_table"],
      "food_behaviors": ["drink_coffee", "eat_at_table"],
      "exercise_behaviors": [],
      "idle_animations": ["stare_at_whiteboard", "lean_back"],
      "stress_threshold": 0.6,
      "sleep_hour": 22,
      "wake_hour": 6,
      "personality_note": "The Boss is in meeting mode — expect lots of whiteboard action."
    },
    "steward": {
      "energy_drain_rate": 0.3,
      "social_tendency": 0.5,
      "break_behaviors": ["water_plant", "talk_to_plant", "browse_books"],
      "food_behaviors": ["eat_at_table"],
      "exercise_behaviors": ["use_treadmill"],
      "idle_animations": ["sweep_idle", "organize_papers"],
      "stress_threshold": 0.3,
      "sleep_hour": 21,
      "wake_hour": 6,
      "personality_note": "Steward woke up early and is keeping everything tidy."
    }
  }
}
```

---

## Plugin Identity Card (plugin.json)

```json
{
  "id": "life_manager",
  "display_name": "The Gardener",
  "badge_emoji": "🌱",
  "role": "life_manager",
  "home_room": "library_room",
  "model": "qwen2.5:1.5b",
  "model_provider": "ollama",
  "unlock_after_tasks": 10,
  "trigger": ["session_start", "room_config_changed"],
  "output_file": "~/.vibe-office/daily_rules.json",
  "personality": {
    "tone": "calm",
    "catchphrase": "every office has a rhythm.",
    "idle_phrases": [
      "observing...",
      "the plants need water.",
      "everyone has their own pace.",
      "change is coming."
    ],
    "done_phrases": [
      "rules set. have a good day.",
      "the office knows what to do now.",
      "i've done my part."
    ]
  }
}
```

---

## Checklist Fase 3

```
[ ] life_manager terdaftar di workers registry
[ ] Ollama qwen2.5:1.5b running dan reachable
[ ] build_life_manager_context() kumpulkan semua data tanpa error
[ ] generate_daily_rules() return valid JSON setiap kali
[ ] daily_rules.json tersimpan di ~/.vibe-office/
[ ] on_session_start() dipanggil saat vibe-office buka
[ ] on_room_config_changed() dipanggil saat file watcher detect perubahan
[ ] Frontend needs engine baca daily_rules.json saat startup
[ ] Speech bubble life_manager muncul saat rules selesai di-generate
[ ] theme_notes ditampilkan di narrator atau TV screen sebagai "daily vibe"
```
