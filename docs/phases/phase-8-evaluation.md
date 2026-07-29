# Fase 8: Evaluasi & Observability

**Status**: Selesai
**Tanggal Mulai**: 2026-07-29
**Tanggal Selesai**: 2026-07-29

## Goal

Membuat mini-benchmark regression yang mengukur recall, precision, latency, dan
token efficiency pada jalur retrieval real-stack untuk tujuh kategori.

## Yang Dibangun

- [x] Audit timing/token instrumentation fase sebelumnya
- [x] Corpus 48 query dalam tujuh kategori
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

Suite, review, dan seluruh pengukuran selesai; baseline overall `PASS`. Pada
48 query, Memory Recall `100%`, Precision@5 `26.67%`, abstention `100%`, security
exclusion `100%`, latency p50/p95 `1350.603/1675.018 ms`, dan mean context
`37.125` token/query. Temporal reasoning tetap `PASS` setelah ADR-0014;
answerability ADR-0015 menutup gap abstention tanpa menurunkan recall/security.
Laporan lengkap: `docs/testing/results/phase-8-results.md`.

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

Follow-up baseline menunjukkan row superseded semantic memang masih diranking
raw Mem0. Mode historis deterministik kini membuka row tersebut hanya untuk
query dengan intent temporal eksplisit, memberi atribut validity boundary, dan
tetap memblok quarantine serta superseded episodic (ref ADR-0014).

## Follow-up Abstention Verifier

**Status**: Selesai

- [x] Audit reranker Hermes dan Mem0 OSS
- [x] Tetapkan lalu koreksi kontrak gate berdasarkan pre-gate run (ADR-0015)
- [x] Perluas abstention menjadi 30 hard-negative query
- [x] Implementasikan verifier kandidat scored yang bounded
- [x] Verifikasi timeout/error/format invalid fail-closed
- [x] Jalankan unit, runtime integration, dan real-stack benchmark
- [x] Promosikan baseline setelah recall/security tidak turun

Target follow-up: abstention minimal `90%`, memory recall tetap `100%`, security
exclusion tetap `100%`, serta tambahan latency/token verifier tercatat numerik.

Pre-gate 30-query menghasilkan abstention `3.33%` (`1/30`). False neighbor
mencapai score `0.846105`, sehingga zona accept langsung dibatalkan: semua
kandidat scored yang lolos threshold harus melalui answerability verifier.

Full post-gate benchmark 48-query menghasilkan seluruh tujuh kategori `PASS`:
abstention `100%` (`30/30`), memory recall `100%`, precision@5 `26.67%`, dan
security exclusion `100%`. Seluruh `44/44` verifier call valid tanpa unavailable
atau retry pada final run. Trade-off besar dicatat apa adanya: latency p50/p95
naik menjadi `1350.603/1675.018 ms`; verifier memakai `111,905` prompt token dan
`408` completion token. Context yang diinjeksi turun menjadi mean `37.125`
token/query karena hard-negative tidak lagi masuk context (ref ADR-0015).
