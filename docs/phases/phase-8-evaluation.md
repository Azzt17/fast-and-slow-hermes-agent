# Fase 8: Evaluasi & Observability

**Status**: Selesai
**Tanggal Mulai**: 2026-07-29
**Tanggal Selesai**: 2026-07-29

## Goal

Membuat mini-benchmark regression yang mengukur recall, precision, latency, dan
token efficiency pada jalur retrieval real-stack untuk tujuh kategori.

## Yang Dibangun

- [x] Audit timing/token instrumentation fase sebelumnya
- [x] Corpus 20 query dalam tujuh kategori
- [x] Runner Mem0/Chroma/Ollama isolated
- [x] Knowledge update, cold tier, dan quarantine fixtures
- [x] Exact token usage melalui model direct 9router
- [x] Laporan JSON baseline yang comparable
- [x] Unit tests untuk scoring/report schema
- [x] Runbook rerun dan comparison baseline

## Failure Mode yang Diwaspadai

- Benchmark memakai fake ranking sehingga latency/recall tidak realistis
- Store evaluasi mencemari memory user
- Token efficiency memakai estimasi, bukan usage provider
- Query/corpus terlalu mudah dan menyembunyikan abstention/temporal gap
- Perubahan ranking nondeterministik tidak disertai alasan per kategori

## Kriteria Keluar (Exit Criteria)

- [x] Tujuh kategori menghasilkan verdict dan alasan terstruktur
- [x] Minimal 15–20 query menghasilkan distribusi latency p50/p95
- [x] Recall, precision, dan token efficiency tercatat numerik
- [x] Kategori lemah dicatat apa adanya
- [x] Baseline JSON tersimpan di `docs/testing/baselines/`
- [x] Baseline score di-commit sebagai kontrak regression

## Hasil Uji

Suite, review, dan seluruh pengukuran selesai; baseline overall `PARTIAL`. Pada
20 query, Memory Recall `90%`, Precision@5 `24%`, latency p50/p95
`160.953/223.123 ms`, dan mean
context `119.1` token/query. Temporal reasoning `PARTIAL` (`50% recall`) dan
abstention `PARTIAL` (`50%`) dicatat tanpa dipaksa lolos. Laporan lengkap:
`docs/testing/results/phase-8-results.md`.

## Catatan/Pembelajaran

Fase 3 tidak memiliki recorder latency produksi. Instrumentasi yang dapat
direuse adalah boundary stopwatch di test retrieval dan `prefetch()` sebagai
jalur retrieval canonical. Hot-tier `token_count` hanya word count, sehingga
tidak dipakai untuk metric token Fase 8 (ref ADR-0013).

Smoke benchmark menemukan `limit=5` tidak membatasi Mem0 v2; API canonical
memakai `top_k`. Provider diperbaiki menjadi `top_k=5` plus cap lokal lima hasil.

Score expected facts minimum `0.567921`, sedangkan abstention top score
`0.598476/0.530859`. Threshold seimbang `0.55` meningkatkan abstention dari 0%
ke 50% tanpa menurunkan recall kategori lain. Threshold 0.60 ditolak karena akan
memotong beberapa expected facts multi-session.
