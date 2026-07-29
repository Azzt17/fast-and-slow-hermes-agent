# Phase 8 Memory Regression

Regression suite real-stack untuk tujuh kategori evaluasi §9. Runner membuat
Mem0 + Chroma dalam temporary directory, memakai Ollama lokal untuk embedding,
dan tidak membaca/menulis memory store user.

## Prasyarat

- Python environment dengan dependency project (`mem0ai`, `chromadb`)
- Ollama aktif dengan `nomic-embed-text`
- Source Hermes tersedia di `~/.hermes/hermes-agent`
- Provider `9router` + credential aktif untuk answerability verifier dan exact
  context-token measurement

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

`--skip-token-measurement` hanya melewati differential context-token calls.
Answerability verifier tetap memakai provider/model yang dipilih karena ia
bagian dari jalur retrieval yang sedang diuji; metric context token ditandai
`unavailable`, bukan diganti estimasi.

Kategori tertentu dapat dijalankan ulang dengan
`--categories abstention` atau daftar comma-separated.

Threshold retrieval default `0.55`; override operasional memakai
`HERMES_DUAL_MEMORY_MIN_SCORE`.

Total timeout answerability default `5` detik; override operasional memakai
`HERMES_DUAL_MEMORY_ANSWERABILITY_TIMEOUT`. Format invalid boleh retry sekali
di dalam total timeout yang sama.

Query dengan marker temporal eksplisit memakai mode historis ADR-0014. Mode ini
tetap melalui raw Mem0 top-k dan shadow policy; hanya superseded semantic
trusted yang ditambahkan ke current state dengan validity attributes.

Kandidat scored yang lolos threshold kemudian melalui answerability gate
ADR-0015. Runner memakai model `--token-model` untuk verifier dan merekam call,
candidate, accepted, latency, prompt token, completion token, retry, serta
unavailable count. Kandidat unscored legacy tetap mengikuti compatibility path.

## Interpretasi

- Recall/precision hanya memakai query yang memang punya expected facts.
- Precision memakai fixed `top_k=5`, sesuai definisi arsitektur.
- Abstention dan security exclusion punya metric/verdict terpisah.
- `PARTIAL`/`FAIL` tetap ditulis ke report dengan alasan; exit code runner tetap
  nol selama suite berhasil dieksekusi dan report valid.
