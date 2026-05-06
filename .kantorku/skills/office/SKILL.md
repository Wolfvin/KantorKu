# Office Skill

## Purpose
The **Office** skill provides orchestration, planning, and task management capabilities. It coordinates workers, manages contracts, drafts plans, and ensures structured execution of complex multi-step tasks.

## Capabilities

1. **Plan** — Draft structured execution plans with dependencies and timelines
2. **Execute** — Orchestrate task execution across multiple workers
3. **Verify** — Validate that outputs meet quality criteria and contracts
4. **Brief** — Create and deliver briefings to worker teams via BriefingRoom
5. **Contract** — Create, review, approve, and manage task contracts
6. **Delegate** — Assign tasks to appropriate workers based on specialization
7. **Manage** — Track task progress, handle escalations, and manage priorities

## Output Schema

```json
{
  "skill": "office",
  "action": "plan|execute|verify|brief|contract|delegate|manage",
  "result": {
    "plan_id": "string",
    "contract_id": "string",
    "tasks": [
      {
        "id": "string",
        "worker": "string",
        "action": "string",
        "status": "pending|running|done|failed",
        "dependencies": ["string"],
        "output": {}
      }
    ],
    "status": "draft|approved|executing|completed|failed",
    "cost_estimate": 0.0
  },
  "metadata": {
    "tokens_used": 0,
    "latency_ms": 0,
    "workers_involved": ["string"],
    "provider": "string"
  }
}
```

## Key Rules

1. **Contract before execution** — No task runs without an approved contract
2. **Right worker, right task** — Match tasks to worker specializations
3. **Parallel when possible** — Use DAG resolution to maximize parallelism
4. **Budget awareness** — Estimate costs before execution, track during
5. **Escalation path** — Failed tasks escalate from worker → squad → conductor
6. **Briefing before complex work** — Use BriefingRoom for multi-worker tasks
7. **Verify before delivery** — All outputs pass through verification
8. **Undo/Redo support** — Contract actions are undoable
