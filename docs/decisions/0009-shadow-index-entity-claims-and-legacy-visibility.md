# ADR-0009: Shadow index dengan klaim entitas dan visibilitas legacy

**Status**: Diterima
**Tanggal**: 2026-07-28

## Konteks

Skema `memory_index` §3.3 menyimpan lifecycle setiap essence berdasarkan
`mem0_id`, tetapi langkah 6 pipeline §4.2 membutuhkan pencarian fakta lama
berdasarkan entitas. Skema canonical tersebut tidak memiliki kolom entitas atau
relasi. Selain itu, essence Fase 1–3 sudah dapat berada di Mem0 tanpa baris
shadow.

## Keputusan

`memory_index` ditempatkan di file SQLite yang sama dengan `hot_sessions` agar
write hot tier, shadow metadata, dan invalidasi memakai satu boundary storage.
Skema §3.3 dipertahankan utuh. Dua tabel pendamping ternormalisasi,
`memory_entities` dan `memory_relations`, menyimpan data laporan konsolidasi
untuk lookup kandidat kontradiksi berdasarkan entity ID/label.

Kontradiksi hanya diproses untuk essence `semantic`. Kandidat harus berbagi
entity ID atau label. Konten essence lama dibaca kembali dari Mem0, lalu kandidat
dikirim ke callable System 2 bersama essence baru dan klaim terstrukturnya untuk
keputusan boolean. Hanya keputusan eksplisit `contradiction=true` yang
menginvalidasi fakta lama; kemiripan entitas saja tidak cukup.

Essence legacy tanpa baris `memory_index` tetap visible saat retrieval. Ini
menjaga kompatibilitas data Fase 1–3 tanpa backfill yang tidak dapat merekonstruksi
entitas/relasi terstruktur secara andal. Setelah sebuah `mem0_id` mempunyai baris
shadow, status dan `t_invalid` shadow menjadi otoritatif.

Essence baru diberi metadata `shadow_index_version=1`. Hasil bertanda ini wajib
memiliki shadow agar visible. Dengan demikian kegagalan SQLite setelah write
Mem0 tidak membocorkan orphan ke retrieval, sedangkan data legacy tanpa marker
tetap mengikuti kebijakan kompatibilitas di atas.

## Alternatif yang Dipertimbangkan

- Menambah JSON entitas ke `memory_index`: ditolak karena mengubah skema §3.3
  dan membuat query-by-entity bergantung pada fitur JSON SQLite.
- Menganggap target berbeda otomatis kontradiksi: ditolak karena relasi yang
  multi-valued dapat menghasilkan false positive.
- Backfill dari metadata Mem0: ditolak karena data lama boleh tidak punya
  shadow dan metadata lama tidak dijamin lengkap atau seragam.
- Menyembunyikan semua hasil tanpa shadow: ditolak karena memutus recall data
  Fase 1–3 secara mendadak.

## Konsekuensi

Retrieval Fase 3 tetap satu jalur, dengan policy gate shadow ditambahkan setelah
`mem0.search()`. Invalidasi dapat diaudit tanpa menghapus fakta lama. Trade-off:
SQLite memiliki dua tabel internal tambahan dan konsistensi Mem0↔shadow harus
dijaga setelah `mem0.add()` berhasil. Kegagalan mencatat shadow membuat hot rows
tetap pending agar konsolidasi dapat ditinjau/diulang, walaupun Mem0 mungkin sudah
memiliki essence hasil percobaan tersebut.
