# ADR-0019: Pilot import Obsidian berlapis dan review-gated

**Status**: Diterima
**Tanggal**: 2026-07-29

## Konteks

Asa perlu memperoleh pengetahuan yang kaya dan relevan tentang Farid dari vault
Obsidian tanpa menyamakan archive, jurnal temporal, project state, atau instruksi
tertulis sebagai fakta aktif. Provider saat ini menerima turn conversation dan
belum memiliki importer yang menyimpan provenance sumber, persetujuan, atau
rollback per batch.

## Keputusan

Import memakai tahap berurutan:

1. Pilot 0 menghasilkan manifest metadata-only dan klasifikasi deterministik.
2. Farid mereview serta membuat allowlist file secara eksplisit.
3. Pilot 1 baru boleh membuat semantic candidate ledger dengan provenance per
   source/hash/chunk dan tanpa vector write.
4. Review Farid pada level fakta menentukan stable/current/historical/exclude.
5. Hanya batch yang disetujui dapat melewati admission, quarantine, shadow index,
   dan Mem0 melalui importer terpisah yang belum diimplementasikan.

Pilot 0 default-exclude archive, inbox, jurnal harian/mimpi, news digest, dan
non-Markdown. Tidak ada source otomatis trusted. Manifest private, tidak masuk
repo, dan output harus berada di luar vault untuk mencegah mutasi source.

## Alternatif yang Dipertimbangkan

- Bulk vectorize semua file: ditolak karena sumber stale/sensitif/duplikat dapat
  muncul sebagai fakta current-state dan melewati review manusia.
- Semantic analysis sebelum prefilter: ditolak karena memboroskan token dan
  memperluas exposure isi sensitif.
- Core Memory sebagai dump vault: ditolak karena batas prompt dan lifecycle
  frozen; Core Memory bukan knowledge base.

## Konsekuensi

Asa memperoleh konteks personal secara bertahap, dapat diaudit, dan dapat
menghindari false recall dari arsip. Trade-off: onboarding membutuhkan review
file/fakta dan importer write-path ditunda sampai Pilot 1/2 tervalidasi.
