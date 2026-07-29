# Beta Dogfooding v0.1.0-beta.1

**Status**: Preflight — belum mulai
**Checkpoint code**: `v0.1.0-beta.1` → `18c770b`
**Implementation commit**: `c6efb9c`
**Baseline SHA-256**: `2cc8763ccde2e9437a2ca34a5b5a86d0649e653403464ed9f1031b6ec25409da`
**Durasi target**: 21 hari kalender, minimal 14 hari aktif dan 30 sesi kerja
**Fase 9**: Ditahan sampai exit criteria beta PASS

## Tujuan

Menggunakan Hermes Agent dengan provider ini untuk pekerjaan sehari-hari,
menilai manfaat dan trade-off secara longitudinal, serta menghasilkan daftar
hardening Fase 9 berdasarkan bukti nyata.

## Preflight Wajib

- [x] PR ADR-0015 merged ke `master` (`18c770b`)
- [x] Tag lokal `v0.1.0-beta.1` dibuat pada checkpoint
- [ ] Tag beta dipush ke origin
- [ ] Plugin checkpoint dideploy ke profile Hermes aktif
- [ ] Gateway direstart setelah deploy
- [ ] Hash file plugin aktif cocok dengan checkpoint
- [ ] Snapshot data pre-beta dibuat di luar Git
- [ ] Manifest snapshot mencatat hash, ukuran, waktu, dan checkpoint code
- [ ] Smoke test retrieval, temporal, abstention, security, dan consolidation PASS
- [ ] Waktu mulai beta dicatat di `CURRENT.md` dan `journal.md`

Clock beta **tidak berjalan** sebelum semua item preflight selesai.

Perintah operasional ada di `RUNBOOK.md`. Manifest snapshot ada di
`SNAPSHOT-MANIFEST.md`; perubahan beta diringkas di `changes.md` dan dijelaskan
lebih lengkap secara append-only di `journal.md`.

## Cakupan Task Harian

Selama periode beta, gunakan Hermes untuk campuran berikut:

1. coding/debugging multi-session;
2. research dan perbandingan keputusan;
3. task operasional berulang;
4. percakapan yang memperbarui fakta lama;
5. pertanyaan historis sebelum/sesudah perubahan;
6. query tanpa jawaban yang seharusnya abstain;
7. recall cold/old session setelah beberapa hari;
8. procedural draft dan approval skill bila muncul alami.

Jangan membuat memory palsu hanya agar metrik terlihat baik. Task sintetis boleh
dipakai untuk reproduksi bug, tetapi diberi label `synthetic` di jurnal.

## Jadwal 21 Hari yang Disarankan

### Hari 1–7 — Baseline Beku

- gunakan config default tanpa tuning;
- jangan ubah threshold, timeout, prompt verifier, schema, atau model;
- fokus pada task riil dan catat first impression latency/helpfulness;
- jalankan baseline comparison pada akhir hari ke-7;
- hanya S0/S1 yang membenarkan perubahan segera.

### Hari 8–14 — Eksperimen Terkendali

- prioritaskan maksimal satu perubahan pada satu waktu;
- buat ID `BETA-NNN`, journal entry, test reproduksi, dan snapshot sebelum
  perubahan policy/data;
- tentukan success metric dan rollback condition sebelum deploy;
- beri observation window minimal 2 hari aktif per perubahan;
- bandingkan dengan minggu pertama, bukan hanya perasaan setelah satu sesi.

### Hari 15–21 — Stabilisasi

- hentikan eksperimen baru kecuali S0/S1;
- gunakan kandidat config/code yang hendak dibawa ke Fase 9;
- jalankan full 48-query regression dan review biaya/latency;
- lakukan satu rollback drill code+data;
- tutup atau prioritas ulang seluruh issue;
- tulis laporan akhir dan daftar hardening Fase 9.

Jika pada hari ke-21 belum mencapai 14 hari aktif/30 sesi nyata, atau ada
perubahan besar pada minggu terakhir, perpanjang beta 7–14 hari. Jangan mengubah
exit criteria agar tanggal terlihat terpenuhi.

## Yang Dicatat per Sesi

Gunakan satu baris/tabel atau entri singkat di `journal.md`:

- tanggal/waktu dan session ID yang telah dipendekkan/di-hash;
- jenis task dan apakah real/synthetic;
- apakah memory membantu, tidak muncul, salah, atau mengganggu;
- latency subjektif: `tidak terasa`, `terasa`, `menghambat`;
- outcome: berhasil, perlu koreksi, atau menyebabkan keputusan salah;
- indikasi false recall, missed recall, stale fact, temporal error, atau leak;
- perubahan config/code yang aktif;
- link commit/ADR/test jika ada perubahan.

Jangan menyalin credential, system prompt, isi memory sensitif, atau conversation
mentah ke repo. Pakai ringkasan yang disanitasi.

## Metrik Mingguan

Setiap 7 hari, isi ringkasan:

- jumlah hari aktif dan sesi;
- retrieval helpful / irrelevant / missed;
- koreksi fakta dan stale-state incident;
- abstention benar / false injection;
- security/quarantine incident;
- latency p50/p95 dari benchmark mingguan;
- context token dan verifier token/cost;
- consolidation success/failure/timeout;
- jumlah draft skill pending/redundant/approved;
- perubahan ukuran SQLite/Chroma;
- perubahan code/config selama minggu tersebut.

## Severity

- `S0`: credential/system prompt leak, quarantine bypass, atau data corruption.
- `S1`: fakta salah menyebabkan tindakan material, rollback gagal, atau memory
  lintas user/profile bocor.
- `S2`: false/missed recall berulang, latency menghambat, consolidation sering
  gagal, atau biaya tidak layak.
- `S3`: UX/polish/documentation issue tanpa dampak correctness.

`S0/S1` → hentikan beta, snapshot bukti yang aman, rollback code+data, buat ADR
atau incident note. `S2` → boleh lanjut hanya dengan mitigation dan approval.

## Exit Criteria Beta

- [ ] 21 hari kalender selesai
- [ ] Minimal 14 hari aktif
- [ ] Minimal 30 sesi kerja nyata
- [ ] Tidak ada S0/S1 unresolved
- [ ] Tidak ada quarantine/profile isolation regression
- [ ] Weekly baseline tidak menunjukkan recall/security regression
- [ ] Latency dan cost dinilai dapat diterima atau punya mitigation Fase 9
- [ ] Rollback drill code+data berhasil minimal sekali
- [ ] Semua eksperimen memiliki journal entry dan commit/ADR bila relevan
- [ ] Daftar hardening Fase 9 diprioritaskan berdasarkan severity/evidence
- [ ] `CURRENT.md` dan laporan akhir beta ditandai `Selesai`

## Rollback

### Code

Gunakan tag `v0.1.0-beta.1` untuk kembali ke code checkpoint. Jangan force-push
atau rewrite history. Buat branch rollback/hotfix dari tag dan deploy file plugin
secara terkontrol.

### Data

Matikan/restart gateway sesuai runbook sebelum mengganti data. Kembalikan seluruh
direktori profile-scoped `$HERMES_HOME/hermes-dual-memory/` dari snapshot yang
berpasangan dengan checkpoint. Jangan restore hanya SQLite atau hanya Chroma.

### Verifikasi Setelah Rollback

- hash plugin cocok dengan checkpoint;
- SQLite integrity check PASS;
- provider initialize PASS;
- recall smoke PASS;
- quarantine result tetap invisible;
- session baru tidak merusak snapshot restored.

Lokasi snapshot aktual dan perintah host-specific dicatat di `CURRENT.md`, bukan
di Git jika path atau metadata mengandung informasi sensitif.
