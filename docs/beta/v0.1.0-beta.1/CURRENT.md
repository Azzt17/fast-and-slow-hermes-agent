# Current Beta State

File ini adalah handoff pertama yang wajib dibaca setiap session baru.

**Versi**: `v0.1.0-beta.1`
**Status**: Preflight — belum mulai
**Checkpoint code**: `18c770b`
**Branch dokumentasi**: `beta/0.1-dogfooding-docs`
**Tanggal mulai**: Belum ditetapkan
**Target selesai**: Belum ditetapkan
**Hari aktif / target**: `0 / 14`
**Sesi nyata / target**: `0 / 30`
**Severity tertinggi unresolved**: Tidak ada

## Temuan Preflight Saat Ini

- PR #2 sudah merged ke `master`.
- Tag lokal `v0.1.0-beta.1` menunjuk merge commit `18c770b`.
- Hermes aktif memakai provider `hermes-dual-memory`.
- Gateway Hermes sedang berjalan saat audit 2026-07-29.
- Plugin aktif belum sama dengan checkpoint: `answerability.py` belum terpasang;
  `__init__.py`, `storage.py`, dan `plugin.yaml` berbeda.
- Data runtime berada di `$HERMES_HOME/hermes-dual-memory/` dan mencakup SQLite,
  Chroma, Mem0 history, serta skill drafts.

**Implikasi**: jangan mulai menghitung hari beta. Deploy/restart/snapshot harus
diselesaikan lebih dulu.

## Active Configuration

- Retrieval minimum score: default `0.55`, kecuali jurnal menyatakan override.
- Answerability timeout: default `5s`, kecuali jurnal menyatakan override.
- Provider aktif tunggal: `hermes-dual-memory`.
- Baseline regression: schema v2, 48 query, overall `PASS`.

## Open Items

1. Push tag `v0.1.0-beta.1` setelah approval manusia.
2. Buat snapshot pre-beta saat gateway dihentikan terkontrol.
3. Deploy exact plugin checkpoint ke profile aktif.
4. Restart gateway dan verifikasi hash.
5. Jalankan smoke test lalu catat tanggal mulai.

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
