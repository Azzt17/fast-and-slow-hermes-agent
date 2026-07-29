# Phase 8 Memory Regression

Regression suite real-stack untuk tujuh kategori evaluasi §9. Runner membuat
Mem0 + Chroma dalam temporary directory, memakai Ollama lokal untuk embedding,
dan tidak membaca/menulis memory store user.

## Prasyarat

- Python environment dengan dependency project (`mem0ai`, `chromadb`)
- Ollama aktif dengan `nomic-embed-text`
- Source Hermes tersedia di `~/.hermes/hermes-agent`
- Provider `9router` + credential aktif untuk exact token measurement

## Membuat Baseline

```bash
PYTHONPATH="$HOME/.hermes/hermes-agent:$PWD" \
  "$HOME/.hermes/hermes-agent/venv/bin/python" \
  evaluation/phase8_regression.py \
  --output docs/testing/baselines/phase-8-baseline.json \
  --token-model ag/gemini-3.5-flash-extra-low
```

## Membandingkan Run

Jangan menimpa baseline saat mengecek delta:

```bash
PYTHONPATH="$HOME/.hermes/hermes-agent:$PWD" \
  "$HOME/.hermes/hermes-agent/venv/bin/python" \
  evaluation/phase8_regression.py \
  --output /tmp/phase8-current.json \
  --compare-to docs/testing/baselines/phase-8-baseline.json
```

`--skip-token-measurement` tersedia untuk smoke lokal tanpa API. Metric token
akan ditandai `unavailable`, bukan diganti estimasi.

Kategori tertentu dapat dijalankan ulang dengan
`--categories abstention` atau daftar comma-separated.

Threshold retrieval default `0.55`; override operasional memakai
`HERMES_DUAL_MEMORY_MIN_SCORE`.

## Interpretasi

- Recall/precision hanya memakai query yang memang punya expected facts.
- Precision memakai fixed `top_k=5`, sesuai definisi arsitektur.
- Abstention dan security exclusion punya metric/verdict terpisah.
- `PARTIAL`/`FAIL` tetap ditulis ke report dengan alasan; exit code runner tetap
  nol selama suite berhasil dieksekusi dan report valid.
