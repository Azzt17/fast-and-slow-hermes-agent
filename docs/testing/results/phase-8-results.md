# Hasil Uji Fase 8

**Tanggal**: 2026-07-29
**Status**: PASS (suite dan baseline overall PASS)

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
Token verifier dicatat terpisah dan tidak dicampur dengan token context yang
akhirnya diinjeksi.

## Struktur Suite

- Corpus: `evaluation/phase8_corpus.json`
- Runner: `evaluation/phase8_regression.py`
- Baseline machine-readable: `docs/testing/baselines/phase-8-baseline.json`
- Unit scoring/schema: `tests/test_evaluation.py`

Suite membuat Mem0 `2.0.14` + Chroma `1.5.9` dalam temporary directory,
memakai Ollama `nomic-embed-text`, menulis semua fixture dengan `infer=False`,
dan melewatkan 48 query melalui `MemoryProvider.prefetch()` serta shadow policy
SQLite yang sama dengan runtime. `user_store_touched=false` tercatat di report.

Corpus follow-up mencakup 16 fixture dan 48 query. Kategori abstention diperbesar
dari 2 menjadi 30 hard-negative yang dekat secara semantik tetapi menanyakan
atribut yang tidak pernah disimpan:

| Kategori | Query |
|---|---:|
| Single-session recall | 3 |
| Multi-session aggregation | 3 |
| Knowledge update | 3 |
| Temporal reasoning | 3 |
| Abstention | 30 |
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

## Answerability Gate dan Abstention

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
(top score `0.598476`). Pada baseline awal sebelum ADR-0014, aggregate recall
tetap `90%`; semua verdict kategori lain tidak turun. Follow-up temporal kemudian
menaikkan aggregate recall menjadi `100%` tanpa mengubah threshold. Ambang dapat
dituning dengan `HERMES_DUAL_MEMORY_MIN_SCORE`.

## Metrik Aggregate

```text
Overall verdict:              PASS
Queries:                      48
Answerable queries:           15
Expected fact occurrences:   20
Recalled fact occurrences:   20
Memory Recall:                100.00%
Memory Precision@5:           26.67%
Latency p50:                  1350.603 ms
Latency p95:                  1675.018 ms
Latency mean:                 1255.022 ms
Token total injected:         1,782
Token mean/query:             37.125
Token p50/query:              0
Token p95/query:              168
Abstention accuracy:          100.00%
Security exclusion rate:      100.00%
```

Precision memakai kontrak arsitektur literal: hasil relevan di fixed top-k
dibagi `k=5`. Kategori no-answer (`abstention`, `security_exclusion`) tidak masuk
denominator recall/precision aggregate.

## Hasil per Kategori

| Kategori | Verdict | Recall | Precision@5 | Latency p50/p95 | Mean token |
|---|---|---:|---:|---:|---:|
| Single-session recall | PASS | 100% | 20.00% | 1191.148 / 1231.591 ms | 80.0 |
| Multi-session aggregation | PASS | 100% | 46.67% | 1375.370 / 1574.224 ms | 193.333 |
| Knowledge update | PASS | 100% | 20.00% | 1376.945 / 1609.062 ms | 80.0 |
| Temporal reasoning | PASS | 100% | 26.67% | 1286.499 / 1590.319 ms | 160.0 |
| Abstention | PASS | n/a | n/a | 1377.667 / 1677.652 ms | 0.0 |
| Cross-tier recall | PASS | 100% | 20.00% | 1089.868 / 1489.477 ms | 80.667 |
| Security exclusion | PASS | n/a | n/a | 168.376 / 176.167 ms | 0.0 |

## Follow-up Kategori

### Temporal Reasoning — PASS (Follow-up ADR-0014)

- Pertanyaan state **sebelum** migrasi menemukan old-state trusted.
- Pertanyaan state **setelah** migrasi tetap menyembunyikan old-state.
- Pertanyaan urutan sebelum+sesudah menemukan kedua state (`2/2`).

Provider kini mendeteksi intent historis dengan marker lexical deterministik.
Hanya row superseded `semantic` berstatus `trusted` yang boleh melewati gate;
blok diberi `keadaan_temporal`, `berlaku_mulai`, dan `berlaku_sampai`. Query
current-state, quarantine, orphan bertanda shadow, dan invalid episodic tetap
diblok. Recall temporal naik `50%` → `100%`; token temporal mean naik karena
before+current state sengaja masuk bersama pada query historis.

### Abstention — PASS (Follow-up ADR-0015)

Pre-gate expanded run hanya abstain pada `1/30` query (`3.33%`). False neighbor
bahkan mencapai score `0.846105`, membuktikan tidak ada zona score tinggi yang
aman diterima langsung. ADR-0015 karena itu memverifikasi seluruh kandidat scored
yang lolos threshold `0.55` setelah shadow policy. Satu batch JSON menilai bukti
langsung per kandidat; format invalid boleh retry sekali dalam total timeout
yang sama, lalu fail-closed.

Final run mencapai abstention `30/30` (`100%`) tanpa menurunkan recall atau
security. Semua `44` verifier query selesai `verified`; `unavailable=0`, retry=0.
Biayanya signifikan: verifier latency p50/p95 `1166.972/1488.342 ms`, prompt
token total `111,905`, completion token `408`.

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
Ran 62 tests
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
