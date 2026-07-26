# Dokumen Arsitektur Final
## Dual-Process Memory Provider untuk Hermes Agent
### Acuan Utama Pembangunan — dari Fase 0 sampai Rilis

**Nama kerja proyek**: `hermes-dual-memory` *(usulan — sesuaikan dengan konvensi penamaan repo-mu, mis. gaya `ai-agent-control-plane`/`ai-assisted-devsecops-learning-system`)*
**Versi dokumen**: 1.0 — konsolidasi final dari 4 dokumen riset sebelumnya
**Status**: Siap jadi acuan implementasi

---

## 0. Cara Membaca Dokumen Ini

Dokumen ini adalah **hasil akhir** dari proses riset & desain panjang (blueprint checkpoint → riset best-case → riset fitur bawaan Hermes → deep dive Jalur A). Beberapa keputusan di sini **merevisi** rekomendasi dokumen-dokumen sebelumnya berdasarkan temuan yang baru diketahui belakangan — revisi ini ditandai eksplisit di §10 (Catatan Penting) supaya tidak membingungkan kalau kamu membaca ulang dokumen-dokumen lama.

Struktur dokumen: §1-2 visi & lingkup, §3-6 arsitektur teknis, §7 mekanisme dokumentasi repo, §8 roadmap fase-demi-fase (bagian paling penting untuk eksekusi harian), §9 evaluasi, §10 catatan penting, §11 referensi.

---

## 1. Visi & Prinsip (Ringkasan)

Landasan konseptual: teori **System 1/System 2** Daniel Kahneman (*Thinking, Fast and Slow*, 2011) — System 1 cepat-otomatis-minim usaha, System 2 lambat-disengaja-penuh usaha, dan tugas yang sering diulang berpindah dari System 2 ke System 1 (automatization) — prinsip inilah yang mendasari seluruh logika promosi/demosi di §5.

Prinsip desain yang dipegang teguh:
1. **Reuse di atas rebuild** — setiap komponen yang sudah battle-tested (di Hermes atau Mem0) dipakai apa adanya; kita hanya membangun yang benar-benar jadi ciri khas rancangan ini
2. **Trigger deterministik** — kapan konsolidasi jalan ditentukan kode/hook, bukan keputusan LLM
3. **Quarantine sebelum trust** — hasil konsolidasi tidak langsung jadi fakta permanen
4. **Supersede, jangan hapus** — kontradiksi fakta ditangani lewat invalidasi bertingkat waktu, bukan overwrite senyap
5. **Setiap fase punya gerbang uji** — tidak lanjut fase berikutnya sebelum kriteria keluar (exit criteria) terpenuhi DAN terdokumentasi di repo

---

## 2. Lingkup Proyek: Apa yang Kita Bangun vs Apa yang Kita Warisi Gratis

Ini pembatas paling penting sejak Jalur A dipilih. Salah paham di sini akan membuang effort besar.

### Di Luar Lingkup (sudah disediakan Hermes Agent, JANGAN dibangun ulang)
| Komponen | Disediakan Oleh |
|---|---|
| Gateway multi-platform (WhatsApp, Telegram, Slack, dst.) | Hermes core |
| Terminal backend (Docker/SSH/Singularity/Modal/Daytona) | Hermes core |
| CLI/TUI, slash command | Hermes core |
| Skill engine dasar (SKILL.md, loading, eksekusi) | Hermes core |
| Curator (decay/pruning skill) | Hermes core (kita re-use pola-nya untuk memori, tidak perlu re-implement) |
| Core Memory dasar (MEMORY.md/USER.md, ~1.300 token, frozen snapshot) | Hermes core — **kita TIDAK membangun tier Core baru** (revisi dari dokumen riset sebelumnya, lihat §10.1) |
| Prompt caching lintas sesi | Hermes core |
| Security scanning dasar (context file, threat pattern) | Hermes core — kita perkuat, bukan mengganti |

### Di Dalam Lingkup (yang benar-benar kita bangun)
| Komponen | Alasan Perlu Dibangun Sendiri |
|---|---|
| Hot tier (SQLite raw session log) | Skema custom (consolidated flag, dst.) tidak disediakan Hermes |
| Trigger hybrid → pemanggilan Sistem 2 | Logika kapan & bagaimana konsolidasi jalan adalah ciri khas rancangan |
| Laporan konsolidasi terstruktur (§4.3) | Format spesifik (importance_score, entities/relations, dst.) bukan bawaan Mem0 |
| Shadow index (bi-temporal, tiering, retrievability decay) | Tidak ada padanan langsung di Mem0 maupun Hermes |
| Quarantine pipeline | Belum ada bawaan untuk memory provider (Curator sudah punya pola serupa untuk skill, kita adaptasi) |
| Lapisan keamanan tambahan (semantic admission check) | Menutup gap yang diketahui belum ditambal di scanning bawaan Hermes |
| Integrasi procedural memory ke Skills system | Logika "kapan sebuah essence layak jadi skill" adalah keputusan kita |

---

## 3. Arsitektur Data Final

### 3.1 Dua Sistem Penyimpanan, Peran Terpisah

```
┌─────────────────────────────┐     ┌──────────────────────────────┐
│  SQLite (punya kita sendiri)  │     │  Mem0 (mem0ai, mode OSS)       │
│  file: memory.db              │     │  backend vector: Chroma        │
│                                │     │  (fallback jika LanceDB        │
│  - hot_sessions (raw log)      │     │   tidak didukung native)       │
│  - memory_index (shadow meta)  │◄───►│                                │
│                                │     │  - Konten essence (teks)       │
│  Kita PEGANG KENDALI di sini: │     │  - Vector + BM25 + entity       │
│  tier, bi-temporal, decay,     │     │    fusion search (bawaan)      │
│  importance, access tracking,  │     │  - mem0_id sebagai kunci        │
│  quarantine status             │     │    penghubung ke memory_index  │
└─────────────────────────────┘     └──────────────────────────────┘
```

**Kenapa dua sistem, bukan satu**: Mem0 unggul di retrieval (vector+BM25+entity fusion, sudah teruji) tapi tidak punya konsep bi-temporal, retrievability decay, atau quarantine. SQLite `memory_index` adalah **lapisan kendali** kita di atas Mem0 — Mem0 jadi "gudang & mesin pencari", `memory_index` jadi "buku besar" yang menentukan apa yang boleh dicari, kapan sesuatu kedaluwarsa, dan seberapa penting sesuatu.

### 3.2 Skema `hot_sessions` (SQLite)
```sql
CREATE TABLE hot_sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL,
    timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,
    role          TEXT,              -- 'user' | 'assistant'
    content       TEXT NOT NULL,
    token_count   INTEGER,
    consolidated  BOOLEAN DEFAULT 0
);
CREATE INDEX idx_hot_session ON hot_sessions(session_id, consolidated);
```
Diisi oleh hook `sync_turn()`. Baris `consolidated=1` disimpan sebagai buffer verifikasi ~7 hari sebelum dihapus job cleanup terpisah.

### 3.3 Skema `memory_index` (SQLite — Shadow Index)
```sql
CREATE TABLE memory_index (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    mem0_id           TEXT NOT NULL UNIQUE,   -- ID dari mem0.add()
    session_id        TEXT NOT NULL,          -- provenance, wajib diisi
    memory_type       TEXT,                   -- 'episodic' | 'semantic' | 'procedural'
    tier              TEXT DEFAULT 'warm',    -- 'warm' | 'cold'
    status            TEXT DEFAULT 'candidate', -- 'candidate' | 'trusted' | 'quarantined'
    t_valid           DATETIME,               -- kapan fakta mulai berlaku
    t_invalid         DATETIME,               -- kapan fakta berhenti berlaku (NULL = masih berlaku)
    t_created         DATETIME DEFAULT CURRENT_TIMESTAMP,
    importance_score  INTEGER DEFAULT 0,      -- 0-10, dari laporan konsolidasi
    stability         REAL DEFAULT 1.0,       -- naik tiap kali diakses (basis retrievability)
    access_count      INTEGER DEFAULT 0,
    last_accessed     DATETIME,
    superseded_by     TEXT,                   -- mem0_id fakta yang menggantikan (jika ada)
    flagged_reason     TEXT                    -- alasan quarantine, kalau ada
);
CREATE INDEX idx_memory_status ON memory_index(status, tier);
```

**Catatan desain penting**: field `memory_type='procedural'` di tabel ini dipakai **hanya sebagai penanda sementara** sebelum essence itu benar-benar dikonversi jadi file `SKILL.md` (§7 Fase 7) — begitu jadi skill, baris ini bisa ditandai `superseded_by` merujuk ke path skill, bukan mem0_id lain.

### 3.4 Core Memory — Tidak Dibangun Ulang
Sesuai §2, kita **tidak** membuat tier Core baru. `MEMORY.md`/`USER.md` bawaan Hermes tetap berfungsi sebagai lapisan itu, dikelola proses agent-curated bawaan Hermes sendiri. Peran plugin kita di sini pasif: memastikan hot tier & warm tier yang rapi memberi "bahan baku" yang baik saat Hermes melakukan refleksi periodiknya sendiri. Kalau `system_prompt_block()` dipakai, isinya dibatasi ringkas (mis. status jumlah entri warm/cold) — bukan duplikasi Core Memory.

### 3.5 Procedural Memory — Lewat Skills System, Bukan Mem0
Saat laporan konsolidasi (§4.3) berisi `new_skills` yang tervalidasi, plugin **tidak** menyimpannya sebagai teks bebas di Mem0. Sebagai gantinya, ia menulis/mengusulkan file `SKILL.md` sesuai format Hermes (kompatibel `agentskills.io`), supaya otomatis kebagian siklus hidup penuh (staleness detection, konsolidasi, arsip) dari Curator bawaan — tidak perlu kita bangun mekanisme lifecycle terpisah untuk procedural memory.

---

## 4. Alur Kerja End-to-End

### 4.1 Peta Hook Resmi Hermes → Komponen Kita
| Hook `MemoryProvider` | Komponen yang Menempel |
|---|---|
| `is_available()` | Cek Mem0/dependency siap (tanpa network call) |
| `initialize(session_id, **kwargs)` | Buka koneksi SQLite (`hermes_home`-scoped) + inisialisasi klien mem0ai |
| `sync_turn(user, assistant)` | Tulis ke `hot_sessions` — **wajib non-blocking**, jalankan di daemon thread |
| `on_session_end(messages)` | **Trigger idle** → panggil pipeline konsolidasi (§4.2) |
| `on_pre_compress(messages)` | **Trigger threshold token** → panggil pipeline konsolidasi (§4.2) |
| `prefetch(query)` | Jalur retrieval sinkron sebelum giliran (§4.4) |
| `queue_prefetch(query)` | Pre-warming kandidat retrieval di background |
| `get_tool_schemas()` / `handle_tool_call()` | Tool eksplisit kalau agent butuh cari/kelola memori secara manual |
| `shutdown()` | Tutup koneksi SQLite & mem0ai dengan bersih |

### 4.2 Pipeline Konsolidasi (Sistem 2)
```
1. Trigger (on_session_end ATAU on_pre_compress)
2. Ambil baris hot_sessions WHERE consolidated=0 AND session_id=X
3. Panggil API model dengan prompt konsolidasi (§4.3) → dapat JSON
4. VALIDASI:
   - JSON well-formed? → jika tidak, retry 1x, lalu fallback needs_review
   - Admission check (§6) → tandai flagged_reason jika mencurigakan
5. STATUS AWAL: "candidate"
6. UNTUK entitas bertipe semantic:
   - Cek memory_index untuk fakta lama yang bertentangan (query by entity)
   - JIKA kontradiksi: set t_invalid lama = sekarang, JANGAN hapus
7. ROUTING:
   - episodic/semantic → mem0.add(essence, metadata={...}) → catat mem0_id di memory_index
   - procedural (tervalidasi) → tulis/usulkan SKILL.md
8. STATUS AKHIR: "trusted" (lolos validasi) atau "quarantined" (gagal/mencurigakan)
9. Update hot_sessions SET consolidated=1
```

### 4.3 Format Laporan Konsolidasi (Prompt Sistem 2)
```
SYSTEM:
Kamu adalah proses konsolidasi memori. Distilasi log mentah jadi entri
terstruktur. Jangan tambahkan interpretasi yang tidak didukung teks.
Field yang tidak relevan boleh dikosongkan.

USER:
Log mentah sesi [session_id], [timestamp_awal]–[timestamp_akhir]:
[isi hot_sessions]

Hasilkan JSON:
{
  "summary": "...",              // maks ~150 kata
  "new_skills": [{"title": "...", "detail": "..."}],
  "anomalies": ["..."],
  "entities": [{"id": "...", "type": "...", "label": "..."}],
  "relations": [{"source": "...", "target": "...", "relation": "..."}],
  "memory_type": "episodic|semantic",
  "importance_score": 0
}
```
**Penting**: Mem0 punya mesin ekstraksi otomatisnya sendiri — **JANGAN** biarkan itu aktif memproses raw log secara paralel. Essence yang masuk ke `mem0.add()` adalah hasil olahan prompt di atas, bukan raw conversation yang dibiarkan diekstrak Mem0 sendiri. Kalau library `mem0ai` mengaktifkan LLM-extraction secara default, matikan opsi itu saat inisialisasi klien.

### 4.4 Alur Retrieval Saat Percakapan Aktif
```
prefetch(query)
   │
   ▼
Cek relevansi ke hot_sessions sesi aktif dulu (murah, tanpa Mem0)
   │ cukup? → return, selesai
   │ tidak cukup
   ▼
mem0.search(query) → daftar hasil + mem0_id
   │
   ▼
JOIN ke memory_index WHERE status='trusted' AND (t_invalid IS NULL)
   │  (buang hasil yang sudah di-supersede atau masih quarantined)
   ▼
Urutkan: skor relevansi → importance_score → recency
   │
   ▼
Update memory_index: access_count+1, last_accessed=now, stability naik
   │
   ▼
Bungkus hasil dengan delimiter data-vs-instruksi (§6.2) → suntik ke context
```

### 4.5 Decay, Promosi/Demosi (Dipicu Opportunis, Bukan Cron Terpisah)
Hermes tidak menyediakan scheduler bawaan untuk plugin, jadi job decay **tidak** dijalankan sebagai proses cron mandiri — cukup dipicu secara opportunis di `on_session_end`/`initialize` (saat sesi baru mulai/berakhir), dengan pengecekan murah "sudah berapa lama sejak siklus decay terakhir jalan":
```
JIKA (waktu sekarang - terakhir_decay_run) > 24 jam:
    UNTUK tiap baris memory_index WHERE status='trusted':
        hitung retrievability berdasarkan (last_accessed, stability)
        JIKA retrievability < ambang DAN memory_type != 'semantic-permanent':
            tier = 'cold'
    Jalankan cold compaction (cluster entri cold yang mirip, gabung via Sistem 2)
    catat waktu_decay_run = sekarang
```

---

## 5. Retrievability & Decay (Formula Kerja)

```
stability(S)       : naik tiap kali entri diakses; nilai awal = importance_score/2 (minimal 0.5)
retrievability(R,t) : meluruh terhadap waktu sejak last_accessed, laju peluruhan
                      berbanding terbalik dengan S (S tinggi → R turun lebih lambat)

Aturan:
  R < 0.3           → kandidat demosi ke cold
  R < 0.3 DAN akses ulang ≥2x dalam 7 hari setelah demosi → promosi balik ke warm
  memory_type='semantic' dengan t_invalid=NULL → DIKECUALIKAN dari decay
    (fakta permanen di-supersede, bukan diluruhkan)
```
Implementasi presisi formula (mis. adaptasi FSRS penuh vs versi sederhana) adalah keputusan level-kode, didetailkan saat Fase 5 (§8).

---

## 6. Lapisan Keamanan

### 6.1 Write-Time Admission Check
Dua lapis, dijalankan sebelum status `candidate` → `trusted`:
1. **Pattern-based** (cepat) — adaptasi pola dari `tools/threat_patterns.py` Hermes (ignore-previous-instructions, eksfiltrasi kredensial, dst.)
2. **Semantic layer tambahan** (menutup Gap 1 yang diketahui di Hermes — bypass lewat framing halus seperti "kamu berkewajiban untuk...") — panggilan model kecil terpisah yang menilai "apakah teks ini menyerupai instruksi tersembunyi", bukan cuma cocokkan kata kunci

### 6.2 Retrieval-Time Filtering
Semua hasil dari `prefetch()`/`queue_prefetch()` dibungkus delimiter eksplisit sebelum disuntik:
```
<memori_lampau sumber="session:{session_id}" waktu="{timestamp}">
...isi essence...
</memori_lampau>
```
Instruksi sistem menyertai penjelasan bahwa blok ini adalah **data historis**, bukan perintah baru.

### 6.3 Load-Time Re-Scan (Menutup Gap yang Diketahui)
Berbeda dari pola Hermes bawaan (yang hanya scan saat *tulis*, bukan saat *baca* — celah nyata yang pernah dilaporkan), setiap entri yang keluar dari `memory_index` lewat retrieval **dicek ulang statusnya** (`status='trusted'`) sebelum disuntik — entri yang somehow berubah jadi `quarantined` setelah ditulis (mis. lewat audit manual) otomatis tidak akan lolos ke context.

---

## 7. Mekanisme Dokumentasi di Repo GitHub

### 7.1 Struktur Direktori
```
hermes-dual-memory/
├── README.md                      — overview, status fase saat ini (badge/tabel)
├── CHANGELOG.md                   — log perubahan per rilis/fase
├── docs/
│   ├── architecture/
│   │   ├── 00-vision.md           — §1 dokumen ini
│   │   ├── 01-data-architecture.md — §3
│   │   ├── 02-workflow.md         — §4
│   │   └── 03-security.md         — §6
│   ├── decisions/                 — Architecture Decision Records (ADR)
│   │   ├── 0000-template.md
│   │   ├── 0001-jalur-a-plugin-vs-standalone.md
│   │   ├── 0002-wrap-mem0-vs-build-custom.md
│   │   ├── 0003-no-separate-core-memory-tier.md
│   │   └── ...
│   ├── phases/
│   │   ├── phase-0-fondasi.md
│   │   ├── phase-1-hot-tier.md
│   │   ├── phase-2-konsolidasi.md
│   │   └── ...                    — satu file per fase §8
│   └── testing/
│       ├── test-plan.md           — kriteria uji tiap fase (rujuk §8)
│       └── results/
│           ├── phase-0-results.md
│           └── ...
├── plugins/memory/hermes-dual-memory/
│   ├── __init__.py
│   ├── plugin.yaml
│   ├── cli.py
│   └── README.md
├── tests/
└── src/ (atau langsung di dalam plugins/... sesuai konvensi Hermes)
```

### 7.2 Template ADR (`docs/decisions/0000-template.md`)
```markdown
# ADR-XXXX: [Judul Keputusan]

**Status**: Diusulkan | Diterima | Digantikan oleh ADR-YYYY
**Tanggal**: YYYY-MM-DD

## Konteks
Apa masalah/pertanyaan yang mendorong keputusan ini?

## Keputusan
Apa yang diputuskan?

## Alternatif yang Dipertimbangkan
Opsi lain apa saja, dan kenapa tidak dipilih?

## Konsekuensi
Apa dampaknya — positif dan trade-off yang diterima?
```
ADR pertama (0001-0003) sudah bisa langsung diisi dari riwayat keputusan di dokumen ini (§10.6 berisi ringkasan siap-tempel).

### 7.3 Template Dokumen Fase (`docs/phases/phase-N-nama.md`)
```markdown
# Fase N: [Nama Fase]

**Status**: Belum Mulai | Berjalan | Selesai
**Tanggal Selesai**: YYYY-MM-DD

## Goal
[dari §8]

## Yang Dibangun
[checklist implementasi]

## Failure Mode yang Diwaspadai
[dari §8]

## Kriteria Keluar (Exit Criteria)
[dari §8 — harus PASS sebelum lanjut fase berikutnya]

## Hasil Uji
[link ke docs/testing/results/phase-N-results.md, atau isi ringkas di sini]

## Catatan/Pembelajaran
[apa yang berbeda dari rencana, kenapa]
```

### 7.4 Aturan Commit & Branch (Ringan, Sesuai Skala Personal)
- Satu branch per fase (`fase/0-fondasi`, `fase/1-hot-tier`, dst.), merge ke `main` **hanya** setelah exit criteria fase itu tercapai dan dokumen fase diisi lengkap
- Commit terakhir sebelum merge selalu menyertakan update `docs/phases/phase-N-*.md` dari status "Berjalan" → "Selesai"
- `CHANGELOG.md` di-update tiap merge fase, bukan tiap commit kecil

**Prinsip yang mendasari mekanisme ini**: ini adalah versi ringan dari "post-hoc forensic detection" yang kita bahas di §6 riset sebelumnya — riwayat keputusan & pengujian yang bisa ditelusuri balik, relevan juga sebagai portofolio kerja DevSecOps-mu.

---

## 8. Roadmap Fase — Goal, Implementasi, Failure Mode, Kriteria Keluar

> **Aturan gerbang**: tidak pindah ke fase berikutnya sebelum kriteria keluar fase saat ini **PASS** dan dokumen fase (§7.3) terisi lengkap di repo.

### Fase 0 — Fondasi Repo & Lingkungan
- **Goal**: Repo terstruktur dengan mekanisme dokumentasi (§7) siap pakai; Hermes + plugin scaffold + mem0ai terpasang
- **Dibangun**: struktur direktori §7.1, ADR 0001-0003 terisi, `plugins/memory/hermes-dual-memory/` skeleton (class kosong, `register()` terdaftar)
- **Failure mode**: salah taruh path storage (tidak pakai `hermes_home` kwarg) — akan ketahuan telat kalau baru dicek di fase belakangan
- **Kriteria keluar**: `hermes plugins list` menampilkan provider kita; skrip terpisah (di luar Hermes) berhasil `mem0.add()` lalu `mem0.search()` round-trip ke backend lokal (Chroma) — verifikasi dependency dasar sebelum diintegrasikan

### Fase 1 — Hot Tier & Sinkronisasi Dasar (Sistem 1 Murni)
- **Goal**: `sync_turn()` menulis ke `hot_sessions`; lifecycle wajib (`is_available`, `initialize`, `get_config_schema`) lengkap
- **Dibangun**: skema §3.2, threading contract (daemon thread untuk write)
- **Failure mode**: `sync_turn()` blocking (lupa daemon thread) — akan terasa sebagai lag di CLI
- **Kriteria keluar**: percakapan CLI normal berjalan, `hot_sessions` terisi sesuai giliran; restart proses Hermes, data tetap ada; ukur latency tambahan per giliran (target: tidak terasa signifikan di CLI)

### Fase 2 — Trigger & Konsolidasi Sistem 2 (Minimal, Belum Ada Tiering)
- **Goal**: `on_session_end`/`on_pre_compress` memicu pipeline §4.2 versi minimal — hasil langsung `trusted` (belum ada quarantine sungguhan)
- **Dibangun**: prompt §4.3, parsing JSON, panggilan `mem0.add()` dengan metadata dasar
- **Failure mode**: mengandalkan ekstraksi otomatis Mem0 secara tidak sengaja (lupa mematikannya) — essence yang tersimpan tidak sesuai skema yang dirancang
- **Kriteria keluar**: sesi panjang berakhir → essence baru muncul lewat `mem0.get_all()`, field sesuai skema §4.3, `hot_sessions.consolidated` berubah jadi 1

### Fase 3 — Retrieval & Injeksi Konteks
- **Goal**: `prefetch()`/`queue_prefetch()` memanggil `mem0.search()`, hasil dibungkus delimiter (§6.2), disuntik ke context
- **Dibangun**: alur §4.4 (tanpa join `memory_index` dulu — itu Fase 4)
- **Failure mode**: delimiter lupa dipasang — hasil retrieval bisa "diperlakukan" sebagai instruksi baru oleh model
- **Kriteria keluar**: tes recall manual ala kasus Honcho di riset sebelumnya — nyatakan fakta spesifik di satu sesi, mulai sesi baru, tanya ulang, verifikasi agent menjawab benar tanpa diberi tahu ulang

### Fase 4 — Shadow Index, Bi-Temporal, Kontradiksi
- **Goal**: `memory_index` aktif, tiap `mem0.add()` dapat baris shadow; cek kontradiksi sebelum tulis fakta semantic baru
- **Dibangun**: skema §3.3, langkah 6 di pipeline §4.2
- **Failure mode**: kontradiksi terdeteksi tapi fakta lama malah dihapus (bukan di-invalidate) — melanggar prinsip "supersede, jangan hapus" di §1
- **Kriteria keluar**: skenario terkontrol — nyatakan fakta A, lalu fakta B yang bertentangan di sesi terpisah; retrieval mengembalikan B sebagai valid; baris A masih ada di `memory_index` dengan `t_invalid` terisi, bisa ditelusuri lewat query historis

### Fase 5 — Decay, Promosi/Demosi, Cold Compaction
- **Goal**: retrievability (§5) dihitung opportunis (§4.5); entri redup didemosi; cold compaction jalan
- **Dibangun**: formula §5, logika opportunis §4.5, pemanggilan Sistem 2 untuk meringkas cluster cold
- **Failure mode**: fakta `semantic-permanent` ikut terdemosi karena lupa pengecualian di §5
- **Kriteria keluar**: skrip simulasi memanipulasi `last_accessed`/`access_count` di `memory_index`, jalankan fungsi decay, verifikasi entri berpindah tier sesuai aturan yang didefinisikan; verifikasi entri semantic-permanent TIDAK ikut terdemosi

### Fase 6 — Lapisan Keamanan
- **Goal**: admission check dua lapis (§6.1) aktif; status `quarantined` benar-benar berfungsi (bukan cuma field kosong)
- **Dibangun**: integrasi pola `threat_patterns`-style + lapisan semantic tambahan, load-time re-scan (§6.3)
- **Failure mode**: false positive tinggi (konten legit soal topik keamanan ikut ke-flag) — perlu tuning ambang
- **Kriteria keluar**: jalankan korpus uji berisi contoh known-bad (upaya injeksi) dan known-good (percakapan wajar termasuk yang membahas topik keamanan), ukur catch rate & false positive rate, tetapkan ambang minimum yang disepakati sebelum lanjut

### Fase 7 — Procedural Memory via Skills System
- **Goal**: `new_skills` tervalidasi dari laporan konsolidasi memicu penulisan/pengusulan `SKILL.md`, bukan disimpan sebagai prosa di Mem0
- **Dibangun**: konverter essence→SKILL.md, integrasi dengan siklus hidup Curator bawaan (§3.5)
- **Failure mode**: skill yang dihasilkan terlalu granular/tumpang tindih (masalah yang sama seperti insiden Curator asli, §5 riset fitur bawaan) — pertimbangkan dry-run + review sebelum skill benar-benar aktif
- **Kriteria keluar**: skenario tugas kompleks (≥5 pemanggilan tool) selesai, skill baru muncul di `~/.hermes/skills/` dengan format sesuai standar `agentskills.io`, Curator bisa mendeteksinya di siklus berikutnya tanpa error

### Fase 8 — Evaluasi & Observability
- **Goal**: mini-benchmark personal (recall, precision, latency p50/p95, token efficiency) jalan sebagai regression suite
- **Dibangun**: set pertanyaan uji kategori ala LongMemEval (single-session recall, multi-session aggregation, knowledge update, temporal reasoning, abstention)
- **Failure mode**: benchmark terlalu kecil/bias ke skenario yang "pasti berhasil" — usahakan sertakan kasus yang memang seharusnya gagal (abstention)
- **Kriteria keluar**: baseline score tercatat & di-commit ke `docs/testing/`; jadi kontrak — perubahan kode berikutnya tidak boleh menurunkan skor tanpa alasan terdokumentasi di ADR baru

### Fase 9 — Hardening & Rilis Portofolio
- **Goal**: dokumentasi lengkap, README siap publik, standar setara "PORTFOLIO-GRADE"
- **Dibangun**: README final, demo/rekaman alur kerja, cleanup dokumen fase
- **Failure mode**: instruksi instalasi di README mengandalkan pengetahuan tersembunyi (state lokal yang lupa didokumentasikan)
- **Kriteria keluar**: instalasi ulang dari nol di environment bersih **mengikuti README saja** berhasil jalan — kalau ada langkah yang perlu ditebak, README belum selesai

---

## 9. Evaluasi & Observability (Detail Fase 8)

### Kategori Uji
| Kategori | Contoh |
|---|---|
| Single-session recall | "Apa yang saya bilang soal X barusan?" |
| Multi-session aggregation | "Semua keputusan soal proyek Y sebulan terakhir?" |
| Knowledge update | "Apa keputusan TERBARU soal Z?" (uji §4.2 langkah 6) |
| Temporal reasoning | "Apa yang saya putuskan SEBELUM ganti ke Chroma?" |
| Abstention | Pertanyaan yang jawabannya memang tidak ada — sistem harus jujur, bukan mengarang |

### Metrik
```
Memory Recall    = fakta benar ditemukan / total fakta seharusnya ada
Memory Precision = hasil relevan di top-k / k
Latency          = p50 & p95, dari query sampai hasil retrieval siap
Token Efficiency = total token yang disuntik ke context per query
```

---

## 10. Catatan Penting yang Harus Dipahami

### 10.1 Revisi dari Dokumen Riset Sebelumnya: Tidak Ada Tier Core Baru
Dokumen "best-case-architecture" sebelumnya mengusulkan Core Memory sebagai tier baru terinspirasi MemGPT — itu diusulkan **sebelum** kita tahu Hermes sudah punya `MEMORY.md`/`USER.md` bawaan yang persis fungsinya. Rancangan final ini **tidak** membangun tier itu lagi (§3.4) — kalau kamu masih menyimpan/membaca ulang dokumen lama, bagian itu sudah tidak berlaku.

### 10.2 Kita BUKAN Provider "mem0" Resmi Hermes
Hermes sudah punya provider resmi bernama `mem0` (salah satu dari 8 provider bawaan). Plugin kita **bukan itu** — kita membangun provider baru dengan nama sendiri (mis. `hermes-dual-memory`) yang secara internal memakai library `mem0ai` sebagai dependency. Jangan bingung mengaktifkan provider `mem0` bawaan Hermes secara bersamaan — aturan "satu provider aktif" (§1 riset Jalur A) akan menolaknya.

### 10.3 Threading Contract Wajib
`sync_turn()` **harus** non-blocking (daemon thread). Ini bukan saran — kalau dilanggar, setiap giliran percakapan di CLI akan terasa lag menunggu proses konsolidasi/network call selesai.

### 10.4 Profile Isolation Wajib
Semua path storage pakai `hermes_home` kwarg dari `initialize()`, bukan `~/.hermes` hardcoded — supaya kalau kamu punya beberapa profil Hermes nanti, `hot_sessions`/`memory_index` masing-masing terisolasi otomatis.

### 10.5 Verifikasi Backend Vector Sejak Fase 0
LanceDB (keputusan awal di blueprint checkpoint) **belum terkonfirmasi** didukung native oleh `mem0ai`; Chroma lebih terdokumentasi untuk setup lokal. Ini sudah dijadikan bagian dari kriteria keluar Fase 0 — jangan asumsikan, verifikasi di awal supaya tidak perlu migrasi besar di fase belakangan.

### 10.6 Ringkasan Riwayat Keputusan (Siap Ditempel ke ADR)
| # | Keputusan | Alasan Singkat |
|---|---|---|
| 0001 | Jalur A: plugin, bukan agent berdiri sendiri | Reuse gateway/skills/curator Hermes yang sudah battle-tested |
| 0002 | Wrap Mem0 (mode OSS in-process), bukan bangun retrieval dari nol | Fusion vector+BM25+entity sudah teruji, hindari reinvent |
| 0003 | Tidak membangun tier Core Memory baru | Hermes sudah punya `MEMORY.md`/`USER.md` yang fungsinya sama |
| 0004 | Fully tied ke interface plugin Hermes, tidak prioritaskan portabilitas | Keputusan eksplisit — trade-off kecepatan build vs fleksibilitas masa depan |
| 0005 | Sistem 2 kita yang mengekstrak fakta, bukan mesin ekstraksi otomatis Mem0 | Menjaga format laporan konsolidasi (§4.3) tidak "ditelan" default behavior Mem0 |
| 0006 | Procedural memory lewat Skills system Hermes, bukan disimpan di Mem0 | Reuse siklus hidup (Curator) yang sudah ada, hindari bangun lifecycle terpisah |
| 0007 | Decay/tiering dipicu opportunis di session hook, bukan cron terpisah | Hermes tidak sediakan scheduler plugin native; opportunis lebih sederhana |

### 10.7 Pelajaran dari Insiden Nyata (Curator, Maret–April 2026)
Auto-mutation tanpa dry-run/approval pernah menyebabkan insiden nyata di Curator Hermes (arsip skill custom user tanpa konfirmasi). Prinsip yang sama berlaku ketat di quarantine pipeline kita (§4.2, §6) — status `quarantined` bukan formalitas, harus benar-benar mem-blokir entri dari retrieval sampai ditinjau.

### 10.8 Known Gap yang Belum Sepenuhnya Ditambal di Hermes Sendiri
Per titik riset ini (pertengahan 2026): scanner pola keyword Hermes bisa di-bypass framing halus (Gap 1), dan sempat ada celah scan-saat-tulis-saja tanpa re-scan saat load (Gap 3, sedang ditambal). Jangan asumsikan keamanan bawaan Hermes cukup untuk lapisan kita — §6.1-6.3 dirancang eksplisit untuk tidak bergantung penuh padanya.

---

## 11. Referensi Ringkas
Daftar lengkap ada di dokumen riset sebelumnya (`hermes-memory-best-case-architecture.md`, `hermes-agent-builtin-features-research.md`, `hermes-jalur-a-deep-dive.md`). Sumber inti: Kahneman (2011), CoALA (Sumers et al. 2023), MemGPT/Letta, Zep/Graphiti, A-MEM, Sleep-time Compute (Lin et al. 2025), FSFM/FadeMem (2026), OWASP ASI06 (2026), LongMemEval/LoCoMo, dokumentasi resmi `hermes-agent.nousresearch.com/docs`, dan dokumentasi `mem0ai`.
