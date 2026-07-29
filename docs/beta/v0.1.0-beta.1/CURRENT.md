# Current Beta State

File ini adalah handoff pertama yang wajib dibaca setiap session baru.

**Versi**: `v0.1.0-beta.1`
**Status**: Berjalan — baseline beku
**Checkpoint code**: `18c770b`
**Branch dokumentasi**: `beta/0.1-dogfooding-docs`
**Tanggal mulai**: `2026-07-29T12:29+08:00`
**Target selesai**: `2026-08-19` (tetap tunduk pada minimum hari/sesi)
**Hari aktif / target**: `0 / 14`
**Sesi nyata / target**: `0 / 30`
**Severity tertinggi unresolved**: Tidak ada

## Temuan Preflight Saat Ini

- Tag remote `v0.1.0-beta.1` menunjuk merge commit `18c770b`.
- Exact plugin checkpoint terpasang dan hash cocok pada profile `default` dan
  `research`; kedua gateway aktif setelah controlled restart.
- Data uji profile default dipindahkan ke snapshot privat; kedua profile mulai
  dengan `0` hot turn, `0` shadow memory, `0` session, dan `0` message.
- Persona default `Asa` dipulihkan selektif dari backup tervalidasi: `SOUL.md`
  plus `asa-daily-checkin`, `asa-night-review`, dan `asa-deep-discussion`.
- Profile `research` menjadi `Nellie`, memakai model `nellie-research`, provider
  `hermes-dual-memory`, dan storage profile-scoped terpisah.
- Clean-start snapshot code+data dua profile dibuat saat kedua gateway berhenti;
  checksum dan archive integrity PASS.
- Final serial 48-query regression PASS: recall `1.0`, abstention `1.0`, security
  exclusion `1.0`, p50 `1386.666 ms`, p95 `1924.301 ms`.
- System-2 real-stack smoke dengan runtime model `asa-complex` PASS. Beberapa
  probe sebelumnya fail-closed saat respons semantic admission timeout/terpotong;
  monitor bila berulang dalam task nyata.

## Active Configuration

- Retrieval minimum score: default `0.55`, kecuali jurnal menyatakan override.
- Answerability timeout: default `5s`, kecuali jurnal menyatakan override.
- Provider aktif tunggal per profile: `hermes-dual-memory`.
- Profile default: persona `Asa`, model `asa-complex`.
- Profile research: persona `Nellie`, model `nellie-research`.
- Baseline regression: schema v2, 48 query, overall `PASS`.

## Open Items

1. Jalankan task nyata tanpa tuning config selama hari 1–7.
2. Catat setiap sesi nyata dan observasi retrieval di `journal.md`.
3. Monitor timeout/JSON invalid semantic admission; buka `BETA-NNN` jika berulang.
4. Jalankan baseline comparison mingguan pertama pada akhir hari aktif ke-7.
5. Merge PR dokumentasi beta #3 setelah review manusia.

## Runbook dan Ledger

- Preflight/deploy/rollback: `RUNBOOK.md`
- Snapshot metadata: `SNAPSHOT-MANIFEST.md`
- Change ledger: `changes.md`
- Observation log: `journal.md`

## Session Handoff Rule

Sebelum mengubah beta code/config/data:

1. baca file ini dan `README.md` di direktori yang sama;
2. baca 20 entri terakhir `journal.md`;
3. cek branch, tag, PR, dan working tree;
4. cek apakah gateway aktif sebelum snapshot/deploy;
5. tambahkan journal entry sebelum dan sesudah perubahan;
6. update file ini jika status, config, open item, atau rollback point berubah.
