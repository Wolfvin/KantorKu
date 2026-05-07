# Smart Plan Examples

## Example 1: New OCR feature

Prompt:
```text
/smart-plan Tambah endpoint OCR untuk scan faktur
```

Expected structure:
- THINK block (assumptions, ambiguities, tradeoffs, pushback)
- EPIC: OCR Faktur
- STORY: Setup backend OCR
- STORY: Integrasi frontend
- TASK list with verify step for each task

## Example 2: Mid-size product feature

Prompt:
```text
/smart-plan Implementasi needs system untuk AI workers
```

Expected structure:
- EPIC: AI Worker Needs
- STORY: Core state + decay logic
- STORY: Visual feedback
- TASK per story with measurable verification

## Example 3: Architecture exploration

Prompt:
```text
/smart-plan Design storage layer untuk DAG nodes
```

Expected structure:
- TRADEOFFS section comparing at least 2 storage options
- PUSHBACK if MVP scope can be simplified
- Phased implementation plan with tests
