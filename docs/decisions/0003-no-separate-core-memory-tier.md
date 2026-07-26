# ADR-0003: Tidak membangun tier Core Memory baru

**Status**: Diterima
**Tanggal**: 2026-07-26

## Konteks

Rancangan awal sempat mengusulkan tier Core Memory terpisah. Setelah evaluasi, Hermes sudah menyediakan `MEMORY.md` dan `USER.md` sebagai core memory yang dikelola proses agent-curated bawaan.

## Keputusan

Tidak membuat tier Core Memory tambahan. Plugin hanya mengelola hot tier, warm/cold tier, dan metadata pendukung; Core Memory Hermes tetap dipakai apa adanya.

## Alternatif yang Dipertimbangkan

- Menambah tier Core Memory khusus plugin: tidak dipilih karena fungsinya bertumpang tindih dengan `MEMORY.md`/`USER.md` Hermes.
- Mengganti Core Memory Hermes: tidak dipilih karena berada di luar lingkup plugin dan menghilangkan reuse komponen bawaan.

## Konsekuensi

Arsitektur lebih kecil dan tidak menduplikasi context penting. Trade-off-nya, plugin tidak mengendalikan lifecycle Core Memory secara langsung dan hanya dapat memberi bahan baku yang rapi untuk refleksi Hermes.
