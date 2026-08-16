# ADR-0020: Batch import Obsidian terkontrol dengan provenance

**Status**: Diterima
**Tanggal**: 2026-07-29

## Konteks

Pilot 1 menghasilkan empat kandidat yang telah direview Farid: dua preferensi
pendampingan stable dan dua ide historical-only. Jalur consolidation biasa
mengasumsikan source berupa session conversation dan belum menyimpan batch import,
hash source note, approval kandidat, atau rollback per sumber. Memasukkan kandidat
langsung ke Mem0 akan memutus audit trail dan berisiko mencampur historical fact
ke current-state.

## Keputusan

Pilot 2 memakai importer profile-scoped khusus Asa dengan batch immutable.
Sebelum write, importer wajib memverifikasi ledger private, source hash yang telah
review, snapshot data berpasangan, dan baseline comparison. Setiap batch menerima
`batch_id` acak serta menyimpan source path/hash, candidate ID, approval status,
temporal class, dan waktu import di tabel provenance baru yang mereferensikan
`memory_index`.

Write untuk setiap kandidat tetap memakai urutan keamanan provider:

1. validasi schema/approval/provenance dan cek idempotensi `candidate_id+hash`;
2. `mem0.add(..., infer=False)` dengan metadata source `obsidian-reviewed-import`;
3. buat shadow row `candidate` melalui `record_memory()`;
4. jalankan admission pattern + semantic fail-closed;
5. finalisasi hanya menjadi `trusted` atau `quarantined`;
6. simpan provenance import setelah `mem0_id` dan shadow row ada.

Stable candidate ditulis sebagai semantic current-state. Historical-only candidate
ditulis semantic dengan metadata historical dan `t_invalid`/retrieval policy yang
memastikan ia tidak menjadi jawaban current-state; desain implementasi detail harus
diuji sebelum activation. Tidak ada automatic supersession pada batch awal.

Rollback batch bersifat compensating dan append-only: provenance batch diberi
status `rolled_back`; shadow row batch ditandai tidak valid atau quarantined sesuai
policy, lalu Mem0 content dihapus hanya bila API/lineage menjamin operasi aman.
Jika tidak, row tetap diblokir retrieval dan orphan content dicatat. Rollback
runtime selalu memakai snapshot code+data berpasangan bila terjadi S0/S1.

## Alternatif yang Dipertimbangkan

- Menyuntik fakta ke `USER.md`: ditolak karena Core Memory kecil/frozen dan tidak
  mendukung provenance, quarantine, historical retrieval, atau rollback batch.
- Memakai session palsu lalu consolidation: ditolak karena provenance source note
  dan approval fact-level menjadi kabur.
- Auto-trust setelah review Farid: ditolak karena admission tetap harus memeriksa
  content injection dan failure harus fail-closed.
- Delete fisik semua row ketika rollback: ditolak karena melanggar prinsip
  supersede/auditability dan dapat membuat Mem0-shadow tidak sinkron.

## Konsekuensi

Onboarding knowledge personal kaya tetapi dapat ditelusuri hingga note/hash dan
keputusan review. Trade-off: schema provenance, importer, test reproduksi,
snapshot, baseline, dan review write menambah langkah sebelum batch pertama.
