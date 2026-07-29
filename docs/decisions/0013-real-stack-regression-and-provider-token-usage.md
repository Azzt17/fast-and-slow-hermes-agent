# ADR-0013: Baseline regression real-stack dan token usage provider

**Status**: Diterima
**Tanggal**: 2026-07-29

## Konteks

Fase 8 membutuhkan baseline recall, precision, latency p50/p95, dan token
efficiency yang dapat dijalankan ulang. Fase 3 sudah mengukur jalur retrieval
dengan stopwatch `time.monotonic()` di sekitar `prefetch()`, tetapi tidak
menyimpan telemetry produksi. Menambah recorder global hanya untuk benchmark
akan memperbesar surface plugin dan mencampur data evaluasi dengan runtime user.

Token count historis di hot tier memakai jumlah kata dan bukan tokenizer nyata.
Hermes juga menyediakan beberapa estimator kasar, tetapi requirement Fase 8
meminta token aktual dari blok context yang diinjeksi. Endpoint 9router
OpenAI-compatible mengembalikan `usage.prompt_tokens`; model combo `asa-complex`
pernah meroute ke backend yang EOL, sedangkan model direct
`ag/gemini-3.5-flash-extra-low` memberikan usage stabil.

## Keputusan

Regression suite memakai instance Mem0 + Chroma + Ollama yang nyata tetapi
terisolasi dalam temporary directory. Fixture ditulis dengan `infer=False`, lalu
setiap query melewati `MemoryProvider.prefetch()` dan policy gate SQLite yang
sama dengan runtime. Store user di `~/.hermes` tidak dibaca atau diubah.

Smoke awal menemukan incompatibility API: provider Fase 3 mengirim `limit=5`,
tetapi Mem0 v2 memakai `top_k`; keyword yang tidak dikenali diabaikan sehingga
semua hasil masuk context. Canonical retrieval diperbaiki menjadi `top_k=5` dan
tetap memotong hasil di sisi provider sebagai defense-in-depth.

Distribusi score baseline awal menunjukkan expected facts `0.567921–0.850527`,
sementara dua abstention query memiliki top score `0.598476` dan `0.530859`.
Karena distribusi overlap, tidak ada threshold yang membuat keduanya abstain
tanpa berisiko menurunkan recall. Ambang default dipilih konservatif `0.55`:
di bawah minimum expected score, tetapi cukup untuk mengosongkan abstention
passport dan membuang neighbor lemah. Ambang dapat dioverride melalui
`HERMES_DUAL_MEMORY_MIN_SCORE`.

Latency memakai pola Fase 3: `time.perf_counter()` tepat sebelum dan sesudah
`prefetch()`. Suite menjalankan 20 query dan menghitung percentile nearest-rank
p50/p95 dari distribusi wall-clock tersebut.

Token Efficiency memakai differential usage provider. Satu prompt kosong
menjadi baseline overhead; setiap blok `<memori_lampau>` dikirim sebagai prompt
ke model direct `ag/gemini-3.5-flash-extra-low`, lalu token blok dihitung sebagai
`prompt_tokens(block) - prompt_tokens(empty)`. Jika provider tidak mengembalikan
usage atau model tidak tersedia, metric berstatus error dan suite tidak
menggantinya dengan estimasi karakter/kata.

Laporan JSON menyimpan schema version, environment, fixture/query definitions,
hasil per query, aggregate metrics, category verdict, dan alasan failure/partial.
Precision dihitung atas hasil visible yang benar-benar masuk top-k; empty result
untuk abstention bernilai precision 1, sedangkan empty result saat fakta
diharapkan bernilai 0.

## Alternatif yang Dipertimbangkan

- Menambahkan telemetry latency permanen ke provider: ditolak karena benchmark
  dapat mengukur boundary yang sama tanpa mengubah runtime path.
- Fake Mem0: ditolak karena tidak mengukur embedding/ranking/latency nyata.
- Memakai store user aktif: ditolak karena hasil tidak reproducible dan berisiko
  mencemari memori personal.
- Menghitung token dengan `split()`, rasio karakter, atau estimator Hermes:
  ditolak karena bukan token aktual.
- Memakai model combo untuk token usage: ditolak karena routing backend dapat
  berubah antar-run dan pernah memilih model EOL.

## Konsekuensi

Baseline mencerminkan stack lokal sebenarnya dan aman diulang, tetapi hasil
latency tetap sensitif terhadap load Ollama/host. Token measurement membutuhkan
endpoint 9router dan menambah panggilan model kecil. Temporal reasoning normal
diperkirakan partial karena retrieval policy sengaja menyembunyikan row
superseded; suite harus mencatat gap tersebut, bukan membypass policy.
