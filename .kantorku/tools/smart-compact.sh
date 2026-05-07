#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$CODEX_DIR/.." && pwd)"
MEMORY_DIR="$CODEX_DIR/memory"

mkdir -p "$MEMORY_DIR"

python3 - "$PROJECT_ROOT" "$CODEX_DIR" "$MEMORY_DIR" <<'PY'
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

project_root = Path(sys.argv[1])
codex_dir = Path(sys.argv[2])
memory_dir = Path(sys.argv[3])

memory_index = memory_dir / "memory.md"
backend_topic = memory_dir / "backend.md"
legacy_memory = memory_dir / "MEMORY.md"

home_codex = Path.home() / ".codex"
session_roots = [
    codex_dir / "sessions",
    home_codex / "sessions",
]

def find_latest_session() -> Path | None:
    latest = None
    for root in session_roots:
        if not root.exists():
            continue
        for p in root.rglob("*.jsonl"):
            if latest is None or p.stat().st_mtime > latest.stat().st_mtime:
                latest = p
    return latest

def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def clip(text: str, limit: int = 240) -> str:
    t = normalize_space(text)
    if len(t) <= limit:
        return t
    return t[: limit - 3] + "..."

def classify_topic(text: str) -> str:
    low = text.lower()
    backend_keywords = [
        "backend", "api", "server", "rust", "tauri", "db", "database",
        "sql", "schema", "endpoint", "auth", "migration", "cargo"
    ]
    for k in backend_keywords:
        if k in low:
            return "backend"
    tokens = re.findall(r"[a-z0-9]+", low)
    stop = {"the", "and", "for", "with", "from", "this", "that", "into", "then", "will", "have", "your", "please"}
    for t in tokens:
        if len(t) >= 4 and t not in stop:
            return t[:40]
    return "general"

def parse_recent_messages(session_path: Path):
    user_msgs = []
    assistant_msgs = []
    if not session_path or not session_path.exists():
        return user_msgs, assistant_msgs
    with session_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            p = obj.get("payload", {})
            t = obj.get("type")

            if t == "event_msg" and p.get("type") == "user_message":
                msg = p.get("message", "")
                if msg:
                    user_msgs.append(normalize_space(msg))

            if t == "response_item":
                if p.get("type") == "message":
                    role = p.get("role")
                    content = p.get("content", [])
                    chunks = []
                    for c in content:
                        if c.get("type") in {"input_text", "output_text"}:
                            chunks.append(c.get("text", ""))
                    msg = normalize_space(" ".join(chunks))
                    if role == "user" and msg:
                        user_msgs.append(msg)
                    if role == "assistant" and msg:
                        assistant_msgs.append(msg)

            if t == "event_msg" and p.get("type") == "task_complete":
                lam = p.get("last_agent_message", "")
                if lam:
                    assistant_msgs.append(normalize_space(lam))

    return user_msgs[-8:], assistant_msgs[-8:]

latest_session = find_latest_session()
user_msgs, assistant_msgs = parse_recent_messages(latest_session) if latest_session else ([], [])

latest_user = user_msgs[-1] if user_msgs else "No user message captured from session evidence."
latest_assistant = assistant_msgs[-1] if assistant_msgs else "No assistant message captured from session evidence."

topic = classify_topic(latest_user + " " + latest_assistant)
topic_file = memory_dir / f"{topic}.md"

task_state = "in_progress"
if re.search(r"\b(done|complete|selesai|implemented)\b", latest_assistant.lower()):
    task_state = "done"
if re.search(r"\b(blocked|error|gagal|fail)\b", latest_assistant.lower()):
    task_state = "blocked"

open_loop = clip(latest_user, 200)
decision = clip(latest_assistant, 200)
next_action = f"Continue from topic '{topic}' using compact handoff summary."

symptom = clip(latest_user, 220)
root_cause = "Long thread context can lose critical state during native compaction."
fix_applied = "Smart compact pre-layer writes latest-relevant state and lessons to topic memory files."
reusable_rule = "Before compacting, persist active decisions/open-loops into memory staging files."
confidence = "medium"

fingerprint_raw = f"{topic}|{symptom}|{reusable_rule}"
fingerprint = hashlib.sha1(fingerprint_raw.encode("utf-8")).hexdigest()[:12]
lesson_id = f"{topic}-{fingerprint}"
now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def ensure_file(path: Path, header: str):
    if not path.exists():
        path.write_text(header, encoding="utf-8")

ensure_file(memory_index, "# Memory Index (Smart Compact v1)\n\n")
ensure_file(backend_topic, "# Topic: backend\n\n")
if not topic_file.exists():
    topic_file.write_text(f"# Topic: {topic}\n\n", encoding="utf-8")

if legacy_memory.exists():
    text = legacy_memory.read_text(encoding="utf-8", errors="ignore")
    if "memory_policy: multi-file staging" not in text:
        text = text.replace(
            "memory_policy: single-file only (`.codex/memory/MEMORY.md`).",
            "memory_policy: multi-file staging (`.codex/memory/memory.md` + topic files).",
        )
        legacy_memory.write_text(text, encoding="utf-8")

topic_text = topic_file.read_text(encoding="utf-8", errors="ignore")
lessons_written = 0
if f"lesson_id: {lesson_id}" not in topic_text:
    block = (
        f"## Lesson {lesson_id}\n"
        f"- timestamp: {now}\n"
        f"- lesson_id: {lesson_id}\n"
        f"- symptom: {symptom}\n"
        f"- root_cause: {root_cause}\n"
        f"- fix_applied: {fix_applied}\n"
        f"- reusable_rule: {reusable_rule}\n"
        f"- confidence: {confidence}\n\n"
    )
    topic_file.write_text(topic_text + block, encoding="utf-8")
    lessons_written = 1

index_text = memory_index.read_text(encoding="utf-8", errors="ignore")
index_marker = f"- {topic}: .codex/memory/{topic}.md"
if index_marker not in index_text:
    index_text += f"## Topics\n{index_marker}\n"

index_text += (
    "\n## Latest Compact Handoff\n"
    f"- timestamp: {now}\n"
    f"- source_session: {latest_session if latest_session else 'none'}\n"
    f"- task_state: {task_state}\n"
    f"- open_loop: {open_loop}\n"
    f"- decision: {decision}\n"
    f"- next_action: {next_action}\n"
    f"- lesson_id: {lesson_id}\n"
)
memory_index.write_text(index_text, encoding="utf-8")

result = {
    "task_state": task_state,
    "open_loops": [open_loop],
    "decisions": [decision],
    "next_actions": [next_action],
    "lessons_written": lessons_written,
    "handoff_summary": clip(
        f"Topic={topic}; state={task_state}; lesson_id={lesson_id}; next={next_action}", 220
    ),
}

print(json.dumps(result, ensure_ascii=True, indent=2))
PY
