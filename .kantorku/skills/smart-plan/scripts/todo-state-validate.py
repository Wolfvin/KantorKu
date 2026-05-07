#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ALLOWED = {"pending", "in_progress", "completed"}


def fail(msg: str, code: int = 2) -> None:
    print(f"status=fail\nreason={msg}")
    sys.exit(code)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate todo state invariants")
    parser.add_argument("--file", required=True, help="Path to JSON todo list")
    args = parser.parse_args()

    p = Path(args.file)
    if not p.exists():
        fail(f"file_not_found:{p}")

    try:
        data = json.loads(p.read_text())
    except Exception as e:
        fail(f"invalid_json:{e}")

    if not isinstance(data, list):
        fail("root_must_be_list")

    in_progress = 0
    completed_without_evidence = []

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            fail(f"item_{i}_must_be_object")

        status = item.get("status")
        if status not in ALLOWED:
            fail(f"item_{i}_invalid_status:{status}")

        if status == "in_progress":
            in_progress += 1

        if status == "completed":
            evidence = item.get("evidence")
            if evidence is None or (isinstance(evidence, str) and evidence.strip() == ""):
                completed_without_evidence.append(i)

    if in_progress > 1:
        fail("multiple_in_progress")

    if completed_without_evidence:
        idx = ",".join(str(i) for i in completed_without_evidence)
        fail(f"completed_without_evidence:{idx}")

    print("status=pass\nin_progress_count=%d" % in_progress)


if __name__ == "__main__":
    main()
