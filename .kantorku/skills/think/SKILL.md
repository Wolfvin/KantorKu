---
name: think
description: Deliberate reasoning gate for non-trivial tasks. Use before planning/routing/execution to reduce hallucination risk, detect context gaps, and choose the minimal correct next action.
---

# Think (Compact)

## Trigger
- Task ambigu/non-trivial/high-risk.
- Semua task yang berdampak ke kualitas evolusi `.codex`.

## Goal Lock (Mandatory)
- Goal tunggal default: tingkatkan kemampuan agent untuk evolve memakai seluruh aset di `.codex`.
- Prioritaskan keputusan yang memperkuat reusable workflow, consistency, dan anti-drift lintas skill.
- Abaikan preferensi ad-hoc jika bertentangan dengan goal evolusi inti, kecuali user memberi override eksplisit.

## 5-Step Gate
1. Clarify objective + constraints.
2. Check context sufficiency across `.codex` assets (skills/tools/memory/reports).
3. `decision_cache_check`: cek apakah keputusan serupa sudah pernah ada (memory/reports/contract) sebelum menyusun aksi baru.
4. Assess uncertainty/evidence level.
5. Choose single best next action that improves `.codex` evolution capability.
6. Generate output seperlunya.

## Evidence Rule
- Klaim kritis butuh source primer/official bila tersedia.
- Jika evidence kurang: nyatakan uncertainty dan ambil langkah verifikasi.

## Tool Discipline
- Pakai tool minimum yang relevan.
- Jangan melebar tanpa alasan.

## Safety Boundary
- Untuk perubahan high-impact, default stance adalah recommendation-first, bukan patch langsung.
- Jika ada risiko regresi strategis, keluarkan posisi tegas `partial|disagree` + opsi aman.
- Nyatakan tradeoff utama secara eksplisit saat menolak atau menunda eksekusi langsung.
- `context_profile_required`: untuk task `architecture|improvement`, wajib bentuk profil konteks minimum (jenis project, skala, prioritas) sebelum final decision.

## Output Wajib
- `judgment_summary`
- `decision`
- `confidence` (`high|medium|low`)
- `next_step`
- `recommended_stance` (`agree|partial|disagree`)
- `goal_alignment` (`pass|fail`)
- `assumption_risk` (`low|medium|high`)
