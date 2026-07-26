# ADR-0007: Decay dan tiering dipicu opportunis di session hook

**Status**: Diterima
**Tanggal**: 2026-07-26

## Konteks

Memory index membutuhkan perhitungan decay, promosi/demosi, dan cold compaction berkala. Hermes tidak menyediakan scheduler plugin native.

## Keputusan

Memicu pemeriksaan decay secara opportunis dari `initialize()` dan hook sesi seperti `on_session_end`, dengan pengecekan ringan agar siklus penuh hanya berjalan setelah interval yang ditentukan.

## Alternatif yang Dipertimbangkan

- Cron atau proses scheduler terpisah: tidak dipilih karena tidak didukung native oleh lifecycle plugin Hermes dan menambah komponen operasional.
- Tidak menjalankan decay: tidak dipilih karena tiering dan retrievability adalah bagian inti rancangan.

## Konsekuensi

Tidak diperlukan service tambahan dan implementasi selaras dengan lifecycle Hermes. Trade-off-nya, decay berjalan saat ada aktivitas sesi, bukan tepat pada waktu kalender tertentu.
