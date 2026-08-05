# ADR-0023: Raise System-2 Consolidation Timeout After Payload Bounding

**Status**: Diterima
**Tanggal**: 2026-08-05

## Konteks

ADR-0021 dan ADR-0022 menurunkan batas transcript System-2 menjadi 6.000
karakter per request untuk membatasi ukuran payload combo 9router. Keputusan
itu **menolak menaikkan timeout** karena saat itu payload masih besar (24.000
karakter) dan dua request besar sudah menghabiskan deadline tanpa membuktikan
backend dapat menyelesaikan payload besar.

Konteks itu berubah. Payload kini sudah terkunci di `MAX_TRANSCRIPT_CHARS =
6_000` dan turn tetap atomic (ADR-0022). Namun profil `research` (Nellie)
berhenti memproduksi konsolidasi sejak 2026-07-31 dengan `httpx.ReadTimeout`
pada `llm_call` (baris `configured_call`). Reproduksi langsung pada sesi yang
menggantung mengukur latensi satu request konsolidasi (payload 6.000 karakter,
model `asa-complex` via 9router):

- n = 20 chunk, 19 sukses, 1 timeout @ 30s
- mean = 14.8s, p50 = 12.5s, p95 = 29.1s, p99 = 29.1s, max sukses = 29.1s
- Distribusi sangat fluktuatif: 5.8s s.d. 29.1s

Timeout default 30s (`HERMES_DUAL_MEMORY_LLM_TIMEOUT=30`) **tepat berada di
p95**. Satu lonjakan latensi backend (combo fallback, antrean) melewati ambang
dan memicu kegagalan ~5% dari chunk dalam uji ini. Karena payload sudah
bounded, kegagalan ini murni akibat variabilitas latensi, bukan ukuran request.

## Keputusan

Naikkan timeout request System-2 konsolidasi dari default 30s ke **90s**,
dapat dikonfigurasi lewat `HERMES_DUAL_MEMORY_LLM_TIMEOUT`, dengan batas bawah
60s sebagai guard (nilai <60 ditolak saat inisialisasi).

Selain itu, catat kegagalan konsolidasi ke `maintenance_state` (key
`last_consolidation_error`) berisi JSON `{ts, session_id, chunk, error_type,
error}`. Ini menutup celah observability: saat ini kegagalan hanya muncul di
`logger.exception` dan database tetap terlihat "beku", sehingga diagnosis
membutuhkan pembongkaran log.

## Alternatif yang Dipertimbangkan

- **Menaikkan timeout seinerhana tanpa batas bawah**: ditolak; tanpa guard,
  nilai salah (mis. 5s) bisa masuk via env dan mengulang masalah.
- **Retry lebih banyak per chunk**: ditolak; `consolidate_once` sudah retry
  1x pada output malformed. Retry tambahan pada timeout tidak membuktikan
  backend sehat dan memperbesar beban combo.
- **Menurunkan payload lebih jauh (< 6.000)**: ditolak; itu mengorbankan
  konteks dan memecah sesi menjadi terlalu banyak request, tanpa mengatasi
  akar (variabilitas latensi pada payload yang sudah bounded).
- **Memilih model direct khusus untuk System-2**: ditunda; perubahan
  routing/config lebih luas daripada hardening provider ini (konsisten dengan
  ADR-0022).

## Konsekuensi

Positif:

- Konsolidasi research dapat menyelesaikan chunk yang sebelumnya timeout,
  menghilangkan akumulasi hot rows `consolidated=0` yang menggantung.
- Margin 90s - 29.1s = ~60.9s di atas max teramati, menyerap lonjakan backend
  tanpa mengubah ukuran payload atau invariants fail-closed.
- Kegagalan yang tersisa (timeout berkepanjangan, malformed, JSON invalid)
  kini tercatat di `maintenance_state` sehingga monitorable tanpa membongkar
  log.

Trade-off:

- satu request yang benar-benar macet kini menunggu hingga 90s sebelum
  fail-closed, sehingga worst-case latensi satu chunk naik. Namun konsolidasi
  berjalan di thread daemon non-blocking (ADR/§4.1), jadi tidak menghambat
  turn CLI.
- security admission tetap memakai timeout seminimal mungkin (5s) yang
  terpisah; ADR ini hanya menaikkan timeout konsolidasi, bukan admission.

## Verifikasi

- Jalankan ulang `scripts/repro_consolidation_timeout.py` dengan
  `HERMES_DUAL_MEMORY_LLM_TIMEOUT=90`: 100% chunk sukses.
- Pastikan `maintenance_state.last_consolidation_error` terisi pada simulasi
  kegagalan (test reproduction wajib sebelum merge, sesuai aturan beta).