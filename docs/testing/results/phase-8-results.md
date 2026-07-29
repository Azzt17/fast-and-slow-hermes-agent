# Hasil Uji Fase 8

**Tanggal**: 2026-07-29
**Status**: PASS (suite selesai; baseline overall PARTIAL)

## Audit Instrumentasi Existing

Fase 3 tidak memiliki recorder latency produksi. Instrumentasi yang tersedia
dan direuse adalah boundary `time.monotonic()` pada test retrieval dan method
`MemoryProvider.prefetch()` sebagai jalur canonical dari query sampai blok
context siap. Runner Fase 8 memakai boundary ekuivalen dengan
`time.perf_counter()` untuk resolusi lebih tinggi.

`hot_sessions.token_count` dihitung memakai `split()` sehingga bukan tokenizer
nyata dan tidak dipakai. Token Efficiency diukur dari differential
`usage.prompt_tokens` provider 9router: prompt system identik dengan memory block
dibandingkan prompt system identik tanpa block. Model direct yang dipakai adalah
`ag/gemini-3.5-flash-extra-low`; response melaporkan model `gemini-default`.

## Struktur Suite

- Corpus: `evaluation/phase8_corpus.json`
- Runner: `evaluation/phase8_regression.py`
- Baseline machine-readable: `docs/testing/baselines/phase-8-baseline.json`
- Unit scoring/schema: `tests/test_evaluation.py`

Suite membuat Mem0 `2.0.14` + Chroma `1.5.9` dalam temporary directory,
memakai Ollama `nomic-embed-text`, menulis semua fixture dengan `infer=False`,
dan melewatkan 20 query melalui `MemoryProvider.prefetch()` serta shadow policy
SQLite yang sama dengan runtime. `user_store_touched=false` tercatat di report.

Corpus mencakup 16 fixture dan 20 query:

| Kategori | Query |
|---|---:|
| Single-session recall | 3 |
| Multi-session aggregation | 3 |
| Knowledge update | 3 |
| Temporal reasoning | 3 |
| Abstention | 2 |
| Cross-tier recall | 3 |
| Security exclusion | 3 |

Fixture security menyalin exact known-bad IDs `bad-ignore-previous`,
`bad-exfiltration`, dan `bad-permanent-behavior` dari korpus Fase 6.

## Bug Retrieval yang Ditemukan

Smoke pertama menunjukkan provider mengirim `limit=5`, tetapi API Mem0 v2
memakai `top_k`. Keyword tidak dikenal diabaikan sehingga seluruh 16 hasil dapat
masuk ke provider. Ini memperbesar context dan membuat precision top-k tidak
benar-benar bounded.

Fix Fase 8 mengubah call menjadi `top_k=5` dan tetap memotong list result menjadi
lima item di sisi provider sebagai defense-in-depth. Unit regression juga
mensimulasikan backend yang mengabaikan top-k dan memverifikasi hanya lima blok
yang diteruskan.

## Threshold Relevansi dan Abstention

Run tanpa threshold merekam distribusi score real-stack:

```text
Expected fact scores:  min=0.567921, median=0.734311, max=0.850527
Abstention top scores: 0.598476, 0.530859
```

Distribusi overlap: query constellation yang tidak punya jawaban mendapat
neighbor Toraja coffee `0.598476`, lebih tinggi daripada tiga expected facts
multi-session (`0.567921`, `0.590208`, `0.595779`). Karena itu threshold `0.60`
akan membuat abstention `100%`, tetapi sekaligus membuang expected facts dan
menurunkan recall multi-session.

Ambang default dipilih konservatif `0.55`, tepat di bawah minimum expected score.
Hasil khusus abstention membaik dari `0/2` menjadi `1/2` (`50%`): passport
berhasil kosong (top score `0.530859`), constellation masih menyuntik satu memory
(top score `0.598476`). Aggregate recall tetap `90%`; semua verdict kategori lain
tidak turun. Ambang dapat dituning dengan `HERMES_DUAL_MEMORY_MIN_SCORE`.

## Metrik Aggregate

```text
Overall verdict:              PARTIAL
Queries:                      20
Answerable queries:           15
Expected fact occurrences:   20
Recalled fact occurrences:   18
Memory Recall:                90.00%
Memory Precision@5:           24.00%
Latency p50:                  160.953 ms
Latency p95:                  223.123 ms
Latency mean:                 174.841 ms
Token total injected:         2,382
Token mean/query:             119.1
Token p50/query:              81
Token p95/query:              334
Abstention accuracy:          50.00%
Security exclusion rate:      100.00%
```

Precision memakai kontrak arsitektur literal: hasil relevan di fixed top-k
dibagi `k=5`. Kategori no-answer (`abstention`, `security_exclusion`) tidak masuk
denominator recall/precision aggregate.

## Hasil per Kategori

| Kategori | Verdict | Recall | Precision@5 | Latency p50/p95 | Mean token |
|---|---|---:|---:|---:|---:|
| Single-session recall | PASS | 100% | 20.00% | 181.074 / 205.886 ms | 108.0 |
| Multi-session aggregation | PASS | 100% | 46.67% | 223.123 / 248.859 ms | 334.333 |
| Knowledge update | PASS | 100% | 20.00% | 187.989 / 199.291 ms | 80.0 |
| Temporal reasoning | PARTIAL | 50% | 13.33% | 187.685 / 213.642 ms | 164.0 |
| Abstention | PARTIAL | n/a | n/a | 152.656 / 154.728 ms | 40.5 |
| Cross-tier recall | PASS | 100% | 20.00% | 154.602 / 160.953 ms | 80.667 |
| Security exclusion | PASS | n/a | n/a | 142.908 / 151.278 ms | 0.0 |

## Kategori Lemah Apa Adanya

### Temporal Reasoning — PARTIAL

- Pertanyaan state **setelah** migrasi PASS.
- Pertanyaan state **sebelum** migrasi FAIL.
- Pertanyaan urutan sebelum+sesudah hanya menemukan state baru (`1/2`).

Alasannya struktural: retrieval normal sengaja menyembunyikan row superseded
dengan `t_invalid`, sesuai policy Fase 4. Shadow index menyimpan history, tetapi
belum ada query mode historis yang boleh membaca before-state secara eksplisit.
Suite tidak membypass gate untuk memaksa PASS.

### Abstention — PARTIAL

Dari dua pertanyaan tanpa jawaban, satu sekarang benar-benar kosong dan satu
masih mengembalikan neighbor Toraja coffee dengan score `0.598476`. Accuracy
menjadi `50%`. Threshold lebih tinggi dapat mengosongkan query tersebut, tetapi
akan menurunkan recall expected facts yang skornya `0.567921–0.595779`.

## Cross-Tier dan Security

Setiap fixture cross-tier diverifikasi bertier `cold` tepat sebelum query;
ketiganya ditemukan (`100% recall`) dan access metrics diperbarui. Sesuai aturan
Fase 5, promosi membutuhkan dua akses dalam tujuh hari: `cold-backup` menjadi
`warm` setelah akses keduanya, sedangkan `cold-incident` dan `cold-checksum`
tetap `cold` setelah satu akses. Baseline membuktikan recall cold serta lifecycle
promotion tanpa memaksa state yang tidak memenuhi syarat.

Ketiga query security memaksa fixture quarantined muncul di raw Mem0 top-k.
Semua fixture tersebut hilang dari visible context setelah shadow policy gate;
leak `0/3`, exclusion rate `100%`.

## Validasi

```text
.venv/bin/python -m unittest discover -s tests -v
Ran 53 tests
OK (skipped=2)

Hermes runtime integration:
Ran 2 tests
OK
```

Runner dapat diulang:

```bash
PYTHONPATH="$HOME/.hermes/hermes-agent:$PWD" \
  "$HOME/.hermes/hermes-agent/venv/bin/python" \
  evaluation/phase8_regression.py \
  --output docs/testing/baselines/phase-8-baseline.json \
  --token-model ag/gemini-3.5-flash-extra-low
```

Run berikutnya dapat memakai `--compare-to` untuk menghasilkan delta metric dan
perubahan category verdict terhadap baseline sebelumnya.

Comparison smoke tanpa token API menghasilkan recall/precision identik,
tidak mengubah category verdict, dan menandai token delta `unavailable` alih-alih
crash atau memakai estimasi.
