# Current Beta State

File ini adalah handoff pertama yang wajib dibaca setiap session baru.

**Versi**: `v0.1.0-beta.1`
**Status**: Berjalan — baseline beku
**Checkpoint code**: `18c770b`
**Branch dokumentasi**: `beta/0.1-dogfooding-docs`
**Tanggal mulai**: `2026-07-29T12:29+08:00`
**Target selesai**: `2026-08-19` (tetap tunduk pada minimum hari/sesi)
**Hari aktif / target**: `0 / 14`
**Sesi nyata / target**: `0 / 30`
**Severity tertinggi unresolved**: S2 — malformed System-2 report chunk

## Temuan Preflight Saat Ini

- Tag remote `v0.1.0-beta.1` menunjuk merge commit `18c770b`.
- Exact plugin checkpoint terpasang dan hash cocok pada profile `default` dan
  `research`; kedua gateway aktif setelah controlled restart.
- Data uji profile default dipindahkan ke snapshot privat; kedua profile mulai
  dengan `0` hot turn, `0` shadow memory, `0` session, dan `0` message.
- Persona default `Asa` dipulihkan selektif dari backup tervalidasi: `SOUL.md`
  plus `asa-daily-checkin`, `asa-night-review`, dan `asa-deep-discussion`.
- Profile `research` menjadi `Nellie`, memakai model `nellie-research`, provider
  `hermes-dual-memory`, dan storage profile-scoped terpisah.
- Clean-start snapshot code+data dua profile dibuat saat kedua gateway berhenti;
  checksum dan archive integrity PASS.
- Final serial 48-query regression PASS: recall `1.0`, abstention `1.0`, security
  exclusion `1.0`, p50 `1386.666 ms`, p95 `1924.301 ms`.
- System-2 real-stack smoke dengan runtime model `asa-complex` PASS. Beberapa
  probe sebelumnya fail-closed saat respons semantic admission timeout/terpotong;
  monitor bila berulang dalam task nyata.
- BETA-011 dideploy hanya ke Asa/default: System-2 membatasi transcript menjadi
  batch whole-turn 24.000 karakter untuk combo 9router; setiap batch sukses
  ditandai sendiri, sisanya tetap pending saat failure. Profile research/Nellie
  tidak diubah.
- BETA-011 juga dideploy ke Nellie/research setelah snapshot privat dan baseline
  subset PASS. Trigger legacy pada sesi terbesar default (104 turn) dan research
  (46 turn) masih timeout dua kali per run; seluruh row tetap pending dan tidak
  ada shadow memory baru.
- BETA-013 dideploy ke kedua profile dengan budget combo 6.000 karakter. Legacy
  default 104 turn dan research 46 turn selesai terkonsolidasi. Satu chunk pada
  sesi default lain menolak `memory_type` invalid dan 11 hot turn tetap pending;
  tidak ada unsafe write.
- Local upstream Hermes gateway fix kini aktif pada kedua gateway: `/new` dan
  `/reset` memanggil cached agent `commit_memory_session()` sebelum cleanup,
  sehingga provider `on_session_end` dapat menerima boundary. Menunggu satu
  verifikasi runtime `/new` pada default sebelum status integrasi ditutup.

## Active Configuration

- Retrieval minimum score: default `0.55`, kecuali jurnal menyatakan override.
- Answerability timeout: default `5s`, kecuali jurnal menyatakan override.
- Provider aktif tunggal per profile: `hermes-dual-memory`.
- Profile default: persona `Asa`, model `asa-complex`.
- Profile research: persona `Nellie`, model `nellie-research`.
- Baseline regression: schema v2, 48 query, overall `PASS`.
- Visualisasi Graphify: user service `graphify-visualization.service`, port
  `8765`, bind eksklusif ke alamat `tailscale0`; hanya `graph.html` yang served.
- Telegram research: bot profile-scoped Nellie aktif dalam polling mode; token
  berbeda dari bot Asa dan allowlist terbatas pada user yang sama.
- Static profile context mengikuti ADR-0017: canonical assets berada di
  `profiles/`, telah dideploy byte-identik dengan mode `0600` ke default dan
  research. Gateway aktif mempertahankan snapshot Core Memory saat ini; konteks
  baru berlaku pada sesi berikutnya tanpa restart paksa.
- ADR-0018 menghapus seluruh custom/personal `SKILL.md` yang dipreseed. Persona
  dan Core Memory tetap aktif; kemampuan reusable baru harus melalui draft
  procedural dan approval manusia. Skill native/hub tidak dipruning.

## Open Items

1. Jalankan task nyata tanpa tuning config selama hari 1–7.
2. Catat setiap sesi nyata dan observasi retrieval di `journal.md`.
3. Monitor timeout/JSON invalid semantic admission; buka `BETA-NNN` jika berulang.
4. Jalankan baseline comparison mingguan pertama pada akhir hari aktif ke-7.
5. Merge PR dokumentasi beta #3 setelah review manusia.
6. Jalankan Pilot 0 manifest metadata-only Obsidian ke output privat, review
   allowlist file dengan Farid, lalu putuskan apakah Pilot 1 semantic ledger
   layak dimulai. Vector/shadow write tetap memerlukan snapshot dan baseline
   comparison terpisah.
7. Pilot 1 menyetujui empat kandidat natural; Pilot 2 design tersedia, tetapi
   implementasi provenance/importer dan write batch tetap menunggu approval
   eksplisit Farid serta pre-write snapshot/baseline PASS.
8. Pilot 2 deployment ditunda: preflight gateway Asa mencapai state `failed`
   sebelum snapshot/deploy. Kedua gateway telah pulih active; diagnosis baseline
   gateway wajib PASS sebelum deployment atau import diulang.
9. Pilot 2 plugin kini dideploy hanya ke Asa/default dengan schema provenance
   kosong dan baseline subset PASS. Empat kandidat Pilot 1 belum diimpor;
   execution tetap menunggu approval batch final Farid.
10. Batch `obsidian-pilot2-batch-001` rollback fail-closed karena admission timeout
    pada 2/4 kandidat; tidak ada memory baru visible. Jangan retry atau tuning
    tanpa reproduksi, baseline comparison, dan review Farid.
11. BETA-013 mengatasi timeout combo pada legacy run. Jangan retry 11 turn
    pending dari session `20260729_145046_8b2bb955` tanpa ADR/repro parser,
    baseline, snapshot, dan approval eksplisit Farid.
12. Kirim `/new` di Asa/default lalu tunggu proses System-2; verifikasi hot
    session sebelumnya berubah consolidated sebelum memperluas kesimpulan ke
    seluruh lifecycle gateway.

## Local Operations

- Graphify status: `systemctl --user status graphify-visualization.service`
- Graphify restart: `systemctl --user restart graphify-visualization.service`
- Graphify disable: `systemctl --user disable --now graphify-visualization.service`
- URL aktual memakai MagicDNS/IP Tailscale host pada port `8765`; alamat tidak
  dicatat di repo agar metadata jaringan tetap lokal.

## Runbook dan Ledger

- Preflight/deploy/rollback: `RUNBOOK.md`
- Snapshot metadata: `SNAPSHOT-MANIFEST.md`
- Change ledger: `changes.md`
- Observation log: `journal.md`

## Session Handoff Rule

Sebelum mengubah beta code/config/data:

1. baca file ini dan `README.md` di direktori yang sama;
2. baca 20 entri terakhir `journal.md`;
3. cek branch, tag, PR, dan working tree;
4. cek apakah gateway aktif sebelum snapshot/deploy;
5. tambahkan journal entry sebelum dan sesudah perubahan;
6. update file ini jika status, config, open item, atau rollback point berubah.
