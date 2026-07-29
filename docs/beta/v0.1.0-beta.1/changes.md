# Beta Change Ledger

Satu baris per perubahan code/config/data selama beta. Ledger ini melengkapi
jurnal observasi dan tidak menggantikannya.

| ID | Tanggal | Jenis | Branch/Commit | ADR | Baseline | Snapshot | Status |
|---|---|---|---|---|---|---|---|
| BETA-000 | 2026-07-29 | checkpoint docs | `beta/0.1-dogfooding-docs` | ADR-0016 | Fase 8 schema v2 PASS | pending | open |

## Aturan

- `Jenis`: `docs`, `config`, `code`, `schema`, `data`, atau `rollback`.
- Perubahan `schema/data/policy` wajib ADR dan snapshot baru.
- Setiap baris harus merujuk journal entry yang menjelaskan alasan/outcome.
- Jangan squash/overwrite baris lama; koreksi memakai baris baru.
