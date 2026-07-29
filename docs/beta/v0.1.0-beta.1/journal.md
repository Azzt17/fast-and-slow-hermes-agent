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

### 2026-07-29T12:02+08:00 — maintenance pre-beta dimulai

- Session: `codex-beta-preflight-2`
- Actor: `Codex`
- Task: Audit persona/profile dan menyiapkan reset data uji profile default.
- Mode: `maintenance`
- Beta code/config: `v0.1.0-beta.1` → `18c770b`; runtime masih pre-checkpoint.
- Observation: Backup Asa valid berisi `SOUL.md` dan tiga skill persona khusus.
  Profile `research` terisolasi lewat `HERMES_HOME`, tidak punya session/memory,
  dan belum mengaktifkan provider eksternal. Profile default berisi 16 hot turn,
  satu shadow memory, lima session state, dan plugin sebelum ADR-0015.
- Severity: `S2`
- Evidence: Audit inventory/hash profile-scoped dan SQLite integrity `ok`.
- Action: Stop hanya gateway default; snapshot penuh; reset data uji default;
  deploy exact checkpoint; restore persona Asa secara selektif; smoke test.
- Result: `open`

### 2026-07-29T12:29+08:00 — beta resmi dimulai

- Session: `codex-beta-preflight-2`
- Actor: `Codex`
- Task: Menyelesaikan preflight, reset data uji, persona multi-profile, deploy,
  snapshot clean-start, dan smoke test.
- Mode: `maintenance`
- Beta code/config: `v0.1.0-beta.1` → `18c770b`; threshold `0.55`; timeout
  answerability/admission `5s`; default `Asa/asa-complex`; research
  `Nellie/nellie-research`.
- Observation: Exact plugin hash cocok pada dua profile. Data uji default
  dipindahkan ke snapshot privat, bukan dihapus tanpa rollback. Kedua profile
  mulai dengan hot/shadow/session/message kosong dan storage terisolasi.
- Observation: Full regression serial 48-query PASS (recall `1.0`, precision@5
  `0.266667`, abstention `1.0`, security exclusion `1.0`, p50 `1386.666 ms`,
  p95 `1924.301 ms`, verifier unavailable `0`). Unit suite: `60 passed`,
  `2 skipped`, `2 subtests passed`.
- Observation: System-2 smoke aktual dengan `asa-complex` menghasilkan trusted
  summary, shadow row trusted, dan hot rows terkonsolidasi. Probe sebelumnya
  sempat fail-closed karena timeout/JSON terpotong; tidak ada unsafe memory yang
  menjadi trusted. Monitor recurrence selama task nyata.
- Observation: Persona Asa dipulihkan hanya dari `SOUL.md` dan tiga skill khusus;
  config/secret lama tidak direstore. Nellie memakai persona riset baru, model
  khusus, dan provider/storage profile-scoped. Kedua gateway aktif.
- Severity: `S2` teramati dan termitigasi; tidak ada severity unresolved.
- Evidence: Snapshot manifest terverifikasi; regression final PASS; plugin hash,
  SQLite integrity, profile model smoke, dan consolidation smoke PASS.
- Action: Mulai baseline beku 7 hari; tanpa tuning; jurnal task nyata dan monitor
  semantic admission latency/invalid JSON.
- Result: `resolved`; beta `Berjalan` sejak `2026-07-29T12:29+08:00`.
