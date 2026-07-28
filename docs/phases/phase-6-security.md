# Fase 6: Lapisan Keamanan

**Status**: Selesai
**Tanggal Selesai**: 2026-07-28

## Goal

Admission dua lapis aktif; hanya candidate yang lolos pattern dan semantic
review menjadi trusted, sementara quarantined benar-benar tidak dapat masuk
retrieval normal.

## Yang Dibangun

- [x] Reuse `tools.threat_patterns` Hermes dengan fallback standalone.
- [x] Semantic hidden-instruction classifier bounded.
- [x] Gerbang nyata `candidate → trusted|quarantined`.
- [x] Persistensi `flagged_reason` dan status final di Mem0/shadow.
- [x] Reuse retrieval status gate Fase 4.
- [x] Korpus known-bad/known-good dengan metrik eksplisit.
- [x] Test quarantine retrieval dan semantic failure policy.

## Failure Mode yang Diwaspadai

False positive tinggi pada pembahasan keamanan legit, atau semantic failure
secara tidak sengaja membuat candidate trusted.

## Kriteria Keluar (Exit Criteria)

Korpus known-bad/known-good dijalankan pada stack nyata, catch rate dan false
positive rate dilaporkan, ambang dinilai layak/tidak, dan quarantined terbukti
tidak keluar melalui jalur `prefetch()` Fase 3/4.

## Hasil Uji

Lihat [hasil uji Fase 6](../testing/results/phase-6-results.md). Regression suite
PASS (`34 tests`, satu skip interpreter-specific yang PASS pada venv Hermes).
Benchmark scanner Hermes + 9router nyata menghasilkan catch rate `100%` dan
false-positive rate `0%` pada run final (6 known-bad, 6 known-good).

## Catatan/Pembelajaran

ADR-0011 menetapkan reuse pola Hermes dan semantic failure fail-closed.

Run awal memiliki FPR `16.67%` pada policy manusia; prompt semantic dituning
berdasarkan addressee lalu run final mencapai `0%`. Ambang layak sebagai baseline
personal, tetapi korpus perlu diperluas sebelum klaim produksi.
