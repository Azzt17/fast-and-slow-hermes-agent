# AGENTS.md — hermes-dual-memory

Instruksi tetap untuk Codex CLI di project ini. Baca file ini penuh sebelum mengerjakan tugas apa pun.

## Apa Proyek Ini
Memory provider plugin untuk Hermes Agent (Nous Research) — mekanisme memori dual-process (System 1/System 2, terinspirasi Kahneman) yang wrap `mem0ai` sebagai mesin storage/retrieval, ditambah shadow index SQLite untuk bi-temporal fact tracking, retrievability decay, dan quarantine keamanan.

Spesifikasi lengkap ada di `docs/architecture/final-architecture.md` — **baca file itu untuk detail sebelum implementasi apa pun**, jangan mengarang skema/alur sendiri. File ini (AGENTS.md) hanya ringkasan aturan main.

## Batas Lingkup — WAJIB DIPATUHI
**Jangan bangun ulang** apa pun yang sudah disediakan Hermes Agent: gateway multi-platform, terminal backend, CLI/TUI, skill engine dasar, Curator, Core Memory (`MEMORY.md`/`USER.md`), prompt caching, security scanning dasar. Kalau ragu apakah sesuatu sudah ada di Hermes, cek dokumentasi resmi Hermes dulu, jangan asumsikan perlu dibangun sendiri.

**Yang memang dibangun di repo ini**: hot tier (SQLite `hot_sessions`), trigger konsolidasi, laporan konsolidasi terstruktur, shadow index (`memory_index`), quarantine pipeline, lapisan keamanan tambahan, integrasi procedural memory ke Skills system.

## Prinsip Arsitektur (Non-Negotiable)
1. **Reuse di atas rebuild** — cek dulu apakah Hermes/Mem0 sudah punya sebelum menulis kode baru
2. **Trigger deterministik** — kapan konsolidasi jalan ditentukan kode/hook (`on_session_end`, `on_pre_compress`), bukan keputusan model di tengah jalan
3. **Quarantine sebelum trust** — hasil konsolidasi baru berstatus `candidate`, tidak langsung `trusted`
4. **Supersede, jangan hapus** — kontradiksi fakta ditangani lewat `t_invalid`, baris lama tidak pernah di-DELETE
5. **Sistem 2 kita yang mengekstrak fakta** — matikan/jangan andalkan mesin ekstraksi otomatis bawaan `mem0ai`
6. **Satu provider aktif** — jangan aktifkan provider `mem0` resmi Hermes bersamaan dengan plugin ini

## Alur Kerja per Fase
Roadmap lengkap ada di `docs/architecture/final-architecture.md` §8. Aturan gerbang: **jangan mulai fase berikutnya sebelum kriteria keluar fase saat ini PASS dan `docs/phases/phase-N-*.md` diisi lengkap**. Kalau diminta mengerjakan "fase berikutnya" tapi dokumen fase sebelumnya belum berstatus "Selesai", tanya dulu ke Farid sebelum lanjut.

## Mekanisme Dokumentasi (Yang Harus Kamu Lakukan Otomatis)
Untuk setiap unit kerja (fitur, keputusan desain, penyelesaian fase):
- **Keputusan arsitektural baru** → buat file ADR baru di `docs/decisions/000N-judul.md` pakai template di `docs/decisions/0000-template.md`
- **Menyelesaikan/memulai fase** → update `docs/phases/phase-N-nama.md` (status, checklist, hasil uji) — jangan tandai "Selesai" kecuali kriteria keluar benar-benar terverifikasi
- **Tiap merge fase** → tambah entri di `CHANGELOG.md`
- **Nama branch**: `fase/N-nama-singkat`, merge ke `main` hanya setelah dokumen fase lengkap

## Alur Git — WAJIB Approval Manusia
Kamu boleh menyiapkan dan menulis dokumentasi/kode sepenuhnya, TAPI:
1. **Boleh** tanpa tanya dulu: `git add`, `git commit` lokal (tidak menyentuh GitHub), menulis/mengedit file dokumentasi di `docs/`
2. **WAJIB tampilkan ringkasan diff/commit dan tunggu approval eksplisit dari Farid** sebelum: `git push`, membuat/mengubah pull request, atau operasi lain yang menyentuh repo GitHub jarak jauh
3. Approval dianggap sah kalau Farid menulis sesuatu yang jelas seperti "approved", "lanjut push", atau "oke push" — diam/tidak merespons BUKAN persetujuan
4. Jangan pernah squash/force-push riwayat yang sudah ada di GitHub tanpa diminta eksplisit
5. Pesan commit selalu merujuk fase/ADR terkait, mis. `[fase-1] implementasi sync_turn ke hot_sessions (ref ADR-0002)`

## Yang Perlu Ditanyakan, Bukan Diasumsikan
- Kalau spesifikasi di `final-architecture.md` ambigu atau tampak kontradiktif dengan kondisi kode saat ini → tanya, jangan menebak
- Kalau sebuah keputusan berubah skema data yang sudah ada di fase sebelumnya → wajib buat ADR baru dulu sebelum implementasi, bukan sesudahnya

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## Beta Dogfooding v0.1.0-beta.1 — WAJIB Lintas Session

Sebelum pekerjaan beta, hardening, atau rilis apa pun, baca berurutan:

1. `docs/beta/v0.1.0-beta.1/CURRENT.md`
2. `docs/beta/v0.1.0-beta.1/README.md`
3. 20 entri terakhir `docs/beta/v0.1.0-beta.1/journal.md`

Checkpoint rollback code adalah tag `v0.1.0-beta.1` pada commit `18c770b`.
Rollback data harus memakai snapshot runtime yang berpasangan; jangan rollback
code saja jika schema/vector/shadow state mungkin berubah.

Selama status beta belum `Selesai`:

- jangan mulai Fase 9;
- semua observasi/perubahan config/code/data ditulis append-only ke jurnal;
- update `CURRENT.md` setelah status, config, open item, rollback point, atau
  severity berubah;
- branch perubahan memakai prefix `beta/0.1-`;
- policy/schema/migration baru wajib ADR + test reproduksi + baseline comparison;
- S0/S1 menghentikan beta dan memicu rollback code+data;
- jangan commit conversation mentah, credential, system prompt, atau isi memory
  sensitif ke repo—hanya ringkasan tersanitasi.
