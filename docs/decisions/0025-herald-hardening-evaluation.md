# ADR-0025: Evaluasi mekanisme herald untuk Fase 9 (micro-compaction & context engine)

**Status**: Diterima
**Tanggal**: 2026-08-16

## Konteks

Hermes di-update ke herald v0.20.1 (2026-08-13). Audit kompatibilitas (ADR-0024,
2026-08-16) mengidentifikasi dua mekanisme baru yang berpotensi diintegrasikan
pada Fase 9:

1. **Micro-compaction** (`compression.micro_compact: true`, off by default):
   setelah tiap turn, lipat pertukaran tertua yang belum ter-absorb ke ringkasan
   berjalan. Biaya per-turn terbatas; **menulis ulang history → break prompt
   cache setiap turn** (peringatan eksplisit di `docs/micro-compaction.md`).
2. **Context engine pluggable** (`context.engine`, default `"compressor"`):
   mengganti compression dengan engine pihak ketiga (mis. LCM) via
   `plugins/context_engine/<name>/`. Hanya satu engine aktif.

## Data dari Beta (dogfooding 29 Jul – 16 Agu 2026)

- Beta selesai 2026-08-16: 14/14 hari aktif, 49/30 sesi, baseline PASS
  (recall 1.0, precision 0.2667, p50 1285ms, p95 2075ms).
- Konsolidasi System-2 berjalan normal dengan batch compression default
  (threshold 0.5) — tidak ada insiden compression-related selama beta.
- Prompt caching aktif (`prompt_caching.cache_ttl: 5m`) dan merupakan aset
  penting untuk biaya per-turn (dok AGENTS.md Hermes: "prompt caching is
  sacred"; AGENTS.md repo hermes-agent eksplisit melarang mutasi konteks
  masa lalu yang memecah cache).
- p95 konsolidasi 2075ms — masih di bawah batas 90s (ADR-0023), tidak ada
  tekanan untuk mengubah distribusi biaya compression.

## Keputusan

### Task 5 — Micro-compaction: TIDAK diaktifkan

Alasan:

- **Biaya cache break > benefit distribusi biaya.** Micro-compaction menulis
  ulang history setiap turn → memecah prompt cache → kenaikan biaya per-turn
  yang tidak sebanding dengan benefit "tidak ada stall panjang" (stall batch
  compression saat ini jarang dan dapat diterima).
- **Fidelity turun lebih awal.** Detail percakapan menjadi ringkasan lebih
  cepat daripada batch compression — merugikan System-1 hot capture dan
  konsolidasi yang bergantung pada detail turn.
- **Dual-memory sudah menangani long-context** via `on_pre_compress`
  konsolidasi — penambahan micro-compaction justru tumpang tindih.

Keputusan: biarkan `compression.micro_compact` **off** (default). Tidak ada
perubahan konfigurasi.

### Task 6 — Context engine: pertahankan default `compressor`

Alasan:

- Default compressor sudah terbukti selama beta (14 hari, tidak ada insiden).
- Engine alternatif (mis. LCM) belum memiliki bukti keunggulan untuk workload
  dual-memory (recall/konsolidasi); mengganti = risiko baru tanpa benefit
  terukur.
- Prinsip YAGNI: jangan menambah kompleksitas tanpa kebutuhan konkret.

Keputusan: gunakan `context.engine: compressor` (default). Tidak ada perubahan
konfigurasi.

## Alternatif yang Dipertimbangkan

- **Aktifkan micro-compaction** — ditolak: break prompt cache per turn,
  fidelity turun, tumpang tindih dengan `on_pre_compress`.
- **Pasang context engine alternatif (LCM)** — ditolak: tanpa bukti benefit
  untuk workload dual-memory; risiko baru.
- **Evaluasi lanjutan dengan A/B** — dipertimbangkan untuk Fase 10+ jika
  terjadi insiden compression atau p95 latency naik signifikan.

## Konsekuensi

- Tidak ada perubahan konfigurasi produksi (3 profile).
- Keputusan terdokumentasi; evaluasi ulang jika: (a) batch compression
  menyebabkan stall yang mengganggu, (b) p95 latency konsolidasi naik > 50%,
  (c) muncul engine alternatif dengan bukti benchmark untuk dual-memory.
- ADR ini menutup Task 5 & 6 rencana Fase 9 (`.hermes/plans/2026-08-16_153000-fase9-hardening-portofolio.md`).
