# Debug Skill

## Purpose
The **Debug** skill provides troubleshooting, error diagnosis, and root cause analysis capabilities. It traces issues through the system, reproduces errors, and suggests or applies fixes.

## Capabilities

1. **Fix** — Apply patches or suggest fixes for identified issues
2. **Debug** — Step through code execution paths to identify problems
3. **Error** — Parse, categorize, and explain error messages and stack traces
4. **Trace** — Follow execution flow through distributed traces and spans
5. **Diagnose** — Perform systematic diagnosis of symptoms to identify root causes
6. **Reproduce** — Create minimal reproduction cases for reported issues

## Output Schema

```json
{
  "skill": "debug",
  "action": "fix|debug|error|trace|diagnose|reproduce",
  "result": {
    "issue_id": "string",
    "severity": "critical|high|medium|low|info",
    "category": "string",
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
    }
  },
  "metadata": {
    "tokens_used": 0,
    "latency_ms": 0,
    "provider": "string"
  }
}
```

## Key Rules

1. **Reproduce first** — Always attempt to reproduce before diagnosing
2. **Evidence-based** — Every conclusion must cite trace, log, or code evidence
3. **Minimal fix** — Prefer the smallest change that resolves the issue
4. **No side effects** — Debug operations must not alter production state
5. **Severity assessment** — Classify severity before proposing fixes
6. **Circuit breaker aware** — Check if the issue is related to provider outage
7. **Check memory first** — Search MEMORY.md and past issues for known patterns
8. **Escalate uncertain fixes** — If confidence < 0.7, flag for human review
