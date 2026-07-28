# Hasil Uji Fase 5

**Tanggal**: 2026-07-28
**Status**: PASS

## Suite Otomatis

Perintah:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Hasil:

```text
Ran 26 tests
OK (skipped=1)
```

Test yang skip mensyaratkan interpreter runtime Hermes dan dijalankan terpisah:

```bash
/home/wajdi/.hermes/hermes-agent/venv/bin/python \
  -m unittest tests.test_hermes_runtime_integration -v
```

Hasil:

```text
Ran 1 test
OK
```

Sembilan test Fase 5 memverifikasi:

- formula exact `R(t)=exp(-t/S)` dan demosi dasar;
- semantic sepenuhnya dikecualikan dari decay;
- promosi cold setelah dua akses dalam tujuh hari;
- tidak ada promosi jika akses baru terjadi setelah jendela tujuh hari;
- queue prefetch tidak menghitung akses sebelum hasil benar-benar dikonsumsi;
- compaction menghasilkan ringkasan representatif dan lineage seluruh sumber;
- `initialize()`/`on_session_end()` berbagi throttle persisten 24 jam;
- claim decay aktif kembali setelah 24 jam;
- timeout compaction graceful dan tidak mengubah sumber.

## Skenario Manual Decay dan Cold Compaction

Stack nyata:

- interpreter Hermes: `~/.hermes/hermes-agent/venv/bin/python`;
- Mem0 OSS + Chroma;
- embedder Ollama `nomic-embed-text`;
- LLM 9router Hermes untuk cold compaction;
- SQLite/Chroma temporer terisolasi.

Data simulasi:

- dua episodic mirip tentang kunjungan kebun kopi dalam perjalanan Toraja;
- satu semantic tentang preferensi durable Farid pada kopi Toraja;
- seluruh `last_accessed` episodic/semantic dimundurkan 30 hari;
- stability awal mengikuti `max(importance_score/2, 0.5)`.

Retrievability episodic:

```text
importance=4, stability=2.0, R=3.059023205018258e-07
importance=6, stability=3.0, R=4.5399929762484854e-05
```

Keduanya di bawah `0.3`, sehingga didemosi. Hasil compaction nyata:

```text
Farid mengunjungi kebun kopi dan mencicipi biji kopi lokal saat perjalanan kopi Toraja.
```

Hasil audit:

```text
CYCLE ran=true
episodic sources: tier=cold, t_invalid terisi, superseded_by=hasil compaction
compacted result: memory_type=episodic, tier=warm, status=trusted
semantic source: tier=warm, t_invalid=NULL
SEMANTIC_UNCHANGED True
SOURCES_PRESERVED True
```

`memory_compaction_sources` mengembalikan kedua `mem0_id` sumber untuk hasil
gabungan. Sumber tetap ada di Mem0 dan `memory_index`; tidak ada delete.

Simulasi promosi:

```text
demote episodic → akses hari ke-1 → tetap cold
akses hari ke-2 → tier=warm
access_count=2
stability=4.5
```

Siklus kedua satu jam setelah decay:

```text
{"ran": false, "demoted": [], "compacted": []}
```

Ini memverifikasi throttle persisten 24 jam.

## Catatan Apa Adanya

- Chroma masih semantic-only; warning BM25 disabled tetap muncul.
- PostHog memberi warning multiple clients pada proses smoke, tanpa mengubah
  hasil.
- Cold compaction memerlukan cluster minimal dua hasil dengan score Mem0
  `>=0.75`; singleton cold tetap cold dan valid.
- Claim 24 jam dicatat sebelum kerja berat. Crash proses setelah claim dapat
  menunda retry sampai interval berikutnya; trade-off ini dicatat ADR-0010.

## Failure Injection Cold Compaction

Cold compaction diuji melalui lifecycle hook nyata dengan:

- Mem0/Chroma/Ollama aktif;
- dua episodic serupa dimundurkan 30 hari agar didemosi dan membentuk cluster;
- timestamp `last_decay_run` dimundurkan 25 jam agar maintenance terpicu dari
  `on_session_end()`;
- callable compaction memakai OpenAI client ke endpoint literal
  `http://127.0.0.1:1/v1`, timeout `0.25s`, `max_retries=0`, dan model invalid.

Hasil:

```text
STARTUP_RETURNED True
STARTUP_SECONDS 1.8006
PROVIDER_READY True True
HOOK_RETURN_SECONDS 0.0007
HOOK_NON_BLOCKING True
FAILURE_LOGGED True
SOURCES_SAFE True
NO_PARTIAL_RESULT True
SESSION_STILL_USABLE True
```

Log relevan:

```text
WARNING hermes_dual_memory.decay: Cold compaction LLM failed: Connection error.
WARNING hermes_dual_memory_phase5_failure: Decay maintenance completed trigger=on_session_end demoted=2 compacted=0
```

Kedua sumber berakhir aman sebagai `tier=cold`, `status=trusted`,
`t_invalid=NULL`, dan `superseded_by=NULL`. Tidak ada row hasil compaction.
Artinya invalidasi sumber baru terjadi di transaksi `record_compaction()` setelah
ringkasan berhasil ditulis ke Mem0 dan menghasilkan `mem0_id`; kegagalan model
tidak dapat meninggalkan sumber setengah-invalidated.
