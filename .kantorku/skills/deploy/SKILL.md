# Deploy Skill

## Purpose
The **Deploy** skill provides deployment, configuration, and environment setup capabilities. It handles Docker orchestration, configuration management, bootstrap processes, and installation workflows.

## Capabilities

1. **Deploy** — Deploy services using Docker Compose or direct execution
2. **Docker** — Build, run, and manage Docker containers and images
3. **Config** — Manage configuration files, environment variables, and secrets
4. **Setup** — Initialize project environments and install dependencies
5. **Install** — Install packages, tools, and extensions
6. **Bootstrap** — Run bootstrap scripts for workspace initialization

## Output Schema

```json
{
  "skill": "deploy",
  "action": "deploy|docker|config|setup|install|bootstrap",
  "result": {
    "deployment_id": "string",
    "environment": "string",
    "services": [
      {
        "name": "string",
        "status": "started|stopped|healthy|unhealthy",
        "port": 0,
        "url": "string"
      }
    ],
    "config_applied": ["string"],
    "steps_completed": ["string"],
    "errors": ["string"]
  },
  "metadata": {
    "tokens_used": 0,
    "latency_ms": 0,
    "provider": "string"
  }
}
```

## Key Rules

1. **Approval gates** — Only approved commands from `home-default.rules` are allowed
2. **Idempotent** — Deploy operations must be safe to run multiple times
3. **Health checks** — Always verify service health after deployment
4. **Rollback ready** — Maintain ability to rollback to previous configuration
5. **Secret safety** — Never log or expose API keys and secrets
6. **Docker-first** — Prefer Docker Compose for multi-service deployments
7. **Config drift detection** — Compare against `home-config.toml` baseline
8. **Environment awareness** — Detect and adapt to dev/staging/prod environments
