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

## Aturan

- `Jenis`: `docs`, `config`, `code`, `schema`, `data`, atau `rollback`.
- Perubahan `schema/data/policy` wajib ADR dan snapshot baru.
- Setiap baris harus merujuk journal entry yang menjelaskan alasan/outcome.
- Jangan squash/overwrite baris lama; koreksi memakai baris baru.
