# GenericAgent Extract (High-Signal)

Source: `lsdefine/GenericAgent` (README + GETTING_STARTED + agent_loop + llmcore + memory SOP + skill_search engine)

## Reusable Patterns
- Minimal core loop + atomic tools is enough for strong autonomy when memory is layered and disciplined.
- `No Execution, No Memory`: only action-verified facts enter memory.
- Layered memory works best with strict pointer density:
  - top layer stays short as routing index,
  - detailed SOP/scripts stay in lower layers.
- Context compression should be periodic and policy-driven, not only at hard token limit.
- Tool output streaming and structured step outcomes improve debuggability and reduce blind spots.
- Compatibility abstraction (provider/session routing by config naming) reduces multi-model integration complexity.

## Anti-Patterns to Avoid
- Storing volatile runtime state in long-term memory.
- Writing memory from inference or plan text without tool-backed evidence.
- Overgrown top-level memory/index with detailed instructions.
- Large one-shot patches without short verification loop.

## Mapping to This Workspace
- `evolve`: enforce action-verified memory write + minimal atomic change + layered memory discipline + compression cadence.
- `memory/MEMORY.md`: store durable governance lessons only.
- `arch-engine`: keep DB source-of-truth, retrieval lane incremental, and evidence-first update policy.

## Suggested Next Micro-Cycles
1. Add explicit compression cadence metric into token/evolve verification.
2. Add evidence annotation in evolve report output (`tool_evidence_count`).
3. Add memory-layer pointer lint check (L1-size style equivalent for current memory conventions).
