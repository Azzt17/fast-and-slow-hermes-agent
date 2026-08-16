# Ringkasan Penutupan Beta — v0.1.0-beta.1

**Tanggal**: 2026-08-16 (target selesai 08-19; metrik sudah tercapai, dokumen ini menyiapkan keputusan penutupan)
**Repo**: `hermes-dual-memory` — branch `beta/0.1-dogfooding-docs`
**Tujuan beta**: dogfooding mekanisme dual-memory sebagai recall utama di 3 profile produksi sebelum Fase 9.

---

## 1. Metrik Akhir (per 2026-08-16, dari hot_sessions 3 profile)

| Metrik | Target | Aktual | Status |
|---|---|---|---|
| Hari aktif | 14 | **14** (07-29..08-16; gap 08-02, 08-08, 08-10-12) | ✅ |
| Sesi nyata | 30 | **49** (default 27, research 14, coding 8) | ✅ |
| Memory index | — | **190** (trusted 124, quarantined 66) | ✅ |
| Pending consolidation | 0 stranded | **12** (semua sesi aktif hari ini — wajar) | ✅ |
| Test suite | — | **87/87 PASS** | ✅ |
| Baseline 2 | recall 1.0 | **PASS** (recall 1.0, p95 2075ms, drift +399ms) | ✅ |
| Rollback drill | 1x wajib | **PASS** (sandbox clone research) | ✅ |
| Hash deployed == repo | — | **3 file × 3 profile identik** | ✅ |

## 2. Exit Criteria — Semua Terverifikasi

1. **Dogfooding berjalan** — plugin aktif sebagai primary memory provider di 3 profile (Asa/Nellie/Ada) sejak 29 Juli.
2. **Hari aktif ≥ 14** — tercapai (14/14).
3. **Sesi ≥ 30** — tercapai (49).
4. **Baseline tidak regresi material** — baseline 08-16 PASS (recall pulih 1.0 dari 0.9; p95 membaik 2350→2075ms; drift +399ms vs baseline resmi, acceptable).
5. **Rollback drill** — PASS via sandbox clone (produksi tak tersentuh; mekanisme restore+retrieval teruji).
6. **Test suite hijau** — 87/87 (termasuk 7 test herald + 1 test sanitize skill).

## 3. Pekerjaan yang Diselesaikan Selama Beta Akhir (16 Agu)

- **ADR-0024** — kompatibilitas herald v0.20.1: `agent_context` filter (subagent/cron skip), `backup_paths()`, `on_memory_write` audit trail (hash-only), lineage `parent_session_id`. Deploy 3 profile.
- **Runtime fixes** — duplikat gateway research dimatikan (crash-loop 41.247×); restart nellie + default + coding ke plugin herald; migrasi schema DB live 3 profile.
- **Baseline mingguan ke-2** — PASS (tersimpan `phase-8-baseline-2026-08-16.json`).
- **Recovery pending** — 71 rows terkonsolidasi (60 stranded + 4 skill-detail + 11 legacy item #11).
- **Fix skill router** — `sanitize_new_skills` drop item melanggar batas, jangan blokir fakta; 87/87 test.
- **Item #11 tertutup** — koreksi diagnosis: bukan malformed, hanya belum diproses; recovery 9 trusted + 2 quarantined.
- **Gap jurnal diisi** — rekonstruksi tersanitasi 08-07..08-15.
- **Rollback drill PASS** — sandbox clone research.

## 4. Temuan Penting (untuk Fase 9)

- **`backup_paths()` (ADR-0024) krusial**: rollback tanpa chroma = integrity OK tapi recall hilang. `hermes backup` kini menyertakan data dual-memory — rollback paired code+data tidak kehilangan retrieval.
- **Skill draft >1200 char memblokir konsolidasi**: satu draft buruk menggagalkan seluruh chunk. Fix: sanitize (drop item, lanjut fakta). Pelajaran untuk hardening konsolidasi.
- **Konsolidasi era awal tanpa jejak error**: `maintenance_state.last_consolidation_error` baru ada sejak ADR-0023 — sesi lama yang gagal tidak meninggalkan jejak. Recovery idempotent menyelesaikannya.
- **Rasio quarantine coding 19:19** (trusted:quarantined) — admission timeout 5s sering memicu quarantine. Rekomendasi: review threshold (opsional, bukan blocker).
- **Cron monitor deterministik** (`no_agent=true`) lebih andal daripada agent cron untuk metrik/baseline (pelajaran recurring-cron-monitor).

## 5. Keputusan yang Diperlukan Farid

Beta **siap ditutup** — semua exit criteria terpenuhi lebih cepat dari target (16 vs 19 Agu). Opsi:

1. **Tutup beta sekarang** → lanjut Fase 9 (hardening: micro-compaction, context engine, review quarantine threshold, evaluasi `backup_paths` production).
2. **Tutup beta + observasi 3 hari** → biarkan 08-19 berjalan sebagai "cool-down" tanpa pekerjaan aktif, tutup resmi 08-19.
3. **Perpanjang beta** → jika ada temuan baru yang ingin diverifikasi lebih lama (tidak direkomendasikan — semua metrik sudah tercapai).

## 6. Lampiran

- Jurnal beta: `docs/beta/v0.1.0-beta.1/journal.md` (1114 baris, append-only)
- CURRENT.md: `docs/beta/v0.1.0-beta.1/CURRENT.md`
- Baseline: `docs/testing/baselines/phase-8-baseline-2026-08-16.json`
- Snapshot: `~/hermes-beta-snapshots/` (herald-0024, a3-recovery)
- Commit: `2abbddb` (ADR-0024) → `c6d133c` (rollback drill) → `b81eb36` (baseline+recovery) → `7ef1c41` (fix skill router)
