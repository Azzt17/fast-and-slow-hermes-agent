# ADR-0004: Mengutamakan antarmuka plugin Hermes daripada portabilitas

**Status**: Diterima
**Tanggal**: 2026-07-26

## Konteks

Plugin perlu diintegrasikan cepat dengan lifecycle sesi, hook memori, konfigurasi, dan discovery provider Hermes.

## Keputusan

Mengikat implementasi pada antarmuka plugin Hermes dan tidak memprioritaskan portabilitas ke framework agent lain pada tahap ini.

## Alternatif yang Dipertimbangkan

- Membuat lapisan abstraksi lintas framework sejak awal: tidak dipilih karena menambah desain dan pengujian tanpa kebutuhan rilis saat ini.
- Membuat layanan memory generik terpisah: tidak dipilih karena mengurangi manfaat reuse lifecycle Hermes dan memperlambat build.

## Konsekuensi

Integrasi dengan Hermes menjadi langsung dan cepat dibangun. Trade-off-nya, migrasi atau penggunaan ulang di framework lain kelak memerlukan adapter atau refactor.
