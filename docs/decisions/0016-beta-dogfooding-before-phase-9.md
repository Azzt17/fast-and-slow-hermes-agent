# ADR-0016: Beta dogfooding sebelum Fase 9

**Status**: Diterima
**Tanggal**: 2026-07-29

## Konteks

Fase 0–8 beserta follow-up temporal dan answerability telah selesai. Baseline
real-stack Fase 8 berstatus `PASS`, tetapi benchmark sintetis belum membuktikan
kenyamanan, biaya, latency, dan kualitas memori dalam pekerjaan harian yang
berlangsung lintas hari dan lintas sesi Hermes. Memulai hardening/rilis
portofolio Fase 9 sekarang berisiko membekukan perilaku yang belum cukup
dirasakan langsung.

Commit `c6efb9ca14ebd7ee66cb872ed9599e6d8b327d76` memuat implementasi ADR-0015.
PR #2 menggabungkannya ke `master` melalui merge commit
`18c770b`. Baseline JSON pada checkpoint memiliki SHA-256
`2cc8763ccde2e9437a2ca34a5b5a86d0649e653403464ed9f1031b6ec25409da`.

Audit preflight menemukan provider aktif Hermes masih memakai plugin sebelum
ADR-0015: `answerability.py` belum terpasang, sementara gateway Hermes sedang
berjalan. Karena itu periode beta tidak boleh dianggap mulai sebelum exact code
checkpoint dideploy, gateway direstart terkontrol, dan data runtime disnapshot.

## Keputusan

Checkpoint diberi versi **`v0.1.0-beta.1`** pada merge commit `18c770b`. Versi
ini menjadi rollback target kode selama dogfooding. Snapshot runtime terpisah
menjadi rollback target data; rollback dianggap lengkap hanya jika code dan
data dikembalikan sebagai pasangan.

Dogfooding berjalan **21 hari kalender** dengan minimal **14 hari aktif** dan
minimal **30 sesi kerja nyata**. Hari aktif berarti ada penggunaan Hermes untuk
task riil, bukan benchmark khusus. Periode boleh diperpanjang sampai minimum
terpenuhi. Fase 9 tidak dimulai selama status beta belum `Selesai`.

Semua perubahan selama beta memakai branch `beta/0.1-*`, ADR baru jika mengubah
policy/arsitektur, dan entri append-only pada
`docs/beta/v0.1.0-beta.1/journal.md`. Setiap sesi Codex wajib membaca
`docs/beta/v0.1.0-beta.1/CURRENT.md` sebelum mengubah code beta, sehingga handoff
tetap utuh saat pengguna berpindah session.

Perubahan observability/dokumentasi rendah risiko boleh dilakukan selama beta.
Perubahan retrieval policy, schema, admission, consolidation, decay, atau data
migration membutuhkan: issue/journal entry, test reproduksi, ADR bila policy
berubah, baseline comparison, snapshot data baru, dan approval manusia sebelum
push/PR sesuai AGENTS.md.

## Alternatif yang Dipertimbangkan

- Langsung masuk Fase 9: ditolak karena belum ada bukti longitudinal dari task
  sehari-hari.
- Uji 7 hari: ditolak karena terlalu pendek untuk mengamati consolidation,
  decay 24 jam, retrieval lintas minggu, dan kebiasaan penggunaan.
- Uji 30 hari wajib: baik untuk keyakinan lebih tinggi, tetapi dipilih sebagai
  opsi perpanjangan agar feedback loop tidak terlalu lambat.
- Hanya tag Git tanpa snapshot data: ditolak karena schema/vector/shadow state
  dapat berubah dan membuat rollback code saja tidak aman.
- Menulis catatan di luar repo: ditolak karena tidak terbawa branch/session dan
  sulit diaudit bersama commit.

## Konsekuensi

Fase 9 tertunda minimal 21 hari, tetapi keputusan hardening didasarkan pada data
penggunaan nyata. Tag beta memudahkan rollback code dan jurnal menyediakan
riwayat lintas-session. Trade-off: observasi manual membutuhkan disiplin, data
beta dapat berisi informasi sensitif sehingga snapshot dan jurnal tidak boleh
menyalin isi memory mentah/credential ke Git, dan perubahan mendesak selama beta
memerlukan prosedur rollback yang lebih ketat.
