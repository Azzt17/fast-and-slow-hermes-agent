# Fase 2: Trigger & Konsolidasi Sistem 2

**Status**: Dalam Pengerjaan

## Goal

Menghubungkan `on_session_end` dan `on_pre_compress` ke pipeline konsolidasi
minimal §4.2–§4.3.

## Yang Dibangun

- Prompt konsolidasi terstruktur dan validasi JSON.
- Retry satu kali untuk output model yang tidak valid.
- `mem0.add(..., infer=False)` agar ekstraksi otomatis Mem0 tidak digunakan.
- Penandaan `hot_sessions.consolidated=1` hanya setelah essence berhasil ditulis.
- Isolasi kegagalan API/Mem0 dari lifecycle Hermes.

## Verifikasi Sementara

Unit test fake LLM/Mem0 mencakup retry, metadata §4.3, `infer=False`, daemon
thread idle, dan kegagalan JSON. Uji Hermes+Mem0 nyata dan kriteria keluar fase
masih menunggu environment `mem0ai` serta kredensial model yang aktif.
