# Beta Change Ledger

Satu baris per perubahan code/config/data selama beta. Ledger ini melengkapi
jurnal observasi dan tidak menggantikannya.

| ID | Tanggal | Jenis | Branch/Commit | ADR | Baseline | Snapshot | Status |
|---|---|---|---|---|---|---|---|
| BETA-000 | 2026-07-29 | checkpoint docs | `beta/0.1-dogfooding-docs` | ADR-0016 | Fase 8 schema v2 PASS | clean-start verified | open |
| BETA-001 | 2026-07-29 | data/config | `beta/0.1-dogfooding-docs` | ADR-0016 | 48-query PASS; unit 60 PASS | clean-start verified | active |
| BETA-002 | 2026-07-29 | config | `beta/0.1-dogfooding-docs` | ADR-0016 | profile isolation + model smoke PASS | clean-start verified | active |
| BETA-003 | 2026-07-29 | config | `beta/0.1-dogfooding-docs` | ADR-0016 | HTTP content match + tailnet-only bind PASS | clean-start verified | active |
| BETA-004 | 2026-07-29 | config | `beta/0.1-dogfooding-docs` | ADR-0016 | Telegram getMe/polling/outbound PASS | runtime config snapshot | active |
| BETA-005 | 2026-07-29 | code | `beta/0.1-dogfooding-docs` | ADR-0019 | unit 67 PASS, 2 skipped | no runtime/vault data touched | active |
| BETA-006 | 2026-07-29 | docs | `beta/0.1-dogfooding-docs` | ADR-0020 | design-only; no regression needed | no runtime/vault data touched | active |
| BETA-007 | 2026-07-29 | code | `beta/0.1-dogfooding-docs` | ADR-0020 | unit 69 PASS, 2 skipped | no runtime/vault data touched | active |
| BETA-008 | 2026-07-29 | code | `beta/0.1-dogfooding-docs` | ADR-0020 | importer temp tests + full suite PASS | no runtime/vault data touched | active |
| BETA-009 | 2026-07-29 | schema/config | `beta/0.1-dogfooding-docs` | ADR-0020 | post-deploy 4-category baseline PASS | paired Asa snapshot verified | active |
| BETA-010 | 2026-07-29 | data/rollback | `beta/0.1-dogfooding-docs` | ADR-0020 | admission timeout → fail-closed rollback | Pilot 2 paired Asa snapshot retained | mitigated |
| BETA-011 | 2026-07-30 | code | `beta/0.1-dogfooding-docs` | ADR-0021 | targeted repro 6 PASS; postdeploy 4-category PASS | paired Asa snapshot verified | active |
| BETA-012 | 2026-07-30 | code | `beta/0.1-dogfooding-docs` | ADR-0021 | Research postdeploy 4-category PASS | paired Research snapshot verified | active; legacy timeout observed |
| BETA-013 | 2026-07-30 | code/data | `beta/0.1-dogfooding-docs` | ADR-0022 | full unit 76 PASS; both postdeploy 4-category PASS | paired default+Research snapshot verified | active; legacy consolidated, one malformed chunk pending |

## Aturan

- `Jenis`: `docs`, `config`, `code`, `schema`, `data`, atau `rollback`.
- Perubahan `schema/data/policy` wajib ADR dan snapshot baru.
- Setiap baris harus merujuk journal entry yang menjelaskan alasan/outcome.
- Jangan squash/overwrite baris lama; koreksi memakai baris baru.
| BETA-014 | 2026-07-30 | code/integration | local Hermes `main` | upstream lifecycle fix | focused direct async regression + compile PASS | paired gateway/default/research snapshot verified | deployed; runtime `/new` verification pending |
