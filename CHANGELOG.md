# Changelog

## 2026-07-28

- [fase-5] menutup episodic decay dan cold compaction: formula `R(t)=exp(-t/S)`, promosi/demosi berbasis access window, throttle persisten 24 jam pada `initialize()`/`on_session_end()`, serta compaction Sistem 2 dengan lineage sumber tanpa delete. Semantic exclusion dan failure injection endpoint LLM tidak terjangkau PASS (ref ADR-0010).
- [fase-4] menutup shadow index dan bi-temporal contradiction handling: setiap essence baru mendapat row `memory_index`, fakta semantic lama di-supersede melalui `t_invalid` tanpa dihapus, dan jalur retrieval Fase 3 memblokir shadow invalid/non-trusted. Skenario lintas sesi serta false-positive entity overlap PASS (ref ADR-0009).

## 2026-07-27

- [fase-3] menutup retrieval lintas sesi: `prefetch()` bounded, `queue_prefetch()` non-blocking, delimiter data historis aktif, dan identitas Mem0 stabil per profil memungkinkan recall lintas sesi (ref ADR-0008).
- [fase-2] menutup trigger dan konsolidasi Sistem 2: `on_session_end`/`on_pre_compress` menghasilkan laporan terstruktur, menulis essence melalui `mem0.add(..., infer=False)`, serta hanya menandai hot rows selesai setelah write berhasil (ref ADR-0002 dan ADR-0005).

## 2026-07-26

- [fase-1] menutup hot tier: `hot_sessions` aktif, `sync_turn()` non-blocking, dan persistensi restart terverifikasi (ref ADR-0002).
