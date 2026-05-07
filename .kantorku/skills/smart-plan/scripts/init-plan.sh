#!/usr/bin/env bash
set -euo pipefail

TASK_NAME="${1:-Unnamed Task}"
DATE="$(date '+%Y-%m-%d %H:%M')"

cat > task_plan.md <<EOF
# Plan: ${TASK_NAME}
Created: ${DATE}
Status: IN_PROGRESS

## Goal
[Tulis hasil akhir yang terlihat jika task sukses]

## Success Criteria
- [ ] [Kriteria terukur 1]
- [ ] [Kriteria terukur 2]

## Phases
### Phase 1: [Nama phase]
- [ ] TASK: [Deskripsi task] -> verify: [Cara cek]

### Phase 2: [Nama phase]
- [ ] TASK: [Deskripsi task] -> verify: [Cara cek]

## Blockers and Decisions
| Issue | Decision | Reason |
|-------|----------|--------|
|       |          |        |
EOF

cat > findings.md <<EOF
# Findings: ${TASK_NAME}
Created: ${DATE}

## Technical Decisions
- [Decision] -> [Reason]

## Research Notes
- [Fakta penting / referensi]

## Known Gotchas
- [Potensi masalah dan mitigasi]
EOF

cat > progress.md <<EOF
# Progress Log: ${TASK_NAME}

## Session ${DATE}
- Start: [Konteks awal]

## Error Log
| Error | Fix | Timestamp |
|-------|-----|-----------|

## Test Results
| Test | Status | Notes |
|------|--------|-------|
EOF

echo "Initialized smart-plan files for: ${TASK_NAME}"
