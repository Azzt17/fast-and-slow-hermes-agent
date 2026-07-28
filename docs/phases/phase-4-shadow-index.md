# Fase 4: Shadow Index, Bi-Temporal, Kontradiksi

**Status**: Selesai
**Tanggal Selesai**: 2026-07-28

## Goal

`memory_index` aktif, tiap `mem0.add()` mendapat baris shadow, dan fakta semantic
lama yang terverifikasi bertentangan di-invalidasi tanpa dihapus.

## Yang Dibangun

- [x] Skema `memory_index` §3.3 pada SQLite provider.
- [x] Lookup klaim semantic berdasarkan entitas.
- [x] Invalidasi bi-temporal dan hubungan `superseded_by`.
- [x] Policy gate shadow pada jalur retrieval Fase 3.
- [x] Kompatibilitas visible untuk essence legacy tanpa shadow.
- [x] Test unit dan skenario kontradiksi lintas sesi.

## Failure Mode yang Diwaspadai

Kontradiksi terdeteksi tetapi fakta lama dihapus alih-alih diberi `t_invalid`,
atau fakta yang hanya mirip salah dianggap bertentangan.

## Kriteria Keluar (Exit Criteria)

Skenario terkontrol menyimpan fakta A lalu fakta B yang bertentangan pada sesi
berbeda. Retrieval normal hanya mengembalikan B; fakta A tetap ada di
`memory_index` dengan `t_invalid` dan `superseded_by` terisi serta dapat diaudit.

## Hasil Uji

Lihat [hasil uji Fase 4](../testing/results/phase-4-results.md). Suite otomatis
PASS (`17 tests`, satu skip interpreter-specific yang PASS saat dijalankan pada
venv Hermes). Smoke nyata dua sesi juga PASS: fakta Jakarta tetap tersimpan
dengan `t_invalid` dan `superseded_by`, sedangkan retrieval normal hanya
mengembalikan pembaruan Bandung. Uji false-positive dengan dua fakta semantic
tentang Farid dan kopi Toraja juga PASS: contradiction judge dipanggil, kedua
fakta tetap `trusted`, dan tidak ada `t_invalid` yang terisi.

## Catatan/Pembelajaran

ADR-0009 menetapkan tabel pendamping klaim dan kebijakan visible untuk data
legacy yang belum mempunyai shadow. `memory_index`, `memory_entities`, dan
`memory_relations` memakai file SQLite yang sama dengan `hot_sessions`.

Tidak ada jalur retrieval kedua: filter shadow ditambahkan setelah
`mem0.search()` di `_search_mem0()`, sehingga `prefetch()` dan
`queue_prefetch()` tetap memakai implementasi Fase 3 yang sama.
