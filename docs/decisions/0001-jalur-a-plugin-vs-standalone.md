# ADR-0001: Jalur A — plugin Hermes, bukan agent berdiri sendiri

**Status**: Diterima
**Tanggal**: 2026-07-26

## Konteks

Proyek membutuhkan memory provider dengan hot tier, konsolidasi, shadow index, dan quarantine. Hermes Agent telah menyediakan gateway multi-platform, skill engine, Curator, Core Memory, CLI/TUI, serta lapisan keamanan dasar.

## Keputusan

Membangun `hermes-dual-memory` sebagai plugin memory provider Hermes, bukan sebagai agent atau aplikasi berdiri sendiri.

## Alternatif yang Dipertimbangkan

- Agent berdiri sendiri: tidak dipilih karena akan menduplikasi gateway, skill engine, Curator, dan integrasi yang sudah tersedia di Hermes.
- Mengubah Hermes core langsung: tidak dipilih karena provider plugin adalah titik ekstensi yang tepat dan menjaga perubahan tetap terisolasi.

## Konsekuensi

Kita dapat memakai komponen Hermes yang sudah teruji dan fokus pada komponen memory khusus. Sebagai trade-off, desain mengikuti lifecycle dan antarmuka plugin Hermes, serta hanya satu provider memory eksternal yang dapat aktif pada satu waktu.
