# Fase 9 — Hardening & Rilis Portofolio: Implementation Plan

> **Untuk Hermes:** gunakan skill `subagent-driven-development` untuk eksekusi task-by-task (fresh subagent per task, review dua tahap: spec compliance → code quality).

**Goal:** Menyelesaikan hardening teknis hasil beta + menyiapkan dokumentasi portofolio-grade sehingga repo `hermes-dual-memory` siap publik dan instalasi ulang dari nol mengikuti README saja berhasil.

**Architecture:** Repo sudah memiliki plugin memory provider lengkap (System-1 hot capture SQLite → System-2 consolidation → Mem0 + shadow index → admission → retrieval). Fase 9 = (a) hardening kecil dari temuan beta (backup_paths production verification, quarantine threshold review), (b) evaluasi opsional mekanisme herald baru (micro-compaction, context engine) dengan keputusan ADR, (c) dokumentasi portofolio (README root, README publik, demo, cleanup), (d) uji instalasi ulang bersih.

**Tech Stack:** Python 3.11, Hermes Agent (herald v0.20.1), Mem0 (OSS in-process), SQLite, Chroma, unittest (no pytest di venv).

---

## Konteks Saat Ini (dari beta, terverifikasi 2026-08-16)

- **Beta TUTUP**: 14/14 hari aktif, 49/30 sesi, baseline PASS (recall 1.0, p95 2075ms), rollback drill PASS, test 87/87, semua open item material tertutup.
- **Hardening candidates dari beta + herald audit** (CLOSURE-SUMMARY §4, herald-provider-contract.md):
  - `backup_paths()` sudah diimplementasikan (ADR-0024) tapi **belum diverifikasi di produksi** (apakah `hermes backup` benar-benar menyertakan data dual-memory).
  - Rasio quarantine coding 19:19 — review threshold admission timeout 5s.
  - Micro-compaction herald (off by default, break prompt cache) — evaluasi, bukan aktifkan.
  - Context engine pluggable — evaluasi.
- **Repo**: tidak ada `README.md` root (harus dibuat). Docs lengkap di `docs/{architecture,decisions,beta,phases,testing}`. 14 test files, 87 test PASS. Plugin di `plugins/memory/hermes-dual-memory/` (12 file).

---

## Prinsip (sesuai AGENTS.md + ADR-0016)

- Perubahan policy/arsitektur → **ADR baru** dulu.
- Perubahan code → test reproduksi → baseline comparison → snapshot → approval manusia sebelum push/PR.
- Branch kerja: `beta/0.1-*` untuk sisa pekerjaan beta; Fase 9 resmi di branch baru (mis. `fase-9/portofolio`) setelah approval.
- Jangan aktifkan provider `mem0` resmi bersamaan dengan plugin ini.
- Jangan over-engineer: kerjakan yang diperlukan, tanya sebelum menambah scope.

---

## Task Breakdown

### Task 1: Tandai penutupan beta resmi

**Objective:** Update CURRENT.md + jurnal + CLOSURE-SUMMARY dengan status "Selesai" dan tanggal tutup resmi (2026-08-16).

**Files:**
- Modify: `docs/beta/v0.1.0-beta.1/CURRENT.md` (status → Selesai)
- Modify: `docs/beta/v0.1.0-beta.1/journal.md` (entri penutupan)
- Modify: `docs/beta/v0.1.0-beta.1/CLOSURE-SUMMARY.md` (tambahkan keputusan Farid + tanggal)

**Steps:**
1. Patch CURRENT.md status beta → `Selesai (2026-08-16)`.
2. Append jurnal entri penutupan resmi (actor, keputusan, konsekuensi).
3. Patch CLOSURE-SUMMARY §5 → catat keputusan "Tutup sekarang → Fase 9".
4. Commit: `git add ... && git commit -m "[fase-9] tutup beta resmi 2026-08-16 (ref ADR-0016)"`.

**Verification:** `grep "Selesai" docs/beta/v0.1.0-beta.1/CURRENT.md` → found; commit ada di log.

---

### Task 2: Buat branch Fase 9

**Objective:** Pisahkan kerja Fase 9 dari branch beta.

**Steps:**
1. `git checkout -b fase-9/portofolio` (dari HEAD).
2. Push branch (perlu approval Farid — minta sebelum push).

**Verification:** `git branch --show-current` → `fase-9/portofolio`.

---

### Task 3: Verifikasi `backup_paths()` di produksi (ADR-0024)

**Objective:** Buktikan `hermes backup` benar-benar menyertakan data dual-memory (hot_sessions, memory_index, chroma) setelah implementasi ADR-0024.

**Files:**
- Modify: (jika gagal) `plugins/memory/hermes-dual-memory/__init__.py` (backup_paths)
- Test: (jika perlu) `tests/test_herald_compatibility.py`

**Steps:**
1. Cek implementasi `backup_paths()` di `__init__.py` (sudah ada dari ADR-0024).
2. Jalankan `hermes backup --help` untuk tahu cara invoke; jalankan backup ke dir temp.
3. Inspeksi isi backup: apakah `hermes-dual-memory/` (hot_sessions.sqlite3, memory_index, chroma) masuk?
4. Jika ya → dokumentasikan bukti di jurnal. Jika tidak → fix `backup_paths()`, test, commit.

**Verification:** Backup berisi `hermes-dual-memory/*` — bukti tertulis di jurnal Fase 9.

---

### Task 4: Review quarantine threshold (admission timeout)

**Objective:** Analisis rasio quarantine coding 19:19 — apakah timeout admission 5s terlalu agresif, dan apakah perlu ADR.

**Files:**
- Read: `plugins/memory/hermes-dual-memory/admission.py`
- Read: `plugins/memory/hermes-dual-memory/consolidation.py` (timeout usage)
- Data: `memory_index` coding (19 trusted vs 19 quarantined)

**Steps:**
1. Query DB coding: breakdown quarantined — berapa karena timeout vs konten.
2. Analisis: apakah timeout 5s menyebabkan false-quarantine massal.
3. Keputusan: naikkan timeout (ADR baru) ATAU biarkan (dokumentasikan alasan).
4. Jika naikkan → test reproduksi + ADR + baseline + snapshot + approval.

**Verification:** Keputusan tertulis di jurnal + (jika perubahan) test baru hijau.

---

### Task 5: Evaluasi micro-compaction herald (opsional, keputusan ADR)

**Objective:** Evaluasi `compression.micro_compact` (off by default) — apakah layak diaktifkan untuk meningkatkan recall konsolidasi.

**Steps:**
1. Baca `docs/micro-compaction.md` di hermes-agent source.
2. Analisis trade-off: per-turn cost vs prompt cache break vs recall gain.
3. Keputusan ADR: aktifkan / jangan aktifkan / evaluasi lanjutan.
4. Jika aktifkan → test + snapshot + approval.

**Verification:** ADR baru + (jika aktif) test hijau + jurnal.

---

### Task 6: Evaluasi context engine pluggable (opsional, keputusan ADR)

**Objective:** Evaluasi `context.engine` herald (default compressor) — apakah mengganti engine memberi manfaat untuk dual-memory.

**Steps:**
1. Baca `docs/context-engine.md` di hermes-agent source.
2. Analisis: engine alternatif (LCM) vs kebutuhan dual-memory.
3. Keputusan ADR: gunakan / tidak (default compressor cukup).
4. Dokumentasikan keputusan.

**Verification:** ADR baru + jurnal.

---

### Task 7: Tulis README root (portofolio-grade)

**Objective:** README publik yang memungkinkan instalasi ulang dari nol mengikuti README saja (kriteria keluar Fase 9).

**Files:**
- Create: `README.md` (root)

**Konten wajib:**
1. Apa itu hermes-dual-memory (1 paragraf + diagram alur System-1/System-2).
2. Fitur (bullet: hot capture, consolidation, quarantine, shadow index, supersede, answerability, decay, procedural skills).
3. Prasyarat (Python 3.11+, Hermes herald v0.20.1+, Mem0, Chroma).
4. Instalasi step-by-step (venv, install mem0ai, salin plugin, konfigurasi provider di config.yaml).
5. Konfigurasi (provider, model, timeout, .env).
6. Penggunaan (cara aktifkan, test, verifikasi).
7. Testing (perintah unittest + HERMES_SOURCE_ROOT).
8. Troubleshooting umum (404 model, konsolidasi tidak jalan, HOME remap).
9. Roadmap / status (beta selesai, Fase 9).
10. Lisensi.

**Verification:** README lengkap, tautan valid, tidak ada `[TBD]`/placeholder.

---

### Task 8: Uji instalasi ulang bersih (kriteria keluar Fase 9)

**Objective:** Buktikan kriteria keluar Fase 9: instalasi ulang dari nol di environment bersih **mengikuti README saja** berhasil.

**Steps:**
1. Buat venv bersih di `/tmp/fase9-clean`.
2. Ikuti README langkah demi langkah (tanpa pengetahuan tersembunyi).
3. Jalankan test suite di env bersih.
4. Verifikasi plugin termuat (smoke test: initialize + sync_turn + shutdown).
5. Catat setiap langkah yang "perlu ditebak" → perbaiki README.
6. Iterasi sampai sukses tanpa asumsi.

**Verification:** `python -m unittest discover -s tests` PASS di env bersih; smoke test OK; README tidak perlu tebakan.

---

### Task 9: Demo/rekaman alur kerja (opsional portofolio)

**Objective:** Dokumentasi visual/cara penggunaan untuk portofolio.

**Steps:**
1. Buat skenario demo singkat (3-5 langkah): start Hermes, percakapan, /new, cek konsolidasi, cek retrieval.
2. Rekam output (teks) atau screenshot alur.
3. Simpan ke `docs/demo/` + tautan di README.

**Verification:** File demo ada, bisa diikuti.

---

### Task 10: Cleanup dokumen fase

**Objective:** Rapikan docs — hapus duplikat, tandai status per fase, pastikan konsisten.

**Steps:**
1. Audit `docs/phases/` — status tiap fase.
2. Tandai fase 0-8 = Selesai, fase 9 = Aktif.
3. Hapus dokumen basi/duplikat (jika ada) setelah backup.
4. Update CHANGELOG dengan ringkasan Fase 9.

**Verification:** `ls docs/phases/` bersih; CHANGELOG ter-update.

---

### Task 11: Update CHANGELOG + commit final

**Objective:** CHANGELOG mencatat seluruh perubahan Fase 9; commit final + push.

**Steps:**
1. Append CHANGELOG: Fase 9 hardening + dokumentasi.
2. Commit semua perubahan Fase 9.
3. Push branch `fase-9/portofolio` (approval Farid).
4. Buka PR ke `master` (approval Farid).

**Verification:** CHANGELOG lengkap; branch pushed; PR open (jika disetujui).

---

## Risiko & Trade-off

| Risiko | Mitigasi |
|---|---|
| README instalasi gagal di env bersih | Task 8 iterasi sampai sukses; catat semua asumsi |
| Micro-compaction break prompt cache | Evaluasi dulu (Task 5), jangan aktifkan tanpa ADR |
| Quarantine threshold naik → false negative naik | Uji korpus known-bad/known-good, ambang disepakati |
| Scope membesar (gold-plating) | Prinsip YAGNI — kerjakan yang diperlukan, tanya sebelum tambah |
| Push/PR tanpa approval | Semua operasi remote butuh approval Farid |

## Open Questions

1. **Branch Fase 9**: `fase-9/portofolio` langsung dari HEAD beta, atau tetap di `beta/0.1-*` sampai semua pekerjaan selesai? (rekomendasi: branch baru)
2. **Micro-compaction & context engine**: evaluasi saja, atau langsung implementasi jika bermanfaat? (rekomendasi: evaluasi + ADR, tanpa implementasi besar kecuali bukti kuat)
3. **Demo**: butuh rekaman visual (screenshot/video) atau teks cukup? (rekomendasi: teks dulu)
4. **Lisensi**: repo publik memakai lisensi apa? (rekomendasi: MIT, konfirmasi Farid)
5. **README bahasa**: Indonesia, Inggris, atau dua-duanya? (rekomendasi: Inggris untuk publik, Indonesia untuk internal)

## Validasi Akhir (Exit Criteria Fase 9)

- [ ] Instalasi ulang dari nol di env bersih mengikuti README saja → berhasil
- [ ] README root lengkap, tidak ada placeholder
- [ ] Semua ADR baru (jika ada) diterima
- [ ] Test suite hijau (87+)
- [ ] Baseline tidak regresi
- [ ] CHANGELOG lengkap
- [ ] Branch `fase-9/portofolio` pushed (dengan approval)
