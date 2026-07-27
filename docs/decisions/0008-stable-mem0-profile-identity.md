# ADR-0008: Identitas Mem0 stabil per profil, bukan per sesi

**Status**: Diterima
**Tanggal**: 2026-07-27

## Konteks

Tes recall lintas sesi Fase 3 gagal karena Fase 2 memakai `session_id` sebagai
`user_id` Mem0. Mem0 mewajibkan filter identitas saat `search()`, sehingga sesi
baru tidak dapat menemukan essence yang dibuat pada sesi sebelumnya walaupun
keduanya memakai profil Hermes yang sama.

## Keputusan

Jalur konsolidasi memakai identitas stabil per profil (`memory_user_id`, default
`"default"`) sebagai `user_id` pada `mem0.add()`. `session_id` tetap disimpan di
metadata essence sebagai provenance. Jalur retrieval memakai identitas stabil
yang sama pada `filters={"user_id": ...}`.

## Alternatif yang Dipertimbangkan

- Memakai `session_id` sebagai `user_id`: ditolak karena memutus recall lintas
  sesi.
- Menghapus filter `user_id`: ditolak karena API Mem0 mewajibkan filter
  identitas dan berisiko mencampur data antarprofil.
- Migrasi data uji lama: tidak dilakukan karena belum ada data produksi dan
  data development boleh di-reset.

## Konsekuensi

Recall lintas sesi dalam satu profil menjadi mungkin, sementara provenance tetap
terjaga melalui metadata `session_id`. Profil berbeda harus memakai
`memory_user_id` berbeda. Data uji lama yang memakai session-scoped identity
diabaikan/reset.
