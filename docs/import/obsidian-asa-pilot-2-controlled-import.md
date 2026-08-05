# Obsidian → Asa Pilot 2 Controlled Import

Pilot 2 belum diaktifkan. Dokumen ini adalah kontrak implementasi/write gate bagi
empat kandidat Pilot 1 yang telah disetujui Farid.

## Batch Pertama

| Candidate | Class | Import intent |
|---|---|---|
| `p1-001` | stable | preference pendampingan Asa |
| `p1-002` | stable | preference dukungan/recovery |
| `p1-003` | historical-only | ide screen-time dynamic |
| `p1-004` | historical-only | ide digital garden |

## Required Provenance

Setiap memory import wajib membawa `batch_id`, `candidate_id`, source relative
path, source SHA-256 review, ledger approval, temporal class, import timestamp,
`mem0_id`, dan `memory_index_id`. Private ledger/source content tidak masuk Git.

## Pre-Write Gate

1. Farid memberi approval write eksplisit untuk candidate/batch exact.
2. Gateway Asa dihentikan; snapshot code+data Asa dibuat dan checksum diverifikasi.
3. Source hash dibandingkan dengan snapshot Pilot 1; mismatch → batch berhenti dan
   kembali review.
4. Schema provenance migration + synthetic tests PASS.
5. Baseline regression category recall, temporal, abstention, security PASS.
6. Importer dry-run menampilkan rencana write, idempotency result, dan rollback
   plan tanpa Mem0/SQLite write.

## Status Implementasi

Schema provenance dan write-path terisolasi telah diuji hanya pada SQLite/Mem0
palsu. Kode belum dideploy ke profile Asa dan tidak dipanggil provider hook.
Sebelum deployment, gunakan checklist pre-write di atas; setelah deployment,
write batch tetap memerlukan approval final Farid untuk `p1-001` sampai `p1-004`.

## Invariant Terverifikasi (Temporary Integration)

- Rollback batch mengkarantina semua shadow row batch dan menghilangkannya dari
  `prefetch()` production path.
- Importer selalu memanggil evaluator admission native; LLM tidak tersedia
  menghasilkan `quarantined` fail-closed, walau kandidat telah direview manusia.
- Historical-only tidak terlihat pada current query, hanya pada query historis
  eksplisit, lalu ikut terblokir setelah rollback batch.

Verifikasi ini memakai SQLite/Mem0 palsu temporary. Runtime Asa belum disentuh
sampai deployment terkontrol disetujui.

## Write Contract

- Profile: Asa/default saja; research tidak disentuh.
- Mem0: `infer=False` wajib.
- Shadow: tulis `candidate`, lalu admission final `trusted`/`quarantined`.
- Historical-only tidak boleh muncul pada current-state retrieval.
- Tidak ada auto-supersede batch pertama.
- Write gagal parsial → batch stopped, tidak retry blind; gunakan provenance dan
  snapshot untuk recovery.

## Verification

- Verify source hash, batch/source provenance, Mem0/shadow bijection, SQLite
  integrity, dan batch idempotency.
- Positive recall: dua preference stable tepat.
- Temporal: dua ide hanya visible ketika query historis eksplisit.
- Negative: excluded candidate dan source instruction tidak visible.
- Security: admission quarantine tetap invisible.
- Baseline comparison tidak boleh menurunkan recall/abstention/security.

## Rollback

- Normal: mark batch provenance `rolled_back`, block all referenced shadow rows,
  preserve audit trail; remove Mem0 only when safe and verified.
- S0/S1/data inconsistency: stop gateway Asa, snapshot incident, restore paired
  code+data snapshot, integrity check, smoke test sebelum start.

## Dry-Run Planner

`plugins/memory/hermes-dual-memory/import_batch.py` saat ini hanya membaca ledger
private dan menghasilkan plan `memory_write=false`. Ia memfilter approval,
membuat idempotency key dari candidate+source hash, dan memastikan historical-only
berlabel historical sebelum write-path dibuat. Ia tidak memiliki akses ke Mem0,
SQLite, atau vault.
