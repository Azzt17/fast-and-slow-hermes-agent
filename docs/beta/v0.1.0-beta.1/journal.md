# Beta Journal — v0.1.0-beta.1

Append-only. Jangan menghapus atau menulis ulang observasi lama; koreksi dibuat
sebagai entri baru yang merujuk entri sebelumnya. Semua waktu memakai timezone
lokal `Asia/Shanghai` dan format ISO-8601.

## Template Entri

```markdown
### YYYY-MM-DDTHH:MM+08:00 — <jenis entri>

- Session: `<ID pendek/hash>`
- Actor: `Farid|Codex|Hermes`
- Task: `<ringkasan tersanitasi>`
- Mode: `real|synthetic|maintenance`
- Beta code/config: `<tag/commit + override>`
- Observation: `<helpful/missed/irrelevant/error/latency/cost>`
- Severity: `none|S0|S1|S2|S3`
- Evidence: `<metric/log/test/commit/ADR tanpa data sensitif>`
- Action: `<none/monitor/fix/rollback>`
- Result: `<open/mitigated/resolved>`
```

## Entries

### 2026-07-29T11:33+08:00 — checkpoint ditetapkan

- Session: `codex-beta-preflight`
- Actor: `Codex`
- Task: Menetapkan checkpoint setelah Fase 8 dan merancang dogfooding beta.
- Mode: `maintenance`
- Beta code/config: `v0.1.0-beta.1` → `18c770b`
- Observation: Fase 8 overall PASS; tag lokal dibuat. Plugin aktif Hermes masih
  versi sebelum ADR-0015 dan gateway sedang berjalan, sehingga clock beta belum
  boleh dimulai.
- Severity: `S2`
- Evidence: PR #2 merged; audit hash plugin aktif; ADR-0016.
- Action: Dokumentasikan preflight, snapshot, deploy, restart, dan smoke test.
- Result: `open`


### 2026-07-29T12:02+08:00 — maintenance pre-beta dimulai

- Session: `codex-beta-preflight-2`
- Actor: `Codex`
- Task: Audit persona/profile dan menyiapkan reset data uji profile default.
- Mode: `maintenance`
- Beta code/config: `v0.1.0-beta.1` → `18c770b`; runtime masih pre-checkpoint.
- Observation: Backup Asa valid berisi `SOUL.md` dan tiga skill persona khusus.
  Profile `research` terisolasi lewat `HERMES_HOME`, tidak punya session/memory,
  dan belum mengaktifkan provider eksternal. Profile default berisi 16 hot turn,
  satu shadow memory, lima session state, dan plugin sebelum ADR-0015.
- Severity: `S2`
- Evidence: Audit inventory/hash profile-scoped dan SQLite integrity `ok`.
- Action: Stop hanya gateway default; snapshot penuh; reset data uji default;
  deploy exact checkpoint; restore persona Asa secara selektif; smoke test.
- Result: `open`

### 2026-07-29T12:29+08:00 — beta resmi dimulai

- Session: `codex-beta-preflight-2`
- Actor: `Codex`
- Task: Menyelesaikan preflight, reset data uji, persona multi-profile, deploy,
  snapshot clean-start, dan smoke test.
- Mode: `maintenance`
- Beta code/config: `v0.1.0-beta.1` → `18c770b`; threshold `0.55`; timeout
  answerability/admission `5s`; default `Asa/asa-complex`; research
  `Nellie/nellie-research`.
- Observation: Exact plugin hash cocok pada dua profile. Data uji default
  dipindahkan ke snapshot privat, bukan dihapus tanpa rollback. Kedua profile
  mulai dengan hot/shadow/session/message kosong dan storage terisolasi.
- Observation: Full regression serial 48-query PASS (recall `1.0`, precision@5
  `0.266667`, abstention `1.0`, security exclusion `1.0`, p50 `1386.666 ms`,
  p95 `1924.301 ms`, verifier unavailable `0`). Unit suite: `60 passed`,
  `2 skipped`, `2 subtests passed`.
- Observation: System-2 smoke aktual dengan `asa-complex` menghasilkan trusted
  summary, shadow row trusted, dan hot rows terkonsolidasi. Probe sebelumnya
  sempat fail-closed karena timeout/JSON terpotong; tidak ada unsafe memory yang
  menjadi trusted. Monitor recurrence selama task nyata.
- Observation: Persona Asa dipulihkan hanya dari `SOUL.md` dan tiga skill khusus;
  config/secret lama tidak direstore. Nellie memakai persona riset baru, model
  khusus, dan provider/storage profile-scoped. Kedua gateway aktif.
- Severity: `S2` teramati dan termitigasi; tidak ada severity unresolved.
- Evidence: Snapshot manifest terverifikasi; regression final PASS; plugin hash,
  SQLite integrity, profile model smoke, dan consolidation smoke PASS.
- Action: Mulai baseline beku 7 hari; tanpa tuning; jurnal task nyata dan monitor
  semantic admission latency/invalid JSON.
- Result: `resolved`; beta `Berjalan` sejak `2026-07-29T12:29+08:00`.

### 2026-07-29T13:25+08:00 — visualisasi Graphify dibuka ke tailnet

- Session: `codex-beta-graphify-serve`
- Actor: `Codex`
- Task: Mengekspos visualisasi Graphify dari VPS ke perangkat lain dalam tailnet.
- Mode: `maintenance`
- Beta code/config: Code/provider tidak berubah; user systemd service baru pada
  port `8765`, bind eksklusif ke alamat `tailscale0`.
- Observation: Native `tailscale serve` ditolak karena user bukan operator;
  fallback memakai static HTTP read-only. Served directory hanya berisi symlink
  `index.html` ke generated `graphify-out/graph.html`, bukan seluruh repo/graph.
- Observation: Request melalui IP Tailscale dan MagicDNS menghasilkan HTTP 200,
  `577945` byte, dan exact content match. Request melalui alamat LAN host gagal;
  socket audit menunjukkan listener hanya pada alamat Tailscale.
- Severity: `none`
- Evidence: Service enabled + active, linger enabled, restart persistence PASS,
  exact listener/content/exposure checks PASS.
- Action: Akses hanya dari perangkat yang sudah tersambung tailnet; disable unit
  bila visualisasi tidak lagi diperlukan.
- Result: `resolved`

### 2026-07-29T13:53+08:00 — Telegram Nellie diaktifkan

- Session: `codex-beta-nellie-telegram`
- Actor: `Codex`
- Task: Mendiagnosis dan memperbaiki profile research yang tidak merespons di
  Telegram.
- Mode: `maintenance`
- Beta code/config: Code/provider/model tidak berubah; credential Telegram
  profile-scoped ditambahkan ke `.env` research dengan mode `0600`.
- Observation: Root cause adalah gateway research tidak memiliki token maupun
  allowlist Telegram, sehingga startup menyatakan tidak ada messaging platform
  aktif. Token bot Nellie berbeda dari bot Asa; allowlist/home channel disalin
  dari profile default tanpa mencatat nilainya ke repo.
- Observation: Telegram `getMe` PASS; bot research teridentifikasi sebagai
  `@NellieFaridResearchBot`. Gateway restart hanya untuk research; adapter
  connected dalam polling mode, command registration PASS, dua socket API aktif,
  tidak ada unauthorized/conflict/forbidden, dan pesan outbound test terkirim.
- Severity: `S3`
- Evidence: Config check mendeteksi token+allowlist; bot identity distinct PASS;
  service active/stable; Telegram sendMessage PASS. Snapshot config sebelum
  perubahan disimpan privat di luar repo.
- Action: Farid mengirim `/start` atau pesan biasa ke bot Nellie untuk smoke
  inbound+agent response. Monitor model response dan memory profile isolation.
- Result: `resolved`

### 2026-07-29T13:27+08:00 — verifikasi setelah Graphify update

- Session: `codex-beta-graphify-serve`
- Actor: `Codex`
- Task: Memastikan service menyajikan HTML terbaru setelah graph regenerate.
- Mode: `maintenance`
- Beta code/config: Tidak berubah dari entri sebelumnya.
- Observation: Symlink mengikuti `graphify-out/graph.html` terbaru (`579540` byte);
  endpoint menghasilkan exact content match tanpa restart atau copy manual.
- Severity: `none`
- Evidence: HTTP 200, source/served byte sama, `cmp` PASS, service active+enabled.
- Action: `graphify update .` dapat dijalankan seperti biasa; halaman berikutnya
  otomatis memakai artifact terbaru.
- Result: `resolved`

### 2026-07-29T14:10+08:00 — audit profile context dimulai

- Session: `codex-beta-profile-context`
- Actor: `Codex`
- Task: Audit dan refactor file statis Asa/Nellie agar native terhadap Hermes dan
  memahami arsitektur dual-memory tanpa fine-tuning manual.
- Mode: `maintenance`
- Beta code/config: Runtime tetap `v0.1.0-beta.1`; belum ada file profile diubah.
- Observation: Kedua profile hanya mempunyai `SOUL.md`; native Core Memory
  `memories/MEMORY.md` dan `memories/USER.md` kosong. Tiga skill Asa tidak punya
  YAML frontmatter sehingga deskripsi trigger hilang dari skills index. Nellie
  tidak punya skill lokal. Aturan `research_vault/.hermes.md` merujuk tool
  `fact_store` yang tidak tersedia. Pengetahuan arsitektur tersebar di repo dan
  belum dilayer ke identity/core-memory/on-demand skill profile.
- Severity: `S2`
- Evidence: Audit prompt builder, memory tool, skill parser, profile inventory,
  prompt-size baseline, dokumentasi Hermes resmi, dan arsitektur/ADR repo.
- Action: ADR-0017; repo-owned profile templates; snapshot static runtime; pisah
  karakter di `SOUL.md`, invariants di Core Memory, arsitektur lengkap di skill
  on-demand, dan workflow proyek di `.hermes.md`.
- Result: `open`
### 2026-07-29T14:39+08:00 — layering context profile dideploy dan diverifikasi

- Session: `codex-beta-profile-context`
- Actor: `Codex`
- Task: Menyelesaikan ADR-0017 dengan canonical static profile assets,
  deployment atomik, dan validasi native Hermes.
- Mode: `maintenance`
- Beta code/config: Provider/schema/model/threshold/timeout tidak berubah.
  SOUL, seeded Core Memory, dan skills statis default/research diperbarui melalui
  aset repo; credential, session, SQLite, Chroma, serta memory dinamis tidak
  disalin atau dicatat ke Git.
- Observation: Asa mendapat Core Memory dan empat skill ber-frontmatter; Nellie
  mendapat Core Memory, profile descriptor, skill arsitektur, dan workflow riset.
  Context workspace riset hanya menggunakan capability native yang tersedia.
  Kedua gateway tetap active; perubahan Core Memory berlaku pada sesi baru karena
  snapshot prompt per sesi bersifat frozen.
- Severity: `none`
- Evidence: Native scanner/frontmatter validation PASS; byte-for-byte deployment
  verification PASS pada 13 asset runtime dengan mode `0600`; full suite `65`
  PASS, `2` skipped; gateway default dan Nellie active.
- Action: Lakukan smoke percakapan sesi baru untuk persona, skill discovery,
  Core Memory, dan isolation; catat observasi retrieval nyata tanpa tuning.
- Result: `resolved`

### 2026-07-29T16:45+08:00 — smoke sesi baru Asa dan Nellie PASS

- Session: `codex-beta-profile-context-smoke`
- Actor: `Codex`
- Task: Memverifikasi context profile ADR-0017 pada sesi baru tanpa tool call,
  write, perubahan config, tuning, atau restart.
- Mode: `read-only smoke`
- Beta code/config: Tidak berubah. Probe one-shot memakai `HERMES_HOME` masing-
  masing profile dan hanya memuat skill static profile yang relevan.
- Observation: Asa menyatakan persona hangat-tegas, abstention bila memory tidak
  cukup, trusted/current-state policy, serta langkah daily check-in sesuai skill.
  Nellie menyatakan standar evidence/provenance, memory sebagai historical
  evidence, abstention, workflow riset, dan batas isolation research.
- Observation: Kedua profile menolak mengklaim akses ke profile lain. Tidak ada
  tool call atau output credential/sensitive content. Kedua gateway tetap active;
  SQLite runtime default/research integrity `ok`; 13 static asset tetap
  byte-identik dengan canonical repo.
- Severity: `none`
- Evidence: Dua probe one-shot selesai exit `0`; service health PASS; scanner
  output smoke tidak menemukan marker credential; database integrity PASS.
- Action: Lanjutkan dogfooding task nyata tanpa tuning pada hari 1–7; catat
  observasi retrieval atau failure nyata secara tersanitasi.
- Result: `resolved`

### 2026-07-29T16:50+08:00 — prune skill custom profile dimulai

- Session: `codex-beta-profile-skill-prune`
- Actor: `Codex`
- Task: Menghapus enam skill statis/custom yang dipreseed oleh ADR-0017, sesuai
  keputusan Farid dan ADR-0018.
- Mode: `maintenance`
- Beta code/config: Provider/schema/model/threshold/timeout tidak berubah.
  Snapshot privat skill legacy dibuat sebelum mutasi. Pipeline procedural Fase 7
  tetap hidup di plugin dan `skill-drafts`, bukan sebagai seeded active skill.
- Observation: Deployer hanya akan menghapus path legacy explicit: tiga skill Asa
  serta shared operasi default, dan shared operasi plus workflow Nellie research.
  Skill native/hub lain tidak berada dalam daftar prune.
- Severity: `none`
- Evidence: Snapshot privat checksum tercatat; test targeted deploy/prune PASS.
- Action: Deploy atomik, restart gateway terkontrol agar skills index refresh,
  lalu verifikasi absence, health, dan smoke sesi baru.
- Result: `open`

### 2026-07-29T16:55+08:00 — prune skill custom profile PASS

- Session: `codex-beta-profile-skill-prune`
- Actor: `Codex`
- Task: Menyelesaikan deployment ADR-0018 dan refresh discovery index gateway.
- Mode: `maintenance`
- Beta code/config: Tidak berubah selain penghapusan enam file static custom
  `SKILL.md`; kedua gateway direstart terkontrol setelah deploy.
- Observation: Enam legacy skill absent pada runtime; asset profile static lain
  byte-identik dengan canonical repo. Skill native/hub tidak dipruning. Direktori
  kosong `procedural-memory` bukan active skill; pipeline Fase 7 tetap memakai
  plugin dan draft store di luar active skills.
- Severity: `none`
- Evidence: Deployer targeted test PASS; verify deployment PASS; default dan
  Nellie gateway active; kedua `hot_sessions.sqlite3` integrity `ok`.
- Action: Jalankan smoke sesi baru tanpa preload custom skill; lanjutkan
  dogfooding alami dan ajukan skill hanya melalui draft→approval bila pola nyata
  berulang.
- Result: `resolved`

### 2026-07-29T17:00+08:00 — smoke tanpa custom skill PASS

- Session: `codex-beta-profile-skill-prune-smoke`
- Actor: `Codex`
- Task: Memverifikasi persona, Core Memory, abstention, dan isolation pada sesi
  baru setelah semua custom `SKILL.md` profile dipruning.
- Mode: `read-only smoke`
- Beta code/config: Tidak berubah; probe one-shot tidak preload skill, tidak
  memanggil tool, dan tidak melakukan write.
- Observation: Asa tetap menunjukkan gaya hangat-tegas dan abstain/klarifikasi
  saat memory kurang. Nellie tetap menunjukkan standar evidence, pemisahan
  current/historical state, abstention, dan isolation research.
- Observation: Tidak ada profile yang mengklaim akses lintas profile. Tidak ada
  output credential atau sensitive content.
- Severity: `none`
- Evidence: Dua probe one-shot exit `0`; default dan Nellie gateway tetap active.
- Action: Gunakan task nyata untuk membuktikan pola reusable; skill baru hanya
  melalui draft procedural dan approval manusia.
- Result: `resolved`

### 2026-07-29T17:10+08:00 — analisis read-only kandidat import Obsidian

- Session: `codex-beta-obsidian-import-analysis`
- Actor: `Codex`
- Task: Menilai kelayakan memasukkan catatan static Obsidian ke memory Asa tanpa
  membaca atau menyalin isi catatan ke repo maupun runtime memory.
- Mode: `read-only analysis`
- Beta code/config: Tidak berubah; tidak ada ingestion, indexing, vector write,
  tool call memory, atau perubahan vault.
- Observation: Vault berisi 201 Markdown sekitar 594 KB; 137 berada di archive,
  termasuk 124 daily journal dan 8 dream journal. Banyak wikilink/tag dan ada
  beberapa keluarga revisi/duplikasi. Bulk import akan mencampur personal facts,
  project state, artefak temporal, archive, dan kemungkinan data sensitif/stale.
- Observation: Provider runtime saat ini hanya memiliki 1 trusted + 1 quarantined
  memory pada profile Asa. Pipeline existing menerima turn lalu konsolidasi; belum
  ada importer/backfill vault yang menjaga provenance per file, policy consent,
  dry-run, batch quarantine, atau rollback per source.
- Severity: `S2`
- Evidence: Inventory metadata read-only, access policy vault, graph/pipeline
  inspection, dan count SQLite profile-scoped; tidak ada isi note dicatat.
- Action: Jangan import semua file. Jika disetujui, buat ADR + importer dry-run
  source-aware + test reproduksi + snapshot + baseline comparison, lalu mulai
  pilot kecil dari allowlist fakta stabil yang direview manusia.
- Result: `open`

### 2026-07-29T17:30+08:00 — Pilot 0 import Obsidian siap, belum dieksekusi

- Session: `codex-beta-obsidian-import-pilot-0`
- Actor: `Codex`
- Task: Menyiapkan importer metadata-only, ADR, dokumentasi review, dan test
  sintetis untuk pre-processing vault Asa.
- Mode: `maintenance`
- Beta code/config: Runtime provider/schema/data tidak berubah. Tool tidak
  mengakses vault pribadi pada sesi ini dan tidak memanggil model, Mem0, SQLite,
  atau memory tool.
- Observation: `obsidian_import_dry_run.py` hanya menulis manifest JSONL privat
  di luar vault berisi metadata/provenance file dan klasifikasi deterministic.
  Semua Markdown non-excluded tetap `needs_review`; tidak ada auto-candidate,
  auto-trust, semantic consolidation, atau vector write.
- Severity: `none`
- Evidence: ADR-0019; targeted test metadata-only PASS; full suite `67` PASS,
  `2` skipped; `git diff --check` PASS.
- Action: Farid menjalankan dry-run ke output privat lalu mereview manifest dan
  memilih allowlist eksplisit. Pilot 1 semantic ledger belum boleh dimulai tanpa
  approval, snapshot, dan baseline comparison.
- Result: `resolved`

### 2026-07-29T17:50+08:00 — Pilot 1 semantic candidate ledger disetujui

- Session: `codex-beta-obsidian-import-pilot-1`
- Actor: `Farid` + `Codex`
- Task: Menganalisis semantic lima file allowlist untuk menghasilkan candidate
  ledger review-only bagi Asa.
- Mode: `review-only analysis`
- Beta code/config: Tidak berubah. Approval eksplisit Farid diterima untuk lima
  source yang tercantum pada report Pilot 0. Tidak ada Mem0, SQLite shadow,
  vector, Core Memory, atau runtime memory write pada tahap ini.
- Observation: Output akan disimpan privat dengan provenance source/hash dan
  diajukan per fakta ke Farid; hanya approval fact-level dapat membuka desain
  controlled-import berikutnya.
- Severity: `none`
- Evidence: Approval chat `approve pilot 1`; ADR-0019; manifest Pilot 0.
- Action: Snapshot hash source allowlist, semantic extraction review-only, lalu
  ajukan kandidat tersanitasi untuk keputusan Farid.
- Result: `open`

### 2026-07-29T17:55+08:00 — Pilot 1 mengecualikan metadata sistem

- Session: `codex-beta-obsidian-import-pilot-1`
- Actor: `Farid` + `Codex`
- Task: Menyesuaikan candidate ledger agar hanya fokus pada fakta personal alami.
- Mode: `review-only analysis`
- Beta code/config: Tidak berubah; tidak ada runtime memory write.
- Observation: `p1-005` (metadata struktur/source-of-truth vault) diubah menjadi
  `exclude` oleh keputusan Farid karena berpotensi mengganggu sistem baru yang
  sudah berjalan dan bukan fakta personal alami.
- Severity: `none`
- Evidence: Keputusan review fact-level Farid; candidate ledger privat diperbarui.
- Action: Review hanya kandidat personal natural tersisa sebelum desain Pilot 2.
- Result: `resolved`

### 2026-07-29T18:00+08:00 — Pilot 1 fakta natural disetujui

- Session: `codex-beta-obsidian-import-pilot-1`
- Actor: `Farid` + `Codex`
- Task: Mengunci review fact-level kandidat personal natural dari allowlist.
- Mode: `review-only analysis`
- Beta code/config: Tidak berubah; ledger privat saja, tanpa Mem0/vector/SQLite/
  Core Memory/runtime memory write.
- Observation: Farid menyetujui dua fakta stable tentang preferensi pendampingan
  dan dua ide sebagai historical-only. Metadata sistem, konteks kosong, instruksi,
  serta jadwal temporal tetap excluded.
- Severity: `none`
- Evidence: Approval chat `approve rekomendasi natural`; ledger private `0600`.
- Action: Rancang Pilot 2 controlled-import untuk empat kandidat approved;
  write-path tetap membutuhkan snapshot, test, baseline comparison, dan approval
  write eksplisit Farid.
- Result: `resolved`

### 2026-07-29T18:10+08:00 — desain Pilot 2 controlled import selesai

- Session: `codex-beta-obsidian-import-pilot-2-design`
- Actor: `Codex`
- Task: Menetapkan kontrak provenance batch, admission, temporal visibility,
  idempotency, verification, dan rollback sebelum import kandidat Pilot 1.
- Mode: `design-only`
- Beta code/config: Tidak berubah; tidak ada schema migration, importer runtime,
  snapshot runtime baru, Mem0/vector/SQLite/Core Memory write, atau vault change.
- Observation: Jalur session consolidation tidak cukup untuk provenance note dan
  approval fact-level. ADR-0020 mensyaratkan batch profile-scoped, shadow
  candidate→admission, source hash, dan rollback compensating tanpa delete diam.
- Severity: `none`
- Evidence: ADR-0020 dan Pilot 2 contract; kontrak storage/admission existing
  ditinjau; Pilot 1 ledger approval terkunci privat.
- Action: Menunggu approval write eksplisit Farid untuk mengimplementasikan schema
  provenance/importer, membuat snapshot, menjalankan dry-run+baseline, lalu
  mengajukan rencana batch exact sebelum write.
- Result: `resolved`

### 2026-07-29T18:20+08:00 — Pilot 2 dry-run planner PASS

- Session: `codex-beta-obsidian-import-pilot-2-design`
- Actor: `Codex`
- Task: Menambahkan planner batch read-only untuk kandidat Pilot 1 approved dan
  test synthetic provenance/temporal/idempotency.
- Mode: `dry-run implementation`
- Beta code/config: Runtime provider/schema/data tidak berubah. Planner tidak
  memiliki write API ke Mem0, SQLite, Core Memory, atau vault.
- Observation: Planner hanya memfilter approval ledger, membuat idempotency key
  candidate+source hash, dan memaksa label historical untuk historical-only;
  semua item tetap `memory_write=false` dan `admission=required_fail_closed`.
- Severity: `none`
- Evidence: Targeted tests PASS; full suite `69` PASS, `2` skipped; diff check
  PASS. Tidak ada snapshot runtime baru karena belum ada mutation.
- Action: Menunggu approval eksplisit Farid untuk implementasi schema provenance
  dan importer write-path; sesudahnya tetap perlu snapshot, dry-run runtime,
  baseline comparison, serta approval write batch final.
- Result: `resolved`

### 2026-07-29T18:35+08:00 — Pilot 2 write-path code PASS, belum dideploy

- Session: `codex-beta-obsidian-import-pilot-2-implementation`
- Actor: `Codex`
- Task: Mengimplementasikan schema provenance dan importer explicit untuk batch
  reviewed, lalu menguji temporal, admission, idempotency, serta rollback pada
  SQLite/Mem0 palsu di temporary directory.
- Mode: `code-only test`
- Beta code/config: Runtime Asa tidak berubah. Tidak ada plugin deployment,
  gateway restart, schema migration runtime, snapshot runtime baru, vault read,
  Mem0/vector/SQLite/Core Memory write pada profile aktif.
- Observation: Write-path tidak dipanggil hook provider. Ia memakai `infer=False`,
  membuat shadow candidate lalu final trusted/quarantined, menyimpan provenance,
  memblokir historical dari current-state, dan rollback mengkarantina batch tanpa
  delete audit lineage.
- Severity: `none`
- Evidence: Import batch synthetic tests PASS; full suite PASS; diff check PASS.
- Action: Sebelum deploy/write: Farid perlu approval deployment schema/importer,
  snapshot Asa code+data, plugin deploy/restart terkontrol, dry-run terhadap ledger
  privat, baseline comparison, lalu approval batch write final untuk empat ID.
- Result: `resolved`

### 2026-07-29T18:50+08:00 — invariant Pilot 2 rollback/admission/temporal PASS

- Session: `codex-beta-obsidian-import-pilot-2-invariants`
- Actor: `Codex`
- Task: Membuktikan sebelum deployment bahwa rollback, admission, dan historical
  visibility bekerja pada jalur importer serta retrieval production di temp DB.
- Mode: `temp integration test`
- Beta code/config: Runtime Asa tidak berubah; seluruh test memakai SQLite/Mem0
  palsu temporary dan tidak membaca vault atau database profile aktif.
- Observation: Rollback batch mengkarantina seluruh shadow row dan prefetch tidak
  lagi menampilkan item. Importer selalu memanggil `evaluate_admission`; LLM
  unavailable menghasilkan quarantine fail-closed, meski kandidat sudah disetujui
  manusia. Historical-only diset invalid untuk current query, tetapi muncul hanya
  pada query historis eksplisit sebelum rollback.
- Severity: `none`
- Evidence: Temp production-prefetch invariant test PASS; full suite PASS; diff
  check PASS. Importer juga menolak execution tanpa `write_approved=True`.
- Action: Invariant code PASS, tetapi runtime Asa belum membuktikannya sampai
  deployment/snapshot/baseline terkontrol disetujui Farid.
- Result: `resolved`

### 2026-07-29T19:00+08:00 — deployment Pilot 2 Asa dimulai

- Session: `codex-beta-obsidian-import-pilot-2-deploy`
- Actor: `Farid` + `Codex`
- Task: Mendeploy jalur import provenance ke profile Asa/default setelah invariant
  temp PASS, tanpa menjalankan batch fakta Pilot 1.
- Mode: `maintenance`
- Beta code/config: Akan menambah schema provenance ketika plugin Asa start.
  Tidak ada write candidate, Mem0/vector content, atau perubahan profile research.
- Observation: Deployment didahului stop terkontrol gateway Asa dan snapshot privat
  code+data berpasangan; Nellie tetap berjalan.
- Severity: `none`
- Evidence: Approval Farid untuk lanjut; invariant `73 PASS, 2 skipped`.
- Action: Snapshot, deploy atomik, restart Asa, integrity/schema/dry-run/baseline,
  lalu ajukan approval write batch terpisah.
- Result: `open`

### 2026-07-29T19:05+08:00 — deployment Pilot 2 ditunda oleh preflight gateway Asa

- Session: `codex-beta-obsidian-import-pilot-2-deploy`
- Actor: `Codex`
- Task: Melindungi deployment Pilot 2 saat preflight gateway default tidak clean.
- Mode: `maintenance`
- Beta code/config: Tidak berubah. Preflight menghentikan gateway Asa, tetapi
  service mencapai state `failed` saat shutdown/start boundary sebelum snapshot
  atau plugin deployment berjalan.
- Observation: Tidak ada snapshot Pilot 2 dibuat, tidak ada deploy plugin,
  schema migration runtime, vector/Mem0/SQLite/Core Memory write, atau import
  candidate. Gateway Asa kemudian dipulihkan `active`; gateway Nellie tetap active.
- Severity: `S2`
- Evidence: systemd menunjukkan exit `1` pada boundary `18:54`; recovery start
  menghasilkan kedua gateway `active`.
- Action: Tunda deployment/import Pilot 2. Diagnosis dan stabilkan failure gateway
  baseline terlebih dahulu; ulang preflight bersih sebelum snapshot/deploy.
- Result: `open`

### 2026-07-29T19:05+08:00 — Pilot 2 Asa dideploy, batch fakta masih kosong

- Session: `codex-beta-obsidian-import-pilot-2-deploy`
- Actor: `Codex`
- Task: Menyelesaikan deployment plugin provenance pada Asa/default dan
  memverifikasi pre-write gate tanpa mengimport kandidat Pilot 1.
- Mode: `maintenance`
- Beta code/config: Plugin Asa diperbarui atomik setelah snapshot privat
  code+data berpasangan; schema `import_batches` dan provenance dibuat kosong.
  Profile research/Nellie tidak diubah.
- Observation: Asa dan Nellie active; SQLite Asa integrity `ok`; deployed code
  byte-match source. Provenance `0` row dan belum ada write batch. Baseline subset
  PASS untuk recall, temporal, abstention, dan security; latency p95 dibanding
  baseline naik, sehingga tetap dimonitor selama dogfooding.
- Severity: `none`
- Evidence: Snapshot checksum privat; schema/count check PASS; regression PASS:
  recall `1.0`, precision `0.233333`, p50 `1596.118 ms`, p95 `2397.524 ms`.
- Action: Minta approval final Farid untuk batch exact `p1-001` sampai `p1-004`.
  Tanpa approval ini importer tidak dieksekusi.
- Result: `resolved`

### 2026-07-29T19:15+08:00 — batch import Obsidian 001 disetujui dan dimulai

- Session: `codex-beta-obsidian-import-batch-001`
- Actor: `Farid` + `Codex`
- Task: Mengimpor empat kandidat Pilot 1 yang telah direview ke Asa/default
  melalui batch `obsidian-pilot2-batch-001`.
- Mode: `controlled data import`
- Beta code/config: Batch hanya target Asa/default; admission fail-closed,
  provenance, idempotency, historical visibility, dan rollback aktif.
- Observation: Approval final Farid diterima untuk `p1-001`–`p1-004`. Source hash
  akan diverifikasi ulang terhadap ledger sebelum write; gateway Asa dihentikan
  terkontrol untuk menghindari concurrent provider write. Nellie tidak disentuh.
- Severity: `none`
- Evidence: Approval chat `approve import batch 001`; snapshot/deploy/baseline
  Pilot 2 PASS.
- Action: Verify hash, execute batch, restart Asa, verify retrieval/security, dan
  rollback bila invariant fail.
- Result: `open`

### 2026-07-29T19:06+08:00 — batch Obsidian 001 rollback fail-closed

- Session: `codex-beta-obsidian-import-batch-001`
- Actor: `Codex`
- Task: Menangani hasil admission batch import empat kandidat approved.
- Mode: `controlled data import`
- Beta code/config: Tidak diubah setelah deployment Pilot 2; tidak ada tuning atau
  retry otomatis dilakukan.
- Observation: Admission semantic timeout pada `p1-001` dan `p1-004`; keduanya
  menjadi quarantined. Karena seluruh batch harus trusted, importer menjalankan
  compensating rollback: empat shadow row batch blocked/quarantined dan batch
  berstatus `rolled_back`. Tidak ada kandidat visible untuk current-state.
- Severity: `S2`
- Evidence: SQLite integrity `ok`; batch provenance `rolled_back`; visible trusted
  current `0`; Asa dan Nellie gateway active setelah recovery.
- Action: Jangan retry batch. Investigasi latency/timeout admission dengan test
  reproduksi dan baseline comparison sebelum mengajukan batch baru; pertahankan
  source/approval ledger privat untuk audit.
- Result: `mitigated`

### 2026-07-30T14:10+08:00 — BETA-011 bounded System-2 combo consolidation dimulai

- Session: `codex-beta-011-router-combo-consolidation`
- Actor: `Farid` + `Codex`
- Task: Mereproduksi timeout konsolidasi Asa/default pada combo `asa-complex` dan
  menyiapkan hardening bounded-request tanpa deploy runtime.
- Mode: `controlled code experiment`
- Beta code/config: Source plugin saja. Tidak ada gateway restart, runtime config,
  SQLite, Chroma, atau memory write yang diubah. ADR-0021 menetapkan batch
  whole-turn deterministik maksimal 24.000 karakter.
- Observation: Sesi default `20260729_192828_3c4c16c0` memiliki 104 hot turn
  pending dan 110.832 karakter. Trigger `on_session_end` berjalan, tetapi dua
  request LLM ke combo timeout (`httpx.ReadTimeout`/`APITimeoutError`) dan
  provider mempertahankan rows pending.
- Severity: `S2`
- Evidence: journal gateway 2026-07-30 13:56+08; test reproduksi local
  `tests/test_consolidation.py`.
- Action: Implementasi source, test targeted, baseline comparison sebelum deploy;
  snapshot runtime berpasangan tetap wajib sebelum plugin Asa diganti.
- Result: `open`

### 2026-07-30T14:10+08:00 — BETA-011 source hardening + repro test PASS

- Session: `codex-beta-011-router-combo-consolidation`
- Actor: `Codex`
- Task: Membatasi request System-2 untuk combo router tanpa mengurangi
  fail-closed semantics.
- Mode: `controlled code experiment`
- Beta code/config: `chunk_rows()` membagi hot turns kronologis pada batas
  24.000 karakter tanpa memotong turn. Hanya chunk yang sukses lengkap melalui
  consolidation, admission, dan shadow write yang ditandai consolidated; failure
  menghentikan run sehingga chunk gagal serta chunk berikutnya tetap pending.
  Tidak ada deploy/runtime mutation.
- Observation: Repro sesi panjang PASS dalam dua request bounded. Repro timeout
  chunk ketiga PASS: dua chunk awal committed, satu chunk terakhir tetap pending.
- Severity: `S2`
- Evidence: `.venv/bin/python -m unittest tests/test_consolidation.py -v` →
  `6 tests OK`; ADR-0021.
- Action: Jalankan baseline comparison yang relevan, review diff, snapshot data
  Asa, lalu minta approval eksplisit sebelum deploy/retry konsolidasi nyata.
- Result: `pending deployment review`

### 2026-07-30T14:15+08:00 — BETA-011 predeploy baseline PASS; deploy Asa disetujui

- Session: `codex-beta-011-router-combo-consolidation`
- Actor: `Farid` + `Codex`
- Task: Menjalankan gate baseline sebelum deployment BETA-011 ke Asa/default.
- Mode: `controlled deployment`
- Beta code/config: Perubahan terbatas pada plugin Asa/default sesuai ADR-0021;
  profile research/Nellie tidak masuk scope dan tidak akan direstart.
- Observation: Gateway Asa active; SQLite hot-session integrity `ok`; regression
  empat kategori PASS sebelum deploy.
- Severity: `S2`
- Evidence: `/tmp/beta-011-predeploy-baseline.json`: recall `1.0`, precision
  `0.233333`, p50 `1785.262 ms`, p95 `2369.507 ms`; single-session, temporal,
  abstention, dan security exclusion seluruhnya PASS.
- Action: Stop Asa, buat snapshot code+data berpasangan privat, deploy atomik,
  restart, verify byte-match/health, lalu smoke/baseline postdeploy.
- Result: `open`

### 2026-07-30T14:36+08:00 — BETA-011 maintenance gate diperbaiki; gateway pulih

- Session: `codex-beta-011-router-combo-consolidation`
- Actor: `Codex`
- Task: Menangani stop gate yang salah saat snapshot predeploy Asa.
- Mode: `controlled deployment`
- Beta code/config: Tidak ada plugin/runtime data yang dideploy atau diubah.
  Runbook diperbaiki: `SIGTERM` gateway dapat berakhir status systemd `failed`
  meski proses sudah berhenti, sehingga gate memakai absennya proses gateway.
- Observation: Stop sebelumnya menghentikan proses Asa; service langsung start
  kembali dan `active`. Snapshot belum lengkap, deployment belum berjalan.
- Severity: `S2`
- Evidence: systemd log 2026-07-30 14:35+08 menunjukkan shutdown SIGTERM lalu
  exit `1`; `systemctl start` memulihkan `active` pada attempt pertama.
- Action: Buat snapshot berpasangan dengan gate proses, deploy atomik Asa saja,
  lalu jalankan smoke dan baseline postdeploy.
- Result: `open`

### 2026-07-30T14:39+08:00 — BETA-011 deployed ke Asa/default; postdeploy PASS

- Session: `codex-beta-011-router-combo-consolidation`
- Actor: `Farid` + `Codex`
- Task: Deploy atomik ADR-0021 ke plugin Asa/default dan verifikasi baseline.
- Mode: `controlled deployment`
- Beta code/config: Asa/default saja menerima bounded whole-turn chunking 24.000
  karakter. Plugin lama dipertahankan lokal sebagai rollback deployment. Nellie/
  research tidak diubah atau direstart. Tidak ada retry konsolidasi sesi pending.
- Observation: Snapshot code+data berpasangan privat dibuat ketika seluruh
  gateway Asa quiescent. Gateway sempat memiliki orphan akibat `Restart=always`;
  orphan dihentikan sebelum snapshot. Gateway baru active setelah deploy;
  deployed files byte-match source dan SQLite integrity `ok`.
- Severity: `S2`
- Evidence: paired snapshot checksum PASS; postdeploy `/tmp/beta-011-postdeploy-
  baseline.json`: overall PASS, recall `1.0`, precision `0.233333`, p50
  `1544.128 ms`, p95 `2323.270 ms`; empat kategori PASS.
- Action: Observasi dua hari aktif. Rollback code+data bila S0/S1 atau invariant
  trusted/retrieval/security gagal; jangan retry pending session tanpa approval.
- Result: `active observation`

### 2026-07-30T14:40+08:00 — BETA-011 gateway orphan cleanup PASS

- Session: `codex-beta-011-router-combo-consolidation`
- Actor: `Codex`
- Task: Memastikan satu gateway Asa/default setelah deployment.
- Mode: `deployment verification`
- Beta code/config: Tidak berubah. Satu proses gateway lama yang orphan dari
  `Restart=always` dihentikan; process systemd `MainPID` aktif dipertahankan.
- Observation: Setelah cleanup, hanya gateway `MainPID` aktif. Deployed
  `__init__.py` dan `consolidation.py` byte-match source; hot SQLite integrity
  tetap `ok`; count tetap `168` total, `162` pending, `6` consolidated.
- Severity: `S2`
- Evidence: `systemctl --user is-active hermes-gateway.service` → `active`;
  PID systemd tunggal verified.
- Action: Lanjut observation window BETA-011; tidak ada retry sesi pending.
- Result: `resolved`

### 2026-07-30T14:50+08:00 — BETA-011 rollout Research + legacy consolidation disetujui

- Session: `codex-beta-011-legacy-consolidation`
- Actor: `Farid` + `Codex`
- Task: Mendeploy ADR-0021 ke Nellie/research dan memicu konsolidasi terkontrol
  untuk hot sessions lama default serta research.
- Mode: `controlled code and data operation`
- Beta code/config: Research menerima plugin byte-identik dengan Asa/default.
  Default tidak diubah lagi. Setiap profile disnapshot sebelum deploy/write;
  consolidation mempertahankan fail-closed dan tidak menghapus hot turns.
- Observation: Asa/default BETA-011 baseline postdeploy PASS. Research hot SQLite
  integrity `ok`, memiliki 50 turn pending; plugin research belum memuat ADR-0021.
- Severity: `S2`
- Evidence: user approval eksplisit; DB summary tersanitasi; ADR-0021.
- Action: Snapshot+deploy Nellie, verify health, lalu invoke consolidation secara
  serial untuk tiap session pending besar; monitor shadow status dan hot markers.
- Result: `open`

### 2026-07-30T14:51+08:00 — BETA-012 Research rollout PASS; legacy triggers fail-closed

- Session: `codex-beta-011-legacy-consolidation`
- Actor: `Farid` + `Codex`
- Task: Rollout ADR-0021 ke Nellie/research dan menjalankan trigger konsolidasi
  serial untuk sesi legacy terbesar default dan research.
- Mode: `controlled code and data operation`
- Beta code/config: Research plugin dideploy atomik dari source yang sama dengan
  Asa/default; previous plugin dan paired private snapshot dipertahankan.
- Observation: Research postdeploy baseline subset PASS: recall `1.0`, precision
  `0.233333`, p50 `1422.811 ms`, p95 `1880.019 ms`; empat kategori PASS.
  Trigger default session `20260729_192828_3c4c16c0` (104 turns) dan research
  session `20260729_183307_116d9cfd` (46 turns) masing-masing mengirim chunk
  pertama lalu retry sekali; keduanya `APITimeoutError`/`ReadTimeout`.
- Severity: `S2`
- Evidence: kedua provider return `report_present=False`; pending tetap default
  `104`, research `46`; shadow status/count tidak berubah; kedua gateway active.
- Action: Hentikan retry. ADR-0021 menjaga fail-closed tetapi batas 24.000
  karakter belum memadai terhadap latency combo. Perubahan baru wajib ADR,
  repro ukuran lebih kecil, baseline, snapshot, dan approval Farid.
- Result: `mitigated; follow-up required`

### 2026-07-30T15:00+08:00 — BETA-013 6k combo budget disetujui untuk deploy

- Session: `codex-beta-013-combo-budget`
- Actor: `Farid` + `Codex`
- Task: Deploy ADR-0022 ke Asa/default dan Nellie/research, lalu retry sekali
  konsolidasi legacy terkontrol.
- Mode: `controlled code and data operation`
- Beta code/config: Batas transcript System-2 berubah 24.000 ke 6.000 karakter;
  turn tetap utuh. ADR-0022 dan full suite `76 PASS, 2 skipped` telah diverifikasi.
- Observation: BETA-011 timeout pada chunk 24.000 karakter di kedua profile;
  seluruh data tetap pending/fail-closed.
- Severity: `S2`
- Evidence: full suite PASS; ADR-0022; approval eksplisit Farid.
- Action: Snapshot paired kedua profile, deploy atomik, baseline postdeploy,
  trigger satu kali legacy default lalu research; rollback code+data untuk S0/S1.
- Result: `open`

### 2026-07-30T15:10+08:00 — BETA-013 6k combo budget deploy + legacy consolidation

- Session: `codex-beta-013-combo-budget`
- Actor: `Farid` + `Codex`
- Task: Deploy ADR-0022 to both profiles and perform approved serial legacy
  consolidation.
- Mode: `controlled code and data operation`
- Beta code/config: Both plugins now use deterministic whole-turn 6.000-character
  System-2 batches. Paired private snapshots, prior plugins, and rollback path
  remain available. No profile isolation change.
- Observation: Postdeploy subset baseline PASS on default (recall `1.0`, p95
  `2077.477 ms`) and research (recall `1.0`, p95 `1874.518 ms`). Default legacy
  session 104/104 and research legacy 46/46 are fully consolidated. Semantic
  admission quarantined unsafe/instruction-like or timed-out reports; trusted
  additions occur only after admission. Both SQLite databases integrity `ok`;
  both gateways active.
- Observation: Default session `20260729_145046_8b2bb955` processed 43/54 rows.
  Chunk 5 returned invalid `memory_type`; retry also invalid. Its remaining 11
  turns stay pending and no report from that chunk was written.
- Severity: `S2`
- Evidence: full suite `76 PASS, 2 skipped`; hot default `104→0`, research
  `46→0`; final shadow counts default trusted `21`/quarantined `14`, research
  trusted `5`/quarantined `8`.
- Action: Observe BETA-013. Do not retry the malformed 11-turn chunk without a
  parser-specific ADR/reproduction/baseline/snapshot/approval sequence.
- Result: `active observation; timeout mitigated`

### 2026-07-30T15:25+08:00 — Gateway `/new` bypasses memory-provider boundary

- Session: `codex-beta-013-gateway-boundary-diagnosis`
- Actor: `Codex`
- Task: Mendiagnosis session default yang berstatus `session_reset` tetapi hot
  rows tetap pending setelah `/new`.
- Mode: `read-only diagnosis`
- Beta code/config/data: Tidak berubah.
- Observation: Hermes CLI path memiliki `MemoryManager.commit_session_boundary_async`,
  yang memanggil provider `on_session_end` sebelum switch. Namun gateway Telegram
  `/new` memakai `gateway.slash_commands._handle_reset_command`: ia membersihkan
  resource/evict cached agent, memutar `AsyncSessionStore.reset_session`, lalu
  hanya menjalankan generic plugin hook `on_session_finalize`. Path itu tidak
  memanggil `MemoryManager.commit_session_boundary_async` atau provider
  `on_session_end`.
- Observation: state.db membuktikan session `20260730_144534_922c306a` sudah
  ended dengan `end_reason=session_reset` dan tiga message persisted; hot rows
  tetap pending serta tidak ada log consolidation. Ini adalah missing Hermes
  gateway integration, bukan gagal plugin/SQLite/model.
- Severity: `S2`
- Evidence: installed Hermes `gateway/slash_commands.py` reset path; installed
  `agent/memory_manager.py` boundary API; default state/hot SQLite read-only.
- Action: Jangan patch/rebuild Hermes di repo plugin ini. Ajukan upstream Hermes
  issue/fix agar gateway reset meneruskan snapshot old session ke memory manager
  sebelum cached-agent eviction; gunakan trigger terkontrol untuk sesi existing
  sampai upstream tersedia.
- Result: `open upstream integration defect`

### 2026-07-30T15:35+08:00 — Upstream Hermes gateway `/new` boundary fix approved

- Session: `codex-beta-013-gateway-boundary-diagnosis`
- Actor: `Farid` + `Codex`
- Task: Deploy local upstream Hermes fix for missing provider `on_session_end`
  delivery from gateway `/new`/`/reset`.
- Mode: `controlled upstream integration fix`
- Beta code/config: Hermes `gateway/slash_commands.py` now invokes the cached
  agent's `commit_memory_session()` before resource cleanup; cleanup skips a
  second memory shutdown to avoid duplicate extraction. A focused async
  regression passes via direct coroutine execution; compile validation PASS.
- Observation: This reuses Hermes existing provider lifecycle rather than adding
  a plugin workaround. Both profile runtime data will be snapshotted before
  gateway restart/test.
- Severity: `S2`
- Evidence: `tests/gateway/test_session_model_reset.py` focused regression;
  installed `MemoryManager` lifecycle contract.
- Action: Snapshot, restart both gateways (shared upstream source), issue `/new`
  on default active session, then verify hot consolidation and lifecycle logs.
- Result: `open`

### 2026-07-30T15:36+08:00 — Gateway boundary fix deployed; runtime verification pending

- Session: `codex-beta-013-gateway-boundary-diagnosis`
- Actor: `Codex`
- Task: Restart both gateways with the local upstream `/new` memory boundary fix.
- Mode: `controlled upstream integration fix`
- Beta code/config: Both gateways load patched local Hermes source. The patch
  commits cached-agent memory before cleanup and suppresses duplicate provider
  shutdown extraction. No plugin/schema/runtime memory mutation occurred.
- Observation: Focused direct async regression PASS; source compile PASS;
  paired snapshot checksum PASS. Default and research gateways active, with one
  process each under their expected profile homes.
- Severity: `S2`
- Evidence: systemd health PASS; source diff restricted to gateway reset lifecycle
  plus focused regression test.
- Action: User sends `/new` once on Asa/default; inspect old hot row markers,
  shadow admissions, and logs after the background consolidation completes.
- Result: `deployed; runtime verification pending`

### 2026-07-30T15:45+08:00 — Gateway `/new` durable-boundary fallback prepared

- Session: `codex-beta-013-gateway-boundary-diagnosis`
- Actor: `Codex`
- Task: Extend the upstream boundary fix for cache-miss gateway sessions.
- Mode: `controlled upstream integration fix`
- Beta code/config: When no cached agent exists at `/new`, gateway loads the
  configured memory provider, restores the durable session transcript from
  `state.db`, initializes provider scope with the old session identity, fires
  `on_session_end`, then shuts down the temporary manager. Cached-agent path
  remains first choice and avoids duplicate shutdown extraction.
- Observation: The prior fix did not activate because the default Telegram
  session had no cached agent at reset. Focused cached-agent and durable-fallback
  async regressions PASS; compile and diff checks PASS.
- Severity: `S2`
- Evidence: `tests/gateway/test_session_model_reset.py` direct coroutine tests.
- Action: Snapshot revised local Hermes source, restart default gateway, issue
  one `/new`, then verify hot rows/shadow writes.
- Result: `open`

### 2026-08-05T05:05+08:00 — ADR-0023: timeout konsolidasi 30s→90s (research mati sejak 07-31)

- Session: `nellie-adr-0023-consolidation-timeout`
- Actor: `Nellie`
- Task: Diagnosa dan perbaiki konsolidasi System-2 profil research yang berhenti
  sejak 2026-07-31 (memory_index beku di 14 entri, 71 hot rows menggantung).
- Mode: `controlled provider hardening (ADR-0023)`
- Beta code/config: Tidak ada perubahan config/schema killer. Naikkan default
  `HERMES_DUAL_MEMORY_LLM_TIMEOUT` 30s→90s dengan guard clamp minimum 60s di
  `_load_llm_callable`; tambah observability kegagalan ke
  `maintenance_state.last_consolidation_error` di `_consolidate_locked`.
- Observation: Reproduksi sebelum perbaikan (timeout 30s) pada 20 chunk
  (2 sesi) mendapati 1 `APITimeoutError` pada payload kecil chunk 2 sesi
  20260731_151911_a1bc21d1; mean 14.8s, p95 29.1s — timeout 30s tepat di p95.
  Setelah perbaikan (timeout 90s), rerun 3 sesi = 21/21 chunk sukses (100%),
  termasuk chunk 4 sesi 20260730 yang makan 38.8s (bukti 30s terlalu ketat).
  Regression suite `test_storage/test_consolidation/test_shadow_index` = 16 passed.
- Severity: `S2` diturunkan — akar kegagalan konsolidasi research teridentifikasi
  dan terverifikasi pulih.
- Action: Deploy ke profil research (restart gateway) lalu verifikasi konsolidasi
  live pada sesi nyata berikutnya; pantau `maintenance_state.last_consolidation_error`.
- Result: `implemented; runtime deployment pending`

### 2026-08-05T05:20+08:00 — Recovery konsolidasi pending research (ADR-0023)

- Session: `nellie-recovery-pending-consolidation`
- Actor: `Nellie`
- Task: Konsolidasikan sisa hot rows `consolidated=0` di profil research yang
  menggantung sejak sebelum ADR-0023 (sesi 07-30, 07-31, 08-03, 08-04).
- Mode: `controlled recovery via production consolidation pipeline`
- Beta code/config: Script `scripts/recover_pending_consolidation.py` meniru
  `_consolidate_locked` (chunk_rows 6000 char, consolidate_once, mark_consolidated
  per-chunk-sukses). Memakai llm_call timeout 90s (ADR-0023), mem0 client sama,
  user_id `default` agar konsisten retrieval. Snapshot data dibuat sebelum run.
- Observation: 74 pending (5 sesi) -> 72 rows ter-consolidate, 2 gagal.
  memory_index naik 15 -> 39 (trusted 25, quarantined 14). 2 baris gagal dari
  sesi 20260731_151911_a1bc21d1 karena model memproduksi `new_skills` dengan
  detail >1200 char (severity S2 yang sudah dikenal). Verifikasi retrieval
  memakai mem0.search + join shadow index: trusted visible, quarantined
  ter-block — memory yang di-recover dapat digunakan dengan benar.
- Severity: `S2` (2 baris gagal parsial, bukan S0/S1 — tidak menghentikan beta).
- Action: 2 baris gagal dibiarkan pending (fail-closed) sampai ada ADR/repro
  parser untuk batas new_skills; tidak paksa retry tanpa baseline.
- Result: `done`
