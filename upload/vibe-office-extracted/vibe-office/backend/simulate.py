#!/usr/bin/env python3
"""
Simulated Backend — Fase 1-2
Emit WebSocket events ke game UI tanpa AI backend.
Pakai ini untuk test game layer sebelum AI siap.

Jalankan: python3 backend/simulate.py
"""

import asyncio
import websockets
import json
import random
import time

# Semua workers dengan naming v4.x
WORKERS = [
    {"id": "conductor",   "badge": "👔", "room": "ceo_office"},
    {"id": "coder_rust",  "badge": "🦀", "room": "workstation"},
    {"id": "coder_css",   "badge": "🎨", "room": "workstation"},
    {"id": "coder_js",    "badge": "⚡", "room": "workstation"},
    {"id": "coder_python","badge": "🐍", "room": "workstation"},
    {"id": "tester",      "badge": "🧪", "room": "workstation"},
    {"id": "auditor",     "badge": "🔍", "room": "workstation"},
    {"id": "scribe",      "badge": "📝", "room": "workstation"},
    {"id": "sentinel",    "badge": "🛡️", "room": "server_room"},
    {"id": "chronicler",  "badge": "📚", "room": "server_room"},
    {"id": "scout",       "badge": "🔭", "room": "server_room"},
    {"id": "curator",     "badge": "🗂️", "room": "library_room"},
    {"id": "trainer",     "badge": "🧠", "room": "lab_room"},
    {"id": "steward",     "badge": "🧹", "room": "break_room"},
    {"id": "designer",    "badge": "🖌️", "room": "design_studio"},
    {"id": "archivist",   "badge": "🌐", "room": "design_studio"},
    {"id": "stylist",     "badge": "✨", "room": "design_studio"},
    {"id": "compositor",  "badge": "⚙️", "room": "design_studio"},
    {"id": "intake",      "badge": "📥", "room": "break_room"},
    {"id": "bridge",      "badge": "🌉", "room": "break_room"},
    {"id": "narrator",    "badge": "📺", "room": "meeting_room"},
]

STATES = ['idle', 'working', 'meeting', 'reviewing', 'resting', 'blocked', 'done']
ROOMS  = ['meeting_room', 'workstation', 'break_room', 'dormitory',
          'server_room', 'ceo_office', 'design_studio']

CATCHPHRASES = {
    "conductor":    "execution is everything.",
    "coder_rust":   "borrow checker says no.",
    "coder_css":    "pixels don't lie.",
    "coder_js":     "event loop never sleeps.",
    "coder_python": "one more lambda...",
    "tester":       "tests don't lie.",
    "auditor":      "the code speaks for itself.",
    "scout":        "reconnaissance complete.",
    "curator":      "knowledge is structured.",
    "trainer":      "updating weights...",
    "steward":      "cleaning in progress.",
    "designer":     "form follows function.",
}

connected_clients: set = set()

async def handler(websocket):
    connected_clients.add(websocket)
    print(f"[sim] client connected. total: {len(connected_clients)}")

    # Spawn semua workers saat koneksi pertama
    for w in WORKERS:
        await websocket.send(json.dumps({
            "type": "hire",
            "worker_profile": {
                "id": w["id"],
                "display_name": w["id"].replace("_", " ").title(),
                "badge_emoji": w["badge"],
                "state": "idle",
                "room": w["room"],
            }
        }))
        await asyncio.sleep(0.05)

    try:
        async for msg in websocket:
            # Terima tapi tidak proses — ini simulated
            data = json.loads(msg)
            print(f"[sim] from client: {data.get('type')}")
    except websockets.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"[sim] client disconnected. total: {len(connected_clients)}")

async def broadcast(event: dict):
    if not connected_clients:
        return
    msg = json.dumps(event)
    await asyncio.gather(*[ws.send(msg) for ws in connected_clients], return_exceptions=True)

async def simulation_loop():
    """Emit random realistic events terus-menerus."""
    task_id = 0

    while True:
        await asyncio.sleep(random.uniform(1.5, 4.0))
        if not connected_clients:
            continue

        worker = random.choice(WORKERS)
        wid = worker["id"]
        event_type = random.choices(
            ['state_change', 'progress', 'speech_bubble', 'tv_update'],
            weights=[40, 30, 20, 10]
        )[0]

        if event_type == 'state_change':
            new_state = random.choice(STATES)
            await broadcast({
                "type": "state_change",
                "worker_id": wid,
                "new_state": new_state,
                "timestamp": time.strftime("%H:%M")
            })
            # Kalau working, juga move ke workstation
            if new_state == 'working':
                await broadcast({
                    "type": "move_to_room",
                    "worker_id": wid,
                    "target_room": "workstation",
                    "reason": "task_assigned"
                })

        elif event_type == 'progress':
            await broadcast({
                "type": "progress",
                "worker_id": wid,
                "progress": random.random(),
                "message": random.choice([
                    "writing...", "compiling...", "testing...",
                    "reviewing...", "indexing...", "analyzing..."
                ])
            })

        elif event_type == 'speech_bubble':
            text = CATCHPHRASES.get(wid, "...") if random.random() > 0.5 \
                   else random.choice(["done ✓", "on it.", "checking...", "hmm."])
            await broadcast({
                "type": "speech_bubble",
                "worker_id": wid,
                "text": text,
                "color": "#00aaff",
                "duration_ms": 2500
            })

        elif event_type == 'tv_update':
            task_id += 1
            await broadcast({
                "type": "tv_update",
                "current_task": f"[TASK-{task_id:04d}] simulated task",
                "worker_statuses": [
                    {"id": w["id"], "state": random.choice(STATES)}
                    for w in random.sample(WORKERS, 3)
                ],
                "new_log": {
                    "time": time.strftime("%H:%M"),
                    "text": f"[{wid}] simulated action #{task_id}"
                }
            })

async def main():
    print("[sim] vibe-office simulated backend")
    print("[sim] WebSocket server: ws://localhost:8765")
    print("[sim] Press Ctrl+C to stop\n")

    server = await websockets.serve(handler, "localhost", 8765)
    await asyncio.gather(server.wait_closed(), simulation_loop())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[sim] stopped.")
