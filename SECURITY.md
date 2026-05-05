# Security Policy / Kebijakan Keamanan

## Supported Versions / Versi yang Didukung

| Version | Supported          |
| ------- | ------------------ |
| 0.4.x   | :white_check_mark: |
| 0.3.x   | :white_check_mark: |
| < 0.3   | :x:                |

---

## Reporting a Vulnerability / Melaporkan Kerentanan

**Do NOT report security vulnerabilities through public GitHub issues.**
**JANGAN melaporkan kerentanan keamanan melalui issue GitHub publik.**

Instead, please report them through one of these channels:
Sebagai gantinya, silakan laporkan melalui salah satu saluran ini:

### Option 1: GitHub Security Advisory (Preferred / Disarankan)

1. Go to [github.com/Wolfvin/KantorKu/security/advisories](https://github.com/Wolfvin/KantorKu/security/advisories)
2. Click **"Report a vulnerability"**
3. Fill in the details

### Option 2: Email

Send a detailed report to: **security@kantorku.dev** (encrypted with PGP if possible)

---

## What to Include in a Report / Apa yang Perlu Disertakan

Please include the following information in your report:
Harap sertakan informasi berikut dalam laporan Anda:

1. **Description** — A clear description of the vulnerability
2. **Impact** — What an attacker could achieve (e.g., data exposure, code execution, privilege escalation)
3. **Affected components** — Which part of KantorKu is affected (framework, web-ui, CLI)
4. **Reproduction steps** — Step-by-step instructions to reproduce the issue
5. **Proof of concept** — Code or commands demonstrating the vulnerability (if applicable)
6. **Suggested fix** — If you have ideas on how to fix it
7. **Your contact info** — For follow-up questions

**Important / Penting:**
- Never include actual API keys or credentials in your report
- Jangan pernah menyertakan kunci API atau kredensial aktual dalam laporan Anda
- Redact any sensitive information before submitting
- Sensor informasi sensitif sebelum mengirimkan

---

## Response Timeline / Timeline Respons

| Timeframe | Action |
|-----------|--------|
| Within 24 hours | Acknowledge receipt of the report |
| Within 72 hours | Initial assessment and severity classification |
| Within 7 days | Detailed response with remediation plan |
| Within 30 days | Fix released (for critical/high severity) |
| Within 90 days | Fix released (for medium/low severity) |

---

## Scope / Ruang Lingkup

**In scope / Dalam ruang lingkup:**
- KantorKu framework (Python backend)
- KantorKu Web UI (Next.js frontend)
- KantorKu CLI (Node.js CLI tool)
- Authentication and authorization mechanisms
- API key handling and storage
- Data persistence and storage

**Out of scope / Di luar ruang lingkup:**
- Vulnerabilities in third-party dependencies (report to upstream)
- Social engineering attacks
- Denial of service attacks
- Issues in development-only tools

---

## Disclosure Policy / Kebijakan Pengungkapan

We follow a **coordinated disclosure** process:
Kami mengikuti proses **pengungkapan terkoordinasi**:

1. Report is received and acknowledged
2. Vulnerability is confirmed and severity assessed
3. Fix is developed and tested
4. Fix is released in a new version
5. Security advisory is published on GitHub
6. Reporter is credited (unless they prefer to remain anonymous)

We ask that reporters:
Kami meminta pelapor untuk:

- Allow reasonable time for the fix before public disclosure
- Not exploit the vulnerability beyond what's needed for proof of concept
- Not access or modify other users' data

---

Thank you for helping keep KantorKu and its users safe!
Terima kasih telah membantu menjaga KantorKu dan penggunanya tetap aman! 🛡️
