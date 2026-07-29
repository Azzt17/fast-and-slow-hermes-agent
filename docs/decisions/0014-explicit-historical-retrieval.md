# ADR-0014: Retrieval historis eksplisit untuk fakta bi-temporal

**Status**: Diterima
**Tanggal**: 2026-07-29

## Konteks

Baseline Fase 8 membuktikan fakta semantic lama tetap tersimpan di Mem0 dan
`memory_index`, bahkan masih berada dalam raw top-5 untuk query temporal. Jalur
retrieval normal selalu memblokir row dengan `t_invalid`, sehingga pertanyaan
state sebelum migrasi gagal dan pertanyaan urutan sebelum-sesudah hanya melihat
state baru. Membuka semua row superseded akan merusak knowledge-update policy
dan berisiko menyajikan fakta lama sebagai keadaan terkini.

## Keputusan

`prefetch()` memilih mode historis secara deterministik hanya ketika query
memuat marker temporal eksplisit, misalnya `before`, `previous`, `history`,
`sequence`, `sebelum`, `riwayat`, atau `kronologi`. Keputusan mode tidak memakai
LLM dan tidak mengubah trigger konsolidasi.

Mode normal tetap hanya menerima shadow `status='trusted'` dengan
`t_invalid IS NULL`. Mode historis juga boleh menerima row superseded jika dan
hanya jika statusnya `trusted` dan `memory_type='semantic'`. Row candidate,
quarantined, orphan bertanda shadow, dan row episodic invalid tetap diblokir.

Blok semantic pada mode historis diberi atribut `keadaan_temporal`,
`berlaku_mulai`, dan bila relevan `berlaku_sampai`. Dengan demikian state lama
dan current dapat masuk bersama untuk query urutan tanpa menghapus atau
mengaktifkan kembali fakta lama. Access event tetap dicatat untuk row historis
yang benar-benar visible.

## Alternatif yang Dipertimbangkan

- Membuka semua row superseded di setiap query: ditolak karena current-state
  retrieval akan kembali membocorkan fakta yang sudah diganti.
- Menambah tool/API historis terpisah: ditunda karena kontrak provider Hermes
  hanya memanggil `prefetch(query)` pada jalur recall otomatis.
- Memakai LLM untuk klasifikasi intent: ditolak karena menambah latency, biaya,
  dan nondeterminisme pada jalur retrieval.
- Mengandalkan kata `after` sebagai marker historis: ditolak karena query state
  setelah migrasi biasanya meminta current state dan tidak membutuhkan row lama.

## Konsekuensi

Temporal before-state dan sequence dapat memakai ledger bi-temporal yang sudah
ada tanpa migrasi skema. Current-state serta quarantine policy tidak berubah.
Trade-off: classifier lexical konservatif dapat melewatkan phrasing temporal
yang tidak memakai marker terdaftar; marker terlalu umum juga dapat menambah
state lama ke context, tetapi hanya untuk fakta semantic trusted dan tetap
dibatasi raw Mem0 top-k.
