# Hasil Uji: Perbaikan Timeout Konsolidasi (ADR-0023)

**Tanggal**: 2026-08-05
**Status**: PASS
**Referensi**: ADR-0023, script `scripts/repro_consolidation_timeout.py`

## Latar Belakang

Profil `research` (Nellie) berhenti memproduksi konsolidasi sejak 2026-07-31
karena `httpx.ReadTimeout` pada `llm_call` konsolidasi. Timeout default 30s
(`HERMES_DUAL_MEMORY_LLM_TIMEOUT`) berada tepat di p95 latensi (29.1s),
sehingga satu lonjakan dapat menggagalkan chunk.

## Pengukuran Sebelum Perbaikan (timeout 30s)

Dari 20 chunk pada 2 sesi research yang menggantung:

| Metrik | Nilai |
|---|---|
| n chunk | 20 |
| sukses | 19 |
| timeout | 1 (`APITimeoutError: Request timed out` @ 30.0s) |
| mean | 14.8s |
| p50 | 12.5s |
| p95 | 29.1s |
| p99 | 29.1s |
| min / max (sukses) | 5.8s / 29.1s |

Chunk yang timeout: sesi `20260731_151911_a1bc21d1` chunk 2 (2 baris, ~4370
karakter) — fail padahal payload kecil, membuktikan kegagalan murni akibat
variabilitas latensi backend combo 9router, bukan ukuran request.

## Perbaikan

- Naikkan default timeout `HERMES_DUAL_MEMORY_LLM_TIMEOUT` 30s → 90s dengan
  guard minimum 60s (nilai <60 di-clamp ke 60).
- Tambah observability: kegagalan konsolidasi dicatat ke
  `maintenance_state.last_consolidation_error` (JSON berisi ts, session_id,
  chunk, error_type, error) sehingga tidak lagi silent.

## Verifikasi Setelah Perbaikan (timeout 90s)

Rerun `scripts/repro_consolidation_timeout.py` dengan
`HERMES_DUAL_MEMORY_LLM_TIMEOUT=90` pada 3 sesi research yang menggantung:

| Sesi | Chunk | Hasil |
|---|---|---|
| 20260730_184221_077ec125 | 4 | 4/4 sukses |
| 20260731_151911_a1bc21d1 | 10 | 10/10 sukses (chunk 2 yang dulu gagal kini SUCCESS in 19.3s) |
| 20260804_210420_ecd900e7 | 7 | 7/7 sukses |
| **Total** | **21** | **21/21 sukses (100%)** |

Catatan: chunk 4 sesi 20260730 makan **38.8s** — melebihi ambang 30s lama.
Ini bukti langsung bahwa timeout 30s memang terlalu ketat dan 90s diperlukan.

## Regression Suite

`pytest tests/test_storage.py tests/test_consolidation.py tests/test_shadow_index.py`
→ **16 passed** setelah perbaikan, tanpa deprecation warning.

## Kesimpulan

Perbaikan timeout 90s + guard 60s + observability kegagalan berhasil
memulihkan konsolidasi System-2 pada profil research. 21/21 chunk sukses
setelah perbaikan, termasuk chunk yang sebelumnya pasti timeout. Hot rows
yang menggantung kini dapat dikonsolidasi oleh trigger berikutnya.