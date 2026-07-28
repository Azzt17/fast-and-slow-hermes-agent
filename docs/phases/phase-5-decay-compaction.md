# Fase 5: Decay, Promosi/Demosi, Cold Compaction

**Status**: Selesai
**Tanggal Selesai**: 2026-07-28

## Goal

Retrievability episodic dihitung opportunis; entri redup didemosi, entri cold
yang kembali relevan dipromosikan, dan cluster cold diringkas tanpa kehilangan
lineage.

## Yang Dibangun

- [x] Formula `R(t)=exp(-t/S)` untuk episodic trusted aktif.
- [x] Access tracking dan promosi ulang tujuh hari.
- [x] Throttle persisten 24 jam pada lifecycle hook existing.
- [x] Cold compaction berbasis similarity Mem0 dan Sistem 2.
- [x] Lineage sumber compaction tanpa penghapusan row.
- [x] Test unit, resiliensi, dan skenario simulasi manual.

## Failure Mode yang Diwaspadai

Fakta semantic ikut terdemosi, maintenance memblokir startup/session end, atau
sumber cold hilang tanpa jejak setelah compaction.

## Kriteria Keluar (Exit Criteria)

Simulasi memanipulasi `last_accessed`/`access_count`, menjalankan decay, dan
memverifikasi episodic berpindah tier sesuai formula sementara semantic tidak
berubah. Cold cluster menghasilkan essence representatif dan seluruh sumber
tetap dapat diaudit.

## Hasil Uji

Lihat [hasil uji Fase 5](../testing/results/phase-5-results.md). Suite regression
PASS (`26 tests`, satu skip interpreter-specific yang PASS pada venv Hermes).
Smoke nyata Mem0/Chroma/Ollama/9router juga PASS: dua episodic tua didemosi dan
digabung, semantic tetap warm, lineage sumber utuh, promosi dua akses berhasil,
dan siklus kedua dalam 24 jam dilewati. Failure injection endpoint LLM tidak
terjangkau juga PASS: hook tetap non-blocking, error tercatat, dan kedua sumber
tetap cold/trusted tanpa `t_invalid` atau hasil gabungan parsial.

## Catatan/Pembelajaran

ADR-0010 menetapkan state pendamping, semantics claim 24 jam, dan lineage cold
compaction tanpa mengubah formula §5.

Tidak ada scheduler baru. `initialize()` dan `on_session_end()` memanggil
maintenance daemon yang sama setelah claim persisten; session-end tetap memakai
thread lifecycle konsolidasi Fase 2.
