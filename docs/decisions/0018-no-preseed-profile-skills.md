# ADR-0018: Tanpa skill profile yang dipreseed

**Status**: Diterima
**Tanggal**: 2026-07-29

## Konteks

ADR-0017 menambahkan skill personal dan operasional statis ke profile Asa dan
Nellie. Walau valid dan terisolasi, skill tersebut menambah permukaan prompt,
workflow paralel, serta beban pemeliharaan sebelum ada bukti pola kerja nyata.
Farid memilih membangun kemampuan secara alami melalui mekanisme procedural
memory yang sudah diimplementasikan pada Fase 7.

## Keputusan

Tidak ada `SKILL.md` custom atau personal yang dipreseed oleh repo pada kedua
profile. Persona dan invariants tetap berada di `SOUL.md` serta Core Memory.
Kemampuan reusable baru harus melewati draft procedural, validasi security dan
Curator native Hermes, pemeriksaan redundansi, lalu approval manusia sebelum
aktif. Deployer hanya mem-prune daftar legacy skill yang sebelumnya dikelola
repo; skill bawaan/native lain tidak dihapus.

Direktori kosong `skills/procedural-memory` bukan `SKILL.md` aktif maupun hasil
pipeline Fase 7. Pipeline itu hidup di plugin dan menyimpan kandidat pada
`skill-drafts` di luar active skills; direktori kategori tidak dihapus karena
bukan asset yang dikelola deployer.

## Alternatif yang Dipertimbangkan

- Mempertahankan skill shared infrastruktur: ditolak karena detail operasional
  tetap dapat dibaca dari repo saat relevan dan tidak perlu preload.
- Menyimpan skill legacy tanpa mengaktifkannya: ditolak karena tetap menciptakan
  lifecycle paralel dan berisiko muncul kembali pada discovery.
- Menghapus seluruh direktori skills: ditolak karena dapat menghapus skill native
  atau data lifecycle yang tidak dikelola repo.

## Konsekuensi

Profile lebih sederhana dan skill masa depan memiliki provenance dari pola nyata.
Trade-off: workflow awal tidak memiliki shortcut; user/agent perlu menjalankan
proses eksplisit sampai pola tersebut cukup kuat untuk diajukan sebagai draft.
