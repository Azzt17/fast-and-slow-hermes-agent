# Changelog

## 2026-08-05

- [beta-0.1 hardening] menaikkan timeout konsolidasi System-2 dari 30s ke 90s dengan guard minimum 60s (ref ADR-0023). Diagnosis: profil research (Nellie) berhenti berkonsolidasi sejak 2026-07-31 karena `httpx.ReadTimeout` — timeout 30s berada tepat di p95 latensi (29.1s). Reproduksi pada 20 chunk mengonfirmasi 1 timeout pada payload kecil; rerun 21/21 chunk sukses setelah perbaikan, termasuk chunk yang makan 38.8s (bukti 30s terlalu ketat). Tambahan observability: kegagalan konsolidasi dicatat ke `maintenance_state.last_consolidation_error`. Regression suite 16 passed.

## 2026-07-29

- [beta-0.1] menetapkan checkpoint dogfooding `v0.1.0-beta.1` setelah Fase 8, protokol uji 21 hari/minimal 14 hari aktif dan 30 sesi nyata, rollback code+data, jurnal append-only, serta handoff wajib lintas-session sebelum Fase 9 (ref ADR-0016).
- [fase-8 follow-up] menambahkan bounded batch answerability gate untuk seluruh kandidat scored yang lolos threshold/shadow policy dan memperbesar abstention corpus menjadi 30 hard-negative. Full 48-query real-stack menjadi overall `PASS`: abstention `100%`, recall `100%`, precision@5 `26.67%`, security exclusion `100%`; trade-off latency p50/p95 `1350.603/1675.018 ms` dan verifier `111,905` prompt token dicatat eksplisit (ref ADR-0015).
- [fase-8 follow-up] menutup gap temporal reasoning melalui mode historis deterministik yang hanya membuka superseded semantic trusted; current-state, quarantine, dan invalid episodic tetap tersembunyi. Real-stack temporal recall naik `50%` → `100%`; baseline aggregate recall menjadi `100%`, precision@5 `26.67%`, security exclusion tetap `100%`, overall tetap `PARTIAL` hanya karena abstention `50%` (ref ADR-0014).
- [fase-8] menutup regression suite real-stack terisolasi untuk 20 query dalam tujuh kategori, memperbaiki retrieval Mem0 menjadi `top_k=5` plus cap lokal, dan menambahkan relevance threshold `0.55`. Baseline mencatat recall `90%`, precision@5 `24%`, latency p50/p95 `160.953/223.123 ms`, mean context `119.1` token/query, security exclusion `100%`, serta gap temporal reasoning dan abstention tetap `PARTIAL` apa adanya (ref ADR-0013).

## 2026-07-28

- [fase-7] menutup procedural memory via Skills system: `new_skills` trusted diroute ke draft non-active dengan transisi candidate→pending/redundant, similarity gate memblokir duplikasi, approval CLI memakai validator/security writer native Hermes lalu menandai provenance agent-created untuk Curator. Sesi Hermes nyata 18 tool call menghasilkan draft, promosi `SKILL.md`, dan Curator memeriksa 69 skill tanpa error (ref ADR-0012).
- [fase-6] menutup admission keamanan dua lapis: scanner `tools.threat_patterns` Hermes + semantic hidden-instruction review bounded, transition candidate→trusted/quarantined nyata, semantic failure fail-closed, dan quarantine diblokir oleh retrieval/compression gate existing. Korpus awal 6 known-bad/6 known-good mencapai catch `100%` dan FPR `0%` setelah tuning (ref ADR-0011).
- [fase-5] menutup episodic decay dan cold compaction: formula `R(t)=exp(-t/S)`, promosi/demosi berbasis access window, throttle persisten 24 jam pada `initialize()`/`on_session_end()`, serta compaction Sistem 2 dengan lineage sumber tanpa delete. Semantic exclusion dan failure injection endpoint LLM tidak terjangkau PASS (ref ADR-0010).
- [fase-4] menutup shadow index dan bi-temporal contradiction handling: setiap essence baru mendapat row `memory_index`, fakta semantic lama di-supersede melalui `t_invalid` tanpa dihapus, dan jalur retrieval Fase 3 memblokir shadow invalid/non-trusted. Skenario lintas sesi serta false-positive entity overlap PASS (ref ADR-0009).

## 2026-07-27

- [fase-3] menutup retrieval lintas sesi: `prefetch()` bounded, `queue_prefetch()` non-blocking, delimiter data historis aktif, dan identitas Mem0 stabil per profil memungkinkan recall lintas sesi (ref ADR-0008).
- [fase-2] menutup trigger dan konsolidasi Sistem 2: `on_session_end`/`on_pre_compress` menghasilkan laporan terstruktur, menulis essence melalui `mem0.add(..., infer=False)`, serta hanya menandai hot rows selesai setelah write berhasil (ref ADR-0002 dan ADR-0005).

## 2026-07-26

- [fase-1] menutup hot tier: `hot_sessions` aktif, `sync_turn()` non-blocking, dan persistensi restart terverifikasi (ref ADR-0002).
