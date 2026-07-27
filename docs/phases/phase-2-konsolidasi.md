# Fase 2: Trigger & Konsolidasi Sistem 2

**Status**: Selesai
**Tanggal Selesai**: 2026-07-27

## Goal

Menghubungkan `on_session_end` dan `on_pre_compress` ke pipeline konsolidasi
minimal §4.2–§4.3.

## Yang Dibangun

- Prompt konsolidasi terstruktur dan validasi JSON.
- Retry satu kali untuk output model yang tidak valid.
- `mem0.add(..., infer=False)` agar ekstraksi otomatis Mem0 tidak digunakan.
- Penandaan `hot_sessions.consolidated=1` hanya setelah essence berhasil ditulis.
- Isolasi kegagalan API/Mem0 dari lifecycle Hermes.

## Hasil Verifikasi

- Unit suite pada venv Hermes: `6 tests`, semuanya `OK`.
- `on_session_end` pada sesi Hermes nyata menulis essence ke Mem0/Chroma dan
  mengubah seluruh baris hot session menjadi `consolidated=1`.
- Compression alami Hermes terpicu dengan telemetry `trigger_source=auto` dan
  `effective_threshold=1000`; hook `on_pre_compress` tetap terisolasi dari loop.
- Jalur LLM konsolidasi memakai timeout eksplisit 8 detik (dapat diatur lewat
  `HERMES_DUAL_MEMORY_LLM_TIMEOUT`) dan `max_retries=0`. Endpoint literal yang
  tidak terjangkau mengembalikan `summary=''` dalam 0.214 detik setelah retry,
  tanpa menggantung sesi.
- Bukti runtime Mem0: `infer=False`, metadata memuat seluruh field §4.3.
- Sesi Hermes substantif menghasilkan essence berikut:
  - `summary`: keputusan memakai SQLite shadow index + Mem0/Chroma; risiko BM25
    pada Chroma; tindak lanjut evaluasi Qdrant.
  - `entities`: SQLite shadow index (technology), Mem0/Chroma (technology),
    BM25 (algorithm), Qdrant (technology).
  - `relations`: Mem0/Chroma tidak mendukung BM25; SQLite shadow index digunakan
    bersama Mem0/Chroma.
  - `memory_type`: `semantic`; `importance_score`: `5`; `new_skills=[]`;
    `anomalies=[]`.

## Status Kriteria Keluar

Semua kriteria Fase 2 terverifikasi pada environment Hermes runtime dan Mem0
asli. Keterbatasan Chroma+BM25 tetap menjadi tindak lanjut arsitektur. Identitas Mem0 stabil per profil didokumentasikan di ADR-0008 setelah tes recall Fase 3.
