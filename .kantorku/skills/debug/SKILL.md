# Debug Skill (Unified)

## Purpose
The **Debug** skill provides a unified troubleshooting and verification workflow. It combines systematic root cause analysis with evidence-first iteration for both frontend (UI/JS) and backend (API/runtime) issues. Every conclusion must cite trace, log, or code evidence.

## Trigger
- User reports a bug, error, or regression
- Need to validate patch results evidence-first
- User asks to fix, debug, trace, diagnose, or reproduce an issue
- Verification needed after plan completion

## Capabilities

1. **Fix** — Apply patches or suggest fixes for identified issues
2. **Debug** — Step through code execution paths to identify problems
3. **Error** — Parse, categorize, and explain error messages and stack traces
4. **Trace** — Follow execution flow through distributed traces and spans
5. **Diagnose** — Perform systematic diagnosis of symptoms to identify root causes
6. **Reproduce** — Create minimal reproduction cases for reported issues
7. **Verify** — Validate that a fix resolves the issue with concrete signal
8. **Check** — Run evidence-first validation on frontend and backend

## Plan Mode Audit Gate
- If user invokes `[$debug] [$review] mode plan`, MUST create a markdown audit file before technical work
- Technical work = before reproduce, edit file, run test/build, or execute debug command
- Audit file location: root workspace (cwd at execution time)
- Audit file name: `AUDIT_PLAN__YYYY-MM-DD__<topic-slug>.md`
- Minimum audit contents:
  - Context & objective
  - Scope in/out
  - Assumptions
  - Planned verification steps
  - Initial risks
  - Start timestamp
- If audit file doesn't exist, process must stop at preparation step (don't continue to debug loop)

## Debug Loop (Evidence-First Iteration)

1. **Reproduce minimal** — Create smallest possible reproduction
2. **Isolate suspect layer** — UI / API / runtime / config / state
3. **Apply smallest fix** — Minimal change that could resolve
4. **Verify with concrete signal** — Log / test / UI behavior confirms fix
5. **Repeat until pass** — Continue if not resolved

## Stagnation Gate
- If 2 loop iterations don't change the symptom → mark `stagnation=active`
- During stagnation: change only 1 variable per subsequent iteration
- Restart process only if health check fails and no meaningful output passes silence window
- If still stagnant after 2 additional iterations → stop and escalate with evidence

## Key Rules

1. **Reproduce first** — Always attempt to reproduce before diagnosing
2. **Evidence-based** — Every conclusion must cite trace, log, or code evidence
3. **Minimal fix** — Prefer the smallest change that resolves the issue
4. **No side effects** — Debug operations must not alter production state
5. **Severity assessment** — Classify severity before proposing fixes (`critical|high|medium|low|info`)
6. **Circuit breaker aware** — Check if the issue is related to provider outage
7. **Check memory first** — Search MEMORY.md and past issues for known patterns
8. **Escalate uncertain fixes** — If confidence < 0.7, flag for human review
9. **Token policy** — Take only necessary logs, cut noisy output, don't dump full console

## Output Schema

```json
{
  "skill": "debug",
  "action": "fix|debug|error|trace|diagnose|reproduce|verify|check",
  "result": {
    "issue_id": "string",
    "severity": "critical|high|medium|low|info",
    "category": "frontend|backend|runtime|config|state|unknown",
    "root_cause": "string",
    "evidence": [
      {
        "type": "trace|log|error|code",
        "source": "string",
        "content": "string",
        "line": 0
      }
    ],
    "fix": {
      "description": "string",
      "files": ["string"],
      "confidence": 0.0,
      "breaking": false
    },
    "reproduction": {
      "steps": ["string"],
      "environment": "string"
    },
    "verification": {
      "signal": "string",
      "passed": false,
      "residual_risk": "string"
    },
    "stagnation": {
      "active": false,
      "iterations_without_change": 0
    }
  },
  "metadata": {
    "tokens_used": 0,
    "latency_ms": 0,
    "provider": "string"
  }
}
```

## Evidence Minimum (Required Output)
- Initial symptom
- Brief root cause
- Fix applied
- Verification signal (log/test/UI behavior)
