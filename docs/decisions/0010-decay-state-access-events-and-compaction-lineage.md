# ADR-0010: State decay, event akses, dan lineage cold compaction

**Status**: Diterima
**Tanggal**: 2026-07-28

## Konteks

Fase 5 memakai formula §5 tanpa perubahan, tetapi skema canonical
`memory_index` §3.3 tidak menyimpan waktu demosi, riwayat akses tujuh hari, waktu
siklus decay terakhir, atau hubungan banyak-ke-satu antara sumber cold dan hasil
compaction. State tersebut diperlukan untuk throttle 24 jam, promosi ulang, dan
audit bahwa sumber compaction tidak hilang tanpa jejak.

## Keputusan

Formula dipakai persis seperti spesifikasi:
`R(t) = exp(-t / S)`, dengan `S` awal `max(importance_score / 2, 0.5)` dan
naik `1.5x` setiap hasil retrieval benar-benar disuntikkan. Jika
`last_accessed=NULL`, `t_created` menjadi baseline umur.

SQLite yang sama mendapat tiga tabel pendamping internal:

- `maintenance_state` untuk timestamp persisten `last_decay_run`;
- `memory_lifecycle_events` untuk menghitung akses ulang cold dalam jendela
  tujuh hari dan menyimpan waktu demosi/promosi;
- `memory_compaction_sources` untuk lineage hasil gabungan ke setiap sumber.

Siklus decay di-claim secara atomik sebelum kerja berat. `initialize()` dan
`on_session_end()` hanya memicu daemon maintenance; tidak ada scheduler baru.
Jika claim belum berumur 24 jam, hook menjadi no-op murah.

Cold compaction memakai Mem0 untuk mengambil konten dan skor kemiripan:
setiap sumber cold menjadi query `mem0.search()`, lalu pasangan cold dengan skor
minimal `0.75` dikelompokkan. Sistem 2 meringkas cluster. Hasil ditulis sebagai
essence episodic baru dan shadow warm; sumber diberi `t_invalid` serta
`superseded_by` ke hasil gabungan, tidak dihapus. Cluster berukuran kurang dari
dua dilewati.

## Alternatif yang Dipertimbangkan

- Menambah kolom ke `memory_index`: ditolak agar skema §3.3 tetap canonical.
- Menghitung promosi dari `access_count` global: ditolak karena tidak dapat
  membuktikan dua akses terjadi dalam tujuh hari setelah demosi.
- Menjalankan maintenance sinkron di `initialize()`: ditolak karena cold
  compaction dapat menambah latency startup.
- Menghapus sumber setelah compaction: ditolak karena melanggar prinsip
  supersede, jangan hapus.
- Menghitung cosine embedding sendiri: ditolak karena Mem0 sudah menyediakan
  semantic search dan skor kemiripan.

## Konsekuensi

Formula inti tetap sesuai §5 dan seluruh state bertahan lintas proses. Startup
dan session end tidak diblokir oleh network/LLM maintenance. Trade-off: claim
24 jam dicatat sebelum compaction; jika proses mati setelah claim, retry penuh
menunggu interval berikutnya kecuali timestamp di-reset secara operasional.
Kegagalan cluster bersifat granular: cluster itu dilewati dan sumber tetap cold
serta valid.
