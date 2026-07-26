# Fase 0: Fondasi Repo & Lingkungan

**Status**: Selesai
**Tanggal Selesai**: 2026-07-26

## Goal

Repo terstruktur dengan mekanisme dokumentasi siap pakai; Hermes + plugin scaffold + mem0ai terpasang.

## Yang Dibangun

- Struktur direktori dokumentasi sesuai §7.1.
- ADR `0001` sampai `0007` terisi.
- Skeleton plugin `plugins/memory/hermes-dual-memory/` dengan `MemoryProvider` kosong dan `register()` terdaftar.
- Dokumentasi hasil uji fase 0 di `docs/testing/results/phase-0-results.md`.

## Failure Mode yang Diwaspadai

- Salah menaruh path storage karena tidak memakai `hermes_home` dari `initialize()`, sehingga data antar profil Hermes tercampur.
- Mengandalkan backend lokal yang tidak mendukung keyword search, membuat hybrid retrieval tidak aktif dan hasil bergantung ke semantic similarity saja.

## Kriteria Keluar (Exit Criteria)

- `hermes plugins list` menampilkan provider kita.
- Skrip terpisah di luar Hermes berhasil menjalankan `mem0.add()` lalu `mem0.search()` ke backend lokal.
- Persistensi disk untuk backend lokal terverifikasi.

## Hasil Uji

Lihat detail di [docs/testing/results/phase-0-results.md](../testing/results/phase-0-results.md).

Ringkasnya, uji round-trip menunjukkan fakta yang disimpan lewat `mem0.add()` bisa ditemukan lagi lewat `mem0.search()`, data juga bertahan di disk pada `./chroma_db_test`, dan metadata custom kembali utuh. Hasil yang sama juga menegaskan bahwa backend Chroma berjalan tanpa dukungan keyword/BM25 search, jadi pencarian di fase ini masih semantic-only.

## Catatan/Pembelajaran

- Fase 0 lulus untuk validasi fondasi dan round-trip dasar, tetapi Chroma lokal bukan titik akhir yang ideal untuk desain final karena hybrid keyword search belum aktif.
- Item tindak lanjut: evaluasi backend storage yang mendukung `keyword_search` sebelum melangkah ke fase yang membutuhkan hybrid retrieval, supaya BM25 tidak jadi asumsi kosong.
