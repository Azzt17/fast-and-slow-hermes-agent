# Beta Journal — v0.1.0-beta.1

Append-only. Jangan menghapus atau menulis ulang observasi lama; koreksi dibuat
sebagai entri baru yang merujuk entri sebelumnya. Semua waktu memakai timezone
lokal `Asia/Shanghai` dan format ISO-8601.

## Template Entri

```markdown
### YYYY-MM-DDTHH:MM+08:00 — <jenis entri>

- Session: `<ID pendek/hash>`
- Actor: `Farid|Codex|Hermes`
- Task: `<ringkasan tersanitasi>`
- Mode: `real|synthetic|maintenance`
- Beta code/config: `<tag/commit + override>`
- Observation: `<helpful/missed/irrelevant/error/latency/cost>`
- Severity: `none|S0|S1|S2|S3`
- Evidence: `<metric/log/test/commit/ADR tanpa data sensitif>`
- Action: `<none/monitor/fix/rollback>`
- Result: `<open/mitigated/resolved>`
```

## Entries

### 2026-07-29T11:33+08:00 — checkpoint ditetapkan

- Session: `codex-beta-preflight`
- Actor: `Codex`
- Task: Menetapkan checkpoint setelah Fase 8 dan merancang dogfooding beta.
- Mode: `maintenance`
- Beta code/config: `v0.1.0-beta.1` → `18c770b`
- Observation: Fase 8 overall PASS; tag lokal dibuat. Plugin aktif Hermes masih
  versi sebelum ADR-0015 dan gateway sedang berjalan, sehingga clock beta belum
  boleh dimulai.
- Severity: `S2`
- Evidence: PR #2 merged; audit hash plugin aktif; ADR-0016.
- Action: Dokumentasikan preflight, snapshot, deploy, restart, dan smoke test.
- Result: `open`
