# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

> KantorKu is in alpha. Breaking changes may occur between minor versions.

---

## Reporting a Vulnerability

**Do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via:

1. **GitHub Security Advisories** — [Report a vulnerability](https://github.com/Wolfvin/KantorKu/security/advisories/new)
2. **Email** — Send details to the maintainer privately

Please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

We will respond within 48 hours and keep you updated on the resolution.

---

## Security Considerations

### API Keys

- **Never commit API keys** to the repository. Use environment variables (`${ANTHROPIC_API_KEY}`) in `kantorku.toml`
- The `.gitignore` excludes `kantorku.toml` and `.env` files
- API keys are resolved at runtime from environment variables

### Red Team Module

KantorKu includes a red team module (`kantorku/redteam/`) for testing LLM safety:

- **STM** — Short-Term Memory exploit testing
- **Godmode** — Bypass testing
- **Parseltongue** — Encoding-based prompt injection testing
- **Classify** — Prompt classification for safety assessment
- **AutoTune** — Automated safety scoring

These tools are intended **solely for security research and testing your own deployments**. They are gated behind the command palette in the TUI and should be used responsibly.

### Worker Security

- Workers run with the permissions of the Python process
- Workers can make HTTP calls using `self.api_call()` — be mindful of network access
- Custom worker code (`worker.py`) executes arbitrary Python — only use workers from trusted sources
- The Conductor has full orchestration control — protect your Conductor model access

### Provider Security

- All provider communication uses HTTPS
- Circuit breakers prevent cascade failures
- Rate limiters protect against accidental API abuse
- Retry logic uses exponential backoff with jitter to avoid thundering herd

### WebSocket Security

- In production, always run behind a reverse proxy with TLS
- Consider adding authentication middleware for WebSocket connections
- Session IDs should be treated as opaque tokens

---

## Best Practices

1. **Use a virtual environment** — Isolate KantorKu dependencies
2. **Rotate API keys regularly** — Especially if they appear in logs
3. **Review custom workers** — Audit `worker.py` files before loading
4. **Limit network access** — Use firewall rules for production deployments
5. **Enable logging** — Monitor worker activity and provider usage
6. **Keep dependencies updated** — Run `pip audit` regularly

---

## Disclosure Policy

When a vulnerability is reported:

1. We will confirm the vulnerability and determine its scope
2. We will develop a fix and test it
3. We will release a patch version as soon as possible
4. We will credit the reporter (unless they prefer to remain anonymous)
5. We will publish a security advisory on GitHub

---

Thank you for helping keep KantorKu secure.
