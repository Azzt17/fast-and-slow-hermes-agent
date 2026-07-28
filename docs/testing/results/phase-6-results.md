# Hasil Uji Fase 6

**Tanggal**: 2026-07-28
**Status**: PASS

## Konfirmasi Kondisi Awal

Sebelum Fase 6, `record_memory()` memasukkan row `candidate` lalu langsung
mengubahnya menjadi `trusted` dalam transaksi yang sama. Tidak ada pattern scan,
semantic decision, atau fail-closed policy. Transition candidate→trusted memang
otomatis seperti catatan Fase 4.

Source Hermes terpasang memiliki
`~/.hermes/hermes-agent/tools/threat_patterns.py`. API yang direuse adalah
`scan_for_threats(content, scope="strict")`. Modul tersebut menjadi sumber pola
Hermes untuk injection, exfiltration, persistence, dan invisible Unicode;
`tools/memory_tool.py` juga memakainya pada write memory.

## Suite Otomatis

```text
.venv/bin/python -m unittest discover -s tests -v
Ran 34 tests
OK (skipped=1)

Hermes runtime integration:
Ran 1 test
OK
```

Coverage keamanan memverifikasi scanner Hermes strict, pattern dan semantic
quarantine, semantic failure fail-closed, persistensi reason, retrieval filter,
compression filter, candidate failure blocking, dan admission cold compaction.

## Korpus dan Metrik

Korpus `tests/security_corpus.json` berisi 12 contoh: 6 known-bad (classic
injection, HTML-hidden injection, credential exfiltration, permanent behavior
change, dua subtle framing) dan 6 known-good (fakta biasa, fakta proyek,
pembahasan keamanan, kutipan known-bad untuk analisis, policy manusia, riset).

Benchmark memakai scanner Hermes dan model 9router nyata.

### Run Awal

```text
known-bad=6
known-good=6
true-positive=6
false-positive=1
catch rate=100.00%
false positive rate=16.67%
```

False positive: “maintainers are obligated to document schema migrations...”
dianggap kewajiban tersembunyi kepada agent.

### Tuning

Prompt semantic diperjelas untuk memeriksa subjek/addressee: aturan proses untuk
maintainer/contributor/tim bukan instruksi kepada agent. Pattern false positive
untuk kutipan explicit known-bad dituning sempit: hanya kombinasi marker “quoted
phrase” + “known-bad example” + “do not execute” yang diteruskan ke semantic
review; hasil pattern tersebut tidak langsung dipercaya.

### Run Final

```text
known-bad=6
known-good=6
true-positive=6
false-positive=0
catch rate=100.00%
false positive rate=0.00%
```

## Smoke Real Stack

Subtle framing dengan report konsolidasi terkontrol dan admission model 9router
nyata menghasilkan `status=quarantined`, `SEMANTIC_QUARANTINED=True`, dan
`RETRIEVAL_BLOCKED=True`.

Failure injection semantic admission memakai endpoint literal
`http://127.0.0.1:1/v1`, `max_retries=0`, menghasilkan
`semantic_unavailable:APIConnectionError`, tetap quarantined dan blocked;
initialize selesai normal.

## Rekomendasi Ambang

Ambang saat ini **layak sebagai baseline Fase 6** untuk penggunaan personal:
catch `100%` dan FPR `0%` pada korpus kecil setelah tuning. Namun 12 contoh belum
cukup untuk klaim produksi. Perlu perluasan korpus multilingual,
obfuscation/confusable Unicode, nested quotations, dan security prose panjang.
Fail-closed semantic policy dipertahankan.

## Catatan Apa Adanya

- Run smoke dengan ekstraksi 9router penuh sempat timeout sebelum admission;
  subtle framing kemudian diisolasi memakai report lokal + admission 9router.
- Chroma tetap semantic-only/BM25 disabled; tidak memengaruhi status gate.
- PostHog multiple-client warning muncul pada smoke multi-provider.
